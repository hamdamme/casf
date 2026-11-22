"""R07/R09/R10: follow-up read errors and configuration boundaries."""

import json
from types import SimpleNamespace

import pytest

from casf.canonical.jcs import canonicalize
from casf.cli import _load_trust, _writer, main
from casf.errors import NoCheckpointError, SchemaError, WitnessResponseError
from casf.online import fetch_latest
from tests.status import active_status
from tests.unit.test_checkpoint import _witness
from tests.unit.test_cli import _trust
from tests.unit.test_verify_online import _evidence
from tests.unit.test_writer import AUTH, LOG_ID, _manifest_envelope


@pytest.fixture
def bundle(tmp_path):
    witness = _witness(tmp_path)
    writer, mh, _, _ = _evidence(tmp_path, SimpleNamespace(witness=witness),
                                 records=2, witnessed=2)
    try:
        path = writer.export_bundle(LOG_ID, tmp_path / "bundle")
        (path / "status.jsonl").write_bytes(canonicalize(active_status(AUTH, mh)) + b"\n")
        yield path
    finally:
        writer.close()
        witness.close()


@pytest.mark.parametrize("payload", [b"", b"<html>private-response</html>", b"{", b"[]",
                                      b'{"code":"NOT_FOUND"}', b'{"code":1}'])
def test_unrecognized_404_is_response_error(monkeypatch, payload):
    monkeypatch.setattr("casf.online.http_request", lambda *a, **k: (404, payload))
    with pytest.raises(WitnessResponseError, match="HTTP 404") as caught:
        fetch_latest("https://w.example", LOG_ID, "synthetic-token")
    assert "private-response" not in str(caught.value)


def test_no_checkpoint_keeps_explicit_category(monkeypatch):
    monkeypatch.setattr("casf.online.http_request",
                        lambda *a, **k: (404, b'{"code":"NO_CHECKPOINT"}'))
    with pytest.raises(NoCheckpointError):
        fetch_latest("https://w.example", LOG_ID, "synthetic-token")


@pytest.mark.parametrize("status,payload,exit_code", [
    (404, b"", 5), (404, b"<html>private-response</html>", 5),
    (404, b'{"code":"NOT_FOUND"}', 5), (409, b"", 5),
    (409, b'{"code":"NO_CHECKPOINT"}', 5), (500, b"", 5),
    (404, b'{"code":"NO_CHECKPOINT"}', 4), (503, b"", 4), (429, b"", 4),
])
def test_online_cli_distinguishes_operational_errors(
        bundle, tmp_path, monkeypatch, capsys, status, payload, exit_code):
    trust = _trust(tmp_path, _manifest_envelope(), mode="online", witness_url="https://w.example")
    state = tmp_path / "state.json"
    monkeypatch.setenv("CASF_WITNESS_TOKEN", "synthetic-token")
    monkeypatch.setattr("casf.online.http_request", lambda *a, **k: (status, payload))
    assert main(["verify", str(bundle), "--trust", str(trust), "--state", str(state),
                 "--initialize-state", "--json"]) == exit_code
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert report["result"] == "INCONCLUSIVE"
    assert report["freshness_status"] == "INCONCLUSIVE"
    assert ("WITNESS_RESPONSE_ERROR" in report["diagnostic_codes"]) == (exit_code == 5)
    assert "WITNESS_STATE_CONFLICT" not in report["diagnostic_codes"]
    assert "private-response" not in output.out + output.err
    assert "synthetic-token" not in output.out + output.err
    # Independently authenticated status may advance, but a read failure never
    # advances the accepted checkpoint or invents a receipt.
    if state.exists():
        assert json.loads(state.read_text())["manifests"][
            _manifest_envelope()["manifest_hash"]]["checkpoint"] is None


@pytest.mark.parametrize("url", ["http://example.com", "https://w.example/prefix",
                                 "https://w.example?token=private", "https://w.example#"])
def test_loaded_origin_is_validated(tmp_path, url):
    trust = _trust(tmp_path, _manifest_envelope(), witness_url=url)
    with pytest.raises(SchemaError, match="URL"):
        _load_trust(str(trust), LOG_ID)


@pytest.mark.parametrize("mode,url,override", [
    ("online", "", None), ("integrity", "", "online"),
    ("anchored", "", "online"), ("online", "http://example.com", None),
    ("online", "https://w.example/prefix", None),
])
def test_invalid_online_origin_precedes_secrets_and_state(
        bundle, tmp_path, monkeypatch, capsys, mode, url, override):
    trust = _trust(tmp_path, _manifest_envelope(), mode=mode, witness_url=url)
    state = tmp_path / "state.json"

    def forbidden(*a, **k):
        pytest.fail("invalid origin reached secrets or network")

    monkeypatch.setattr("casf.cli._secret", forbidden)
    monkeypatch.setattr("casf.online.http_request", forbidden)
    args = ["verify", str(bundle), "--trust", str(trust), "--state", str(state),
            "--initialize-state"]
    if override:
        args += ["--mode", override]
    assert main(args) == 2
    assert "URL" in capsys.readouterr().err
    assert not state.exists() and not state.with_suffix(".json.lock").exists()


@pytest.mark.parametrize("url,override", [("", None), ("http://example.com", None),
                                        ("", "https://w.example/prefix"), ("https://w.example", "")])
def test_invalid_startup_origin_precedes_key_loading(tmp_path, monkeypatch, url, override):
    trust = _trust(tmp_path, _manifest_envelope(), witness_url=url)
    args = SimpleNamespace(local_only=False, trust=str(trust), status_file="unused",
                           state="unused", initialize_state=False, url=override)

    def forbidden(*a, **k):
        pytest.fail("invalid startup origin reached key loading")

    monkeypatch.setattr("casf.cli.load_key", forbidden)
    with pytest.raises(SchemaError):
        _writer(args, _manifest_envelope())


@pytest.mark.parametrize("mode,url", [("integrity", ""), ("anchored", ""),
    ("online", "https://w.example/"), ("online", "http://127.0.0.1:8123"),
    ("online", "http://[::1]:8123")])
def test_supported_origins_remain_valid(tmp_path, mode, url):
    trust = _trust(tmp_path, _manifest_envelope(), mode=mode, witness_url=url)
    assert _load_trust(str(trust), LOG_ID)[1]["witness_url"] == url
