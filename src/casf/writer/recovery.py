"""Fresh, bounded writer journal recovery (SPEC Sections 14 and 17; ADR-007)."""

import http.client
import math
import os
import re
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, cast

from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import SAFE_INT_MAX
from casf.errors import CasfError, InconclusiveError, SchemaError, TrustError
from casf.online import LatestView, fetch_latest, verify_latest_response
from casf.transport import ResponseLimitError
from casf.transport import request as http_request
from casf.trust.state import _secure
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
             view: LatestView, missing: list[tuple[JsonObject, JsonObject]], deadline: float,
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

    if latest_index == chain.index and (view.checkpoint != last_checkpoint
                                       or view.receipt != last_receipt):
        raise CasfError("fresh witness evidence conflicts with the accepted local journal")
    # A receipt may have arrived while the network query was in flight.
    # Any now-accepted downloaded pair must match that committed evidence.
    remaining = []
    for cp, rc in missing:
        body = cast(JsonObject, cp["body"])
        if cast(int, body["index"]) <= chain.index:
            local = con.execute(
                "SELECT c.envelope, r.envelope FROM checkpoints c JOIN receipts r "
                "ON c.checkpoint_hash=r.checkpoint_hash WHERE c.log_id=? AND c.idx=?",
                (log_id, body["index"])).fetchone()
            if local is None or writer._stored_object(local[0]) != cp \
                    or writer._stored_object(local[1]) != rc:
                raise CasfError("concurrent receipt conflicts with downloaded evidence")
        else:
            remaining.append((cp, rc))
    missing = remaining

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


@contextmanager
def recovery_lock(writer: "Writer", timeout: float) -> Iterator[None]:
    """Serialize recoveries across processes without a SQLite transaction."""
    import fcntl

    from casf.writer import BusyError

    path = str(Path(writer._db.path).resolve()) + ".recovery.lock"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        _secure(fd)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise BusyError("recovery lock time budget exhausted") from None
                time.sleep(max(0, min(0.05, deadline - time.monotonic())))
        yield
    finally:
        os.close(fd)


def hold_writer(writer: "Writer", log_id: str) -> None:
    """Commit the hold without losing a terminal record-loss seal."""
    from casf.writer import RestoreBehindWitnessError

    con = writer._db.connection
    con.execute("BEGIN IMMEDIATE")
    try:
        writer._check_heads()
        row = con.execute("SELECT sealed FROM heads WHERE log_id=?", (log_id,)).fetchone()
        if row is None:
            raise CasfError("unknown log")
        if row[0] == 1:
            raise RestoreBehindWitnessError(
                "RESTORE_BEHIND_WITNESS: recover missing records into a new verified store")
        con.execute("UPDATE heads SET sealed=3 WHERE log_id=?", (log_id,))
        con.commit()
    except BaseException:
        con.rollback()
        raise


def reconcile_witness(writer: "Writer", log_id: str, base_url: str, token: str, *,
                      timeout: float, max_chain_steps: int,
                      retained_checkpoint: tuple[int, str] | None,
                      before_resume: Callable[[LatestView], None] | None = None) -> LatestView:
    from casf.writer import RestoreBehindWitnessError

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
    with recovery_lock(writer, timeout):
        hold_writer(writer, log_id)
        count = con.execute("SELECT count FROM heads WHERE log_id=?", (log_id,)).fetchone()[0]
        row = con.execute("SELECT MAX(idx) FROM checkpoints WHERE log_id=? AND state='accepted'",
                          (log_id,)).fetchone()
        accepted_index = -1 if row[0] is None else row[0]
        deadline = time.monotonic() + timeout
        response, nonce = fetch_latest(base_url, log_id, token, timeout=_remaining(deadline))
        view = verify_latest_response(response, nonce, context.witness_key, log_id)
        body = context.anchor(view.checkpoint, view.receipt)
        _remaining(deadline)
        missing: list[tuple[JsonObject, JsonObject]] = []
        if cast(int, body["count"]) <= count:
            index = cast(int, body["index"])
            if index - accepted_index > max_chain_steps:
                raise InconclusiveError("witness reconciliation chain budget exhausted")
            cp, rc = view.checkpoint, view.receipt
            while index > accepted_index:
                _remaining(deadline)
                current = context.anchor(cp, rc)
                if current["index"] != index:
                    raise CasfError("intervening checkpoint index is inconsistent")
                missing.append((cp, rc))
                index -= 1
                if index > accepted_index:
                    cp, rc = _lookup(base_url, log_id, token,
                                     cast(str, current["previous_checkpoint_hash"]), deadline)
        con.execute("BEGIN IMMEDIATE")
        try:
            writer._check_heads()
            current_count, current_seal = con.execute(
                "SELECT count, sealed FROM heads WHERE log_id=?", (log_id,)).fetchone()
            if current_count != count or current_seal != 3:
                raise CasfError("local state changed during witness reconciliation")
            if cast(int, body["count"]) > count:
                con.execute("UPDATE heads SET sealed=1 WHERE log_id=?", (log_id,))
                con.commit()
                raise RestoreBehindWitnessError(
                    "RESTORE_BEHIND_WITNESS: fresh witness evidence exceeds the local record count")
            sealed = _recover(writer, log_id, context, view, missing, deadline,
                              max_chain_steps, retained_checkpoint, count)
            if before_resume is not None:
                before_resume(view)
            con.execute("UPDATE heads SET sealed=? WHERE log_id=?", (sealed, log_id))
            con.commit()
            return view
        except BaseException:
            con.rollback()
            raise
