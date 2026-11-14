"""R05/R10: credentials cannot escape through rendered transport exceptions."""

import http.client
import socket
import traceback

import pytest

from casf import online, transport
from casf.canonical.jcs import canonicalize
from casf.errors import SchemaError
from tests.unit.test_verify_online import TOKEN, _service
from tests.unit.test_writer import LOG_ID, _append, _writer
from tests.unit.test_writer_trust import _pins

MARKER = 'SYNTHETIC_SECRET_TOKEN'
BAD_TOKENS = [MARKER + '\n', MARKER + '\r\n', MARKER + '\ninjected',
              MARKER + '\u2603']


def assert_redacted(error):
    rendered = ''.join(traceback.format_exception(error))
    assert MARKER not in str(error)
    assert MARKER not in rendered
    assert 'Bearer ' + MARKER not in rendered
    assert error.__cause__ is None
    assert error.__context__ is None


def call(target, writer, token, url='http://127.0.0.1:9'):
    if target == 'transport':
        return transport.request(url, 'POST', '/test', token, b'{}', timeout=1)
    if target == 'online':
        return online.fetch_latest(url, LOG_ID, token)
    if target == 'submit':
        return writer.submit_pending(LOG_ID, url, token)
    return writer.recover_pending_receipt(LOG_ID, url, token)


@pytest.mark.parametrize('target', ['transport', 'online', 'submit', 'recover'])
@pytest.mark.parametrize('token', BAD_TOKENS)
def test_malformed_bearer_is_redacted_before_connection(tmp_path, monkeypatch, target, token):
    writer = _writer(tmp_path / 'writer.db', trust_pins={LOG_ID: _pins()})
    client, peer = socket.socketpair()
    connections = []

    def connected(*args, **kwargs):
        connections.append(True)
        return client

    monkeypatch.setattr(transport, '_connected_socket', connected)
    try:
        _append(writer, 1)
        writer.create_checkpoint(LOG_ID)
        before = canonicalize(writer.pending_checkpoint(LOG_ID)[0])
        expected = SchemaError if target in ('submit', 'recover') else ValueError
        with pytest.raises(expected) as caught:
            call(target, writer, token)
        assert_redacted(caught.value)
        assert not connections
        peer.setblocking(False)
        try:
            received = peer.recv(4096)
        except BlockingIOError:
            received = b''
        assert received == b''
        assert canonicalize(writer.pending_checkpoint(LOG_ID)[0]) == before
    finally:
        writer.close()
        client.close()
        peer.close()


@pytest.mark.parametrize('target', ['submit', 'recover', 'online'])
def test_wrapper_discards_unsafe_value_error_object(tmp_path, monkeypatch, target):
    writer = _writer(tmp_path / 'writer.db', trust_pins={LOG_ID: _pins()})

    def unsafe(*args, **kwargs):
        raise ValueError('Invalid header value: Bearer ' + MARKER)

    monkeypatch.setattr('casf.online.http_request' if target == 'online'
                        else 'casf.writer.http_request', unsafe)
    try:
        writer.create_checkpoint(LOG_ID)
        before = canonicalize(writer.pending_checkpoint(LOG_ID)[0])
        with pytest.raises(SchemaError if target != 'online' else ValueError) as caught:
            call(target, writer, TOKEN)
        assert_redacted(caught.value)
        assert canonicalize(writer.pending_checkpoint(LOG_ID)[0]) == before
    finally:
        writer.close()


def test_direct_transport_discards_header_construction_error(tmp_path, monkeypatch):
    client, peer = socket.socketpair()
    monkeypatch.setattr(transport, '_connected_socket', lambda *a, **kw: client)

    def unsafe(*args, **kwargs):
        raise ValueError('Invalid header value: Bearer ' + MARKER)

    monkeypatch.setattr(http.client.HTTPConnection, 'request', unsafe)
    try:
        with pytest.raises(ValueError) as caught:
            transport.request('http://127.0.0.1:9', 'POST', '/test', TOKEN, b'{}', timeout=1)
        assert_redacted(caught.value)
        assert client.fileno() == -1
        assert peer.recv(4096) == b''
    finally:
        client.close()
        peer.close()


@pytest.mark.parametrize('target', ['submit', 'recover'])
def test_valid_retry_after_malformed_credential_preserves_pending(tmp_path, target):
    service, server = _service(tmp_path)
    writer = _writer(tmp_path / 'writer.db', trust_pins={LOG_ID: _pins()})
    url = f'http://127.0.0.1:{server.server_port}'
    try:
        _append(writer, 1)
        checkpoint = writer.create_checkpoint(LOG_ID)
        before = canonicalize(checkpoint)
        if target == 'recover':
            service.witness.submit(LOG_ID, checkpoint, list(writer.records(LOG_ID)))
        with pytest.raises(SchemaError) as caught:
            call(target, writer, BAD_TOKENS[0], url)
        assert_redacted(caught.value)
        assert canonicalize(writer.pending_checkpoint(LOG_ID)[0]) == before
        receipt = call(target, writer, TOKEN, url)
        assert writer.pending_checkpoint(LOG_ID) is None
        assert service.witness.receipt(checkpoint['checkpoint_hash'])[1] == receipt
        latest, nonce = online.fetch_latest(url, LOG_ID, TOKEN)
        assert latest['body']['count'] == 1 and len(nonce) == 32
        code, _ = transport.request(url, 'GET',
            f"/v1/logs/{LOG_ID}/receipts/{checkpoint['checkpoint_hash']}", TOKEN, b'', timeout=2)
        assert code == 200
    finally:
        writer.close()
        server.shutdown()
        server.server_close()
        service.close()
