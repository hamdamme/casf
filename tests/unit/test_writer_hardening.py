"""SPEC §17/§18 hardening: immutability triggers, backup, startup checks,
and the remaining T07 kill points."""

import os
import sqlite3

import pytest

from casf.errors import CasfError
from casf.verifier import Result
from casf.writer import Writer
from tests.unit.test_writer import (
    LOG,
    LOG_ID,
    MP,
    _append,
    _verify_db,
    _writer,
)


def _tamper(db, sql):
    con = sqlite3.connect(db)
    try:
        con.execute(sql)
        con.commit()
    finally:
        con.close()


# ---------------- append-only triggers (SPEC §17) ----------------

def test_records_reject_update(tmp_path):
    db = tmp_path / "t.db"
    w = _writer(db)
    _append(w)  # triggers fire per row; the table must not be empty
    with pytest.raises(sqlite3.IntegrityError):
        _tamper(db, "UPDATE records SET record_hash = 'ff' || substr(record_hash, 3)")

def test_records_reject_delete(tmp_path):
    db = tmp_path / "t.db"
    w = _writer(db)
    _append(w)
    with pytest.raises(sqlite3.IntegrityError):
        _tamper(db, "DELETE FROM records")

def test_manifests_reject_update(tmp_path):
    db = tmp_path / "t.db"
    _writer(db)
    with pytest.raises(sqlite3.IntegrityError):
        _tamper(db, "UPDATE manifests SET manifest_hash = 'ab'")

# ---------------- consistent backup (SPEC §18) ----------------

def test_backup_produces_verifiable_copy(tmp_path):
    db = tmp_path / "b.db"
    w = _writer(db)
    for n in range(1, 4):
        _append(w, n)
    backup = tmp_path / "backup.db"
    w.backup(backup)
    w2 = Writer(backup, LOG)
    assert _verify_db(w2).result == Result.PASS
    assert [r["body"]["seq"] for r in w2.records(LOG_ID)] == [1, 2, 3]

def test_backup_does_not_overwrite(tmp_path):
    db = tmp_path / "b.db"
    w = _writer(db)
    _append(w)
    backup = tmp_path / "backup.db"
    backup.write_text("existing")
    with pytest.raises(CasfError):
        w.backup(backup)

# ---------------- startup verification (SPEC §17) ----------------

def test_startup_detects_head_tampering(tmp_path):
    db = tmp_path / "s.db"
    w = _writer(db)
    _append(w)
    w.close()
    # heads has no trigger (the writer updates it); corrupt it directly
    _tamper(db, "UPDATE heads SET count = 99")
    with pytest.raises(CasfError, match="head"):
        Writer(db, LOG)

def test_startup_detects_missing_record(tmp_path):
    db = tmp_path / "s.db"
    w = _writer(db)
    for n in range(1, 3):
        _append(w, n)
    w.close()
    con = sqlite3.connect(db)
    con.execute("PRAGMA foreign_keys=OFF")
    # Change the first character based on its current value so this
    # corruption always differs from the valid hash.
    (head_hash,) = con.execute(
        "SELECT head_hash FROM heads").fetchone()
    first = "0" if head_hash[0] != "0" else "1"
    corrupted_hash = first + head_hash[1:]
    assert corrupted_hash != head_hash
    con.execute("UPDATE heads SET head_hash = ?", (corrupted_hash,))
    con.commit()
    con.close()
    with pytest.raises(CasfError, match="head"):
        Writer(db, LOG)

def test_clean_startup_passes(tmp_path):
    db = tmp_path / "ok.db"
    w = _writer(db)
    _append(w)
    w.close()
    Writer(db, LOG).close()  # no error

# ---------------- T07 remaining kill points ----------------

class CrashBeforeInsert(Writer):
    def _debug_hook(self, stage):
        if stage == "before_insert":
            os._exit(1)


class CrashAfterCommit(Writer):
    def _debug_hook(self, stage):
        if stage == "after_commit":
            os._exit(1)


def _mp_crash_before(db_path):
    CrashBeforeInsert(db_path, LOG).append(
        LOG_ID, event_id="123e4567-e89b-42d3-a456-4266000000b1",
        actor="a", event_type="t", payload={}, attributes={})


def _mp_crash_after_commit(db_path):
    CrashAfterCommit(db_path, LOG).append(
        LOG_ID, event_id="123e4567-e89b-42d3-a456-4266000000b2",
        actor="a", event_type="t", payload={}, attributes={})


def test_crash_before_insert_leaves_nothing(tmp_path):
    db = tmp_path / "c.db"
    _writer(db)
    p = MP.Process(target=_mp_crash_before, args=(db,))
    p.start()
    p.join(60)
    assert p.exitcode == 1
    w = Writer(db, LOG)
    assert list(w.records(LOG_ID)) == []
    # the same event id is still free to use
    env = w.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-4266000000b1",
                   actor="a", event_type="t", payload={}, attributes={})
    assert env["body"]["seq"] == 1

def test_crash_after_commit_retry_returns_committed_record(tmp_path):
    db = tmp_path / "c.db"
    _writer(db)
    p = MP.Process(target=_mp_crash_after_commit, args=(db,))
    p.start()
    p.join(60)
    assert p.exitcode == 1
    # the caller never got a response, but the append committed; a same
    # ID retry must return the original record, not append a new one
    w = Writer(db, LOG)
    env = w.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-4266000000b2",
                   actor="a", event_type="t", payload={}, attributes={})
    assert env["body"]["seq"] == 1
    assert len(list(w.records(LOG_ID))) == 1
    assert _verify_db(w).result == Result.PASS

# ---------------- transient contention resolves ----------------

def test_retry_succeeds_after_brief_contention(tmp_path):
    import threading
    import time as time_mod
    db = tmp_path / "r.db"
    w = _writer(db, busy_timeout_ms=100, max_retries=10, retry_jitter=0.05)
    def hold_and_release():
        # sqlite3 connections are bound to their creating thread
        blocker = sqlite3.connect(db)
        blocker.execute("BEGIN IMMEDIATE")
        blocker.execute("INSERT INTO heads VALUES ('tmp', 0, 'ab', 0)")
        time_mod.sleep(0.3)
        blocker.rollback()
        blocker.close()
    t = threading.Thread(target=hold_and_release)
    t.start()
    time_mod.sleep(0.1)  # let the blocker take the write lock first
    env = _append(w)  # must wait, retry, and succeed
    t.join()
    assert env["body"]["seq"] == 1
