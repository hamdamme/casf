"""Strict fixed-schema validation for all casf-v1 protocol bodies
(SPEC §10-§16).

Every fixed body has an exact field set: missing fields, unknown fields,
and parser-supplied defaults are all rejected. This module checks shape
and scalar constraints only; semantic rules (chain linkage, signatures)
live in the verifier and witness (SPEC §8).
"""

import re
from dataclasses import dataclass

from casf.canonical.limits import SAFE_INT_MAX, SAFE_INT_MIN
from casf.errors import SchemaError
from casf.types import JsonValue

# ------------------------------------------------------------ field kinds

@dataclass(frozen=True)
class Field:
    kind: str
    max_bytes: int | None = None        # for strings
    min_value: int | None = None
    max_value: int | None = None

K = Field  # alias

TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ZERO_DIGEST = "0" * 64

def _check_timestamp(value: str, field: str) -> None:
    if not TIMESTAMP_RE.match(value):
        raise SchemaError(f"{field}: invalid UTC timestamp format")
    from datetime import datetime
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as e:
        raise SchemaError(f"{field}: invalid calendar time") from e
    if not ("00" <= value[17:19] <= "59"):
        raise SchemaError(f"{field}: seconds must be 00-59 (no leap seconds)")

def _check_int(value: object, field: str, f: Field) -> None:
    if type(value) is not int:  # bool explicitly excluded
        raise SchemaError(f"{field}: expected integer")
    if not (SAFE_INT_MIN <= value <= SAFE_INT_MAX):
        raise SchemaError(f"{field}: integer outside safe range")
    if f.min_value is not None and value < f.min_value:
        raise SchemaError(f"{field}: below minimum {f.min_value}")
    if f.max_value is not None and value > f.max_value:
        raise SchemaError(f"{field}: above maximum {f.max_value}")

def validate_body(body: JsonValue, fields: dict[str, Field], where: str) -> None:
    """Validate a fixed protocol body: exact field set + per-field checks."""
    if not isinstance(body, dict):
        raise SchemaError(f"{where}: body must be an object")
    expected = set(fields)
    actual = set(body)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise SchemaError(f"{where}: missing fields: {sorted(missing)}")
    if unknown:
        raise SchemaError(f"{where}: unknown fields: {sorted(unknown)}")
    for name, f in fields.items():
        value = body[name]
        if value is None:
            if f.kind not in ("null", "predecessor"):
                raise SchemaError(f"{where}.{name}: null not allowed")
            continue
        if f.kind == "int":
            _check_int(value, f"{where}.{name}", f)
        elif f.kind == "bool":
            if type(value) is not bool:
                raise SchemaError(f"{where}.{name}: expected boolean")
        elif f.kind == "str":
            if not isinstance(value, str):
                raise SchemaError(f"{where}.{name}: expected string")
            if f.max_bytes is not None and len(value.encode("utf-8")) > f.max_bytes:
                raise SchemaError(f"{where}.{name}: string too long")
        elif f.kind == "ts":
            if not isinstance(value, str):
                raise SchemaError(f"{where}.{name}: expected timestamp string")
            _check_timestamp(value, f"{where}.{name}")
        elif f.kind == "digest":
            if not isinstance(value, str) or not DIGEST_RE.match(value):
                raise SchemaError(f"{where}.{name}: expected 64 lowercase hex digits")
        elif f.kind == "b64url":
            if not isinstance(value, str) or not B64URL_RE.match(value):
                raise SchemaError(f"{where}.{name}: expected unpadded base64url")
        elif f.kind == "uuid":
            if not isinstance(value, str) or not UUID_RE.match(value):
                raise SchemaError(f"{where}.{name}: expected lowercase UUID string")
        elif f.kind == "object":
            if not isinstance(value, dict):
                raise SchemaError(f"{where}.{name}: expected object")
        elif f.kind == "predecessor":
            _validate_predecessor(value, f"{where}.{name}")
        else:
            raise SchemaError(f"{where}.{name}: unknown field kind {f.kind}")

