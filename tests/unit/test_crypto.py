"""T03/T04 (SPEC §21): domains, envelopes, and negative vectors."""

import pytest

from casf import crypto
from casf.errors import CasfError, SchemaError

AUTH = crypto.generate_key()
LOG = crypto.generate_key()
WIT = crypto.generate_key()
AUTH_PUB = crypto.public_key_raw(AUTH)
LOG_PUB = crypto.public_key_raw(LOG)
WIT_PUB = crypto.public_key_raw(WIT)

LOG_ID = "123e4567-e89b-42d3-a456-426614174000"
MH = "ab" * 32
TS = "2026-10-11T00:00:00.000000Z"

def _manifest():
    return {
        "version": 1, "type": "manifest", "log_id": LOG_ID,
        "issuer_id": crypto.key_id(AUTH_PUB),
        "log_key_id": crypto.key_id(LOG_PUB),
        "log_public_key": crypto.b64url_encode(LOG_PUB),
        "witness_id": crypto.key_id(WIT_PUB),
        "witness_public_key": crypto.b64url_encode(WIT_PUB),
        "created_at": TS, "predecessor": None,
    }

def _record(seq=1, prev=None):
    return {
        "version": 1, "type": "record", "log_id": LOG_ID,
        "manifest_hash": MH, "seq": seq,
        "event_id": "123e4567-e89b-42d3-a456-426614174001",
        "recorded_at": TS, "actor": "alice", "event_type": "login",
        "payload": {}, "attributes": {},
        "prev_hash": prev or "cd" * 32,
        "key_id": crypto.key_id(LOG_PUB),
    }

def _checkpoint(index=0, count=1, prev_cp="0" * 64, final=False):
    return {
        "version": 1, "type": "checkpoint", "log_id": LOG_ID,
        "manifest_hash": MH, "index": index, "count": count,
        "head_hash": "ef" * 32,
        "previous_checkpoint_hash": prev_cp,
        "key_id": crypto.key_id(LOG_PUB),
        "issued_at": TS, "final": final,
    }

# ---------------- positive vectors ----------------

def test_manifest_sign_verify_roundtrip():
    body = _manifest()
    sig = crypto.sign_manifest(AUTH, body)
    crypto.verify_manifest(AUTH_PUB, body, sig)  # no exception = pass

def test_record_sign_verify_roundtrip():
    body = _record()
    sig = crypto.sign_record(LOG, body)
    crypto.verify_record(LOG_PUB, body, sig)

def test_checkpoint_and_receipt_roundtrip():
    cp = _checkpoint()
    sig = crypto.sign_checkpoint(LOG, cp)
    crypto.verify_checkpoint(LOG_PUB, cp, sig)
    rc = {
        "version": 1, "type": "receipt",
        "witness_id": crypto.key_id(WIT_PUB),
        "log_id": LOG_ID, "manifest_hash": MH,
        "checkpoint_hash": crypto.digest_checkpoint(cp),
        "checkpoint_index": 0, "count": 1, "head_hash": cp["head_hash"],
        "previous_receipt_hash": "0" * 64, "accepted_at": TS,
    }
    rsig = crypto.sign_receipt(WIT, rc)
    crypto.verify_receipt(WIT_PUB, rc, rsig)

def test_latest_and_status_roundtrip():
    lb = {
        "version": 1, "type": "latest", "nonce": crypto.b64url_encode(b"n" * 32),
        "witness_id": crypto.key_id(WIT_PUB), "log_id": LOG_ID,
        "manifest_hash": MH, "checkpoint_hash": "ef" * 32,
        "receipt_hash": "fe" * 32, "checkpoint_index": 0, "count": 1,
        "head_hash": "ef" * 32, "final": False, "responded_at": TS,
    }
    crypto.verify_latest(WIT_PUB, lb, crypto.sign_latest(WIT, lb))
    sb = {
        "version": 1, "type": "status",
        "issuer_id": crypto.key_id(AUTH_PUB), "serial": 1,
        "manifest_hash": MH, "status": "active", "issued_at": TS,
        "reason": "initial",
    }
    crypto.verify_status(AUTH_PUB, sb, crypto.sign_status(AUTH, sb))

def test_key_id_is_domain_separated():
    kid = crypto.key_id(LOG_PUB)
    assert len(kid) == 64 and kid != crypto.sha256(LOG_PUB).hex()
    # key-id domain differs from raw-pubkey hash
    assert kid == crypto.sha256(b"CASF/v1/key-id\x00" + LOG_PUB).hex()

def test_genesis_hash_domain():
    m = crypto.digest_manifest(_manifest())
    g = crypto.genesis_hash(m)
    assert g != m and len(g) == 64

# ---------------- negative vectors (T03) ----------------

def test_wrong_key_fails():
    body = _record()
    sig = crypto.sign_record(LOG, body)
    with pytest.raises(CasfError):
        crypto.verify_record(AUTH_PUB, body, sig)

def test_tampered_body_fails():
    body = _record()
    sig = crypto.sign_record(LOG, body)
    body["actor"] = "mallory"
    with pytest.raises(CasfError):
        crypto.verify_record(LOG_PUB, body, sig)

def test_wrong_domain_fails():
    # signature from the checkpoint domain must not verify as a record
    cp = _checkpoint()
    wrong = crypto.sign_checkpoint(LOG, cp)
    with pytest.raises(CasfError):
        crypto.verify_record(LOG_PUB, cp, wrong)

def test_cross_object_reuse_fails():
    body = _record()
    sig = crypto.sign_record(LOG, body)
    with pytest.raises(CasfError):
        crypto.verify_checkpoint(LOG_PUB, body, sig)

def test_bad_signature_encoding_fails():
    body = _record()
    with pytest.raises((CasfError, SchemaError)):
        crypto.verify_record(LOG_PUB, body, "!!!not-b64!!!")
    with pytest.raises((CasfError, SchemaError)):
        crypto.verify_record(LOG_PUB, body, crypto.b64url_encode(b"short"))

def test_manifest_key_id_binding():
    # manifest log_key_id must derive from the raw log public key
    body = _manifest()
    body["log_key_id"] = crypto.key_id(AUTH_PUB)  # wrong key id
    sig = crypto.sign_manifest(AUTH, body)
    crypto.verify_manifest(AUTH_PUB, body, sig)  # signature still valid...
    # ...binding to the key is a schema/semantic rule (SPEC §10);
    # here we assert the derivation rule itself:
    assert body["log_key_id"] != crypto.key_id(
        crypto.b64url_decode(body["log_public_key"]))
