"""R09: destination WAL/SHM must not substitute the published snapshot."""

import os
import stat
from pathlib import Path

import pytest

from casf.errors import CasfError
from casf.storage import migrate_database
from casf.verifier import Result
from casf.writer import Writer
from tests.unit.test_backup_failures import BackupHook
from tests.unit.test_storage_migrations import legacy, rows
from tests.unit.test_writer import LOG_ID, _append, _verify_db, _writer


def stale_wal(destination):
    old = _writer(destination)
    try:
        _append(old, 2)
        wal = Path(str(destination) + '-wal').read_bytes()
        assert len(wal) > 32
    finally:
        old.close()
    destination.unlink()
    Path(str(destination) + '-wal').write_bytes(wal)
    return wal


@pytest.fixture(params=['backup', 'writer-migration', 'witness-migration'])
def operation(tmp_path, request):
    destination = tmp_path / 'destination.db'
    if request.param == 'backup':
        writer = _writer(tmp_path / 'source.db')
        _append(writer, 1)
        source = Path(writer._db.path)
        publish = lambda: writer.backup(destination)
    else:
        writer = None
        kind = request.param.split('-')[0]
        source = legacy(tmp_path / 'source.db', kind)
        publish = lambda: migrate_database(source, destination, kind=kind)
    original = rows(source)
    before = source.read_bytes()
    yield destination, publish
    assert source.read_bytes() == before
    assert rows(source) == original
    if writer is not None:
        assert _verify_db(writer).result is Result.PASS
        writer.close()


@pytest.mark.parametrize('suffix', ['', '-wal', '-shm'])
@pytest.mark.parametrize('dangling', [False, True])
def test_destination_artifacts_are_preserved(operation, suffix, dangling):
    destination, publish = operation
    artifact = Path(str(destination) + suffix)
    missing = destination.parent / 'missing'
    if dangling:
        artifact.symlink_to(missing)
    else:
        artifact.write_bytes(b'preexisting evidence')
    with pytest.raises(CasfError, match='already exists'):
        publish()
    if dangling:
        assert artifact.is_symlink() and artifact.readlink() == missing
        assert not missing.exists()
    else:
        assert artifact.read_bytes() == b'preexisting evidence'
    if suffix:
        assert not destination.exists()


def test_valid_stale_wal_is_rejected_before_backup_publication(tmp_path):
    destination = tmp_path / 'destination.db'
    wal = stale_wal(destination)
    source = _writer(tmp_path / 'source.db')
    try:
        _append(source, 1)
        before = list(source.records(LOG_ID))
        with pytest.raises(CasfError, match='already exists'):
            source.backup(destination)
        assert not destination.exists()
        assert Path(str(destination) + '-wal').read_bytes() == wal
        assert list(source.records(LOG_ID)) == before
        assert _verify_db(source).result is Result.PASS
    finally:
        source.close()


@pytest.mark.parametrize('kind', ['writer', 'witness'])
def test_migration_refuses_populated_destination_wal(tmp_path, kind):
    destination = tmp_path / 'destination.db'
    wal = stale_wal(destination)
    source = legacy(tmp_path / 'legacy.db', kind)
    before, original = source.read_bytes(), rows(source)
    with pytest.raises(CasfError, match='already exists'):
        migrate_database(source, destination, kind=kind)
    assert not destination.exists()
    assert Path(str(destination) + '-wal').read_bytes() == wal
    assert source.read_bytes() == before and rows(source) == original


@pytest.mark.parametrize('suffix', ['-wal', '-shm'])
def test_sidecar_created_during_copy_prevents_publication(tmp_path, monkeypatch, suffix):
    destination = tmp_path / 'destination.db'
    artifact = Path(str(destination) + suffix)
    source = _writer(tmp_path / 'source.db')
    original = source._db.connection
    try:
        _append(source, 1)
        records = list(source.records(LOG_ID))
        monkeypatch.setattr(source._db, 'connection', BackupHook(original,
                            lambda: artifact.write_bytes(b'concurrent evidence')))
        with pytest.raises(CasfError, match='already exists'):
            source.backup(destination)
        assert not destination.exists()
        assert artifact.read_bytes() == b'concurrent evidence'
        monkeypatch.setattr(source._db, 'connection', original)
        assert list(source.records(LOG_ID)) == records
    finally:
        source.close()


@pytest.mark.parametrize('suffix', ['-wal', '-shm'])
@pytest.mark.parametrize('stage', ['link', 'directory_sync'])
def test_sidecar_publication_race_cannot_report_success(operation, monkeypatch, suffix, stage):
    destination, publish = operation
    artifact = Path(str(destination) + suffix)
    link, sync = os.link, os.fsync

    def racing_link(src, dst):
        result = link(src, dst)
        if Path(dst) == destination and stage == 'link':
            artifact.write_bytes(b'concurrent evidence')
        return result

    def racing_sync(fd):
        sync(fd)
        if stat.S_ISDIR(os.fstat(fd).st_mode) and stage == 'directory_sync':
            artifact.write_bytes(b'concurrent evidence')

    monkeypatch.setattr('casf.storage.os.link', racing_link)
    monkeypatch.setattr('casf.storage.os.fsync', racing_sync)
    with pytest.raises(CasfError, match='already exists'):
        publish()
    assert artifact.read_bytes() == b'concurrent evidence'
    # A collision after publication is an explicit failure; preserve evidence.
    assert destination.exists()


def test_clean_destination_preserves_exact_source_rows(operation):
    destination, publish = operation
    source = destination.parent / 'source.db'
    original = rows(source)
    publish()
    assert rows(destination) == original
    if 'records' in original:
        reader = Writer(destination)
        try:
            assert _verify_db(reader).result is Result.PASS
        finally:
            reader.close()
