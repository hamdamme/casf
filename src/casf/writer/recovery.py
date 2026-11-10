"""Fresh, bounded writer journal recovery (SPEC Sections 14 and 17; ADR-007)."""

import http.client
import math
import re
import time
from typing import TYPE_CHECKING, cast

from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import SAFE_INT_MAX
from casf.errors import CasfError, InconclusiveError, SchemaError, TrustError
from casf.online import LatestView, fetch_latest, verify_latest_response
from casf.transport import ResponseLimitError
from casf.transport import request as http_request
from casf.types import JsonObject
from casf.writer.validation import CheckpointChain, ManifestContext

if TYPE_CHECKING:
    from casf.writer import Writer


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise InconclusiveError("witness reconciliation time budget exhausted")
    return remaining


def _lookup(base_url: str, log_id: str, token: str, digest: str,
            deadline: float) -> tuple[JsonObject, JsonObject]:
    try:
        status, payload = http_request(
            base_url, "GET", f"/v1/logs/{log_id}/receipts/{digest}", token, b"",
            timeout=_remaining(deadline))
    except (OSError, http.client.HTTPException, ResponseLimitError) as exc:
        raise InconclusiveError("intervening witness evidence is unavailable") from exc
    if status != 200:
        raise InconclusiveError("intervening witness evidence is unavailable")
    value = parse(payload)
    if not isinstance(value, dict) or set(value) != {"checkpoint", "receipt"} \
            or not isinstance(value["checkpoint"], dict) \
            or not isinstance(value["receipt"], dict):
        raise SchemaError("receipt lookup must return checkpoint and receipt objects")
    if value["checkpoint"].get("checkpoint_hash") != digest:
        raise CasfError("receipt lookup returned a different checkpoint")
    return value["checkpoint"], value["receipt"]


def _recover(writer: "Writer", log_id: str, context: ManifestContext,
             view: LatestView, base_url: str, token: str, deadline: float,
             max_chain_steps: int, retained: tuple[int, str] | None, count: int) -> int:
    """Validate the complete journal before applying changes in the caller's transaction."""
    con = writer._db.connection
    chain = CheckpointChain(context, lambda n: writer._record_head(log_id, context, n), count)
    retained_seen = retained is None
    last_checkpoint = last_receipt = None
    for cp_blob, rc_blob in con.execute(
            "SELECT c.envelope, r.envelope FROM checkpoints c JOIN receipts r "
            "ON c.checkpoint_hash=r.checkpoint_hash "
            "WHERE c.log_id=? AND c.state='accepted' ORDER BY c.idx", (log_id,)):
        last_checkpoint, last_receipt = (writer._stored_object(cp_blob),
                                         writer._stored_object(rc_blob))
        body = chain.checkpoint(last_checkpoint)
        chain.receipt(last_receipt, body)
        retained_seen |= retained == (chain.index, chain.digest)

    latest_index = cast(int, view.body["checkpoint_index"])
    if latest_index < chain.index:
        raise CasfError("witness state is behind the accepted local journal")
    if retained is not None and latest_index < retained[0]:
        raise CasfError("witness state is behind the retained checkpoint")
    if latest_index - chain.index > max_chain_steps:
        raise InconclusiveError("witness reconciliation chain budget exhausted")

    missing: list[tuple[JsonObject, JsonObject]] = []
    cp, rc = view.checkpoint, view.receipt
    index = latest_index
    while index > chain.index:
        _remaining(deadline)
        body = context.anchor(cp, rc)
        if body["index"] != index:
            raise CasfError("intervening checkpoint index is inconsistent")
        missing.append((cp, rc))
        index -= 1
        if index > chain.index:
            cp, rc = _lookup(base_url, log_id, token,
                             cast(str, body["previous_checkpoint_hash"]), deadline)
    if not missing and (cp != last_checkpoint or rc != last_receipt):
        raise CasfError("fresh witness evidence conflicts with the accepted local journal")

    for cp, rc in reversed(missing):
        body = chain.checkpoint(cp)
        chain.receipt(rc, body)
        retained_seen |= retained == (chain.index, chain.digest)
        local = con.execute(
            "SELECT envelope, state FROM checkpoints WHERE log_id=? AND idx=?",
            (log_id, chain.index)).fetchone()
        if local is not None \
                and (local[1] != "pending" or writer._stored_object(local[0]) != cp):
            raise CasfError("fresh witness checkpoint conflicts with the local pending journal")
        # These writes are still private to the transaction. Any later failure
        # rolls back all recovered pairs; the earlier durable hold remains.
        if local is None:
            con.execute("INSERT INTO checkpoints VALUES (?, ?, ?, ?, ?, 'accepted')",
                        (log_id, chain.index, chain.count, chain.digest, canonicalize(cp)))
        else:
            con.execute("UPDATE checkpoints SET state='accepted' WHERE log_id=? AND idx=?",
                        (log_id, chain.index))
            con.execute("DELETE FROM outbox WHERE log_id=?", (log_id,))
        con.execute("INSERT INTO receipts VALUES (?, ?)", (chain.digest, canonicalize(rc)))
        writer._debug_hook("after_reconciled_pair")
    if not retained_seen:
        raise CasfError("verified journal does not contain the retained checkpoint")

    pending = writer.pending_checkpoint(log_id)
    if pending is not None:
        chain.checkpoint(pending[0])
    sealed = 2 if chain.final else 0
    writer._check_journal(log_id, context, count, sealed)
    _remaining(deadline)
    return sealed


