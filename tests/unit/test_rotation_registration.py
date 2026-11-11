"""Epoch registration authenticates the final predecessor evidence."""

import json
from copy import deepcopy

import pytest
from cryptography.hazmat.primitives import serialization

from casf import crypto
from casf.cli import main
from casf.errors import CasfError
from casf.lifecycle import rotate_epoch
from casf.witness import Witness
from tests.unit.test_lifecycle import _final_evidence, _seeded
from tests.unit.test_writer import AUTH, AUTH_PUB, LOG_ID, TS, WIT, WIT_PUB

NEW_ID = "123e4567-e89b-42d3-a456-426614174111"


def _successor(cp, receipt):
    return rotate_epoch(authority_priv=AUTH, new_log_priv=_seeded("next-epoch"),
                        new_log_id=NEW_ID, witness_pub=WIT_PUB, created_at=TS,
                        final_checkpoint=cp, final_receipt=receipt)


def test_registration_requires_predecessor_evidence(tmp_path):
    writer, original, cp, receipt = _final_evidence(tmp_path)
    empty = Witness(tmp_path / "empty.db", WIT,
                    authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    try:
        successor = _successor(cp, receipt)
        with pytest.raises(CasfError):
            empty.register_log(successor)
        assert not empty.log_registered(NEW_ID)
        assert original.register_log(successor) == NEW_ID
    finally:
        empty.close()
        original.close()
        writer.close()


@pytest.mark.parametrize("field,value", [("count", 0), ("checkpoint_index", 10),
                                        ("log_id", NEW_ID), ("manifest_hash", "00" * 32),
                                        ("head_hash", "00" * 32)])
def test_rotation_rejects_signed_mismatching_receipt(tmp_path, field, value):
    writer, witness, cp, receipt = _final_evidence(tmp_path)
    try:
        bad = deepcopy(receipt)
        bad["body"][field] = value
        bad["receipt_hash"] = crypto.digest_receipt(bad["body"])
        bad["signature"] = crypto.sign_receipt(WIT, bad["body"])
        with pytest.raises(CasfError):
            _successor(cp, bad)
    finally:
        witness.close()
        writer.close()


@pytest.mark.parametrize("corruption", [None, "signature", "receipt", "authority"])
def test_external_predecessor_evidence_is_authenticated(tmp_path, corruption):
    writer, original, cp, receipt = _final_evidence(tmp_path)
    authority_keys = {crypto.key_id(AUTH_PUB): AUTH_PUB}
    empty = Witness(tmp_path / "empty.db", WIT, authority_keys=authority_keys)
    try:
        successor = _successor(cp, receipt)
        old = writer.manifest_envelope(LOG_ID)
        if corruption == "signature":
            old["signature"] = crypto.b64url_encode(b"\0" * 64)
        elif corruption == "receipt":
            receipt["signature"] = crypto.b64url_encode(b"\0" * 64)
        elif corruption == "authority":
            other = _seeded("unprovisioned-root")
            old["body"]["issuer_id"] = crypto.key_id(crypto.public_key_raw(other))
            old["manifest_hash"] = crypto.digest_manifest(old["body"])
            old["signature"] = crypto.sign_manifest(other, old["body"])
            successor["body"]["predecessor"]["manifest_hash"] = old["manifest_hash"]
            successor["manifest_hash"] = crypto.digest_manifest(successor["body"])
            successor["signature"] = crypto.sign_manifest(AUTH, successor["body"])
        if corruption is None:
            assert empty.register_log(successor, predecessor_evidence=(old, cp, receipt)) == NEW_ID
        else:
            with pytest.raises(CasfError):
                empty.register_log(successor, predecessor_evidence=(old, cp, receipt))
            assert not empty.log_registered(NEW_ID)
            assert not empty._db.connection.in_transaction
    finally:
        empty.close()
        original.close()
        writer.close()


def test_cli_rotates_to_a_new_witness_and_registers_external_evidence(tmp_path, monkeypatch):
    writer, original, cp, receipt = _final_evidence(tmp_path)
    password = b"synthetic-rotation-test"
    monkeypatch.setenv("CASF_PASSPHRASE", password.decode())
    new_log, new_witness = _seeded("new-log"), _seeded("new-witness")
    try:
        for name, key in (("authority", AUTH), ("new-log", new_log), ("witness", new_witness)):
            path = tmp_path / (name + ".pem")
            path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.PKCS8,
                             serialization.BestAvailableEncryption(password)))
            path.chmod(0o600)
        for name, key in (("authority", AUTH), ("witness", new_witness)):
            (tmp_path / (name + ".pub.pem")).write_bytes(key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        for name, value in (("old", writer.manifest_envelope(LOG_ID)),
                            ("checkpoint", cp), ("receipt", receipt)):
            (tmp_path / (name + ".json")).write_text(json.dumps(value))
        output = tmp_path / "next.json"
        assert main(["admin", "rotate", "--old-manifest", str(tmp_path / "old.json"),
                     "--final-checkpoint", str(tmp_path / "checkpoint.json"),
                     "--final-receipt", str(tmp_path / "receipt.json"),
                     "--authority-key", str(tmp_path / "authority.pem"),
                     "--new-log-key", str(tmp_path / "new-log.pem"),
                     "--witness-public-key", str(tmp_path / "witness.pub.pem"),
                     "--out", str(output)]) == 0
        successor = json.loads(output.read_text())
        from tests.status import active_status
        status = tmp_path / "status.json"
        status.write_text(json.dumps(active_status(AUTH, successor["manifest_hash"])))
        assert main(["admin", "register", "--manifest", str(output),
                     "--status-file", str(status),
                     "--authority-public-key", str(tmp_path / "authority.pub.pem"),
                     "--witness-key", str(tmp_path / "witness.pem"),
                     "--db", str(tmp_path / "new-witness.db"),
                     "--predecessor-manifest", str(tmp_path / "old.json"),
                     "--predecessor-checkpoint", str(tmp_path / "checkpoint.json"),
                     "--predecessor-receipt", str(tmp_path / "receipt.json")]) == 0
    finally:
        original.close()
        writer.close()
