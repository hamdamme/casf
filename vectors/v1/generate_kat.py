"""Regenerate the frozen casf-v1 conformance vectors deterministically.

Run from the repository root:  python vectors/v1/generate_kat.py

- jcs_kat.json is NOT rewritten. It was independently cross checked
  against the rfc8785 reference package on 2026-10-11 and is frozen;
  this script only verifies that it still matches the implementation.
- crypto_kat.json and jcs_reject.json are regenerated deterministically.
  Keys derive from fixed seeds and are test keys only, never for use
  outside the test suite (SPEC §21).
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.model.schema import validate_protocol_body

VEC = ROOT / "vectors" / "v1"

TS = "2026-01-01T00:00:00.000000Z"
ZERO = "0" * 64
LOG_ID = "11111111-2222-4333-8444-555555555555"
EVENT_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
ROLES = ("authority", "log", "witness")


def role_key(role: str) -> Ed25519PrivateKey:
    seed = hashlib.sha256(f"casf-kat-{role}".encode("ascii")).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def main() -> int:
    keys = {role: role_key(role) for role in ROLES}
    pubs = {role: crypto.public_key_raw(k) for role, k in keys.items()}
    test_keys = {
        role: {
            "seed_hex": hashlib.sha256(f"casf-kat-{role}".encode("ascii")).hexdigest(),
            "public_b64": crypto.b64url_encode(pubs[role]),
            "key_id": crypto.key_id(pubs[role]),
        }
        for role in ROLES
    }

    manifest = {
        "version": 1, "type": "manifest", "log_id": LOG_ID,
        "issuer_id": test_keys["authority"]["key_id"],
        "log_key_id": test_keys["log"]["key_id"],
        "log_public_key": test_keys["log"]["public_b64"],
        "witness_id": test_keys["witness"]["key_id"],
        "witness_public_key": test_keys["witness"]["public_b64"],
        "created_at": TS, "predecessor": None,
    }
    mh = crypto.digest_manifest(manifest)
    record = {
        "version": 1, "type": "record", "log_id": LOG_ID, "manifest_hash": mh,
        "seq": 1, "event_id": EVENT_ID, "recorded_at": TS,
        "actor": "alice", "event_type": "login",
        "payload": {"ip": "203.0.113.10"}, "attributes": {},
        "prev_hash": ZERO, "key_id": test_keys["log"]["key_id"],
    }
    rh = crypto.digest_record(record)
    checkpoint = {
        "version": 1, "type": "checkpoint", "log_id": LOG_ID, "manifest_hash": mh,
        "index": 0, "count": 1, "head_hash": rh,
        "previous_checkpoint_hash": ZERO,
        "key_id": test_keys["log"]["key_id"], "issued_at": TS, "final": False,
    }
    ch = crypto.digest_checkpoint(checkpoint)
    receipt = {
        "version": 1, "type": "receipt", "witness_id": test_keys["witness"]["key_id"],
        "log_id": LOG_ID, "manifest_hash": mh, "checkpoint_hash": ch,
        "checkpoint_index": 0, "count": 1, "head_hash": rh,
        "previous_receipt_hash": ZERO, "accepted_at": TS,
    }
    rc = crypto.digest_receipt(receipt)
    nonce = crypto.b64url_encode(hashlib.sha256(b"casf-kat-nonce").digest()[:16])
    latest = {
        "version": 1, "type": "latest", "nonce": nonce,
        "witness_id": test_keys["witness"]["key_id"], "log_id": LOG_ID,
        "manifest_hash": mh, "checkpoint_hash": ch, "receipt_hash": rc,
        "checkpoint_index": 0, "count": 1, "head_hash": rh,
        "final": False, "responded_at": TS,
    }
    status = {
        "version": 1, "type": "status", "issuer_id": test_keys["authority"]["key_id"],
        "serial": 1, "manifest_hash": mh, "status": "active",
        "issued_at": TS, "reason": "",
    }

    bodies = {
        "manifest": manifest, "record": record, "checkpoint": checkpoint,
        "receipt": receipt, "latest": latest, "status": status,
    }
    for kind, body in bodies.items():
        validate_protocol_body(kind, body)

    digests = {
        "manifest": mh, "record": rh, "checkpoint": ch,
        "receipt": rc,
        "latest": crypto.digest_latest(latest),
        "status": crypto.digest_status(status),
    }
    signers = {
        "manifest": ("authority", crypto.sign_manifest),
        "record": ("log", crypto.sign_record),
        "checkpoint": ("log", crypto.sign_checkpoint),
        "receipt": ("witness", crypto.sign_receipt),
        "latest": ("witness", crypto.sign_latest),
        "status": ("authority", crypto.sign_status),
    }
    signatures = {
        kind: {"signed_by": role, "signature": fn(keys[role], bodies[kind])}
        for kind, (role, fn) in signers.items()
    }

    crypto_kat = {
        "description": "Frozen casf-v1 cryptographic known answer vectors "
                       "(SPEC 21). Deterministic; test keys only.",
        "test_keys": test_keys,
        "bodies": bodies,
        "digests": digests,
        "genesis_hash": crypto.genesis_hash(mh),
        "signatures": signatures,
        "negative": [
            {
                "name": "record_signature_under_manifest_domain",
                "verify_as": "manifest",
                "body": "record",
                "signature_of": "record",
                "expect": "CasfError",
            },
            {
                "name": "noncanonical_base64url_trailing_bits",
                "input": "AR",
                "expect": "SchemaError",
            },
        ],
    }

    jcs_reject = [
        {"name": "byte_order_mark", "wire_hex": "efbbbf7b7d", "expect": "SchemaError"},
        {"name": "invalid_utf8", "wire_hex": "7b2261223ac3287d", "expect": "SchemaError"},
        {"name": "duplicate_key", "wire": '{"a":1,"a":2}', "expect": "DuplicateKeyError"},
        {"name": "float", "wire": '{"x":1.5}', "expect": "NumericError"},
        {"name": "exponent", "wire": '{"x":1e3}', "expect": "NumericError"},
        {"name": "negative_zero", "wire": '{"x":-0}', "expect": "NumericError"},
        {"name": "nan", "wire": "NaN", "expect": "NumericError"},
        {"name": "lone_surrogate", "wire": '"\\ud800"', "expect": "UnicodeError_"},
        {"name": "depth_overflow", "wire": "[" * 17 + "1" + "]" * 17,
         "stage": "canonicalize", "expect": "LimitError"},
    ]

    # Frozen JCS KATs: verify only, never rewrite.
    from casf.canonical.jcs import canonicalize
    jcs_kat = json.loads((VEC / "jcs_kat.json").read_text())
    for v in jcs_kat:
        actual = canonicalize(v["input"]).hex()
        if actual != v["canonical_hex"]:
            raise SystemExit(f"jcs_kat drift on {v['name']}: {actual} != {v['canonical_hex']}")

    (VEC / "crypto_kat.json").write_text(json.dumps(crypto_kat, indent=1) + "\n")
    (VEC / "jcs_reject.json").write_text(json.dumps(jcs_reject, indent=1) + "\n")
    print("jcs_kat.json verified (frozen), crypto_kat.json and jcs_reject.json regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
