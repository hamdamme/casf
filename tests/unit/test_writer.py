"""R04 / T06 / T07 (SPEC §17, §21): writer and SQLite storage.

Covers transactional append, idempotency by event ID, contiguous
sequences under concurrent writers, and crash recovery outcomes.
"""

import multiprocessing
import os
from hashlib import sha256

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.errors import CasfError
from casf.verifier import Mode, Result, TrustPins, verify
from casf.writer import BusyError, EventIdConflictError, Writer


def _seeded(role):
    # deterministic keys: multiprocessing children re-import this module
    return Ed25519PrivateKey.from_private_bytes(
        sha256(f"casf-writer-test-{role}".encode()).digest())


AUTH = _seeded("authority")
LOG = _seeded("log")
WIT = _seeded("witness")
AUTH_PUB = crypto.public_key_raw(AUTH)
LOG_PUB = crypto.public_key_raw(LOG)
WIT_PUB = crypto.public_key_raw(WIT)

LOG_ID = "123e4567-e89b-42d3-a456-426614174000"
TS = "2026-10-11T00:00:00.000000Z"


def _manifest_envelope():
    body = {
        "version": 1, "type": "manifest", "log_id": LOG_ID,
        "issuer_id": crypto.key_id(AUTH_PUB),
        "log_key_id": crypto.key_id(LOG_PUB),
        "log_public_key": crypto.b64url_encode(LOG_PUB),
        "witness_id": crypto.key_id(WIT_PUB),
        "witness_public_key": crypto.b64url_encode(WIT_PUB),
        "created_at": TS, "predecessor": None,
    }
    return {
        "body": body,
        "manifest_hash": crypto.digest_manifest(body),
        "signature": crypto.sign_manifest(AUTH, body),
    }


def _writer(db_path, **kw):
    w = Writer(db_path, LOG, **kw)
    w.create_log(_manifest_envelope())
    return w


def _append(w, n=1, prefix="ev"):
    return w.append(LOG_ID, event_id=f"123e4567-e89b-42d3-a456-4266{n:08d}",
                    actor="alice", event_type="login",
                    payload={"n": n}, attributes={})


def _verify_db(w):
    env = w.manifest_envelope(LOG_ID)
    records = list(w.records(LOG_ID))
    pins = TrustPins(
        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
        witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
        log_id=LOG_ID, manifest_hash=env["manifest_hash"])
    return verify(env, records, pins, mode=Mode.INTEGRITY)


# ---------------- basic append and idempotency ----------------

def test_create_log_and_first_append(tmp_path):
    w = _writer(tmp_path / "a.db")
    env = _append(w)
    assert env["body"]["seq"] == 1
    assert env["body"]["prev_hash"] == crypto.genesis_hash(
        w.manifest_envelope(LOG_ID)["manifest_hash"])
    crypto.verify_record(LOG_PUB, env["body"], env["signature"])

def test_writer_output_passes_verifier(tmp_path):
    w = _writer(tmp_path / "a.db")
    for n in range(1, 6):
        _append(w, n)
    report = _verify_db(w)
    assert report.result == Result.PASS
    assert report.verified_through == 5

def test_retry_same_event_id_returns_same_record(tmp_path):
    w = _writer(tmp_path / "a.db")
    first = _append(w)
    again = w.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-426600000001",
                     actor="alice", event_type="login",
                     payload={"n": 1}, attributes={})
    assert again == first
    assert len(list(w.records(LOG_ID))) == 1

def test_conflicting_event_id_fails_without_consuming_seq(tmp_path):
    w = _writer(tmp_path / "a.db")
    _append(w)
    with pytest.raises(EventIdConflictError):
        w.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-426600000001",
                 actor="alice", event_type="login",
                 payload={"n": 999}, attributes={})
    nxt = _append(w, 2)
    assert nxt["body"]["seq"] == 2

def test_writer_key_must_match_manifest(tmp_path):
    w = Writer(tmp_path / "a.db", WIT)  # wrong key for this manifest
    with pytest.raises(CasfError):
        w.create_log(_manifest_envelope())

def test_append_to_unknown_log_fails(tmp_path):
    w = _writer(tmp_path / "a.db")
    with pytest.raises(CasfError):
        w.append("123e4567-e89b-42d3-a456-42660000ffff",
                 event_id="123e4567-e89b-42d3-a456-4266000000ff",
                 actor="a", event_type="t", payload={}, attributes={})

