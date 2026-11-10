"""Independent verification from public trust material (SPEC §15).

This module never imports writer, storage, or HTTP code and never
accepts private keys. It checks a manifest envelope, a record stream,
and optionally checkpoint, receipt, and status envelopes, and reports
per dimension results with exact failure positions (R03, R07).

Invalid evidence produces FAIL; unavailable evidence produces INCONCLUSIVE.
Both retain diagnostic codes. Exceptions from caller supplied iterators
propagate; callers must handle reading failures before accepting a report.
Programmer errors (wrong Python types) still raise.
"""

from collections.abc import Callable, Iterable
from itertools import islice
from typing import Any

from casf import crypto
from casf.canonical.limits import MAX_CHECKPOINT_CHAIN_STEPS, SAFE_INT_MAX
from casf.errors import (
    CasfError,
    InconclusiveError,
    SchemaError,
)
from casf.model.schema import validate_protocol_body
from casf.types import JsonObject
from casf.verifier.report import (
    AnchorStatus,
    Dimension,
    FreshnessStatus,
    Mode,
    ProtocolStatus,
    Report,
    Result,
    TrustPins,
    TrustStatus,
)

__all__ = [
    "AnchorStatus",
    "Dimension",
    "FreshnessStatus",
    "Mode",
    "ProtocolStatus",
    "Report",
    "Result",
    "TrustPins",
    "TrustStatus",
    "verify",
]

ZERO = "0" * 64
MAX_CHECKPOINT_EXTENSION = 128  # SPEC §12


def _expect_envelope(env: JsonObject, hash_field: str) -> tuple[JsonObject, str, str]:
    """Check the exact {body, <hash_field>, signature} envelope shape."""
    if set(env) != {"body", hash_field, "signature"}:
        raise SchemaError(f"envelope must be exactly body, {hash_field}, signature")
    body, digest_hex, sig = env["body"], env[hash_field], env["signature"]
    if not isinstance(body, dict) or not isinstance(digest_hex, str) \
            or not isinstance(sig, str):
        raise SchemaError("envelope field types are wrong")
    return body, digest_hex, sig


def _field_str(body: JsonObject, name: str) -> str:
    value = body[name]
    if not isinstance(value, str):
        raise SchemaError(f"{name}: expected string")
    return value


def _field_int(body: JsonObject, name: str) -> int:
    value = body[name]
    if type(value) is not int:
        raise SchemaError(f"{name}: expected integer")
    return value


