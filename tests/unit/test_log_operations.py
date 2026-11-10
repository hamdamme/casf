"""R04/R07/R09: typed writer operations preserve commit and trust boundaries."""

import sqlite3
from dataclasses import FrozenInstanceError

import pytest

from casf import crypto
from casf.api import (
    Checkpoint,
    EventRequest,
    ExportResult,
    Manifest,
    WitnessResult,
    create_log,
    open_log,
)
from casf.bundle import read_bundle
from casf.canonical.jcs import canonicalize, parse
from casf.errors import CasfError, InconclusiveError, SchemaError, TrustError
from casf.writer import Writer
from tests.unit.test_event_models import event
from tests.unit.test_writer import (
    AUTH,
    AUTH_PUB,
    LOG,
    LOG_ID,
    WIT,
    _append,
    _manifest_envelope,
    _writer,
)


@pytest.fixture
def operation_log(tmp_path, monkeypatch):
    from casf.witness import Witness
    from tests.status import register_active

    writer = _writer(tmp_path / 'writer.db')
    witness = Witness(tmp_path / 'witness.db', WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(witness, _manifest_envelope(), AUTH)
    requests = []

    def transport(_url, method, _path, _token, payload, **_kwargs):
        assert method == 'POST'
        assert not writer._db.connection.in_transaction
        request = parse(payload)
        requests.append(request)
        receipt = witness.submit(LOG_ID, request['checkpoint'], request['records'])
        return 201, canonicalize({'receipt': receipt})

    monkeypatch.setattr('casf.writer.http_request', transport)
    try:
        yield writer, open_log(writer, LOG_ID), requests, transport
    finally:
        writer.close()
        witness.close()


def test_create_and_open_handle_preserve_legacy_manifest_result(tmp_path):
    writer = Writer(tmp_path / 'writer.db', LOG, local_only=True)
    try:
        manifest = Manifest(_manifest_envelope())
        handle = create_log(manifest, writer)
        assert handle.log_id == LOG_ID
        assert handle.manifest == manifest
        assert open_log(writer, LOG_ID) == handle
        with pytest.raises(FrozenInstanceError):
            handle.manifest = Manifest(_manifest_envelope())
        handle.append(EventRequest(**event()))
        assert len(list(writer.records(LOG_ID))) == 1
        assert 'Writer' not in repr(handle)
    finally:
        writer.close()


def test_typed_operation_lifecycle_and_legacy_returns(operation_log, tmp_path):
    writer, log, requests, _ = operation_log
    result = log.append(EventRequest(**event()))
    cp = log.create_checkpoint()
    assert isinstance(cp, Checkpoint) and cp.count == 1
    assert log.pending_checkpoint() == cp
    witnessed = log.submit_pending('https://witness.example', 'synthetic-token')
    assert isinstance(witnessed, WitnessResult) and witnessed.stored is True
    assert witnessed.checkpoint_hash == cp.checkpoint_hash
    assert requests[0]['checkpoint'] == cp.to_dict()
    assert requests[0]['records'] == [result.record]
    assert log.pending_checkpoint() is None
    exported = log.export_bundle(tmp_path / 'bundle')
    assert isinstance(exported, ExportResult)
    bundle = read_bundle(exported.destination)
    assert exported.metadata == bundle.metadata
    assert exported.through == 1
    final = log.seal_log()
    assert final.final is True
    with pytest.raises(CasfError):
        log.append(EventRequest(**event(event_id='123e4567-e89b-42d3-a456-426600000002')))
    with pytest.raises(CasfError, match='receipt is pending'):
        log.export_bundle(tmp_path / 'pending-final')
    log.submit_pending('https://witness.example', 'synthetic-token')
    assert writer.export_bundle(LOG_ID, tmp_path / 'legacy').name == 'legacy'
    assert isinstance(writer.append(LOG_ID, **event()), dict)


def test_timeout_keeps_pending_bytes_for_typed_retry(operation_log, monkeypatch):
    writer, log, requests, transport = operation_log
    log.append(EventRequest(**event()))
    cp = log.create_checkpoint()

    def offline(*args, **kwargs):
        raise OSError('synthetic network failure')

    monkeypatch.setattr('casf.writer.http_request', offline)
    with pytest.raises(InconclusiveError):
        log.submit_pending('https://witness.example', 'synthetic-token')
    assert log.pending_checkpoint() == cp
    assert len(list(writer.records(LOG_ID))) == 1
    monkeypatch.setattr('casf.writer.http_request', transport)
    assert log.submit_pending('https://witness.example', 'synthetic-token').checkpoint_hash == cp.digest
    assert len(requests) == 1


def deny_commit(action, arg1, _arg2, _database, _source):
    return (sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION and arg1 == 'COMMIT'
            else sqlite3.SQLITE_OK)


@pytest.mark.parametrize('operation', ['checkpoint', 'seal'])
def test_checkpoint_commit_failure_returns_no_result(operation_log, operation):
    writer, log, _, _ = operation_log
    log.append(EventRequest(**event()))
    con = writer._db.connection
    con.set_authorizer(deny_commit)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            log.seal_log() if operation == 'seal' else log.create_checkpoint()
        assert not con.in_transaction
        assert log.pending_checkpoint() is None
    finally:
        con.set_authorizer(None)
    assert log.create_checkpoint().count == 1
    assert con.execute('SELECT sealed FROM heads').fetchone()[0] == 0


def test_receipt_commit_failure_cannot_return_witnessed(operation_log, monkeypatch):
    writer, log, requests, transport = operation_log
    log.append(EventRequest(**event()))
    cp = log.create_checkpoint()

    def fail_local_commit(*args, **kwargs):
        response = transport(*args, **kwargs)
        writer._db.connection.set_authorizer(deny_commit)
        return response

    monkeypatch.setattr('casf.writer.http_request', fail_local_commit)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            log.submit_pending('https://witness.example', 'synthetic-token')
        assert log.pending_checkpoint() == cp
        assert writer._db.connection.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] == 0
    finally:
        writer._db.connection.set_authorizer(None)
    monkeypatch.setattr('casf.writer.http_request', transport)
    assert log.submit_pending('https://witness.example', 'synthetic-token').stored is True
    assert requests[0] == requests[1]


