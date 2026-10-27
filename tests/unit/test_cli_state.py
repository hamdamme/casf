"""Command line state detects restored history and stale authority status."""

import json
import os
import sqlite3
import threading

import pytest

from casf.canonical.jcs import canonicalize
from casf.cli import main
from casf.lifecycle import sign_status
from casf.witness.http import make_server
from casf.writer import Writer
from tests.status import active_status
from tests.unit.test_cli import _trust
from tests.unit.test_verify_online import TOKEN, _service
from tests.unit.test_writer import AUTH, LOG, LOG_ID, _append, _manifest_envelope, _writer


def copy_database(connection, path):
    destination = sqlite3.connect(path)
    try:
        connection.backup(destination)
    finally:
        destination.close()


def anchor(writer, service):
    writer.create_checkpoint(LOG_ID)
    cp, start, end = writer.pending_checkpoint(LOG_ID)
    receipt = service.witness.submit(LOG_ID, cp, list(writer.records(LOG_ID))[start - 1:end])
    writer.record_receipt(LOG_ID, receipt)


def export(writer, path, serial=1):
    writer.export_bundle(LOG_ID, path)
    status = sign_status(AUTH, serial=serial,
                         manifest_hash=writer.manifest_envelope(LOG_ID)["manifest_hash"],
                         status="active", issued_at="2026-10-11T00:00:00.000000Z", reason="")
    (path / "status.jsonl").write_bytes(canonicalize(status) + b"\n")


def command(bundle, trust, state, *, initialize=False):
    args = ["verify", str(bundle), "--trust", str(trust), "--state", str(state), "--json"]
    if initialize:
        args.append("--initialize-state")
    return main(args)


@pytest.fixture()
def environment(tmp_path, monkeypatch):
    svc, server = _service(tmp_path)
    writer = _writer(tmp_path / "writer.db")
    monkeypatch.setenv("CASF_WITNESS_TOKEN", TOKEN)
    trust = _trust(tmp_path, _manifest_envelope(), mode="online",
                   witness_url=f"http://127.0.0.1:{server.server_port}")
    try:
        yield writer, svc, trust, tmp_path / "state.json"
    finally:
        writer.close()
        server.shutdown()
        server.server_close()
        svc.close()