def reconcile_witness(writer: "Writer", log_id: str, base_url: str, token: str, *,
                      timeout: float, max_chain_steps: int,
                      retained_checkpoint: tuple[int, str] | None) -> LatestView:
    from casf.writer import BusyError, RestoreBehindWitnessError

    if writer._trust_pins is None:
        raise TrustError("witness reconciliation requires independent trust pins")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) \
            or not math.isfinite(timeout) or timeout <= 0:
        raise SchemaError("reconciliation timeout must be positive and finite")
    if type(max_chain_steps) is not int or not 1 <= max_chain_steps <= SAFE_INT_MAX:
        raise SchemaError("reconciliation chain budget must be a positive safe integer")
    if retained_checkpoint is not None:
        if not isinstance(retained_checkpoint, tuple) or len(retained_checkpoint) != 2:
            raise SchemaError("retained checkpoint must be an index and digest pair")
        index, digest = retained_checkpoint
        if type(index) is not int or not 0 <= index <= SAFE_INT_MAX \
                or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise SchemaError("retained checkpoint index or digest is invalid")
    context = writer._manifest_context(writer.manifest_envelope(log_id))
    con = writer._db.connection
    # A competing reconciliation can finish between committing the hold and
    # reacquiring the write lock. Rearm it before any network work in that case.
    # Never normalize a corrupt preexisting seal before local validation.
    for _ in range(4):
        con.execute("BEGIN IMMEDIATE")
        try:
            writer._check_heads()
            row = con.execute("SELECT sealed FROM heads WHERE log_id=?", (log_id,)).fetchone()
            if row is None:
                raise CasfError("unknown log")
            if row[0] == 1:
                raise RestoreBehindWitnessError(
                    "RESTORE_BEHIND_WITNESS: recover missing records into a new verified store")
            if row[0] == 3:
                break
            con.execute("UPDATE heads SET sealed=3 WHERE log_id=?", (log_id,))
            con.commit()
        except BaseException:
            con.rollback()
            raise
    else:
        raise BusyError("competing reconciliations exhausted the lock retry budget")
    try:
        count = con.execute("SELECT count FROM heads WHERE log_id=?", (log_id,)).fetchone()[0]
        deadline = time.monotonic() + timeout
        response, nonce = fetch_latest(base_url, log_id, token, timeout=_remaining(deadline))
        view = verify_latest_response(response, nonce, context.witness_key, log_id)
        body = context.anchor(view.checkpoint, view.receipt)
        _remaining(deadline)
        if cast(int, body["count"]) > count:
            con.execute("UPDATE heads SET sealed=1 WHERE log_id=?", (log_id,))
            con.commit()
            raise RestoreBehindWitnessError(
                "RESTORE_BEHIND_WITNESS: fresh witness evidence exceeds the local record count")
        sealed = _recover(writer, log_id, context, view, base_url, token, deadline,
                          max_chain_steps, retained_checkpoint, count)
        con.execute("UPDATE heads SET sealed=? WHERE log_id=?", (sealed, log_id))
        con.commit()
        return view
    except BaseException:
        con.rollback()
        raise
