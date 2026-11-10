"""R09: backup publication never exposes an incomplete or replacement copy."""

import errno
import os
import sqlite3
import stat

import pytest

from casf.errors import CasfError
from casf.verifier import Result
from casf.writer import Writer
from tests.unit.test_writer import LOG_ID, MP, _append, _verify_db, _writer


@pytest.fixture
def source(tmp_path):
    writer = _writer(tmp_path / "writer.db")
    try:
        _append(writer, 1)
        destination = tmp_path / "backups"
        destination.mkdir()
        yield writer, destination
    finally:
        writer.close()


class BackupHook:
    def __init__(self, connection, hook):
        self.connection, self.hook = connection, hook

    def backup(self, target):
        def progress(status, remaining, total):
            self.hook()
        self.connection.backup(target, pages=1, progress=progress)

    def close(self):
        self.connection.close()


@pytest.mark.parametrize("failure", ["disk_full", "interrupt"])
def test_interrupted_backup_leaves_no_destination_and_can_retry(source, monkeypatch, failure):
    writer, directory = source
    destination = directory / "backup.db"
    original = writer._db.connection

    def fail():
        if failure == "interrupt":
            raise KeyboardInterrupt()
        raise OSError(errno.ENOSPC, "synthetic backup exhaustion")

    monkeypatch.setattr(writer._db, "connection", BackupHook(original, fail))
    with pytest.raises(KeyboardInterrupt if failure == "interrupt" else OSError):
        writer.backup(destination)
    assert not destination.exists()
    assert list(directory.iterdir()) == []
    monkeypatch.setattr(writer._db, "connection", original)
    assert _verify_db(writer).result is Result.PASS
    writer.backup(destination)
    reader = Writer(destination)
    try:
        assert _verify_db(reader).result is Result.PASS
        assert len(list(reader.records(LOG_ID))) == 1
    finally:
        reader.close()


def test_backup_destination_appears_only_after_complete_copy(source, monkeypatch):
    writer, directory = source
    destination = directory / "backup.db"
    original = writer._db.connection
    observations = []

    def observe():
        observations.append(destination.exists())

    monkeypatch.setattr(writer._db, "connection", BackupHook(original, observe))
    writer.backup(destination)
    assert observations and not any(observations)
    assert destination.is_file()
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600


def test_backup_rejects_dangling_destination_symlink(source):
    writer, directory = source
    target = directory / "unrelated.db"
    destination = directory / "backup.db"
    destination.symlink_to(target)
    with pytest.raises(CasfError, match="already exists"):
        writer.backup(destination)
    assert destination.is_symlink()
    assert not target.exists()


def test_backup_preserves_destination_created_during_copy(source, monkeypatch):
    writer, directory = source
    destination = directory / "backup.db"
    original = writer._db.connection

    def race():
        if not destination.exists():
            destination.write_bytes(b"competing backup")

    monkeypatch.setattr(writer._db, "connection", BackupHook(original, race))
    with pytest.raises(CasfError, match="already exists"):
        writer.backup(destination)
    assert destination.read_bytes() == b"competing backup"
    assert list(directory.iterdir()) == [destination]


@pytest.mark.parametrize("stage", ["file", "directory"])
def test_backup_sync_failure_never_exposes_partial_database(source, monkeypatch, stage):
    writer, directory = source
    destination = directory / "backup.db"
    original = os.fsync

    def fail(fd):
        is_directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        if is_directory == (stage == "directory"):
            raise OSError(errno.ENOSPC, "synthetic sync exhaustion")
        original(fd)

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError):
        writer.backup(destination)
    if stage == "file":
        assert list(directory.iterdir()) == []
    else:
        # Publication succeeded, but durability was not acknowledged.
        assert list(directory.iterdir()) == [destination]
        with sqlite3.connect(destination) as con:
            assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        reader = Writer(destination)
        try:
            assert _verify_db(reader).result is Result.PASS
        finally:
            reader.close()


def _crash_backup(source, destination):
    writer = Writer(source)
    writer._db.connection = BackupHook(writer._db.connection, lambda: os._exit(23))
    writer.backup(destination)


def test_backup_process_exit_does_not_publish_partial_copy(source):
    writer, directory = source
    destination = directory / "backup.db"
    process = MP.Process(target=_crash_backup, args=(writer._db.path, destination))
    process.start()
    process.join(15)
    if process.is_alive():
        process.kill()
        process.join(5)
        pytest.fail("backup child did not exit")
    assert process.exitcode == 23
    assert not destination.exists()
    leftovers = list(directory.iterdir())
    assert leftovers
    assert all(path.is_dir() and stat.S_IMODE(path.stat().st_mode) == 0o700
               for path in leftovers)
    assert _verify_db(writer).result is Result.PASS
    writer.backup(destination)
    reader = Writer(destination)
    try:
        assert _verify_db(reader).result is Result.PASS
    finally:
        reader.close()
