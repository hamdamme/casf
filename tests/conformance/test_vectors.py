"""Conformance gate (M1): frozen vectors in vectors/v1 must hold.

- jcs_kat.json: canonical bytes match the frozen hex
- jcs_reject.json: malformed wire input fails with the expected error
- crypto_kat.json: keys, digests, genesis and signatures are exact
  known answers; wrong domain and non-canonical encodings fail
"""

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.canonical.jcs import canonicalize, parse
from casf.errors import (
    CasfError,
    DuplicateKeyError,
    LimitError,
    NumericError,
    SchemaError,
    UnicodeError_,
)
from casf.model.schema import validate_protocol_body

VEC = Path(__file__).resolve().parents[2] / "vectors" / "v1"

ERRORS = {
    "SchemaError": SchemaError,
    "DuplicateKeyError": DuplicateKeyError,
    "NumericError": NumericError,
    "UnicodeError_": UnicodeError_,
    "LimitError": LimitError,
    "CasfError": CasfError,
}

DIGEST_FN = {
    "manifest": crypto.digest_manifest,
    "record": crypto.digest_record,
    "checkpoint": crypto.digest_checkpoint,
    "receipt": crypto.digest_receipt,
    "latest": crypto.digest_latest,
    "status": crypto.digest_status,
}

VERIFY_FN = {
    "manifest": crypto.verify_manifest,
    "record": crypto.verify_record,
    "checkpoint": crypto.verify_checkpoint,
    "receipt": crypto.verify_receipt,
    "latest": crypto.verify_latest,
    "status": crypto.verify_status,
}

SIGN_FN = {
    "manifest": crypto.sign_manifest,
    "record": crypto.sign_record,
    "checkpoint": crypto.sign_checkpoint,
    "receipt": crypto.sign_receipt,
    "latest": crypto.sign_latest,
    "status": crypto.sign_status,
}

KAT = json.loads((VEC / "crypto_kat.json").read_text())


def _keys():
    return {
        role: Ed25519PrivateKey.from_private_bytes(bytes.fromhex(k["seed_hex"]))
        for role, k in KAT["test_keys"].items()
    }


def test_jcs_kat_canonical_bytes():
    for v in json.loads((VEC / "jcs_kat.json").read_text()):
        assert canonicalize(v["input"]).hex() == v["canonical_hex"], v["name"]


def test_jcs_reject_malformed_wire():
    for case in json.loads((VEC / "jcs_reject.json").read_text()):
        wire = bytes.fromhex(case["wire_hex"]) if "wire_hex" in case else case["wire"]
        if case.get("stage") == "canonicalize":
            with pytest.raises(ERRORS[case["expect"]]):
                canonicalize(parse(wire))
        else:
            with pytest.raises(ERRORS[case["expect"]]):
                parse(wire)


def test_oversized_string_rejected():
    with pytest.raises(LimitError):
        canonicalize({"s": "a" * 32769})


def test_crypto_kat_keys():
    for role, entry in KAT["test_keys"].items():
        priv = _keys()[role]
        raw = crypto.public_key_raw(priv)
        assert crypto.b64url_encode(raw) == entry["public_b64"], role
        assert crypto.key_id(raw) == entry["key_id"], role


def test_crypto_kat_bodies_schema_valid():
    for kind, body in KAT["bodies"].items():
        validate_protocol_body(kind, body)


def test_crypto_kat_digests_and_genesis():
    for kind, expected in KAT["digests"].items():
        assert DIGEST_FN[kind](KAT["bodies"][kind]) == expected, kind
    assert crypto.genesis_hash(KAT["digests"]["manifest"]) == KAT["genesis_hash"]


def test_crypto_kat_signatures():
    keys = _keys()
    for kind, entry in KAT["signatures"].items():
        body = KAT["bodies"][kind]
        priv = keys[entry["signed_by"]]
        raw = crypto.public_key_raw(priv)
        assert SIGN_FN[kind](priv, body) == entry["signature"], kind
        VERIFY_FN[kind](raw, body, entry["signature"])


def test_crypto_kat_negative_cases():
    keys = _keys()
    for case in KAT["negative"]:
        if case["name"] == "record_signature_under_manifest_domain":
            log_raw = crypto.public_key_raw(keys["log"])
            with pytest.raises(CasfError):
                crypto.verify_manifest(
                    log_raw,
                    KAT["bodies"]["record"],
                    KAT["signatures"]["record"]["signature"])
        elif case["name"] == "noncanonical_base64url_trailing_bits":
            with pytest.raises(SchemaError):
                crypto.b64url_decode(case["input"])
        else:
            raise AssertionError(f"unknown negative case {case['name']}")