def _validate_predecessor(value: JsonValue, where: str) -> None:
    if not isinstance(value, dict) or set(value) != {
            "log_id", "manifest_hash", "final_checkpoint_hash", "final_receipt_hash"}:
        raise SchemaError(f"{where}: predecessor must have exactly "
                          "log_id, manifest_hash, final_checkpoint_hash, final_receipt_hash")
    validate_body(value, {
        "log_id": K("uuid"), "manifest_hash": K("digest"),
        "final_checkpoint_hash": K("digest"),
        "final_receipt_hash": K("digest")}, where)

# ------------------------------------------------- fixed body definitions

SAFE = {"min_value": SAFE_INT_MIN, "max_value": SAFE_INT_MAX}

MANIFEST_FIELDS = {
    "version": K("int", min_value=1, max_value=1),
    "type": K("str", max_bytes=16),
    "log_id": K("uuid"),
    "issuer_id": K("digest"),
    "log_key_id": K("digest"),
    "log_public_key": K("b64url"),
    "witness_id": K("digest"),
    "witness_public_key": K("b64url"),
    "created_at": K("ts"),
    "predecessor": K("predecessor"),
}

RECORD_FIELDS = {
    "version": K("int", min_value=1, max_value=1),
    "type": K("str", max_bytes=16),
    "log_id": K("uuid"),
    "manifest_hash": K("digest"),
    "seq": K("int", min_value=1),
    "event_id": K("uuid"),
    "recorded_at": K("ts"),
    "actor": K("str", max_bytes=256),
    "event_type": K("str", max_bytes=256),
    "payload": K("object"),
    "attributes": K("object"),
    "prev_hash": K("digest"),
    "key_id": K("digest"),
}

CHECKPOINT_FIELDS = {
    "version": K("int", min_value=1, max_value=1),
    "type": K("str", max_bytes=16),
    "log_id": K("uuid"),
    "manifest_hash": K("digest"),
    "index": K("int", min_value=0),
    "count": K("int", min_value=0),
    "head_hash": K("digest"),
    "previous_checkpoint_hash": K("digest"),
    "key_id": K("digest"),
    "issued_at": K("ts"),
    "final": K("bool"),
}

RECEIPT_FIELDS = {
    "version": K("int", min_value=1, max_value=1),
    "type": K("str", max_bytes=16),
    "witness_id": K("digest"),
    "log_id": K("uuid"),
    "manifest_hash": K("digest"),
    "checkpoint_hash": K("digest"),
    "checkpoint_index": K("int", min_value=0),
    "count": K("int", min_value=0),
    "head_hash": K("digest"),
    "previous_receipt_hash": K("digest"),
    "accepted_at": K("ts"),
}

LATEST_FIELDS = {
    "version": K("int", min_value=1, max_value=1),
    "type": K("str", max_bytes=16),
    "nonce": K("b64url"),
    "witness_id": K("digest"),
    "log_id": K("uuid"),
    "manifest_hash": K("digest"),
    "checkpoint_hash": K("digest"),
    "receipt_hash": K("digest"),
    "checkpoint_index": K("int", min_value=0),
    "count": K("int", min_value=0),
    "head_hash": K("digest"),
    "final": K("bool"),
    "responded_at": K("ts"),
}

STATUS_FIELDS = {
    "version": K("int", min_value=1, max_value=1),
    "type": K("str", max_bytes=16),
    "issuer_id": K("digest"),
    "serial": K("int", min_value=1),
    "manifest_hash": K("digest"),
    "status": K("str", max_bytes=16),
    "issued_at": K("ts"),
    "reason": K("str", max_bytes=1024),
}

BODY_SPECS = {
    "manifest": MANIFEST_FIELDS,
    "record": RECORD_FIELDS,
    "checkpoint": CHECKPOINT_FIELDS,
    "receipt": RECEIPT_FIELDS,
    "latest": LATEST_FIELDS,
    "status": STATUS_FIELDS,
}

def validate_protocol_body(kind: str, body: JsonValue) -> None:
    """Validate one fixed protocol body by its type name."""
    fields = BODY_SPECS[kind]
    if not isinstance(body, dict) or body.get("type") != kind:
        raise SchemaError(f"expected body of type {kind!r}")
    if body.get("version") != 1:
        raise SchemaError(f"{kind}: unsupported version (only version 1 accepted)")
    validate_body(body, fields, kind)
