"""CASF-02 / R05/R10: submission categories, pending bytes and safe diagnostics."""

import json
import sqlite3
from contextlib import closing

import pytest

from casf import cli, crypto
from casf.canonical.jcs import canonicalize
from casf.errors import InconclusiveError, SchemaError, TrustError
from casf.witness import Witness
from casf.writer import Writer
from tests.status import register_active
from tests.unit.test_writer import AUTH, AUTH_PUB, LOG, LOG_ID, WIT, _writer

TOKEN = 'SYNTHETIC_SUBMISSION_TOKEN'
PEER_SECRET = 'SYNTHETIC_PEER_RESPONSE_SECRET'
RECORD_SECRET = 'SYNTHETIC_RECORD_CONTENT'
PASSPHRASE = 'SYNTHETIC_TEST_PASSPHRASE'
MARKERS = (TOKEN, PEER_SECRET, RECORD_SECRET, PASSPHRASE,
           'SYNTHETIC_WRONG_TOKEN', crypto.b64url_encode(LOG.private_bytes_raw()))


def assert_redacted(output):
    for marker in MARKERS:
        assert marker not in output.out + output.err
    assert len(output.err) < 200


@pytest.fixture
def pending(tmp_path, monkeypatch):
    path = tmp_path / 'writer.db'
    writer = _writer(path)
    writer.append(LOG_ID, event_id='123e4567-e89b-42d3-a456-426600000001',
                  actor='test', event_type='test', payload={'secret': RECORD_SECRET}, attributes={})
    cp = writer.create_checkpoint(LOG_ID)
    with closing(Witness(tmp_path / 'witness.db', WIT,
                 authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})) as witness:
        register_active(witness, writer.manifest_envelope(LOG_ID), AUTH)
        receipt = witness.submit(LOG_ID, cp, list(writer.records(LOG_ID)))
    monkeypatch.setattr(cli, '_writer', lambda args: writer)
    monkeypatch.setenv('CASF_WITNESS_TOKEN', TOKEN)
    monkeypatch.setenv('CASF_PASSPHRASE', PASSPHRASE)
    yield writer, path, cp, receipt
    writer.close()


def invoke(path):
    return cli.main(['witness', 'submit', '--local-only', '--db', str(path),
                     '--key', 'unused', '--url', 'http://127.0.0.1:12345'])


def retained_and_retry(path, cp, receipt, monkeypatch):
    with sqlite3.connect(path) as db:
        stored = db.execute('SELECT c.envelope FROM checkpoints c JOIN outbox o '
                            'ON c.checkpoint_hash=o.checkpoint_hash').fetchone()
        assert stored is not None and bytes(stored[0]) == canonicalize(cp)
    monkeypatch.setattr('casf.writer.http_request',
                        lambda *a, **k: (200, canonicalize({'receipt': receipt})))
    with closing(Writer(path, LOG, local_only=True)) as writer:
        assert writer.submit_pending(LOG_ID, 'http://127.0.0.1', TOKEN) == receipt
        assert writer.pending_checkpoint(LOG_ID) is None


@pytest.mark.parametrize('status,expected', [(400, 2), (401, 3), (403, 3), (409, 1),
    (429, 4), (500, 5), (502, 5), (503, 4), (504, 5), (302, 5), (404, 5)])
def test_http_submission_categories(pending, monkeypatch, capsys, status, expected):
    _, path, cp, receipt = pending
    monkeypatch.setattr('casf.writer.http_request',
                        lambda *a, **k: (status, '|'.join(MARKERS).encode()))
    assert invoke(path) == expected
    out = capsys.readouterr()
    assert_redacted(out)
    retained_and_retry(path, cp, receipt, monkeypatch)


@pytest.mark.parametrize('error,expected', [(TimeoutError(PEER_SECRET), 4),
    (ConnectionRefusedError(PEER_SECRET), 4), (SchemaError('safe schema failure'), 2),
    (TrustError('safe trust failure'), 3), (InconclusiveError('safe uncertainty'), 4)])