def verify(manifest_envelope: JsonObject,
           records: Iterable[JsonObject],
           pins: TrustPins,
           mode: Mode = Mode.INTEGRITY,
           checkpoint_envelopes: Iterable[JsonObject] = (),
           receipt_envelopes: Iterable[JsonObject] = (),
           status_envelopes: Iterable[JsonObject] = (),
           allow_unwitnessed: bool = False,
           online_query: Callable[[], Any] | None = None,
           retained_checkpoint: tuple[int, str] | None = None,
           retained_revoked: bool = False,
           max_chain_steps: int = MAX_CHECKPOINT_CHAIN_STEPS,
           max_records: int = 1_000_000) -> Report:
    """Verify evidence using only pinned public trust (SPEC §15).

    Online mode additionally calls online_query, a callable returning
    a fresh witness view (see casf.online.query_latest), and compares
    it to the evidence and the retained high water checkpoint.

    Records are consumed once. Anchored and online modes buffer at most
    max_chain_steps + 1 checkpoint envelopes before reading records and keep
    only the digests at their requested record counts. Iterator exceptions
    propagate, and checkpoint iterators must be independent of record iteration.
    """
    if type(max_chain_steps) is not int or max_chain_steps < 1:
        raise ValueError("max_chain_steps must be a positive integer")
    if type(pins.minimum_status_serial) is not int or pins.minimum_status_serial < 1:
        raise ValueError("minimum_status_serial must be a positive integer")
    if type(max_records) is not int or max_records < 1:
        raise ValueError("max_records must be a positive integer")
    if type(retained_revoked) is not bool:
        raise ValueError("retained_revoked must be boolean")
    revoked = retained_revoked
    codes: list[str] = []
    report = Report(
        mode=mode, result=Result.PASS,
        protocol_status=ProtocolStatus.VALID, signature_status=Dimension.NOT_CHECKED,
        chain_status=Dimension.NOT_CHECKED, trust_status=TrustStatus.UNKNOWN,
        anchor_status=AnchorStatus.NONE if mode is Mode.INTEGRITY else AnchorStatus.INCOMPLETE,
        freshness_status=FreshnessStatus.INCONCLUSIVE if mode is Mode.ONLINE
        else FreshnessStatus.NOT_REQUESTED,
        verified_from=0, verified_through=0, unwitnessed_count=None,
        witnessed_through=None, first_failure_seq=None,
        diagnostic_codes=codes,
        assumptions={
            "authority_trust": "caller_provisioned",
            "status_currentness": "supplied_statements_only",
            "witness_honesty_required": mode is not Mode.INTEGRITY,
            "allow_unwitnessed": allow_unwitnessed,
            "minimum_status_serial": pins.minimum_status_serial,
            "retained_checkpoint_supplied": retained_checkpoint is not None,
            "retained_revoked": retained_revoked,
            "max_records": max_records, "max_chain_steps": max_chain_steps,
        })

    def fail(code: str, seq: int | None = None) -> None:
        report.result = Result.FAIL
        if code not in codes:
            codes.append(code)
        if seq is not None and report.first_failure_seq is None:
            report.first_failure_seq = seq

    def inconclusive(code: str) -> None:
        if report.result is not Result.FAIL:
            report.result = Result.INCONCLUSIVE
        if code not in codes:
            codes.append(code)

    def supported(body: JsonObject, seq: int | None = None) -> bool:
        version = body.get("version")
        if type(version) is int and 1 < version <= SAFE_INT_MAX:
            fail("VERSION_UNSUPPORTED", seq)
            if report.protocol_status is not ProtocolStatus.INVALID:
                report.protocol_status = ProtocolStatus.UNSUPPORTED
            return False
        return True  # Missing, boolean and invalid integers fail schema validation.

    def complete_checks(*, signatures_checked: bool = True) -> None:
        if signatures_checked and report.signature_status is Dimension.NOT_CHECKED:
            report.signature_status = Dimension.VALID
        if report.chain_status is Dimension.NOT_CHECKED:
            report.chain_status = Dimension.VALID

    def set_trust(status: TrustStatus) -> None:
        report.trust_status = TrustStatus.REVOKED if revoked else status

    if revoked:
        fail("STATUS_REVOKED_RETAINED")
        set_trust(TrustStatus.REVOKED)

    # -------------------------------------------------- manifest and trust
    try:
        body, manifest_hash, manifest_sig = _expect_envelope(
            manifest_envelope, "manifest_hash")
    except CasfError:
        fail("MANIFEST_SCHEMA")
        report.protocol_status = ProtocolStatus.INVALID
        set_trust(TrustStatus.UNKNOWN)
        return report
    if not supported(body):
        return report
    try:
        validate_protocol_body("manifest", body)
    except CasfError:
        fail("MANIFEST_SCHEMA")
        report.protocol_status = ProtocolStatus.INVALID
        set_trust(TrustStatus.UNKNOWN)
        return report

    issuer_id = _field_str(body, "issuer_id")
    authority_key = pins.authority_keys.get(issuer_id)
    if authority_key is None:
        inconclusive("ISSUER_UNTRUSTED")
        return report
    if crypto.key_id(authority_key) != issuer_id:
        fail("ISSUER_KEY_ID_MISMATCH")
        set_trust(TrustStatus.CONFLICT)
        return report
    try:
        crypto.verify_manifest(authority_key, body, manifest_sig)
    except CasfError:
        fail("MANIFEST_SIGNATURE")
        report.signature_status = Dimension.INVALID
        set_trust(TrustStatus.CONFLICT)
        return report
    if crypto.digest_manifest(body) != manifest_hash:
        fail("MANIFEST_HASH_MISMATCH")
        report.protocol_status = ProtocolStatus.INVALID
        return report
    if _field_str(body, "log_id") != pins.log_id:
        fail("LOG_ID_MISMATCH")
        set_trust(TrustStatus.CONFLICT)
        return report
    if pins.manifest_hash is not None and manifest_hash != pins.manifest_hash:
        fail("MANIFEST_REPLACED")
        set_trust(TrustStatus.CONFLICT)
        return report

    try:
        log_raw = crypto.b64url_decode(_field_str(body, "log_public_key"))
        witness_raw = crypto.b64url_decode(_field_str(body, "witness_public_key"))
        crypto.load_public_key(log_raw)
        crypto.load_public_key(witness_raw)
    except CasfError:
        fail("MANIFEST_KEY_SCHEMA")
        report.protocol_status = ProtocolStatus.INVALID
        return report
    if crypto.key_id(log_raw) != _field_str(body, "log_key_id"):
        fail("LOG_KEY_ID_MISMATCH")
        set_trust(TrustStatus.CONFLICT)
        return report
    witness_id = _field_str(body, "witness_id")
    if crypto.key_id(witness_raw) != witness_id:
        fail("WITNESS_KEY_ID_MISMATCH")
        set_trust(TrustStatus.CONFLICT)
        return report
    pinned_witness = pins.witness_keys.get(witness_id)
    if pinned_witness is not None and pinned_witness != witness_raw:
        fail("WITNESS_PIN_CONFLICT")
        set_trust(TrustStatus.CONFLICT)
        return report
    witness_trust_missing = mode is not Mode.INTEGRITY and pinned_witness is None
    if witness_trust_missing:
        inconclusive("WITNESS_UNTRUSTED")

    # ---------------------------------------------------- status statements
    accepted_status = False
    invalid_status = False
    stale_status = False
    for status_index, env in enumerate(status_envelopes):
        if status_index >= max_chain_steps:
            report.result = Result.FAIL if report.result is Result.FAIL else Result.INCONCLUSIVE
            set_trust(TrustStatus.UNKNOWN)
            codes.append("STATUS_BUDGET_EXCEEDED")
            return report
        try:
            sbody, ssig = _expect_status_envelope(env)
            if not supported(sbody):
                invalid_status = True
                continue
            validate_protocol_body("status", sbody)
            if sbody["status"] not in ("active", "revoked"):
                raise SchemaError("unknown authority status")
        except CasfError:
            fail("STATUS_SCHEMA")
            report.protocol_status = ProtocolStatus.INVALID
            invalid_status = True
            set_trust(TrustStatus.UNKNOWN)
            continue
        if _field_str(sbody, "manifest_hash") != manifest_hash:
            continue
        if _field_str(sbody, "issuer_id") != issuer_id:
            fail("STATUS_ISSUER")
            invalid_status = True
            set_trust(TrustStatus.CONFLICT)
            continue
        try:
            crypto.verify_status(authority_key, sbody, ssig)
        except CasfError:
            fail("STATUS_SIGNATURE")
            report.signature_status = Dimension.INVALID
            invalid_status = True
            set_trust(TrustStatus.UNKNOWN)
            continue
        # Revocation is terminal even if a newer active statement is supplied.
        if _field_str(sbody, "status") == "revoked":
            revoked = True
            fail("STATUS_REVOKED")
        report.observed_status_serial = max(
            report.observed_status_serial, _field_int(sbody, "serial"))
        if _field_int(sbody, "serial") < pins.minimum_status_serial:
            inconclusive("STATUS_SERIAL_LOW")
            stale_status = True
            continue
        accepted_status = True
    if not accepted_status:
        if report.observed_status_serial:
            inconclusive("STATUS_SERIAL_LOW")
        inconclusive("STATUS_MISSING")
    if accepted_status and not revoked:
        codes.append("STATUS_CURRENTNESS_UNCONFIRMED")
        if not invalid_status and not stale_status and not witness_trust_missing:
            set_trust(TrustStatus.TRUSTED)
    if revoked:
        set_trust(TrustStatus.REVOKED)

    # --------------------------------------------------------- record stream
    genesis = crypto.genesis_hash(manifest_hash)
    expected_prev = genesis
    # Only checkpoint boundaries need historical digests. Buffer at most the
    # configured protocol budget plus a sentinel, never the record history.
    # Validation stays below the record loop to preserve failure precedence.
    checkpoint_input = (list(islice(checkpoint_envelopes, max_chain_steps + 1))
                        if mode is not Mode.INTEGRITY else [])
    head_targets: set[int] = set()
    for candidate in checkpoint_input[:max_chain_steps]:
        candidate_body = candidate.get("body")
        if isinstance(candidate_body, dict):
            candidate_count = candidate_body.get("count")
            if type(candidate_count) is int and 0 < candidate_count <= max_records:
                head_targets.add(candidate_count)
    verified_heads: dict[int, str] = {}
    verified_count = 0
    records_complete = False
    for seq, env in enumerate(records, start=1):
        if seq > max_records:
            report.verified_through = verified_count
            if report.result is not Result.FAIL:
                report.result = Result.INCONCLUSIVE
            codes.append("RECORD_BUDGET_EXCEEDED")
            return report
        try:
            rbody, record_hash, rsig = _expect_envelope(env, "record_hash")
            if not supported(rbody, seq):
                break
            validate_protocol_body("record", rbody)
        except CasfError:
            fail("RECORD_SCHEMA", seq)
            report.protocol_status = ProtocolStatus.INVALID
            break
        if _field_str(rbody, "log_id") != pins.log_id \
                or _field_str(rbody, "manifest_hash") != manifest_hash \
                or _field_str(rbody, "key_id") != _field_str(body, "log_key_id"):
            fail("LOG_BINDING", seq)
            report.chain_status = Dimension.INVALID
            break
        if _field_int(rbody, "seq") != seq:
            fail("SEQ_GAP", seq)
            report.chain_status = Dimension.INVALID
            break
        if _field_str(rbody, "prev_hash") != expected_prev:
            fail("CHAIN_BREAK", seq)
            report.chain_status = Dimension.INVALID
            break
        if crypto.digest_record(rbody) != record_hash:
            fail("RECORD_HASH_MISMATCH", seq)
            report.protocol_status = ProtocolStatus.INVALID
            break
        try:
            crypto.verify_record(log_raw, rbody, rsig)
        except CasfError:
            fail("RECORD_SIGNATURE", seq)
            report.signature_status = Dimension.INVALID
            break
        verified_count = seq
        report.verified_from = 1
        if seq in head_targets:
            verified_heads[seq] = record_hash
        expected_prev = record_hash
    else:
        records_complete = True
    report.verified_through = verified_count
    if mode is Mode.INTEGRITY:
        if records_complete:
            complete_checks(signatures_checked=not invalid_status)
        return report
    if report.result is Result.FAIL:
        return report

    # ------------------------------------------------- checkpoints (anchored)
    checkpoints: list[tuple[JsonObject, str]] = []
    prev_cp = ZERO
    prev_count = 0
    prev_head = genesis
    for index, env in enumerate(checkpoint_input):
        if index >= max_chain_steps:
            report.result = Result.INCONCLUSIVE
            report.anchor_status = AnchorStatus.INCOMPLETE
            codes.append("CHAIN_BUDGET_EXCEEDED")
            return report
        try:
            cbody, checkpoint_hash, csig = _expect_envelope(env, "checkpoint_hash")
            if not supported(cbody):
                return report
            validate_protocol_body("checkpoint", cbody)
        except CasfError:
            fail("CHECKPOINT_SCHEMA")
            report.protocol_status = ProtocolStatus.INVALID
            return report
        if _field_str(cbody, "log_id") != pins.log_id \
                or _field_str(cbody, "manifest_hash") != manifest_hash \
                or _field_str(cbody, "key_id") != _field_str(body, "log_key_id"):
            fail("CHECKPOINT_BINDING")
            report.chain_status = Dimension.INVALID
            return report
        if _field_int(cbody, "index") != index:
            fail("CHECKPOINT_INDEX_GAP")
            report.chain_status = Dimension.INVALID
            return report
        if _field_str(cbody, "previous_checkpoint_hash") != prev_cp:
            fail("CHECKPOINT_CHAIN_BREAK")
            report.chain_status = Dimension.INVALID
            return report
        count = _field_int(cbody, "count")
        head = _field_str(cbody, "head_hash")
        if count < prev_count or count - prev_count > MAX_CHECKPOINT_EXTENSION:
            fail("CHECKPOINT_COUNT_RULE")
            report.chain_status = Dimension.INVALID
            return report
        if count == prev_count and head != prev_head:
            fail("CHECKPOINT_HEAD_CHANGED")
            report.chain_status = Dimension.INVALID
            return report
        expected_head = genesis if count == 0 else (
            verified_heads.get(count) if count <= verified_count else None)
        if crypto.digest_checkpoint(cbody) != checkpoint_hash:
            fail("CHECKPOINT_HASH_MISMATCH")
            report.protocol_status = ProtocolStatus.INVALID
            return report
        try:
            crypto.verify_checkpoint(log_raw, cbody, csig)
        except CasfError:
            fail("CHECKPOINT_SIGNATURE")
            report.signature_status = Dimension.INVALID
            return report
        if expected_head is not None and head != expected_head:
            report.anchor_status = AnchorStatus.DIVERGENT
            fail("ANCHOR_DIVERGENT")
            return report
        checkpoints.append((cbody, checkpoint_hash))
        prev_cp, prev_count, prev_head = checkpoint_hash, count, head

    # ------------------------------------------------------ receipts
    receipts: list[JsonObject] = []
    prev_rc = ZERO
    for receipt_index, env in enumerate(receipt_envelopes):
        if receipt_index >= max_chain_steps:
            report.result = Result.INCONCLUSIVE
            report.anchor_status = AnchorStatus.INCOMPLETE
            codes.append("CHAIN_BUDGET_EXCEEDED")
            return report
        try:
            rbody2, receipt_hash, rsig2 = _expect_envelope(env, "receipt_hash")
            if not supported(rbody2):
                return report
            validate_protocol_body("receipt", rbody2)
        except CasfError:
            fail("RECEIPT_SCHEMA")
            report.protocol_status = ProtocolStatus.INVALID
            return report
        if _field_str(rbody2, "witness_id") != witness_id \
                or _field_str(rbody2, "log_id") != pins.log_id \
                or _field_str(rbody2, "manifest_hash") != manifest_hash:
            fail("RECEIPT_BINDING")
            report.chain_status = Dimension.INVALID
            return report
        if _field_str(rbody2, "previous_receipt_hash") != prev_rc:
            fail("RECEIPT_CHAIN_BREAK")
            report.chain_status = Dimension.INVALID
            return report
        if crypto.digest_receipt(rbody2) != receipt_hash:
            fail("RECEIPT_HASH_MISMATCH")
            report.protocol_status = ProtocolStatus.INVALID
            return report
        if pinned_witness is None:
            inconclusive("WITNESS_UNTRUSTED")
            set_trust(TrustStatus.UNKNOWN)
            return report
        try:
            crypto.verify_receipt(pinned_witness, rbody2, rsig2)
        except CasfError:
            fail("RECEIPT_SIGNATURE")
            report.signature_status = Dimension.INVALID
            return report
        receipts.append(rbody2)
        prev_rc = receipt_hash

    if not checkpoints:
        inconclusive("ANCHOR_MISSING")
        report.anchor_status = AnchorStatus.INCOMPLETE
        return report

    anchor_body, anchor_hash = checkpoints[-1]
    anchor_count = _field_int(anchor_body, "count")
    matching = [r for r in receipts
                if _field_str(r, "checkpoint_hash") == anchor_hash]
    if receipts and not matching:
        fail("RECEIPT_CHECKPOINT_MISMATCH")
        report.chain_status = Dimension.INVALID
        return report
    if not receipts:
        inconclusive("RECEIPT_MISSING")
        report.anchor_status = AnchorStatus.INCOMPLETE
        return report

    if verified_count < anchor_count:
        report.anchor_status = AnchorStatus.INCOMPLETE
        fail("ANCHOR_INCOMPLETE")
        return report
    if _field_int(anchor_body, "count") > 0 and \
            verified_heads[anchor_count] != _field_str(anchor_body, "head_hash"):
        report.anchor_status = AnchorStatus.DIVERGENT
        fail("ANCHOR_DIVERGENT")
        return report

    complete_checks()
    report.witnessed_through = anchor_count
    report.unwitnessed_count = verified_count - anchor_count
    if report.unwitnessed_count > 0:
        report.anchor_status = AnchorStatus.PARTIAL_ANCHOR
        if not allow_unwitnessed:
            fail("UNWITNESSED_SUFFIX")
            return report
    else:
        report.anchor_status = AnchorStatus.MATCHED

    # A newer index alone cannot prove continuity with retained history.
    # The validated chain must include the previously accepted checkpoint.
    if retained_checkpoint is not None:
        kept_index, kept_hash = retained_checkpoint
        if (kept_index < 0 or kept_index >= len(checkpoints)
                or checkpoints[kept_index][1] != kept_hash):
            report.anchor_status = AnchorStatus.DIVERGENT
            if mode is Mode.ONLINE:
                report.freshness_status = FreshnessStatus.CONFLICT
            fail("WITNESS_STATE_CONFLICT")
            return report
    report.checkpoint = (_field_int(anchor_body, "index"), anchor_hash)
    if mode is not Mode.ONLINE:
        return report

    # ------------------------------------------------ freshness (online)
    if online_query is None:
        raise CasfError("online mode requires an online_query callable")
    anchor_index = _field_int(anchor_body, "index")
    try:
        view = online_query()
    except InconclusiveError:
        report.freshness_status = FreshnessStatus.INCONCLUSIVE
        report.result = Result.INCONCLUSIVE
        codes.append("FRESHNESS_INCONCLUSIVE")
        return report
    except CasfError:
        # An unsigned error, including NO_CHECKPOINT, cannot prove rollback.
        report.freshness_status = FreshnessStatus.INCONCLUSIVE
        report.result = Result.INCONCLUSIVE
        codes.append("FRESHNESS_INCONCLUSIVE")
        return report
    view_body = view.body
    view_index = _field_int(view_body, "checkpoint_index")
    view_hash = _field_str(view_body, "checkpoint_hash")
    if retained_checkpoint is not None:
        kept_index, kept_hash = retained_checkpoint
        if view_index < kept_index \
                or (view_index == kept_index and view_hash != kept_hash):
            report.freshness_status = FreshnessStatus.CONFLICT
            fail("WITNESS_STATE_CONFLICT")
            return report
    if view_index < anchor_index \
            or (view_index == anchor_index and view_hash != anchor_hash):
        report.freshness_status = FreshnessStatus.CONFLICT
        fail("WITNESS_STATE_CONFLICT")
        return report
    if view_index > anchor_index:
        # the witness advanced; the intervening chain must be supplied
        # before the local pin may move (SPEC §15)
        report.freshness_status = FreshnessStatus.INCONCLUSIVE
        report.result = Result.INCONCLUSIVE
        codes.append("WITNESS_AHEAD")
        return report
    report.freshness_status = FreshnessStatus.FRESH_WITNESS_VIEW
    return report


def _expect_status_envelope(env: JsonObject) -> tuple[JsonObject, str]:
    """Status envelopes are exactly {body, signature} (SPEC §16)."""
    if set(env) != {"body", "signature"}:
        raise SchemaError("status envelope must be exactly body and signature")
    body, sig = env["body"], env["signature"]
    if not isinstance(body, dict) or not isinstance(sig, str):
        raise SchemaError("status envelope field types are wrong")
    return body, sig