def test_create_commit_failure_returns_no_handle(tmp_path):
    writer = Writer(tmp_path / 'writer.db', LOG, local_only=True)
    writer._db.connection.set_authorizer(deny_commit)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            create_log(Manifest(_manifest_envelope()), writer)
        assert writer._db.connection.execute('SELECT COUNT(*) FROM manifests').fetchone()[0] == 0
    finally:
        writer._db.connection.set_authorizer(None)
        writer.close()


def test_untyped_creation_and_unknown_log_cannot_write(tmp_path):
    writer = Writer(tmp_path / 'writer.db', LOG, local_only=True)
    try:
        with pytest.raises(SchemaError):
            create_log(_manifest_envelope(), writer)
        with pytest.raises(CasfError, match='unknown log'):
            open_log(writer, LOG_ID)
        assert writer._db.connection.execute('SELECT COUNT(*) FROM manifests').fetchone()[0] == 0
    finally:
        writer.close()


def test_handle_checks_bound_manifest_before_delegating(operation_log, monkeypatch):
    writer, log, _, _ = operation_log
    replacement = _manifest_envelope()
    replacement['signature'] = 'A' * 86
    monkeypatch.setattr(writer, 'manifest_envelope', lambda _: replacement)
    with pytest.raises(TrustError, match='no longer matches'):
        log.append(EventRequest(**event()))
    assert list(writer.records(LOG_ID)) == []


def test_read_only_handle_can_export_but_cannot_sign(tmp_path):
    writer = _writer(tmp_path / 'writer.db')
    _append(writer)
    writer.close()
    reader = Writer(tmp_path / 'writer.db')
    try:
        log = open_log(reader, LOG_ID)
        assert log.export_bundle(tmp_path / 'bundle').through == 1
        with pytest.raises(CasfError):
            log.create_checkpoint()
        with pytest.raises(CasfError):
            log.append(EventRequest(**event()))
    finally:
        reader.close()