def test_submission_preserves_error_categories(pending, monkeypatch, capsys, error, expected):
    _, path, cp, receipt = pending
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr('casf.writer.http_request', fail)
    assert invoke(path) == expected
    out = capsys.readouterr()
    assert_redacted(out)
    retained_and_retry(path, cp, receipt, monkeypatch)


@pytest.mark.parametrize('kind,expected', [('json', 2), ('missing', 2), ('schema', 2), ('unknown_field', 2),
                                         ('signature', 1), ('checkpoint', 1), ('manifest', 1),
    ('witness', 1), ('count', 1), ('head', 1), ('index', 1), ('previous', 1)])
def test_invalid_success_receipt_retains_pending(pending, monkeypatch, capsys, kind, expected):
    _, path, cp, receipt = pending
    bad = json.loads(json.dumps(receipt))
    if kind == 'json':
        payload = PEER_SECRET.encode()
    elif kind == 'missing':
        payload = canonicalize({'secret': PEER_SECRET})
    elif kind == 'schema':
        payload = canonicalize({'receipt': {'secret': PEER_SECRET}})
    else:
        if kind == 'unknown_field':
            bad['body'][PEER_SECRET] = 'private'
        elif kind == 'signature':
            bad['signature'] = crypto.b64url_encode(bytes(64))
        else:
            field = {'checkpoint': 'checkpoint_hash', 'manifest': 'manifest_hash',
                     'witness': 'witness_id', 'count': 'count', 'head': 'head_hash',
                     'index': 'checkpoint_index', 'previous': 'previous_receipt_hash'}[kind]
            bad['body'][field] = 9 if kind in ('count', 'index') else 'ab' * 32
            bad['receipt_hash'] = crypto.digest_receipt(bad['body'])
            bad['signature'] = crypto.sign_receipt(WIT, bad['body'])
        payload = canonicalize({'receipt': bad})
    monkeypatch.setattr('casf.writer.http_request', lambda *a, **k: (200, payload))
    assert invoke(path) == expected
    out = capsys.readouterr()
    assert_redacted(out)
    retained_and_retry(path, cp, receipt, monkeypatch)


def test_real_wrong_token_is_trust_failure_and_retry_succeeds(pending, monkeypatch, capsys, tmp_path):
    import threading

    from casf.witness.http import WitnessService, make_server

    writer, path, cp, _receipt = pending
    service = WitnessService(tmp_path / 'http-witness.db', WIT, token=TOKEN,
                             authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(service.witness, writer.manifest_envelope(LOG_ID), AUTH)
    server = make_server(service, '127.0.0.1', 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    try:
        monkeypatch.setenv('CASF_WITNESS_TOKEN', 'SYNTHETIC_WRONG_TOKEN')
        code = cli.main(['witness', 'submit', '--local-only', '--db', str(path),
                         '--key', 'unused', '--url', url])
        output = capsys.readouterr()
        assert code == 3
        assert_redacted(output)
        with closing(Writer(path, LOG, local_only=True)) as reopened:
            assert canonicalize(reopened.pending_checkpoint(LOG_ID)[0]) == canonicalize(cp)
            receipt = reopened.submit_pending(LOG_ID, url, TOKEN)
            assert receipt['body']['checkpoint_hash'] == cp['checkpoint_hash']
            assert reopened.pending_checkpoint(LOG_ID) is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        service.close()


def test_receipt_schema_traceback_does_not_echo_peer_fields(pending):
    import traceback

    writer, _path, _cp, receipt = pending
    receipt['body'][PEER_SECRET] = 'private'
    with pytest.raises(SchemaError) as exc:
        writer.record_receipt(LOG_ID, receipt)
    assert PEER_SECRET not in ''.join(traceback.format_exception(exc.value))
