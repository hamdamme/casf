"""R08 (SPEC §12, §16; T13, T14): lifecycle operations.

Covers the encrypted key provider, final sealing, linked epoch
rotation with predecessor evidence, terminal revocation, and status
serial retention outside the log store.
"""

import os
import stat

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.keys import generate_key, load_key
from casf.lifecycle import (
    StatusBook,
    rotate_epoch,
    sign_status,
    verify_predecessor,
)
from casf.verifier import Mode, Result, TrustPins, TrustStatus, verify
from casf.witness import Witness
from casf.writer import SealedError
from tests.status import active_status
from tests.unit.test_writer import (
    AUTH,
    AUTH_PUB,
    LOG_ID,
    LOG_PUB,
    TS,
    WIT,
    WIT_PUB,
    _append,
    _manifest_envelope,
    _writer,
)

PASS = b"test-passphrase"  # test only, never a real secret


def _seeded(role):
    from hashlib import sha256

    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    return Ed25519PrivateKey.from_private_bytes(
        sha256(f"casf-writer-test-{role}".encode()).digest())


# ---------------- encrypted key provider (SPEC §16) ----------------

def test_key_roundtrip(tmp_path):
    path = tmp_path / "log.key"
    generate_key("log", path, passphrase=PASS)
    key = load_key(path, passphrase=PASS)
    assert crypto.public_key_raw(key) == crypto.public_key_raw(
        load_key(path, passphrase=PASS))
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600  # owner only

def test_key_refuses_overwrite(tmp_path):
    path = tmp_path / "log.key"
    generate_key("log", path, passphrase=PASS)
    with pytest.raises(CasfError):
        generate_key("log", path, passphrase=PASS)

def test_key_wrong_passphrase_rejected(tmp_path):
    path = tmp_path / "log.key"
    generate_key("log", path, passphrase=PASS)
    with pytest.raises(CasfError):
        load_key(path, passphrase=b"wrong-passphrase")

# ---------------- sealing (SPEC §12) ----------------

def test_seal_log_final_checkpoint(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    _append(w, 2)
    cp = w.seal_log(LOG_ID)
    assert cp["body"]["final"] is True
    assert cp["body"]["count"] == 2
    with pytest.raises(SealedError):
        _append(w, 3)

def test_sealed_evidence_stays_inspectable(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    cp = w.seal_log(LOG_ID)
    assert cp["body"]["count"] == 1
    pins = TrustPins(
        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
        witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
        log_id=LOG_ID, manifest_hash=None)
    report = verify(w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)),
                    pins, mode=Mode.INTEGRITY,
                    status_envelopes=[active_status(AUTH, w.manifest_envelope(LOG_ID)["manifest_hash"]) ])
    assert report.result == Result.PASS  # old public evidence inspectable

# ---------------- epoch rotation (SPEC §16, T14) ----------------

