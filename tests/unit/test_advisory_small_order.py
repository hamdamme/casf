"""R02/R03/R04: reject Ed25519 signature bypasses using synthetic evidence."""

import json
from pathlib import Path

import pytest

from casf import crypto
from casf.errors import SchemaError
from casf.verifier import Dimension, Mode, Result, TrustPins, verify
from casf.witness import Witness
from tests.status import active_status
from tests.unit.test_verifier import (
    AUTH,
    AUTH_PUB,
    LOG_ID,
    WIT,
    WIT_PUB,
    _checkpoint_env,
    _manifest_body,
    _receipt_env,
    _record_body,
    _record_env,
)

IDENTITY = b"\x01" + bytes(31)
UNIVERSAL_SIGNATURE = crypto.b64url_encode(IDENTITY + bytes(32))


def _manifest(role):
    body = _manifest_body()
    if role == "authority":
        body["issuer_id"] = crypto.key_id(IDENTITY)
    else:
        body[f"{role}_public_key"] = crypto.b64url_encode(IDENTITY)
        body["log_key_id" if role == "log" else "witness_id"] = crypto.key_id(IDENTITY)
    return {
        "body": body,
        "manifest_hash": crypto.digest_manifest(body),
        "signature": UNIVERSAL_SIGNATURE
        if role == "authority"
        else crypto.sign_manifest(AUTH, body),
    }


def _pins(role):
    authority = IDENTITY if role == "authority" else AUTH_PUB
    witness = IDENTITY if role == "witness" else WIT_PUB
    return TrustPins(
        authority_keys={crypto.key_id(authority): authority},
        witness_keys={crypto.key_id(witness): witness},
        log_id=LOG_ID,
    )


@pytest.mark.parametrize("mode", list(Mode))
def test_authorized_identity_log_never_passes(mode):
    manifest = _manifest("log")
    # The real authority approves this manifest; only its log key is invalid.
    crypto.verify_manifest(AUTH_PUB, manifest["body"], manifest["signature"])
    mh = manifest["manifest_hash"]
    previous = crypto.genesis_hash(mh)
    records = []
    for seq in range(1, 4):
        body = _record_body(seq, previous, mh, event_id=f"123e4567-e89b-42d3-a456-{seq:012d}")
        body["key_id"] = crypto.key_id(IDENTITY)
        body["payload"] = {"synthetic": seq}
        previous = crypto.digest_record(body)
        records.append({"body": body, "record_hash": previous, "signature": UNIVERSAL_SIGNATURE})
    report = verify(
        manifest, records, _pins("log"), mode=mode, status_envelopes=[active_status(AUTH, mh)]
    )
    assert report.result is Result.FAIL
    assert report.signature_status is not Dimension.VALID
    assert report.verified_through == 0
    assert "MANIFEST_KEY_SCHEMA" in report.diagnostic_codes


@pytest.mark.parametrize("role", ["log", "authority"])
def test_witness_registration_rejects_small_order_keys(tmp_path, role):
    pins = _pins(role)
    witness = Witness(tmp_path / "witness.db", WIT, authority_keys=pins.authority_keys)
    try:
        with pytest.raises(SchemaError, match="^Ed25519 public key has small order$"):
            witness.register_log(_manifest(role))
        assert witness._db.connection.execute("SELECT count(*) FROM manifests").fetchone() == (0,)
        assert witness._db.connection.execute("SELECT count(*) FROM w_state").fetchone() == (0,)
    finally:
        witness.close()


def test_identity_authority_pin_cannot_authorize_manifest():
    report = verify(_manifest("authority"), [], _pins("authority"))
    assert report.result is Result.FAIL
    assert report.signature_status is Dimension.INVALID
    assert "MANIFEST_SIGNATURE" in report.diagnostic_codes


def test_identity_witness_pin_cannot_anchor_records():
    manifest = _manifest("witness")
    mh = manifest["manifest_hash"]
    record = _record_env(_record_body(1, crypto.genesis_hash(mh), mh))
    checkpoint = _checkpoint_env(0, 1, record["record_hash"], "0" * 64, mh)
    receipt = _receipt_env(checkpoint)
    receipt["body"]["witness_id"] = crypto.key_id(IDENTITY)
    receipt["receipt_hash"] = crypto.digest_receipt(receipt["body"])
    receipt["signature"] = UNIVERSAL_SIGNATURE
    report = verify(
        manifest,
        [record],
        _pins("witness"),
        mode=Mode.ANCHORED,
        checkpoint_envelopes=[checkpoint],
        receipt_envelopes=[receipt],
        status_envelopes=[active_status(AUTH, mh)],
    )
    assert report.result is Result.FAIL
    assert report.signature_status is not Dimension.VALID
    assert "MANIFEST_KEY_SCHEMA" in report.diagnostic_codes


@pytest.mark.parametrize(
    "kind", ["manifest", "record", "checkpoint", "receipt", "latest", "status"]
)
def test_every_signature_domain_rejects_small_order_pin(kind):
    vectors = Path(__file__).resolve().parents[2] / "vectors/v1/crypto_kat.json"
    body = json.loads(vectors.read_text())["bodies"][kind]
    with pytest.raises(SchemaError, match="^Ed25519 public key has small order$"):
        getattr(crypto, f"verify_{kind}")(IDENTITY, body, UNIVERSAL_SIGNATURE)


@pytest.mark.parametrize("role", ["log", "witness", "authority"])
def test_witness_rejects_small_order_predecessor_keys(tmp_path, role):
    predecessor = _manifest(role)
    body = _manifest_body()
    body["log_id"] = "123e4567-e89b-42d3-a456-426614174002"
    body["predecessor"] = {
        "log_id": LOG_ID,
        "manifest_hash": predecessor["manifest_hash"],
        "final_checkpoint_hash": "ab" * 32,
        "final_receipt_hash": "cd" * 32,
    }
    successor = {
        "body": body,
        "manifest_hash": crypto.digest_manifest(body),
        "signature": crypto.sign_manifest(AUTH, body),
    }
    authorities = {**_pins(role).authority_keys, crypto.key_id(AUTH_PUB): AUTH_PUB}
    witness = Witness(tmp_path / "witness.db", WIT, authority_keys=authorities)
    try:
        # Reject the predecessor key before reading its checkpoint/receipt.
        with pytest.raises(SchemaError, match="^Ed25519 public key has small order$"):
            witness.register_log(successor, predecessor_evidence=(predecessor, {}, {}))
        assert witness._db.connection.execute("SELECT count(*) FROM manifests").fetchone() == (0,)
    finally:
        witness.close()
