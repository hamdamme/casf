"""R07/R09/R10: offline CLI restore requires independent signed evidence."""

import json

import pytest
from cryptography.hazmat.primitives import serialization

from casf import crypto
from casf.writer import SealedError, Writer
from tests.local_mode import local_cli as main
from tests.unit.test_cli import PASS, _trust
from tests.unit.test_restore_anchors import evidence
from tests.unit.test_restore_status import status
from tests.unit.test_writer import LOG, LOG_ID, _append, _writer


@pytest.fixture
def restore_args(tmp_path, monkeypatch):
    path, bundle, _pins = evidence(tmp_path)
    key = tmp_path / "synthetic-log.pem"
    key.write_bytes(LOG.private_bytes(serialization.Encoding.PEM,
                                     serialization.PrivateFormat.PKCS8,
                                     serialization.BestAvailableEncryption(PASS)))
    key.chmod(0o600)
    monkeypatch.setenv("CASF_PASSPHRASE", PASS.decode())
    monkeypatch.delenv("CASF_WITNESS_TOKEN", raising=False)
    trust = _trust(tmp_path, bundle.manifest)
    (path / "status.jsonl").write_text(json.dumps(status(bundle.manifest_hash)) + "\n")
    for name, envelope in (("anchor-checkpoint", bundle.checkpoints[-1]),
                           ("anchor-receipt", bundle.receipts[-1])):
        (tmp_path / (name + ".json")).write_text(json.dumps(envelope))
    return ["restore", str(path), "--db", str(tmp_path / "restored.db"),
            "--key", str(key), "--trust", str(trust), "--anchor-checkpoint",
            str(tmp_path / "anchor-checkpoint.json"), "--anchor-receipt",
            str(tmp_path / "anchor-receipt.json"), "--json"]


def test_cli_restore_reports_offline_scope(restore_args, tmp_path, capsys):
    assert main(restore_args) == 0
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert report["restored"] is True and report["freshness_checked"] is False
    assert not output.err and PASS.decode() not in output.out
    writer = Writer(tmp_path / "restored.db", LOG, local_only=True)
    try:
        assert len(list(writer.records(LOG_ID))) == 2
        assert _append(writer, 3)["body"]["seq"] == 3
    finally:
        writer.close()


@pytest.mark.parametrize("change,code", [
    ("missing_status", 3), ("revoked", 3), ("old_serial", 3),
    ("forged_anchor", 1), ("wrong_manifest", 3), ("malformed_anchor", 2),
])
def test_cli_restore_rejects_bad_evidence(restore_args, tmp_path, capsys, change, code):
    if change == "missing_status":
        (tmp_path / "bundle/status.jsonl").unlink()
    elif change == "revoked":
        manifest = json.loads((tmp_path / "bundle/manifest.json").read_text())
        (tmp_path / "bundle/status.jsonl").write_text(json.dumps(
            status(manifest["manifest_hash"], 2, "revoked")) + "\n")
    elif change in {"old_serial", "wrong_manifest"}:
        path = tmp_path / "trust.json"
        trust = json.loads(path.read_text())
        if change == "old_serial":
            trust["logs"][LOG_ID]["minimum_status_serial"] = 2
        else:
            trust["logs"][LOG_ID]["manifest_hash"] = "ab" * 32
        path.write_text(json.dumps(trust))
    else:
        path = tmp_path / "anchor-receipt.json"
        receipt = json.loads(path.read_text())
        receipt["signature"] = crypto.b64url_encode(bytes(64))
        path.write_text("{" if change == "malformed_anchor" else json.dumps(receipt))
    assert main(restore_args) == code
    output = capsys.readouterr()
    assert not (tmp_path / "restored.db").exists()
    assert not output.out and PASS.decode() not in output.err


@pytest.mark.parametrize("flag", ["--trust", "--anchor-checkpoint", "--anchor-receipt"])
def test_cli_restore_requires_trust_and_anchor(restore_args, tmp_path, flag):
    index = restore_args.index(flag)
    del restore_args[index:index + 2]
    assert main(restore_args) == 2
    assert not (tmp_path / "restored.db").exists()


def test_cli_restore_never_overwrites_destination(restore_args, tmp_path):
    path = tmp_path / "restored.db"
    path.write_bytes(b"preserve this file")
    assert main(restore_args) == 5
    assert path.read_bytes() == b"preserve this file"


def test_cli_restore_behind_anchor_reports_sealed_result(restore_args, tmp_path, capsys):
    writer = _writer(tmp_path / "old.db")
    try:
        bundle = writer.export_bundle(LOG_ID, tmp_path / "old-bundle")
        manifest = writer.manifest_envelope(LOG_ID)
    finally:
        writer.close()
    (bundle / "status.jsonl").write_text(json.dumps(status(manifest["manifest_hash"])) + "\n")
    restore_args[1] = str(bundle)
    assert main(restore_args) == 4
    report = json.loads(capsys.readouterr().out)
    assert report["restored"] is True and report["sealed"] is True
    assert report["diagnostic_codes"] == ["RESTORE_BEHIND_WITNESS"]
    reopened = Writer(tmp_path / "restored.db", LOG, local_only=True)
    try:
        with pytest.raises(SealedError):
            _append(reopened, 1)
    finally:
        reopened.close()