def _final_evidence(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    _append(w, 2)
    wit = Witness(tmp_path / "wit.db", WIT,
                  authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    wit.register_log(_manifest_envelope())
    cp = w.create_checkpoint(LOG_ID, final=True)
    _env, from_seq, to_seq = w.pending_checkpoint(LOG_ID)
    records = list(w.records(LOG_ID))[from_seq - 1:to_seq]
    receipt = wit.submit(LOG_ID, cp, records)
    w.record_receipt(LOG_ID, receipt)
    return w, wit, cp, receipt


def test_rotation_links_new_epoch(tmp_path):
    w, _wit, cp, receipt = _final_evidence(tmp_path)
    new_log = _seeded("log-epoch-2")
    new_id = "123e4567-e89b-42d3-a456-426614174111"
    env = rotate_epoch(
        authority_priv=AUTH, new_log_priv=new_log, new_log_id=new_id,
        witness_pub=WIT_PUB, created_at=TS,
        final_checkpoint=cp, final_receipt=receipt)
    body = env["body"]
    assert body["predecessor"] == {
        "log_id": LOG_ID,
        "manifest_hash": w.manifest_envelope(LOG_ID)["manifest_hash"],
        "final_checkpoint_hash": cp["checkpoint_hash"],
        "final_receipt_hash": receipt["receipt_hash"],
    }
    assert body["log_key_id"] == crypto.key_id(crypto.public_key_raw(new_log))
    verify_predecessor(env, cp, receipt, LOG_PUB, WIT_PUB)  # link verifies

def test_rotation_rejects_nonfinal_checkpoint(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    cp = w.create_checkpoint(LOG_ID)  # not final
    _env, from_seq, to_seq = w.pending_checkpoint(LOG_ID)
    wit = Witness(tmp_path / "wit.db", WIT,
                  authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    wit.register_log(_manifest_envelope())
    receipt = wit.submit(LOG_ID, cp,
                         list(w.records(LOG_ID))[from_seq - 1:to_seq])
    with pytest.raises(CasfError):
        rotate_epoch(
            authority_priv=AUTH, new_log_priv=_seeded("log-epoch-2"),
            new_log_id="123e4567-e89b-42d3-a456-426614174111",
            witness_pub=WIT_PUB, created_at=TS,
            final_checkpoint=cp, final_receipt=receipt)

def test_predecessor_tampering_detected(tmp_path):
    _, _, cp, receipt = _final_evidence(tmp_path)
    env = rotate_epoch(
        authority_priv=AUTH, new_log_priv=_seeded("log-epoch-2"),
        new_log_id="123e4567-e89b-42d3-a456-426614174111",
        witness_pub=WIT_PUB, created_at=TS,
        final_checkpoint=cp, final_receipt=receipt)
    forged = dict(cp)
    forged["checkpoint_hash"] = "ff" * 32
    with pytest.raises(CasfError):
        verify_predecessor(env, forged, receipt, LOG_PUB, WIT_PUB)

def test_emergency_epoch_marks_discontinuity(tmp_path):
    """Emergency restart: predecessor is null, the gap is explicit."""
    new_log = _seeded("log-emergency")
    body = {
        "version": 1, "type": "manifest",
        "log_id": "123e4567-e89b-42d3-a456-426614174222",
        "issuer_id": crypto.key_id(AUTH_PUB),
        "log_key_id": crypto.key_id(crypto.public_key_raw(new_log)),
        "log_public_key": crypto.b64url_encode(
            crypto.public_key_raw(new_log)),
        "witness_id": crypto.key_id(WIT_PUB),
        "witness_public_key": crypto.b64url_encode(WIT_PUB),
        "created_at": TS, "predecessor": None,  # documented discontinuity
    }
    env = {"body": body, "manifest_hash": crypto.digest_manifest(body),
           "signature": crypto.sign_manifest(AUTH, body)}
    pins = TrustPins(
        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
        witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
        log_id=body["log_id"], manifest_hash=None)
    report = verify(env, [], pins, mode=Mode.INTEGRITY,
                    status_envelopes=[active_status(AUTH, env["manifest_hash"]) ])
    assert report.result == Result.PASS  # inspectable, continuity lost
    assert body["predecessor"] is None  # gap is visible, never hidden

# ---------------- status statements and serials (SPEC §16, T13) ----------------

def _status(serial, status="active", mh="ab" * 32, reason=""):
    return sign_status(AUTH, serial=serial, manifest_hash=mh,
                       status=status, issued_at=TS, reason=reason)


def test_status_statement_verifies(tmp_path):
    w = _writer(tmp_path / "w.db")
    mh = w.manifest_envelope(LOG_ID)["manifest_hash"]
    env = _status(1, mh=mh)
    assert env["body"]["type"] == "status"
    crypto.verify_status(AUTH_PUB, env["body"], env["signature"])
    pins = TrustPins(
        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
        witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
        log_id=LOG_ID, manifest_hash=None)
    revoked = _status(2, status="revoked", mh=mh, reason="key compromise")
    report = verify(w.manifest_envelope(LOG_ID), [], pins,
                    mode=Mode.INTEGRITY, status_envelopes=[revoked])
    assert report.trust_status == TrustStatus.REVOKED
    assert report.result == Result.FAIL  # revoked trust fails

def test_status_book_retains_largest_serial(tmp_path):
    book = StatusBook(tmp_path / "status.json")
    mh = "ab" * 32
    assert book.observe(_status(2, mh=mh), AUTH_PUB) is True
    assert book.observed_serial(mh) == 2
    # serial rollback never moves the retained high water mark
    assert book.observe(_status(1, mh=mh), AUTH_PUB) is False
    assert book.observed_serial(mh) == 2
    book2 = StatusBook(tmp_path / "status.json")  # retained across restart
    assert book2.observed_serial(mh) == 2

def test_revocation_is_terminal(tmp_path):
    book = StatusBook(tmp_path / "status.json")
    mh = "ab" * 32
    assert book.observe(_status(1, status="revoked", mh=mh,
                                reason="compromise"), AUTH_PUB) is True
    # a later active statement cannot unrevoke
    assert book.observe(_status(2, status="active", mh=mh),
                        AUTH_PUB) is False

def test_status_book_rejects_bad_signature(tmp_path):
    book = StatusBook(tmp_path / "status.json")
    env = _status(1)
    with pytest.raises(CasfError):
        book.observe(env, WIT_PUB)  # wrong authority key
