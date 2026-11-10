"""R03/R10: writer CLI uses independently provisioned manifest trust."""

import json

import pytest

from casf import crypto
from casf.cli import main
from tests.unit.test_cli import PASS, TOKEN, _event, _key, _manifest_for, _trust


@pytest.fixture
def prepared(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CASF_PASSPHRASE", PASS.decode())
    monkeypatch.setenv("CASF_WITNESS_TOKEN", TOKEN)
    key = _key(tmp_path, capsys)
    manifest = _manifest_for(key)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    trust = _trust(tmp_path, manifest)
    return tmp_path / "writer.db", key, path, trust, manifest


def test_cli_initializes_and_appends_with_trust(prepared, tmp_path, capsys):
    db, key, manifest, trust, _env = prepared
    assert main(["init", "--db", str(db), "--key", str(key),
                 "--manifest", str(manifest), "--trust", str(trust)]) == 0
    assert main(["append", "--db", str(db), "--key", str(key),
                 "--event", str(_event(tmp_path)), "--trust", str(trust)]) == 0
    assert main(["checkpoint", "--db", str(db), "--key", str(key),
                 "--trust", str(trust)]) == 0
    assert main(["export", "--db", str(db), "--out", str(tmp_path / "bundle"),
                 "--trust", str(trust)]) == 0
    output = capsys.readouterr()
    assert not output.err
    assert PASS.decode() not in output.out


def test_cli_rejects_forged_authority_during_init(prepared, capsys):
    db, key, path, trust, manifest = prepared
    manifest["signature"] = crypto.b64url_encode(bytes(64))
    path.write_text(json.dumps(manifest))
    assert main(["init", "--db", str(db), "--key", str(key),
                 "--manifest", str(path), "--trust", str(trust)]) == 3
    assert "authority signature" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["append", "checkpoint", "seal", "submit", "export"])
def test_cli_rejects_untrusted_existing_store(prepared, tmp_path, capsys, command):
    db, key, path, trust, manifest = prepared
    manifest["signature"] = crypto.b64url_encode(bytes(64))
    path.write_text(json.dumps(manifest))
    assert main(["init", "--db", str(db), "--key", str(key), "--manifest", str(path)]) == 0
    capsys.readouterr()
    args = ["witness", "submit"] if command == "submit" else [command]
    args += ["--db", str(db), "--trust", str(trust)]
    if command != "export":
        args += ["--key", str(key)]
    if command == "append":
        args += ["--event", str(_event(tmp_path))]
    elif command == "submit":
        args += ["--url", "http://127.0.0.1:9"]
    elif command == "export":
        args += ["--out", str(tmp_path / "bundle")]
    assert main(args) == 3
    error = capsys.readouterr().err
    assert "authority signature" in error
    assert PASS.decode() not in error and TOKEN not in error
    assert not (tmp_path / "bundle").exists()


def test_cli_requires_provisioned_log(prepared, capsys):
    db, key, path, trust, _manifest = prepared
    config = json.loads(trust.read_text())
    config["logs"] = {}
    trust.write_text(json.dumps(config))
    assert main(["init", "--db", str(db), "--key", str(key),
                 "--manifest", str(path), "--trust", str(trust)]) == 3
    assert not db.exists()
    assert "LOG_NOT_PROVISIONED" in capsys.readouterr().err


@pytest.mark.parametrize("version", [True, 2, "1"])
def test_cli_rejects_invalid_trust_version(prepared, capsys, version):
    db, key, path, trust, _manifest = prepared
    config = json.loads(trust.read_text())
    config["version"] = version
    trust.write_text(json.dumps(config))
    assert main(["init", "--db", str(db), "--key", str(key),
                 "--manifest", str(path), "--trust", str(trust)]) == 2
    assert not db.exists()
    assert "trust version" in capsys.readouterr().err