def test_lock_contention_returns_busy(tmp_path):
    import sqlite3
    db = tmp_path / "a.db"
    w = _writer(db, busy_timeout_ms=100, max_retries=1, retry_jitter=0)
    blocker = sqlite3.connect(db)
    blocker.execute("BEGIN IMMEDIATE")
    blocker.execute("INSERT INTO heads VALUES ('x', 0, 'ab', 0)")
    try:
        with pytest.raises(BusyError):
            _append(w)
    finally:
        blocker.rollback()
        blocker.close()

# ---------------- T06: concurrent writers ----------------

def _mp_worker(db_path, worker_id, count):
    w = Writer(db_path, LOG)
    for n in range(count):
        w.append(LOG_ID,
                 event_id=f"123e4567-e89b-42d3-a456-{worker_id:04d}{n:08d}",
                 actor="alice", event_type="login",
                 payload={"w": worker_id, "n": n}, attributes={})

def test_concurrent_writers_contiguous_sequence(tmp_path):
    db = tmp_path / "mp.db"
    _writer(db)
    workers, per = 4, 5
    procs = [multiprocessing.Process(target=_mp_worker, args=(db, w, per))
             for w in range(workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
        assert p.exitcode == 0
    w = Writer(db, LOG)
    bodies = [r["body"] for r in w.records(LOG_ID)]
    assert sorted(b["seq"] for b in bodies) == list(range(1, workers * per + 1))
    assert len({b["event_id"] for b in bodies}) == workers * per
    assert _verify_db(w).result == Result.PASS

def _mp_same_event(db_path):
    w = Writer(db_path, LOG)
    try:
        w.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-4266000000aa",
                 actor="alice", event_type="login", payload={}, attributes={})
    except EventIdConflictError:
        pass

def test_concurrent_same_event_id_one_record(tmp_path):
    db = tmp_path / "mp2.db"
    _writer(db)
    procs = [multiprocessing.Process(target=_mp_same_event, args=(db,))
             for _ in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
    w = Writer(db, LOG)
    matches = [r for r in w.records(LOG_ID)
               if r["body"]["event_id"] == "123e4567-e89b-42d3-a456-4266000000aa"]
    assert len(matches) == 1

# ---------------- T07: crash outcomes ----------------

class CrashWriter(Writer):
    def _debug_hook(self, stage):
        if stage == "after_insert":
            os._exit(1)  # simulated power loss before COMMIT


def _mp_crash(db_path):
    w = CrashWriter(db_path, LOG)
    w.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-4266000000cc",
             actor="alice", event_type="login", payload={}, attributes={})


def test_crash_before_commit_is_all_or_none(tmp_path):
    db = tmp_path / "crash.db"
    w = _writer(db)
    _append(w)  # seq 1 committed
    p = multiprocessing.Process(target=_mp_crash, args=(db,))
    p.start()
    p.join(60)
    assert p.exitcode == 1
    w2 = Writer(db, LOG)
    bodies = [r["body"] for r in w2.records(LOG_ID)]
    assert [b["seq"] for b in bodies] == [1]  # no partial state
    # retry with the same event id resolves the uncertain outcome
    env = w2.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-4266000000cc",
                    actor="alice", event_type="login", payload={}, attributes={})
    assert env["body"]["seq"] == 2
    assert _verify_db(w2).result == Result.PASS

def test_committed_record_survives_restart(tmp_path):
    db = tmp_path / "restart.db"
    w = _writer(db)
    first = _append(w)
    del w
    w2 = Writer(db, LOG)
    again = w2.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-426600000001",
                      actor="alice", event_type="login",
                      payload={"n": 1}, attributes={})
    assert again == first

def test_settings_verified_at_startup(tmp_path):
    # Database refuses to open without the SPEC 17 settings; check what
    # its own verified connection reports. foreign_keys is per
    # connection in SQLite, so a raw second connection proves nothing.
    from casf.storage import Database
    db = tmp_path / "s.db"
    _writer(db)
    d = Database(db)
    con = d.connection
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert con.execute("PRAGMA synchronous").fetchone()[0] == 2  # FULL
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    d.close()
