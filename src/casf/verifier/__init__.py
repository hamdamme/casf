"""Independent verification from public trust material (SPEC §15).

This module never imports writer, storage, or HTTP code and never
accepts private keys. It checks a manifest envelope, a record stream,
and optionally checkpoint, receipt, and status envelopes, and reports
per dimension results with exact failure positions (R03, R07).

Evidence problems produce a FAIL report with diagnostic codes; they do
not raise. Programmer errors (wrong Python types) still raise.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from casf import crypto
from casf.canonical.limits import MAX_CHECKPOINT_CHAIN_STEPS
from casf.errors import (
    CasfError,
    InconclusiveError,
    SchemaError,
)
from casf.model.schema import validate_protocol_body
from casf.types import JsonObject

__all__ = [
    "AnchorStatus",
    "FreshnessStatus",
    "Mode",
    "Report",
    "Result",
    "TrustPins",
    "TrustStatus",
    "verify",
]

ZERO = "0" * 64
MAX_CHECKPOINT_EXTENSION = 128  # SPEC §12


class Mode(str, Enum):
    INTEGRITY = "integrity"
    ANCHORED = "anchored"
    ONLINE = "online"


class Result(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class FreshnessStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    FRESH_WITNESS_VIEW = "FRESH_WITNESS_VIEW"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONFLICT = "CONFLICT"


class TrustStatus(str, Enum):
    OK = "OK"
    UNTRUSTED = "UNTRUSTED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class AnchorStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    OK = "OK"
    INCOMPLETE = "INCOMPLETE"
    DIVERGENT = "DIVERGENT"
    PARTIAL_ANCHOR = "PARTIAL_ANCHOR"


class Dimension(str, Enum):
    OK = "OK"
    FAIL = "FAIL"
    NOT_CHECKED = "NOT_CHECKED"


@dataclass(frozen=True)
class TrustPins:
    """Independently provisioned trust material (SPEC §10, §15)."""
    authority_keys: dict[str, bytes]   # issuer_id -> raw public key
    witness_keys: dict[str, bytes]     # witness_id -> raw public key
    log_id: str
    manifest_hash: str | None = None   # expected manifest digest, if pinned
    minimum_status_serial: int = 1


@dataclass
class Report:
    mode: Mode
    result: Result
    protocol_status: Dimension
    signature_status: Dimension
    chain_status: Dimension
    trust_status: TrustStatus
    anchor_status: AnchorStatus
    verified_from: int
    verified_through: int
    unwitnessed_count: int
    witnessed_through: int | None
    first_failure_seq: int | None
    diagnostic_codes: list[str] = field(default_factory=list)
    freshness_status: FreshnessStatus = FreshnessStatus.NOT_REQUESTED


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
           max_chain_steps: int = MAX_CHECKPOINT_CHAIN_STEPS,
           max_records: int = 1_000_000) -> Report:
    """Verify evidence using only pinned public trust (SPEC §15).

    Online mode additionally calls online_query, a callable returning
    a fresh witness view (see casf.online.query_latest), and compares
    it to the evidence and the retained high water checkpoint."""
    if type(max_chain_steps) is not int or max_chain_steps < 1:
        raise ValueError("max_chain_steps must be a positive integer")
    if type(pins.minimum_status_serial) is not int or pins.minimum_status_serial < 1:
        raise ValueError("minimum_status_serial must be a positive integer")
    if type(max_records) is not int or max_records < 1:
        raise ValueError("max_records must be a positive integer")
    codes: list[str] = []
    report = Report(
        mode=mode, result=Result.PASS,
        protocol_status=Dimension.OK, signature_status=Dimension.OK,
        chain_status=Dimension.OK, trust_status=TrustStatus.OK,
        anchor_status=AnchorStatus.NOT_REQUESTED if mode is Mode.INTEGRITY
        else AnchorStatus.OK,
        verified_from=1, verified_through=0, unwitnessed_count=0,
        witnessed_through=None, first_failure_seq=None,
        diagnostic_codes=codes)

    def fail(code: str, seq: int | None = None) -> None:
        report.result = Result.FAIL
        if code not in codes:
            codes.append(code)
        if seq is not None and report.first_failure_seq is None:
            report.first_failure_seq = seq

    # -------------------------------------------------- manifest and trust
    try:
        body, manifest_hash, manifest_sig = _expect_envelope(
            manifest_envelope, "manifest_hash")
    except CasfError:
        fail("MANIFEST_SCHEMA")
        report.protocol_status = Dimension.FAIL
        report.trust_status = TrustStatus.UNKNOWN
        return report
    if body.get("version") != 1:
        # Unknown versions never fall back to weaker behavior (SPEC §11).
        fail("VERSION_UNSUPPORTED")
        report.protocol_status = Dimension.FAIL
        report.trust_status = TrustStatus.UNKNOWN
        return report
    try:
        validate_protocol_body("manifest", body)
    except CasfError:
        fail("MANIFEST_SCHEMA")
        report.protocol_status = Dimension.FAIL
        report.trust_status = TrustStatus.UNKNOWN
        return report

    issuer_id = _field_str(body, "issuer_id")
    authority_key = pins.authority_keys.get(issuer_id)
    if authority_key is None:
        fail("ISSUER_UNTRUSTED")
        report.trust_status = TrustStatus.UNTRUSTED
        return report
    try:
        crypto.verify_manifest(authority_key, body, manifest_sig)
    except CasfError:
        fail("MANIFEST_SIGNATURE")
        report.signature_status = Dimension.FAIL
        report.trust_status = TrustStatus.UNTRUSTED
        return report
    if crypto.digest_manifest(body) != manifest_hash:
        fail("MANIFEST_HASH_MISMATCH")
        report.protocol_status = Dimension.FAIL
        return report
    if _field_str(body, "log_id") != pins.log_id:
        fail("LOG_ID_MISMATCH")
        report.protocol_status = Dimension.FAIL
        return report
    if pins.manifest_hash is not None and manifest_hash != pins.manifest_hash:
        fail("MANIFEST_REPLACED")
        report.trust_status = TrustStatus.UNTRUSTED
        return report

    log_raw = crypto.b64url_decode(_field_str(body, "log_public_key"))
    if crypto.key_id(log_raw) != _field_str(body, "log_key_id"):
        fail("LOG_KEY_ID_MISMATCH")
        report.trust_status = TrustStatus.UNTRUSTED
        return report
    witness_raw = crypto.b64url_decode(_field_str(body, "witness_public_key"))
    witness_id = _field_str(body, "witness_id")
    if crypto.key_id(witness_raw) != witness_id:
        fail("WITNESS_KEY_ID_MISMATCH")
        report.trust_status = TrustStatus.UNTRUSTED
        return report
    pinned_witness = pins.witness_keys.get(witness_id)

    # ---------------------------------------------------- status statements
    accepted_status = False
    revoked = False
    for status_index, env in enumerate(status_envelopes):
        if status_index >= max_chain_steps:
            report.result = Result.FAIL if report.result is Result.FAIL else Result.INCONCLUSIVE
            report.trust_status = TrustStatus.REVOKED if revoked else TrustStatus.UNKNOWN
            codes.append("STATUS_BUDGET_EXCEEDED")
            return report
        try:
            sbody, ssig = _expect_status_envelope(env)
            validate_protocol_body("status", sbody)
        except CasfError:
            fail("STATUS_SCHEMA")
            report.trust_status = TrustStatus.UNKNOWN
            continue
        if _field_str(sbody, "manifest_hash") != manifest_hash:
            continue
        if _field_str(sbody, "issuer_id") != issuer_id:
            fail("STATUS_ISSUER")
            report.trust_status = TrustStatus.UNKNOWN
            continue
        try:
            crypto.verify_status(authority_key, sbody, ssig)
        except CasfError:
            fail("STATUS_SIGNATURE")
            report.trust_status = TrustStatus.UNKNOWN
            continue
        # Revocation is terminal even if a newer active statement is supplied.
        if _field_str(sbody, "status") == "revoked":
            revoked = True
            fail("STATUS_REVOKED")
        if _field_int(sbody, "serial") < pins.minimum_status_serial:
            fail("STATUS_SERIAL_LOW")
            report.trust_status = TrustStatus.UNKNOWN
            continue
        accepted_status = True
    if not accepted_status:
        fail("STATUS_MISSING")
        report.trust_status = TrustStatus.UNKNOWN
    if accepted_status and not revoked:
        codes.append("STATUS_CURRENTNESS_UNCONFIRMED")
    if revoked:
        report.trust_status = TrustStatus.REVOKED

    # --------------------------------------------------------- record stream
    genesis = crypto.genesis_hash(manifest_hash)
    expected_prev = genesis
    verified_digests: list[str] = []
    for seq, env in enumerate(records, start=1):
        if seq > max_records:
            report.verified_through = len(verified_digests)
            if report.result is not Result.FAIL:
                report.result = Result.INCONCLUSIVE
            codes.append("RECORD_BUDGET_EXCEEDED")
            return report
        try:
            rbody, record_hash, rsig = _expect_envelope(env, "record_hash")
            if rbody.get("version") != 1:
                fail("VERSION_UNSUPPORTED", seq)
                break
            validate_protocol_body("record", rbody)
        except CasfError:
            fail("RECORD_SCHEMA", seq)
            report.protocol_status = Dimension.FAIL
            break
        if _field_str(rbody, "log_id") != pins.log_id \
                or _field_str(rbody, "manifest_hash") != manifest_hash \
                or _field_str(rbody, "key_id") != _field_str(body, "log_key_id"):
            fail("LOG_BINDING", seq)
            report.chain_status = Dimension.FAIL
            break
        if _field_int(rbody, "seq") != seq:
            fail("SEQ_GAP", seq)
            report.chain_status = Dimension.FAIL
            break
        if _field_str(rbody, "prev_hash") != expected_prev:
            fail("CHAIN_BREAK", seq)
            report.chain_status = Dimension.FAIL
            break
        if crypto.digest_record(rbody) != record_hash:
            fail("RECORD_HASH_MISMATCH", seq)
            report.protocol_status = Dimension.FAIL
            break
        try:
            crypto.verify_record(log_raw, rbody, rsig)
        except CasfError:
            fail("RECORD_SIGNATURE", seq)
            report.signature_status = Dimension.FAIL
            break
        verified_digests.append(record_hash)
        expected_prev = record_hash
    report.verified_through = len(verified_digests)
    if report.result is Result.FAIL:
        return report

    if mode is Mode.INTEGRITY:
        return report

    # ------------------------------------------------- checkpoints (anchored)
    checkpoints: list[tuple[JsonObject, str]] = []
    prev_cp = ZERO
    prev_count = 0
    prev_head = genesis
    for index, env in enumerate(checkpoint_envelopes):
        if index >= max_chain_steps:
            report.result = Result.INCONCLUSIVE
            report.anchor_status = AnchorStatus.INCOMPLETE
            codes.append("CHAIN_BUDGET_EXCEEDED")
            return report
        try:
            cbody, checkpoint_hash, csig = _expect_envelope(env, "checkpoint_hash")
            validate_protocol_body("checkpoint", cbody)
        except CasfError:
            fail("CHECKPOINT_SCHEMA")
            report.protocol_status = Dimension.FAIL
            return report
        if _field_str(cbody, "log_id") != pins.log_id \
                or _field_str(cbody, "manifest_hash") != manifest_hash \
                or _field_str(cbody, "key_id") != _field_str(body, "log_key_id"):
            fail("CHECKPOINT_BINDING")
            report.chain_status = Dimension.FAIL
            return report
        if _field_int(cbody, "index") != index:
            fail("CHECKPOINT_INDEX_GAP")
            report.chain_status = Dimension.FAIL
            return report
        if _field_str(cbody, "previous_checkpoint_hash") != prev_cp:
            fail("CHECKPOINT_CHAIN_BREAK")
            report.chain_status = Dimension.FAIL
            return report
        count = _field_int(cbody, "count")
        head = _field_str(cbody, "head_hash")
        if count < prev_count or count - prev_count > MAX_CHECKPOINT_EXTENSION:
            fail("CHECKPOINT_COUNT_RULE")
            report.chain_status = Dimension.FAIL
            return report
        if count == prev_count and head != prev_head:
            fail("CHECKPOINT_HEAD_CHANGED")
            report.chain_status = Dimension.FAIL
            return report
        expected_head = genesis if count == 0 else (
            verified_digests[count - 1] if count <= len(verified_digests) else None)
        if crypto.digest_checkpoint(cbody) != checkpoint_hash:
            fail("CHECKPOINT_HASH_MISMATCH")
            report.protocol_status = Dimension.FAIL
            return report
        try:
            crypto.verify_checkpoint(log_raw, cbody, csig)
        except CasfError:
            fail("CHECKPOINT_SIGNATURE")
            report.signature_status = Dimension.FAIL
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
            validate_protocol_body("receipt", rbody2)
        except CasfError:
            fail("RECEIPT_SCHEMA")
            report.protocol_status = Dimension.FAIL
            return report
        if _field_str(rbody2, "witness_id") != witness_id \
                or _field_str(rbody2, "log_id") != pins.log_id \
                or _field_str(rbody2, "manifest_hash") != manifest_hash:
            fail("RECEIPT_BINDING")
            report.chain_status = Dimension.FAIL
            return report
        if _field_str(rbody2, "previous_receipt_hash") != prev_rc:
            fail("RECEIPT_CHAIN_BREAK")
            report.chain_status = Dimension.FAIL
            return report
        if crypto.digest_receipt(rbody2) != receipt_hash:
            fail("RECEIPT_HASH_MISMATCH")
            report.protocol_status = Dimension.FAIL
            return report
        if pinned_witness is None:
            fail("WITNESS_UNTRUSTED")
            report.trust_status = TrustStatus.UNTRUSTED
            return report
        try:
            crypto.verify_receipt(pinned_witness, rbody2, rsig2)
        except CasfError:
            fail("RECEIPT_SIGNATURE")
            report.signature_status = Dimension.FAIL
            return report
        receipts.append(rbody2)
        prev_rc = receipt_hash

    if not checkpoints:
        fail("ANCHOR_MISSING")
        report.anchor_status = AnchorStatus.INCOMPLETE
        return report

    anchor_body, anchor_hash = checkpoints[-1]
    anchor_count = _field_int(anchor_body, "count")
    matching = [r for r in receipts
                if _field_str(r, "checkpoint_hash") == anchor_hash]
    if receipts and not matching:
        fail("RECEIPT_CHECKPOINT_MISMATCH")
        report.chain_status = Dimension.FAIL
        return report
    if not receipts:
        fail("RECEIPT_MISSING")
        report.anchor_status = AnchorStatus.INCOMPLETE
        return report

    if len(verified_digests) < anchor_count:
        report.anchor_status = AnchorStatus.INCOMPLETE
        fail("ANCHOR_INCOMPLETE")
        return report
    if _field_int(anchor_body, "count") > 0 and \
            verified_digests[anchor_count - 1] != _field_str(anchor_body, "head_hash"):
        report.anchor_status = AnchorStatus.DIVERGENT
        fail("ANCHOR_DIVERGENT")
        return report

    report.witnessed_through = anchor_count
    report.unwitnessed_count = len(verified_digests) - anchor_count
    if report.unwitnessed_count > 0:
        if allow_unwitnessed:
            report.anchor_status = AnchorStatus.PARTIAL_ANCHOR
        else:
            fail("UNWITNESSED_SUFFIX")
            return report
    else:
        report.anchor_status = AnchorStatus.OK

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
