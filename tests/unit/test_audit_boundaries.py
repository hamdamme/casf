"""CASF-01/H01/H02: reject ambiguous policy and transport configuration."""

import pytest

from casf import online, transport
from casf.errors import CasfError
from casf.verifier import Result, verify
from tests.unit.test_incremental_verification import history


@pytest.mark.parametrize('value', ['false', 'true', 0, 1, None])
def test_anchored_policy_rejects_wrong_type_before_consuming_records(value):
    args = history()
    def unread():
        pytest.fail('invalid policy consumed evidence')
        yield
    args.update(checkpoint_envelopes=[], receipt_envelopes=[], records=unread(),
                allow_unwitnessed=value)
    with pytest.raises(ValueError, match='allow_unwitnessed must be boolean'):
        verify(**args)


@pytest.mark.parametrize('allowed', [False, True])
def test_anchored_policy_preserves_boolean_suffix_behavior(allowed):
    args = history()
    args.update(checkpoint_envelopes=[], receipt_envelopes=[], allow_unwitnessed=allowed)
    report = verify(**args)
    assert report.result is (Result.PASS if allowed else Result.FAIL)
    assert report.unwitnessed_count == 2
    assert ('UNWITNESSED_SUFFIX' in report.diagnostic_codes) is not allowed
    assert report.assumptions['allow_unwitnessed'] is allowed


@pytest.mark.parametrize('suffix', ['/prefix', '/prefix/', '?secret=value', '#secret',
                                     '/?secret=value', '/#secret', '?', '#'])
@pytest.mark.parametrize('client', ['online', 'transport'])
def test_base_url_components_rejected_before_connection(monkeypatch, suffix, client):
    def unexpected(*args, **kwargs):
        pytest.fail('invalid URL attempted a connection')
    monkeypatch.setattr(transport, '_connected_socket', unexpected)
    url = 'http://127.0.0.1:12345' + suffix
    with pytest.raises(CasfError if client == 'online' else ValueError) as exc:
        if client == 'online':
            online.fetch_latest(url, 'unused', 'SYNTHETIC_TOKEN')
        else:
            transport.request(url, 'POST', '/v1/test', 'SYNTHETIC_TOKEN', b'{}', timeout=1)
    assert 'secret' not in str(exc.value)
    assert 'SYNTHETIC_TOKEN' not in str(exc.value)


@pytest.mark.parametrize('timeout', [True, False, '1', None, float('nan'),
                                      float('inf'), -float('inf'), 0, -1])
def test_transport_invalid_timeout_rejected_before_connection(monkeypatch, timeout):
    def unexpected(*args, **kwargs):
        pytest.fail('invalid timeout attempted a connection')
    monkeypatch.setattr(transport, '_connected_socket', unexpected)
    with pytest.raises(ValueError, match='timeout must be positive and finite'):
        transport.request('http://127.0.0.1', 'POST', '/', 'SYNTHETIC_TOKEN', b'',
                          timeout=timeout)


@pytest.mark.parametrize('method', ['submit', 'typed', 'recover', 'reconcile'])
@pytest.mark.parametrize('timeout', [True, False, 'secret-timeout', None, float('nan'),
                                      float('inf'), -float('inf')])
def test_writer_timeout_boundaries(tmp_path, monkeypatch, method, timeout):
    from casf.api import open_log
    from casf.canonical.jcs import canonicalize
    from casf.errors import SchemaError
    from tests.unit.test_writer import LOG_ID, _append, _writer
    from tests.unit.test_writer_trust import _pins

    writer = _writer(tmp_path / 'writer.db', trust_pins={LOG_ID: _pins()})
    try:
        _append(writer)
        checkpoint = canonicalize(writer.create_checkpoint(LOG_ID))
        def unexpected(*args, **kwargs):
            pytest.fail('invalid timeout attempted a connection')
        monkeypatch.setattr(transport, '_connected_socket', unexpected)
        with pytest.raises(SchemaError) as exc:
            if method == 'typed':
                open_log(writer, LOG_ID).submit_pending('http://127.0.0.1', 'TOKEN', timeout=timeout)
            else:
                operation = {'submit': writer.submit_pending,
                             'recover': writer.recover_pending_receipt,
                             'reconcile': writer.reconcile_witness}[method]
                operation(LOG_ID, 'http://127.0.0.1', 'TOKEN', timeout=timeout)
        assert 'secret-timeout' not in str(exc.value)
        assert canonicalize(writer.pending_checkpoint(LOG_ID)[0]) == checkpoint
    finally:
        writer.close()


@pytest.mark.parametrize('suffix', ['', '/'])
@pytest.mark.parametrize('timeout', [1, 1.5])
def test_transport_valid_origin_and_timeout(suffix, timeout):
    from tests.unit.test_online_transport import server

    with server() as (port, received):
        status, payload = transport.request(f'http://127.0.0.1:{port}' + suffix,
                                           'POST', '/', 'TOKEN', b'{}', timeout=timeout)
        assert status == 200 and payload == b'{}'
        assert received == ['Bearer TOKEN']


def test_online_error_does_not_echo_peer_code(monkeypatch):
    monkeypatch.setattr(online, 'http_request',
                        lambda *a, **k: (403, b'{"code":"SYNTHETIC_PEER_SECRET"}'))
    with pytest.raises(CasfError) as exc:
        online.fetch_latest('http://127.0.0.1', 'unused', 'TOKEN')
    assert 'SYNTHETIC_PEER_SECRET' not in str(exc.value)
