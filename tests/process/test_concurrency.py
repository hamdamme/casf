"""R04/T06: process death releases SQLite locks for retries and new events."""

import pytest

from casf.canonical.jcs import canonicalize
from casf.verifier import Result
from casf.writer import Writer
from tests.process.support import BeginSignal, finish, kill, receive, worker
from tests.process.test_writer_crashes import _crash_append
from tests.unit.test_writer import LOG, LOG_ID, _append, _verify_db, _writer


def _waiting_append(path, event, pipe):
    writer = Writer(path, LOG, local_only=True, busy_timeout_ms=30_000)
    writer._db.connection = BeginSignal(writer._db.connection, pipe)
    try:
        result = _append(writer, event)
        pipe.send(("result", canonicalize(dict(result))))
    finally:
        writer.close()


@pytest.mark.parametrize("stage", ["before_commit", "after_commit"])
@pytest.mark.parametrize("event", [2, 3])
def test_killed_writer_allows_competing_append_or_retry(tmp_path, stage, event):
    path = tmp_path / "writer.db"
    writer = _writer(path)
    _append(writer, 1)
    writer.close()
    with worker(_crash_append, path, stage) as (first, first_pipe):
        snapshot = receive(first_pipe, stage)
        with worker(_waiting_append, path, event) as (second, second_pipe):
            receive(second_pipe, "attempting")
            kill(first)
            result = receive(second_pipe, "result")
            finish(second)
    writer = Writer(path, LOG, local_only=True)
    try:
        assert canonicalize(dict(_append(writer, event))) == result
        retried = _append(writer, 2)
        if stage == "after_commit":
            assert canonicalize(dict(retried)) == snapshot
        records = list(writer.records(LOG_ID))
        count = 2 if event == 2 else 3
        assert [row["body"]["seq"] for row in records] == list(range(1, count + 1))
        assert len({row["body"]["event_id"] for row in records}) == count
        assert _verify_db(writer).result == Result.PASS
    finally:
        writer.close()
