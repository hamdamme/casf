"""R04/R09/R10: storage failures preserve evidence and remain distinguishable."""

import sqlite3

import pytest

from casf.cli import main
from casf.storage import Database
from casf.verifier import Result
from casf.writer import Writer
from tests.unit.test_writer import LOG, LOG_ID, _append, _verify_db, _writer


def test_sqlite_full_preserves_history_and_same_event_retry(tmp_path):
    path = tmp_path / "writer.db"
    writer = _writer(path)
    try:
        first = _append(writer, 1)
        con = writer._db.connection
        limit = con.execute("PRAGMA page_count").fetchone()[0]
        assert con.execute(f"PRAGMA max_page_count={limit}").fetchone()[0] == limit
        event = {"event_id": "123e4567-e89b-42d3-a456-426600000002", "actor": "test",
                 "event_type": "storage-drill", "payload": {"value": "x" * 32000}, "attributes": {}}
        with pytest.raises(sqlite3.OperationalError) as error:
            writer.append(LOG_ID, **event)
        assert error.value.sqlite_errorcode == sqlite3.SQLITE_FULL
        assert not con.in_transaction
        assert list(writer.records(LOG_ID)) == [first]
        assert _verify_db(writer).result is Result.PASS
    finally:
        writer.close()
    writer = Writer(path, LOG, local_only=True)
    try:
        writer._db.connection.execute("PRAGMA max_page_count=10000")
        accepted = writer.append(LOG_ID, **event)
        assert accepted["body"]["seq"] == 2
        assert writer.append(LOG_ID, **event) == accepted
        assert len(list(writer.records(LOG_ID))) == 2
        assert _verify_db(writer).result is Result.PASS
    finally:
        writer.close()


def test_corrupt_database_open_closes_connection(tmp_path, monkeypatch):
    path = tmp_path / "corrupt.db"
    path.write_bytes(b"synthetic corrupt backup" * 100)
    original = sqlite3.connect
    connections = []

    def tracked(*args, **kwargs):
        con = original(*args, **kwargs)
        connections.append(con)
        return con

    monkeypatch.setattr(sqlite3, "connect", tracked)
    with pytest.raises(sqlite3.DatabaseError):
        Database(path)
    assert len(connections) == 1
    try:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connections[0].execute("SELECT 1")
    finally:
        connections[0].close()


def test_cli_corrupt_backup_returns_local_error_without_traceback(tmp_path, capsys):
    path = tmp_path / "corrupt.db"
    original = b"synthetic corrupt backup" * 100
    path.write_bytes(original)
    assert main(["status", "--db", str(path), "--json"]) == 5
    output = capsys.readouterr()
    assert not output.out
    assert output.err == "error: local database failure\n"
    assert path.read_bytes() == original
