"""R07/R09: the public CLI requires verified startup unless explicitly bypassed."""

import json

import pytest
from cryptography.hazmat.primitives import serialization

from casf.canonical.jcs import canonicalize
from casf.cli import main
from casf.writer import Writer
from tests.unit.test_cli import PASS, _event, _trust
from tests.unit.test_verified_startup import statement
from tests.unit.test_verify_online import TOKEN, _service
from tests.unit.test_writer import LOG, LOG_ID, _manifest_envelope


@pytest.fixture
def setup(tmp_path, monkeypatch):
    service, server = _service(tmp_path)
    monkeypatch.setenv("CASF_PASSPHRASE", PASS.decode())
    monkeypatch.setenv("CASF_WITNESS_TOKEN", TOKEN)
    key = tmp_path / "log.pem"
    key.write_bytes(LOG.private_bytes(serialization.Encoding.PEM,
                                     serialization.PrivateFormat.PKCS8,
                                     serialization.BestAvailableEncryption(PASS)))
    key.chmod(0o600)
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(canonicalize(_manifest_envelope()))
    status = tmp_path / "active.json"
    status.write_bytes(canonicalize(statement(1)))
    url = f"http://127.0.0.1:{server.server_port}"
    trust = _trust(tmp_path, _manifest_envelope(), witness_url=url)
    common = ["--db", str(tmp_path / "writer.db"), "--key", str(key),
              "--trust", str(trust), "--status-file", str(status),
              "--state", str(tmp_path / "state.json"), "--json"]
    try:
        yield common, manifest, status, trust, url, service
    finally:
        server.shutdown()
        server.server_close()
        service.close()


def initialize(setup):
    common, manifest, _, _, _, _ = setup
    return main(["init", *common, "--manifest", str(manifest), "--initialize-state"])


def test_cli_defaults_to_verified_init_append_checkpoint_submit(setup, tmp_path, capsys):
    common, _, _, _, url, _ = setup
    assert initialize(setup) == 0
    assert json.loads(capsys.readouterr().out)["startup_verified"] is True
    assert main(["append", *common, "--event", str(_event(tmp_path))]) == 0
    assert json.loads(capsys.readouterr().out)["seq"] == 1
    assert main(["checkpoint", *common]) == 0
    capsys.readouterr()
    assert main(["witness", "submit", *common, "--url", url]) == 0
    assert json.loads(capsys.readouterr().out)["accepted"] is True
    assert json.loads((tmp_path / "state.json").read_text())["manifests"][
        _manifest_envelope()["manifest_hash"]]["checkpoint"]["index"] == 1
    # Startup itself can recover an accepted pending receipt; repeat is success.
    assert main(["witness", "submit", *common, "--url", url]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 1
    reader = Writer(tmp_path / "writer.db")
    try:
        assert len(list(reader.records(LOG_ID))) == 1
    finally:
        reader.close()


def test_cli_refuses_unverified_write_by_default(tmp_path, capsys):
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(canonicalize(_manifest_envelope()))
    assert main(["init", "--db", str(tmp_path / "db"), "--key", "unused.pem",
                 "--manifest", str(manifest)]) == 3
    assert "verified startup requires" in capsys.readouterr().err
    assert not (tmp_path / "db").exists()


def test_cli_revocation_survives_later_active_status(setup, tmp_path, capsys):
    common, _, status, _, _, _ = setup
    assert initialize(setup) == 0
    capsys.readouterr()
    event = _event(tmp_path)
    status.write_bytes(canonicalize(statement(2, "revoked")))
    assert main(["append", *common, "--event", str(event)]) == 3
    capsys.readouterr()
    status.write_bytes(canonicalize(statement(3)))
    assert main(["append", *common, "--event", str(event)]) == 3
    assert "STATUS_REVOKED_RETAINED" in capsys.readouterr().err
    assert json.loads((tmp_path / "state.json").read_text())["manifests"][
        _manifest_envelope()["manifest_hash"]]["revoked"] is True


def test_cli_offline_startup_refuses_append_and_allows_inspection(setup, tmp_path, capsys):
    common, _, _, trust, _, _ = setup
    assert initialize(setup) == 0
    capsys.readouterr()
    config = json.loads(trust.read_text())
    config["logs"][LOG_ID]["witness_url"] = "http://127.0.0.1:9"
    trust.write_text(json.dumps(config))
    assert main(["append", *common, "--event", str(_event(tmp_path))]) == 4
    assert TOKEN not in capsys.readouterr().err
    assert main(["status", "--db", str(tmp_path / "writer.db"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 0


def test_cli_verifier_remembers_revocation_independently(setup, tmp_path, capsys):
    _, _, _, trust, _, _ = setup
    assert initialize(setup) == 0
    capsys.readouterr()
    reader = Writer(tmp_path / "writer.db")
    bundle = tmp_path / "bundle"
    try:
        reader.export_bundle(LOG_ID, bundle)
    finally:
        reader.close()
    status = bundle / "status.jsonl"
    status.write_bytes(canonicalize(statement(2, "revoked")) + b"\n")
    args = ["verify", str(bundle), "--trust", str(trust),
            "--state", str(tmp_path / "verify-state.json"), "--json"]
    assert main([*args, "--initialize-state"]) == 3
    capsys.readouterr()
    status.write_bytes(canonicalize(statement(3)) + b"\n")
    assert main(args) == 3
    assert "STATUS_REVOKED_RETAINED" in json.loads(capsys.readouterr().out)["diagnostic_codes"]


def test_interrupted_bootstrap_retries_identical_checkpoint(setup, tmp_path, capsys):
    common, _, _, trust, url, _ = setup
    config = json.loads(trust.read_text())
    config["logs"][LOG_ID]["witness_url"] = "http://127.0.0.1:9"
    trust.write_text(json.dumps(config))
    assert initialize(setup) == 4
    capsys.readouterr()
    reader = Writer(tmp_path / "writer.db")
    pending = reader.pending_checkpoint(LOG_ID)[0]
    assert reader._db.connection.execute("SELECT sealed FROM heads").fetchone()[0] == 3
    reader.close()
    config["logs"][LOG_ID]["witness_url"] = url
    trust.write_text(json.dumps(config))
    assert main(["append", *common, "--event", str(_event(tmp_path))]) == 0
    reader = Writer(tmp_path / "writer.db")
    try:
        row = reader._db.connection.execute("SELECT envelope FROM checkpoints WHERE idx=0").fetchone()
        assert row[0] == canonicalize(pending)
        assert len(list(reader.records(LOG_ID))) == 1
    finally:
        reader.close()
