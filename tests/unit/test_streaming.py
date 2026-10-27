"""Streaming evidence, bounded checkpoint heads, and late read failures."""
import gc
import json
import tracemalloc
from contextlib import contextmanager

import pytest

from benchmarks.streaming import generate
from casf import crypto
from casf.bundle import BundleReadError, open_bundle, read_bundle
from casf.canonical.jcs import canonicalize
from casf.errors import LimitError
from casf.verifier import Mode, Result, TrustPins, verify
from tests.unit.test_verifier import (
    _anchored,
    _chain,
    _checkpoint_env,
    _manifest_env,
    _pins,
    _receipt_env,
    _status_env,
)


def public_pins(path):
    trust = json.loads(path.with_suffix('.trust.json').read_text())
    ap, wp = [crypto.b64url_decode(trust[k]) for k in ('authority', 'witness')]
    return TrustPins({crypto.key_id(ap): ap}, {crypto.key_id(wp): wp},
                     trust['log_id'], trust['manifest_hash'])


def check(bundle, pins, mode=Mode.ANCHORED):
    return verify(bundle.manifest, bundle.records, pins, mode=mode,
                  checkpoint_envelopes=bundle.checkpoints, receipt_envelopes=bundle.receipts,
                  status_envelopes=bundle.statuses)


@pytest.mark.parametrize('count', [0, 1, 129, 2048])
@pytest.mark.parametrize('mode', [Mode.INTEGRITY, Mode.ANCHORED])
def test_stream_matches_eager(tmp_path, count, mode):
    path = tmp_path / 'bundle'
    generate(path, count)
    pins = public_pins(path)
    eager = read_bundle(path)
    assert isinstance(eager.records, list)
    expected = check(eager, pins, mode)
    with open_bundle(path) as bundle:
        assert not isinstance(bundle.records, list)
        actual = check(bundle, pins, mode)
    assert actual == expected
    assert actual.result is Result.PASS
    assert actual.verified_through == count


@pytest.mark.parametrize('tail', [b'\n', b'{}', b'{bad}\n', b'[]\n', b'\xef\xbb\xbf{}\n',
                                  b'{"body":{},"body":{}}\n'])
def test_late_malformed_line(tmp_path, tail):
    path = tmp_path / 'bundle'
    generate(path, 1)
    with (path / 'records.jsonl').open('ab') as stream:
        stream.write(tail)
    with open_bundle(path) as bundle:
        assert next(bundle.records)['body']['seq'] == 1
        with pytest.raises(BundleReadError):
            next(bundle.records)


@pytest.mark.parametrize('mutation', ['duplicate', 'reorder', 'missing', 'altered'])
def test_stream_rejects_record_changes(tmp_path, mutation):
    path = tmp_path / 'bundle'
    generate(path, 3)
    lines = (path / 'records.jsonl').read_bytes().splitlines(keepends=True)
    if mutation == 'duplicate':
        lines[1] = lines[0]
    elif mutation == 'reorder':
        lines.reverse()
    elif mutation == 'missing':
        del lines[1]
    else:
        record = json.loads(lines[1])
        record['body']['actor'] = 'changed'
        lines[1] = canonicalize(record) + b'\n'
    (path / 'records.jsonl').write_bytes(b''.join(lines))
    with open_bundle(path) as bundle:
        if mutation == 'altered':
            report = check(bundle, public_pins(path))
            assert report.result is Result.FAIL
            assert report.first_failure_seq == 2
            assert 'RECORD_HASH_MISMATCH' in report.diagnostic_codes
        else:
            with pytest.raises(BundleReadError, match='ordered'):
                check(bundle, public_pins(path))


def test_truncation_checked_at_eof(tmp_path):
    path = tmp_path / 'bundle'
    generate(path, 2)
    file = path / 'records.jsonl'
    file.write_bytes(file.read_bytes().splitlines(keepends=True)[0])
    with open_bundle(path) as bundle:
        next(bundle.records)
        with pytest.raises(BundleReadError, match='record count'):
            next(bundle.records)


