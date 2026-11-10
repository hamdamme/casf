"""R05/R09/R10: recover accepted evidence without resubmitting a checkpoint."""

import json

import pytest

from casf import crypto
from casf.cli import main
from casf.errors import CasfError
from casf.transport import request
from casf.writer import SealedError, Writer
from tests.status import register_active
from tests.unit.test_checkpoint import _witness
from tests.unit.test_cli import _trust
from tests.unit.test_verify_online import TOKEN, _service
from tests.unit.test_writer import AUTH, LOG, LOG_ID, WIT, _append, _manifest_envelope, _writer
from tests.unit.test_writer_trust import _pins


def pending_store(tmp_path, final=False):
    writer = _writer(tmp_path / "writer.db")
    try:
        _append(writer, 1)
        checkpoint = writer.create_checkpoint(LOG_ID, final=final)
        records = list(writer.records(LOG_ID))
    finally:
        writer.close()
    return checkpoint, records


@pytest.mark.parametrize("final", [False, True])
def test_recover_receipt_after_restart_over_http(tmp_path, final):
    checkpoint, records = pending_store(tmp_path, final)
    svc, server = _service(tmp_path)
    writer = Writer(tmp_path / "writer.db", trust_pins={LOG_ID: _pins()})
    try:
        accepted = svc.witness.submit(LOG_ID, checkpoint, records)
        receipt = writer.recover_pending_receipt(
            LOG_ID, f"http://127.0.0.1:{server.server_port}", TOKEN)
        assert receipt == accepted and writer.pending_checkpoint(LOG_ID) is None
        assert svc.witness.receipt(checkpoint["checkpoint_hash"]) == (checkpoint, accepted)
    finally:
        writer.close()
        server.shutdown()
        server.server_close()
        svc.close()
    reopened = Writer(tmp_path / "writer.db", LOG, trust_pins={LOG_ID: _pins()})
    try:
        if final:
            with pytest.raises(SealedError):
                _append(reopened, 2)
        else:
            assert reopened.create_checkpoint(LOG_ID)["body"]["index"] == 1
    finally:
        reopened.close()


@pytest.mark.parametrize("change", [
    "timeout", "missing", "unavailable", "json", "shape", "checkpoint",
    "signature", "manifest", "previous_receipt", "no_pins",
])
def test_failed_receipt_recovery_preserves_pending_bytes(tmp_path, monkeypatch, change):
    checkpoint, records = pending_store(tmp_path)
    witness = _witness(tmp_path)
    try:
        receipt = witness.submit(LOG_ID, checkpoint, records)
    finally:
        witness.close()
    if change == "signature":
        receipt["signature"] = crypto.b64url_encode(bytes(64))
    elif change in {"manifest", "previous_receipt"}:
        receipt["body"]["manifest_hash" if change == "manifest" else "previous_receipt_hash"] = "ab" * 32
        receipt["receipt_hash"] = crypto.digest_receipt(receipt["body"])
        receipt["signature"] = crypto.sign_receipt(WIT, receipt["body"])
    data = {"checkpoint": checkpoint, "receipt": receipt}
    if change == "checkpoint":
        data["checkpoint"] = {**checkpoint, "signature": crypto.b64url_encode(bytes(64))}

    def answer(url, method, path, token, body, **kwargs):
        assert method == "GET" and body == b""
        assert path.endswith("/receipts/" + checkpoint["checkpoint_hash"])
        if change == "timeout":
            raise TimeoutError("private transport details")
        if change in {"missing", "unavailable"}:
            return (404 if change == "missing" else 503), b'{"message":"private details"}'
        return 200, b"{" if change == "json" else json.dumps({} if change == "shape" else data).encode()

    monkeypatch.setattr("casf.writer.http_request", answer)
    writer = Writer(tmp_path / "writer.db", trust_pins=None if change == "no_pins" else {LOG_ID: _pins()})
    try:
        before = writer.pending_checkpoint(LOG_ID)
        with pytest.raises(CasfError) as error:
            writer.recover_pending_receipt(LOG_ID, "http://127.0.0.1:9", TOKEN)
        assert "private" not in str(error.value)
        assert writer.pending_checkpoint(LOG_ID) == before
    finally:
        writer.close()
    reopened = Writer(tmp_path / "writer.db", trust_pins={LOG_ID: _pins()})
    try:
        assert reopened.pending_checkpoint(LOG_ID) == before
    finally:
        reopened.close()


@pytest.mark.parametrize("result", ["accepted", "forged", "unavailable"])
def test_cli_recovers_receipt_without_signing_key(tmp_path, monkeypatch, capsys, result):
    checkpoint, records = pending_store(tmp_path)
    witness = _witness(tmp_path)
    try:
        receipt = witness.submit(LOG_ID, checkpoint, records)
    finally:
        witness.close()
    if result == "forged":
        receipt["signature"] = crypto.b64url_encode(bytes(64))
    data = json.dumps({"checkpoint": checkpoint, "receipt": receipt}).encode()
    monkeypatch.setattr("casf.writer.http_request", lambda *a, **k:
                        (503, b"{}") if result == "unavailable" else (200, data))
    monkeypatch.setenv("CASF_WITNESS_TOKEN", TOKEN)
    monkeypatch.delenv("CASF_PASSPHRASE", raising=False)
    trust = _trust(tmp_path, _manifest_envelope())
    assert main(["witness", "recover", "--db", str(tmp_path / "writer.db"),
                 "--trust", str(trust), "--url", "http://127.0.0.1:9", "--json"]) == {
                     "accepted": 0, "forged": 1, "unavailable": 4}[result]
    output = capsys.readouterr()
    assert TOKEN not in output.out + output.err
    if result == "accepted":
        report = json.loads(output.out)
        assert report["recovered"] is True and report["count"] == 1
        assert report["freshness_checked"] is False


def test_receipt_lookup_is_bound_to_requested_log(tmp_path):
    checkpoint, records = pending_store(tmp_path)
    svc, server = _service(tmp_path)
    try:
        svc.witness.submit(LOG_ID, checkpoint, records)
        other = _manifest_envelope()
        other_id = "223e4567-e89b-42d3-a456-426614174000"
        other["body"]["log_id"] = other_id
        other["manifest_hash"] = crypto.digest_manifest(other["body"])
        other["signature"] = crypto.sign_manifest(AUTH, other["body"])
        register_active(svc.witness, other, AUTH)
        code, payload = request(f"http://127.0.0.1:{server.server_port}", "GET",
                                f"/v1/logs/{other_id}/receipts/{checkpoint['checkpoint_hash']}",
                                TOKEN, b"", timeout=2)
        assert code == 404
        assert "checkpoint" not in json.loads(payload)
    finally:
        server.shutdown()
        server.server_close()
        svc.close()
