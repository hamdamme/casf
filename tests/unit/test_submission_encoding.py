"""UTF-8 transport must not inflate valid records beyond wire budgets."""

import json

from casf import crypto
from casf.canonical.limits import MAX_WIRE_ENVELOPE_BYTES, MAX_WITNESS_REQUEST_BYTES
from casf.witness import Witness
from tests.status import register_active
from tests.unit.test_writer import AUTH, AUTH_PUB, LOG_ID, WIT, _manifest_envelope, _writer


def test_large_unicode_record_uses_bounded_utf8_wire_encoding(tmp_path, monkeypatch):
    writer = _writer(tmp_path / "writer.db")
    witness = Witness(tmp_path / "witness.db", WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    try:
        register_active(witness, _manifest_envelope(), AUTH)
        writer.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-426614174001",
                      actor="test", event_type="unicode", attributes={},
                      payload={"a": "\u0080" * 16000, "b": "\u0080" * 16000})
        writer.create_checkpoint(LOG_ID)

        def transport(_url, _method, _path, _token, raw, *, timeout):
            assert b"\\u0080" not in raw
            assert len(raw) < MAX_WIRE_ENVELOPE_BYTES
            assert len(raw) * 128 < MAX_WITNESS_REQUEST_BYTES
            request = json.loads(raw)
            receipt = witness.submit(LOG_ID, request["checkpoint"], request["records"])
            return 201, json.dumps({"receipt": receipt}).encode()

        monkeypatch.setattr("casf.writer.http_request", transport)
        writer.submit_pending(LOG_ID, "http://127.0.0.1", "test-token")
        assert writer.pending_checkpoint(LOG_ID) is None
    finally:
        witness.close()
        writer.close()
