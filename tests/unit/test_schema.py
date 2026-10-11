"""Fixed-schema validation: exact field sets, types, timestamps."""

import pytest

from casf.errors import SchemaError
from casf.model import schema


def _record(**over):
    body = {
        "version": 1, "type": "record",
        "log_id": "123e4567-e89b-42d3-a456-426614174000",
        "manifest_hash": "ab" * 32,
        "seq": 1,
        "event_id": "123e4567-e89b-42d3-a456-426614174001",
        "recorded_at": "2026-10-11T00:00:00.000000Z",
        "actor": "alice", "event_type": "login",
        "payload": {}, "attributes": {},
        "prev_hash": "cd" * 32,
        "key_id": "ef" * 32,
    }
    body.update(over)
    return body

def test_valid_record_passes():
    schema.validate_protocol_body("record", _record())

def test_missing_field_rejected():
    b = _record(); del b["actor"]
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record", b)

def test_unknown_field_rejected():
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record", _record(extra=1))

def test_wrong_type_rejected():
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record", _record(seq="1"))

def test_timestamp_rules():
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record", _record(recorded_at="2026-10-11"))
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record",
            _record(recorded_at="2026-10-11T00:00:60.000000Z"))  # leap second
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record",
            _record(recorded_at="2026-13-11T00:00:00.000000Z"))  # month 13
    schema.validate_protocol_body("record",
        _record(recorded_at="2026-10-11T23:59:59.999999Z"))

def test_wrong_type_literal_rejected():
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record", _record(type="checkpoint"))

def test_digest_format():
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record", _record(prev_hash="AB" * 32))  # uppercase
    with pytest.raises(SchemaError):
        schema.validate_protocol_body("record", _record(prev_hash="ab" * 31))   # short