@pytest.mark.parametrize('limit', ['line', 'count', 'bytes'])
def test_stream_limits(tmp_path, limit):
    path = tmp_path / 'bundle'
    generate(path, 2)
    total = sum(p.stat().st_size for p in path.iterdir())
    kwargs = {'line': {'max_line_bytes': 100}, 'count': {'max_records': 1},
              'bytes': {'max_total_bytes': total - 1}}[limit]
    with pytest.raises(LimitError), open_bundle(path, **kwargs) as bundle:
        list(bundle.records)


def test_context_closes_after_early_exit(tmp_path, monkeypatch):
    import casf.bundle as module
    path = tmp_path / 'bundle'
    generate(path, 2)
    opened = []
    original = module._open_regular
    def capture(path):
        f = original(path)
        opened.append(f)
        return f
    monkeypatch.setattr(module, '_open_regular', capture)
    with open_bundle(path) as bundle:
        next(bundle.records)
    assert all(f.closed for f in opened)
    assert list(bundle.records) == []


def test_checkpoint_targets_include_duplicate_counts_and_retained_pin():
    env, records, cps, receipts = _anchored(n=2, anchor_count=2)
    final = _checkpoint_env(1, 2, records[-1]['record_hash'], cps[0]['checkpoint_hash'],
                            env['manifest_hash'], final=True)
    cps.append(final)
    receipts.append(_receipt_env(final, receipts[0]['receipt_hash']))
    report = verify(env, iter(records), _pins(env['manifest_hash']), Mode.ANCHORED,
                    iter(cps), iter(receipts), [_status_env(env['manifest_hash'])],
                    retained_checkpoint=(0, cps[0]['checkpoint_hash']))
    assert report.result is Result.PASS
    assert report.checkpoint == (1, final['checkpoint_hash'])


def test_intermediate_checkpoint_head_must_match():
    env, records, _cps, _receipts = _anchored(n=2, anchor_count=1)
    bad = _checkpoint_env(0, 1, 'ab' * 32, '0' * 64, env['manifest_hash'])
    end = _checkpoint_env(1, 2, records[-1]['record_hash'], bad['checkpoint_hash'],
                          env['manifest_hash'])
    report = verify(env, iter(records), _pins(env['manifest_hash']), Mode.ANCHORED,
                    [bad, end], [_receipt_env(end)], [_status_env(env['manifest_hash'])])
    assert report.result is Result.FAIL
    assert 'ANCHOR_DIVERGENT' in report.diagnostic_codes


def test_record_failure_precedes_checkpoint_schema_failure():
    env = _manifest_env()
    records = _chain(1)
    records[0]['record_hash'] = 'ab' * 32
    report = verify(env, iter(records), _pins(env['manifest_hash']), Mode.ANCHORED,
                    [{}], [], [_status_env(env['manifest_hash'])])
    assert report.diagnostic_codes == ['STATUS_CURRENTNESS_UNCONFIRMED', 'RECORD_HASH_MISMATCH']


@pytest.mark.parametrize('failure', ['schema', 'io', 'tail_after_crypto_failure'])
def test_cli_late_error_never_saves_or_prints_pass(tmp_path, capsys, monkeypatch, failure):
    from casf import cli
    from tests.unit.test_cli import _exported, _trust
    from tests.unit.test_writer import _manifest_envelope
    _, dest = _exported(tmp_path, capsys)
    trust = _trust(tmp_path, _manifest_envelope())
    state = tmp_path / 'state.json'
    if failure == 'io':
        original = cli.open_bundle
        @contextmanager
        def injected(*args, **kwargs):
            with original(*args, **kwargs) as bundle:
                original_records = bundle.records
                def broken():
                    yield next(original_records)
                    raise OSError('simulated disk read failure')
                bundle.records = broken()
                yield bundle
        monkeypatch.setattr(cli, 'open_bundle', injected)
    else:
        path = dest / 'records.jsonl'
        data = path.read_bytes()
        if failure == 'tail_after_crypto_failure':
            lines = data.splitlines(keepends=True)
            first = json.loads(lines[0])
            first['record_hash'] = 'ab' * 32
            data = canonicalize(first) + b'\n' + b''.join(lines[1:])
        path.write_bytes(data + b'{invalid}\n')
    code = cli.main(['verify', str(dest), '--trust', str(trust), '--state', str(state),
                     '--initialize-state', '--json'])
    assert code == (5 if failure == 'io' else 2)
    output = capsys.readouterr()
    assert not output.out
    assert output.err
    assert not state.exists()


