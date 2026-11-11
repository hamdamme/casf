"""R05/T22: killed witness transactions and exact stored receipt replay."""

import pytest

from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.errors import CasfError
from casf.witness import ConflictError, Witness
from tests.process.support import (
    BeginSignal,
    CommitBarrier,
    finish,
    kill,
    receive,
    worker,
)
from tests.unit.test_witness import _checkpoint, _state, _witness
from tests.unit.test_writer import AUTH_PUB, LOG_ID, WIT, _append, _writer


def _open(path):
    return Witness(path, WIT, authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
                   busy_timeout_ms=30_000)


def _crash_accept(path, checkpoint, records, stage, pipe):
    witness = _open(path)
    witness._db.connection = CommitBarrier(
        witness._db.connection, pipe, stage,
        lambda con: con.execute("SELECT envelope FROM w_receipts").fetchone()[0])
    witness.submit(LOG_ID, checkpoint, records)
    raise AssertionError("witness missed crash barrier")


def _journal(witness):
    return tuple(witness._db.connection.execute(f"SELECT * FROM {table}").fetchall()
                 for table in ("w_state", "w_checkpoints", "w_receipts", "w_record_digests"))


@pytest.mark.parametrize("stage", ["before_commit", "after_commit"])
@pytest.mark.parametrize("final", [False, True])
def test_killed_witness_replays_committed_receipt(tmp_path, stage, final):
    writer = _writer(tmp_path / "writer.db")
    _append(writer, 1)
    checkpoint = _checkpoint(writer, 0, 1, final=final)
    alternative = _checkpoint(writer, 0, 1, final=not final)
    records = list(writer.records(LOG_ID))
    writer.close()
    path = tmp_path / "wit.db"
    witness = _witness(tmp_path)
    before = _journal(witness)
    witness.close()
    with worker(_crash_accept, path, checkpoint, records, stage) as (process, pipe):
        snapshot = receive(pipe, stage)
        kill(process)
    witness = _open(path)
    try:
        committed = stage == "after_commit"
        if not committed:
            assert _journal(witness) == before
        else:
            assert _state(path) == (1, records[0]["record_hash"], 0,
                                   checkpoint["checkpoint_hash"], int(final))
        receipt = witness.submit(LOG_ID, checkpoint, records)
        if committed:
            assert canonicalize(receipt) == snapshot
        accepted = _journal(witness)
        assert witness.submit(LOG_ID, checkpoint, records) == receipt
        with pytest.raises(CasfError if final else ConflictError):
            witness.submit(LOG_ID, alternative, records)
        assert _journal(witness) == accepted
        assert [len(rows) for rows in accepted] == [1, 1, 1, 1]
        con = witness._db.connection
        assert con.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        witness.close()


def _competing_accept(path, checkpoint, records, pipe):
    witness = _open(path)
    witness._db.connection = BeginSignal(witness._db.connection, pipe)
    try:
        try:
            receipt = witness.submit(LOG_ID, checkpoint, records)
        except ConflictError:
            pipe.send(("result", "conflict"))
        else:
            pipe.send(("result", receipt))
    finally:
        witness.close()


@pytest.mark.parametrize("stage", ["before_commit", "after_commit"])
def test_competing_witness_process_accepts_only_one_branch_after_kill(tmp_path, stage):
    writer = _writer(tmp_path / "writer.db")
    _append(writer, 1)
    checkpoint = _checkpoint(writer, 0, 1)
    records = list(writer.records(LOG_ID))
    writer.close()
    fork = _writer(tmp_path / "fork.db")
    _append(fork, 2)  # A different signed event at the same sequence position.
    alternative = _checkpoint(fork, 0, 1)
    fork_records = list(fork.records(LOG_ID))
    fork.close()
    assert records[0]["body"]["seq"] == fork_records[0]["body"]["seq"] == 1
    assert records[0]["record_hash"] != fork_records[0]["record_hash"]
    path = tmp_path / "wit.db"
    _witness(tmp_path).close()
    with worker(_crash_accept, path, checkpoint, records, stage) as (first, first_pipe):
        original_receipt = receive(first_pipe, stage)
        with worker(_competing_accept, path, alternative, fork_records) as (second, second_pipe):
            receive(second_pipe, "attempting")
            kill(first)
            result = receive(second_pipe, "result")
            finish(second)
    witness = _open(path)
    try:
        accepted = _journal(witness)
        if stage == "after_commit":
            assert result == "conflict"
            assert canonicalize(witness.submit(LOG_ID, checkpoint, records)) == original_receipt
        else:
            assert result["body"]["checkpoint_hash"] == alternative["checkpoint_hash"]
            assert witness.submit(LOG_ID, alternative, fork_records) == result
            with pytest.raises(ConflictError):
                witness.submit(LOG_ID, checkpoint, records)
        assert _journal(witness) == accepted
        assert [len(rows) for rows in accepted] == [1, 1, 1, 1]
    finally:
        witness.close()