@pytest.mark.parametrize("fork_length", [0, 1, 2])
def test_cli_detects_restored_witness_and_fork(environment, tmp_path, capsys, fork_length):
    writer, svc, trust, state = environment
    _append(writer, 1)
    anchor(writer, svc)
    copy_database(writer._db.connection, tmp_path / "fork.db")
    copy_database(svc.witness._db.connection, tmp_path / "restored.db")
    export(writer, tmp_path / "first")
    assert command(tmp_path / "first", trust, state, initialize=True) == 0
    first = json.loads(capsys.readouterr().out)
    assert "VERIFIER_STATE_INITIALIZED" in first["diagnostic_codes"]
    assert "CHECKPOINT_FIRST_OBSERVATION" in first["diagnostic_codes"]
    _append(writer, 2)
    anchor(writer, svc)
    export(writer, tmp_path / "honest")
    assert command(tmp_path / "honest", trust, state) == 0
    assert "VERIFIER_STATE_INITIALIZED" not in json.loads(capsys.readouterr().out)["diagnostic_codes"]
    saved = state.read_bytes()
    # The restored service starts from the old database but uses the same test key.
    from casf import crypto
    from casf.witness.http import WitnessService
    from tests.unit.test_writer import AUTH_PUB, WIT

    restored = WitnessService(tmp_path / "restored.db", WIT, token=TOKEN,
                              authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    server = make_server(restored, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    fork = Writer(tmp_path / "fork.db", LOG)
    try:
        for n in range(fork_length):
            fork.append(LOG_ID, event_id=f"123e4567-e89b-42d3-a456-4266000000{90+n}",
                        actor="test", event_type="login", payload={"alternative": n}, attributes={})
            anchor(fork, restored)
        export(fork, tmp_path / "fork")
        _trust(tmp_path, _manifest_envelope(), mode="online",
               witness_url=f"http://127.0.0.1:{server.server_port}")
        assert command(tmp_path / "fork", trust, state) == 1
        result = json.loads(capsys.readouterr().out)
        assert result["result"] == "FAIL"
        assert "WITNESS_STATE_CONFLICT" in result["diagnostic_codes"]
        assert state.read_bytes() == saved
    finally:
        fork.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        restored.close()


@pytest.mark.parametrize("mode", ["online", "anchored", "integrity"])
def test_status_serial_cannot_go_backward(environment, tmp_path, capsys, mode):
    writer, svc, trust, state = environment
    _append(writer, 1)
    anchor(writer, svc)
    export(writer, tmp_path / "new", serial=2)
    export(writer, tmp_path / "old", serial=1)
    configuration = json.loads(trust.read_text())
    configuration["policy"]["mode"] = mode
    trust.write_text(json.dumps(configuration))
    assert command(tmp_path / "new", trust, state, initialize=True) == 0
    capsys.readouterr()
    saved = state.read_bytes()
    assert command(tmp_path / "old", trust, state) == 3
    assert "STATUS_SERIAL_LOW" in json.loads(capsys.readouterr().out)["diagnostic_codes"]
    assert state.read_bytes() == saved


def test_inconclusive_query_cannot_advance_state(environment, tmp_path, capsys, monkeypatch):
    writer, svc, trust, state = environment
    _append(writer, 1)
    anchor(writer, svc)
    export(writer, tmp_path / "first")
    assert command(tmp_path / "first", trust, state, initialize=True) == 0
    capsys.readouterr()
    saved = state.read_bytes()
    _append(writer, 2)
    anchor(writer, svc)
    export(writer, tmp_path / "new", serial=2)
    from casf.errors import InconclusiveError

    def unavailable(*args, **kwargs):
        raise InconclusiveError("test partition")

    monkeypatch.setattr("casf.cli.query_latest", unavailable)
    assert command(tmp_path / "new", trust, state) == 4
    assert json.loads(capsys.readouterr().out)["result"] == "INCONCLUSIVE"
    assert state.read_bytes() == saved


def test_save_failure_cannot_report_pass(environment, tmp_path, capsys, monkeypatch):
    writer, svc, trust, state = environment
    _append(writer, 1)
    anchor(writer, svc)
    export(writer, tmp_path / "first")

    def broken(*args, **kwargs):
        raise OSError("test disk failure")

    monkeypatch.setattr(os, "replace", broken)
    assert command(tmp_path / "first", trust, state, initialize=True) == 5
    assert not capsys.readouterr().out
    assert not state.exists()


def test_missing_damaged_and_bundle_state_refused(environment, tmp_path, capsys):
    writer, svc, trust, state = environment
    _append(writer, 1)
    anchor(writer, svc)
    bundle = tmp_path / "bundle"
    export(writer, bundle)
    assert command(bundle, trust, state) == 5
    assert not capsys.readouterr().out
    state.write_text("broken")
    state.chmod(0o600)
    assert command(bundle, trust, state, initialize=True) == 5
    assert not capsys.readouterr().out
    assert state.read_text() == "broken"
    assert command(bundle, trust, bundle / "state.json", initialize=True) == 2
    assert not (bundle / "state.json").exists()


def test_invalid_signature_cannot_initialize_state(environment, tmp_path, capsys):
    writer, svc, trust, state = environment
    _append(writer, 1)
    anchor(writer, svc)
    bundle = tmp_path / "bundle"
    export(writer, bundle)
    status = active_status(AUTH, writer.manifest_envelope(LOG_ID)["manifest_hash"])
    status["body"]["serial"] = 999  # signature still authenticates serial 1
    (bundle / "status.jsonl").write_bytes(canonicalize(status) + b"\n")
    assert command(bundle, trust, state, initialize=True) == 3
    assert json.loads(capsys.readouterr().out)["result"] == "FAIL"
    assert not state.exists()


def test_directory_sync_failure_cannot_report_pass(environment, tmp_path, capsys, monkeypatch):
    writer, svc, trust, state = environment
    _append(writer, 1)
    anchor(writer, svc)
    export(writer, tmp_path / "first")
    original = os.fsync
    calls = 0

    def fail_directory(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("test directory sync failure")
        original(fd)

    monkeypatch.setattr(os, "fsync", fail_directory)
    assert command(tmp_path / "first", trust, state, initialize=True) == 5
    assert not capsys.readouterr().out
    # Replacement may have occurred, but durability has not been confirmed.
    assert json.loads(state.read_text())["version"] == 1


def test_integrity_run_preserves_saved_checkpoint(environment, tmp_path, capsys):
    writer, svc, trust, state = environment
    _append(writer, 1)
    anchor(writer, svc)
    export(writer, tmp_path / "first")
    assert command(tmp_path / "first", trust, state, initialize=True) == 0
    capsys.readouterr()
    previous = json.loads(state.read_text())
    configuration = json.loads(trust.read_text())
    configuration["policy"]["mode"] = "integrity"
    trust.write_text(json.dumps(configuration))
    export(writer, tmp_path / "second", serial=2)
    assert command(tmp_path / "second", trust, state) == 0
    current = json.loads(state.read_text())
    digest = writer.manifest_envelope(LOG_ID)["manifest_hash"]
    assert current["manifests"][digest]["checkpoint"] == previous["manifests"][digest]["checkpoint"]
    assert current["manifests"][digest]["status_serial"] == 2