def test_record_memory_does_not_scale_with_file(tmp_path):
    # A fixed one checkpoint prefix isolates record count from protocol state.
    paths = [tmp_path / 'small', tmp_path / 'large']
    for path, count in zip(paths, (128, 4096), strict=True):
        generate(path, count, anchor_records=128)
    peaks = []
    for path in paths:
        pins = public_pins(path)
        gc.collect()
        tracemalloc.start()
        try:
            with open_bundle(path) as bundle:
                report = verify(bundle.manifest, bundle.records, pins,
                                status_envelopes=bundle.statuses)
                assert report.result is Result.PASS
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
    # Generous headroom for interpreter variation; eager storage adds megabytes.
    assert peaks[1] < peaks[0] + 512 * 1024, peaks


def test_open_descriptor_does_not_follow_replaced_record_path(tmp_path):
    path = tmp_path / 'bundle'
    generate(path, 2)
    pins = public_pins(path)
    with open_bundle(path) as bundle:
        records = path / 'records.jsonl'
        records.rename(path / 'original.jsonl')
        records.symlink_to(tmp_path / 'nonexistent')
        report = check(bundle, pins)
    assert report.result is Result.PASS
    assert report.verified_through == 2


def test_online_stream_matches_eager_with_retained_checkpoint(tmp_path):
    from casf.online import verify_latest_response
    from tests.unit.test_verifier import LOG_ID, TS, WIT, WIT_PUB
    path = tmp_path / 'bundle'
    generate(path, 257)
    pins = public_pins(path)
    eager = read_bundle(path)
    cp, rc = eager.checkpoints[-1], eager.receipts[-1]
    nonce = b'n' * 32
    latest = {'version': 1, 'type': 'latest', 'nonce': crypto.b64url_encode(nonce),
              'witness_id': crypto.key_id(WIT_PUB), 'log_id': LOG_ID,
              'manifest_hash': eager.manifest_hash, 'checkpoint_hash': cp['checkpoint_hash'],
              'receipt_hash': rc['receipt_hash'], 'checkpoint_index': cp['body']['index'],
              'count': cp['body']['count'], 'head_hash': cp['body']['head_hash'],
              'final': False, 'responded_at': TS}
    view = verify_latest_response(
        {'body': latest, 'signature': crypto.sign_latest(WIT, latest),
         'checkpoint': cp, 'receipt': rc}, nonce, WIT_PUB, LOG_ID)
    options = {'mode': Mode.ONLINE, 'online_query': lambda: view,
               'retained_checkpoint': (0, eager.checkpoints[0]['checkpoint_hash'])}
    expected = verify(eager.manifest, eager.records, pins,
                      checkpoint_envelopes=eager.checkpoints, receipt_envelopes=eager.receipts,
                      status_envelopes=eager.statuses, **options)
    with open_bundle(path) as bundle:
        actual = verify(bundle.manifest, bundle.records, pins,
                        checkpoint_envelopes=bundle.checkpoints, receipt_envelopes=bundle.receipts,
                        status_envelopes=bundle.statuses, **options)
    assert actual == expected
    assert actual.result is Result.PASS
    assert actual.verified_through == 257
