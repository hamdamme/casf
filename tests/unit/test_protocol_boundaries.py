"""The verifier must enforce the same body profile as the writer."""

import pytest

from casf.canonical.jcs import canonicalize
from casf.errors import CasfError
from casf.model.api import EventRequest
from casf.model.schema import validate_protocol_body
from casf.verifier import ProtocolStatus, Result, verify
from tests.unit.test_verifier import (
    _chain,
    _manifest_env,
    _pins,
    _record_env,
    _status_env,
)


@pytest.mark.parametrize("field", ["actor", "event_type"])
def test_empty_required_event_string_rejected(field):
    body = _chain(1)[0]["body"]
    body[field] = ""
    request = {key: body[key] for key in
               ("event_id", "actor", "event_type", "payload", "attributes")}
    with pytest.raises(CasfError):
        EventRequest.from_dict(request)
    _assert_record_schema_failure(_record_env(body))


def _assert_record_schema_failure(record):
    manifest = _manifest_env()
    report = verify(manifest, [record], _pins(),
                    status_envelopes=[_status_env(manifest["manifest_hash"])])
    assert report.result is Result.FAIL
    assert report.protocol_status is ProtocolStatus.INVALID
    assert report.first_failure_seq == 1
    assert "RECORD_SCHEMA" in report.diagnostic_codes
    return report


def test_signed_oversized_body_rejected():
    body = _chain(1)[0]["body"]
    body["payload"] = {"a": "x" * 32768, "b": "y" * 32768}
    assert len(canonicalize(body)) > 65536
    _assert_record_schema_failure(_record_env(body))


@pytest.mark.parametrize("payload", [{"bad": 1.5}, {"bad": "x" * 32769},
                                      {"bad": "\ud800"}])
def test_invalid_payload_returns_report(payload):
    record = _chain(1)[0]
    record["body"]["payload"] = payload
    assert _assert_record_schema_failure(record).result is Result.FAIL


def test_protocol_body_limit_precedes_signature_work():
    body = _manifest_env()["body"]
    body["log_public_key"] = "A" * 16384
    with pytest.raises(CasfError):
        validate_protocol_body("manifest", body)


def test_maximum_body_depth_survives_append_and_startup(tmp_path):
    from tests.unit.test_writer import LOG_ID, _writer

    payload = {"leaf": 0}
    for _ in range(14):
        payload = {"nested": payload}
    body = _chain(1)[0]["body"]
    body["payload"] = payload
    validate_protocol_body("record", body)  # body + 15 payload containers
    writer = _writer(tmp_path / "writer.db")
    try:
        record = writer.append(LOG_ID, **{key: body[key] for key in
                               ("event_id", "actor", "event_type", "payload", "attributes")})
        assert record["body"]["payload"] == payload
        writer._check_heads()
    finally:
        writer.close()


def test_witness_rejects_nonobject_record_without_internal_error(tmp_path):
    from casf import crypto
    from casf.witness import Witness
    from tests.status import register_active
    from tests.unit.test_writer import (
        AUTH,
        AUTH_PUB,
        LOG_ID,
        WIT,
        _append,
        _manifest_envelope,
        _writer,
    )

    writer = _writer(tmp_path / "writer.db")
    witness = Witness(tmp_path / "witness.db", WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    try:
        register_active(witness, _manifest_envelope(), AUTH)
        _append(writer, 1)
        checkpoint = writer.create_checkpoint(LOG_ID)
        with pytest.raises(CasfError):
            witness.submit(LOG_ID, checkpoint, [1])
        assert witness.submit(LOG_ID, checkpoint, list(writer.records(LOG_ID)))["body"]["count"] == 1
    finally:
        witness.close()
        writer.close()
