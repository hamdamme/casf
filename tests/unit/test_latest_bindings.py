"""R06 / T11: signed latest views must bind the complete evidence pair."""

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.online import verify_latest_response
from tests.unit.test_witness import _checkpoint, _witness
from tests.unit.test_writer import LOG_ID, WIT, WIT_PUB, _writer


@pytest.mark.parametrize("target,field,value", [
    ("body", "version", True),
    ("body", "final", True),
    ("body", "manifest_hash", "ab" * 32),
    ("checkpoint", "version", True),
    ("receipt", "version", True),
    ("receipt", "log_id", "123e4567-e89b-42d3-a456-426614174999"),
    ("receipt", "manifest_hash", "ab" * 32),
    ("receipt", "witness_id", "ab" * 32),
])
def test_latest_rejects_signed_schema_and_binding_conflicts(tmp_path, target, field, value):
    writer = _writer(tmp_path / "writer.db")
    witness = _witness(tmp_path)
    try:
        cp = _checkpoint(writer, index=0, count=0)
        witness.submit(LOG_ID, cp, [])
        nonce = b"n" * 32
        response = witness.latest(LOG_ID, nonce)
        if target == "body":
            response["body"][field] = value
        else:
            env = response[target]
            env["body"][field] = value
            env[target + "_hash"] = getattr(crypto, "digest_" + target)(env["body"])
            if target == "receipt":
                env["signature"] = crypto.sign_receipt(WIT, env["body"])
            response["body"][target + "_hash"] = env[target + "_hash"]
        response["signature"] = crypto.sign_latest(WIT, response["body"])
        with pytest.raises(CasfError):
            verify_latest_response(response, nonce, WIT_PUB, LOG_ID)
    finally:
        writer.close()
        witness.close()
