"""R04/T07: record, checkpoint, outbox and seal commit boundaries."""

import sqlite3

import pytest

from casf.canonical.jcs import canonicalize
from casf.verifier import Result
from casf.writer import SealedError, Writer
from tests.process.support import CommitBarrier, kill, pause, receive, worker
from tests.unit.test_writer import LOG, LOG_ID, _append, _verify_db, _writer


def _crash_append(path, stage, pipe):
    writer = Writer(path, LOG, local_only=True)
    if stage == "before_insert":
        writer._debug_hook = lambda current: pause(pipe, stage) if current == stage else None
    else:
        writer._db.connection = CommitBarrier(
            writer._db.connection, pipe, stage,
            lambda con: con.execute("SELECT envelope FROM records WHERE seq = 2").fetchone()[0])
    _append(writer, 2)
    raise AssertionError("append missed crash barrier")


@pytest.mark.parametrize("stage", ["before_insert", "before_commit", "after_commit"])
def test_killed_append_retries_one_complete_record(tmp_path, stage):
    path = tmp_path / "writer.db"
    writer = _writer(path)
    first = _append(writer, 1)
    writer.close()
    with worker(_crash_append, path, stage) as (process, pipe):
        snapshot = receive(pipe, stage)
        kill(process)
    writer = Writer(path, LOG, local_only=True)
    try:
        assert len(list(writer.records(LOG_ID))) == (2 if stage == "after_commit" else 1)
        retried = _append(writer, 2)
        if stage == "after_commit":
            assert canonicalize(dict(retried)) == snapshot
        assert _append(writer, 2) == retried
        assert _append(writer, 3)["body"]["seq"] == 3
        records = list(writer.records(LOG_ID))
        assert records[0] == first
        assert _verify_db(writer).result == Result.PASS
        assert writer._db.connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert writer._db.connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        writer.close()


def _crash_checkpoint(path, stage, final, pipe):
    writer = Writer(path, LOG, local_only=True)
    writer._db.connection = CommitBarrier(
        writer._db.connection, pipe, stage,
        lambda con: con.execute("SELECT envelope FROM checkpoints").fetchone()[0])
    writer.create_checkpoint(LOG_ID, final=final)
    raise AssertionError("checkpoint missed crash barrier")


@pytest.mark.parametrize("stage", ["before_commit", "after_commit"])
@pytest.mark.parametrize("final", [False, True])
def test_killed_checkpoint_commits_outbox_and_seal_together(tmp_path, stage, final):
    path = tmp_path / "writer.db"
    writer = _writer(path)
    _append(writer, 1)
    writer.close()
    with worker(_crash_checkpoint, path, stage, final) as (process, pipe):
        snapshot = receive(pipe, stage)
        kill(process)
    writer = Writer(path, LOG, local_only=True)
    try:
        con = writer._db.connection
        committed = stage == "after_commit"
        for table in ("checkpoints", "outbox"):
            assert con.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == int(committed)
        assert con.execute("SELECT sealed FROM heads").fetchone()[0] == (
            2 if committed and final else 0)
        if not committed:
            assert writer.pending_checkpoint(LOG_ID) is None
            writer.create_checkpoint(LOG_ID, final=final)
        pending, start, end = writer.pending_checkpoint(LOG_ID)
        assert (start, end) == (1, 1)
        assert pending["body"]["final"] is final
        if committed:
            assert canonicalize(dict(pending)) == snapshot
        if final:
            with pytest.raises(SealedError):
                _append(writer, 2)
        else:
            assert _append(writer, 2)["body"]["seq"] == 2
        assert con.execute("SELECT count(*) FROM checkpoints").fetchone() == (1,)
        assert con.execute("SELECT count(*) FROM outbox").fetchone() == (1,)
    finally:
        writer.close()
    # Read independently after all writer connections close.
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA integrity_check").fetchone() == ("ok",)
