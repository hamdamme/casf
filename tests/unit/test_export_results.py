"""Export observations describe the published snapshot and its actual outcome."""

import pytest

from casf.api import open_log
from casf.bundle import read_bundle
from casf.errors import CasfError
from casf.writer import Writer
from tests.unit.test_writer import LOG, LOG_ID, _append, _writer


@pytest.mark.parametrize('through', [0, 1, None])
def test_result_is_exact_metadata_from_one_snapshot(tmp_path, monkeypatch, through):
    path = tmp_path / 'writer.db'
    writer = _writer(path)
    _append(writer, 1)
    other = Writer(path, LOG, local_only=True)
    original = writer._write_member
    appended = False

    def concurrent(path, data):
        nonlocal appended
        if not appended:
            _append(other, 2)
            appended = True
        original(path, data)

    monkeypatch.setattr(writer, '_write_member', concurrent)
    try:
        result = open_log(writer, LOG_ID).export_bundle(tmp_path / 'bundle', through=through)
        bundle = read_bundle(result.destination)
        assert result.metadata == bundle.metadata
        assert result.through == (1 if through is None else through)
        assert len(bundle.records) == result.through
        assert len(list(writer.records(LOG_ID))) == 2
        result.metadata['through'] = 999
        assert result.through == bundle.metadata['through']
    finally:
        writer.close()
        other.close()


def test_failed_export_does_not_return_published_result(tmp_path, monkeypatch):
    writer = _writer(tmp_path / 'writer.db')
    destination = tmp_path / 'bundle'

    def disk_full(*_args, **_kwargs):
        raise OSError('synthetic filesystem failure')

    monkeypatch.setattr(writer, '_write_member', disk_full)
    try:
        with pytest.raises(OSError):
            open_log(writer, LOG_ID).export_bundle(destination)
        assert not destination.exists()
        assert not writer._db.connection.in_transaction
    finally:
        writer.close()


def test_parent_sync_error_leaves_complete_bundle_without_success_result(tmp_path, monkeypatch):
    writer = _writer(tmp_path / 'writer.db')
    destination = tmp_path / 'bundle'
    from casf.filesystem import sync_directory

    def fail_parent(path):
        if path == tmp_path:
            raise OSError('synthetic parent sync failure')
        return sync_directory(path)

    monkeypatch.setattr('casf.writer.sync_directory', fail_parent)
    try:
        log = open_log(writer, LOG_ID)
        with pytest.raises(OSError):
            log.export_bundle(destination)
        assert read_bundle(destination).metadata['through'] == 0
        with pytest.raises(CasfError, match='already exists'):
            log.export_bundle(destination)
    finally:
        writer.close()
