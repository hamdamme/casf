"""R03/R07/R10/R11: bounded complete reads and explicit incremental starts."""

import json
from dataclasses import replace

import pytest

from benchmarks.streaming import generate
from casf import crypto
from casf.bundle import BundleReadError, read_bundle
from casf.canonical.jcs import canonicalize
from casf.errors import CasfError, LimitError
from casf.verifier import Mode, Result, VerificationAnchor, verify_bundle
from tests.unit.test_streaming import check, public_pins


def rewrite(path, values):
    path.write_bytes(b''.join(canonicalize(value) + b'\n' for value in values))


def setup_bundle(tmp_path, count=129, anchor_index=0):
    path = tmp_path / 'bundle'
    generate(path, count)
    evidence = read_bundle(path)
    cp, rc = evidence.checkpoints[anchor_index], evidence.receipts[anchor_index]
    return path, evidence, VerificationAnchor(cp, rc, expected_checkpoint_hash=cp['checkpoint_hash'])


@pytest.mark.parametrize('mode', list(Mode)[:2])
@pytest.mark.parametrize('count', [0, 1, 129])
def test_complete_bundle_api_matches_stream_verifier(tmp_path, mode, count):
    path, evidence, _ = setup_bundle(tmp_path, count)
    assert verify_bundle(path, public_pins(path), mode) == check(evidence, public_pins(path), mode)


@pytest.mark.parametrize('reason', ['unknown_trust', 'bad_signature'])
@pytest.mark.parametrize('tail', [b'\n', b'{bad}\n', b'{}', b'[]\n', b'{"body":{},"body":{}}\n'])
def test_early_verdict_cannot_hide_malformed_tail(tmp_path, reason, tail):
    path, evidence, _ = setup_bundle(tmp_path, 2)
    pins = public_pins(path)
    if reason == 'unknown_trust':
        pins = replace(pins, authority_keys={})
    else:
        evidence.records[0]['signature'] = 'A' * 86
        rewrite(path / 'records.jsonl', evidence.records)
    with (path / 'records.jsonl').open('ab') as output:
        output.write(tail)
    with pytest.raises(BundleReadError):
        verify_bundle(path, pins)


def test_early_verdict_cannot_hide_missing_records(tmp_path):
    path, evidence, _ = setup_bundle(tmp_path, 2)
    rewrite(path / 'records.jsonl', evidence.records[:1])
    with pytest.raises(BundleReadError, match='record count'):
        verify_bundle(path, replace(public_pins(path), authority_keys={}))


@pytest.mark.parametrize('outcome', ['success', 'invalid_signature', 'late_error'])
def test_files_closed_before_return_or_error(tmp_path, monkeypatch, outcome):
    import casf.bundle as module

    path, evidence, _ = setup_bundle(tmp_path, 2)
    opened = []
    original = module._open_regular

    def track(file):
        result = original(file)
        opened.append(result)
        return result

    monkeypatch.setattr(module, '_open_regular', track)
    if outcome == 'invalid_signature':
        evidence.records[0]['signature'] = 'A' * 86
        rewrite(path / 'records.jsonl', evidence.records)
    elif outcome == 'late_error':
        with (path / 'records.jsonl').open('ab') as output:
            output.write(b'\n')
    if outcome == 'late_error':
        with pytest.raises(BundleReadError):
            verify_bundle(path, public_pins(path))
    else:
        report = verify_bundle(path, public_pins(path))
        assert report.result is (Result.PASS if outcome == 'success' else Result.FAIL)
    assert opened and all(file.closed for file in opened)


@pytest.mark.parametrize('limit', ['records', 'line', 'bytes', 'evidence'])
def test_limits_include_drained_input(tmp_path, limit):
    path, _, _ = setup_bundle(tmp_path)
    total = sum(file.stat().st_size for file in path.iterdir())
    options = {'records': {'max_records': 128}, 'line': {'max_line_bytes': 100},
               'bytes': {'max_total_bytes': total - 1}, 'evidence': {'max_evidence_objects': 1}}[limit]
    with pytest.raises(LimitError):
        verify_bundle(path, replace(public_pins(path), authority_keys={}), **options)


def test_incremental_bundle_checks_only_suffix_signatures(tmp_path, monkeypatch):
    path, evidence, anchor = setup_bundle(tmp_path)
    evidence.records[0]['signature'] = 'A' * 86
    rewrite(path / 'records.jsonl', evidence.records)
    seen = []
    original = crypto.verify_record

    def track(key, body, signature):
        seen.append(body['seq'])
        original(key, body, signature)

    monkeypatch.setattr(crypto, 'verify_record', track)
    report = verify_bundle(path, public_pins(path), Mode.ANCHORED, anchor=anchor)
    assert report.result is Result.PASS
    assert seen == [129]
    assert report.verified_from == report.verified_through == 129
    assert report.assumptions['prefix_signatures_checked'] is False
    assert report.assumptions['trusted_prefix_through'] == 128
    assert verify_bundle(path, public_pins(path), Mode.ANCHORED).result is Result.FAIL


@pytest.mark.parametrize('kind', ['checkpoint', 'receipt'])
@pytest.mark.parametrize('mode', [Mode.INTEGRITY, Mode.ANCHORED])
def test_bundle_cannot_replace_explicit_anchor_evidence(tmp_path, kind, mode):
    path, evidence, anchor = setup_bundle(tmp_path)
    values = evidence.checkpoints if kind == 'checkpoint' else evidence.receipts
    values[0]['signature'] = 'A' * 86
    rewrite(path / (kind + 's.jsonl'), values)
    with pytest.raises(BundleReadError, match='conflicts with the explicit anchor'):
        verify_bundle(path, public_pins(path), mode, anchor=anchor)


@pytest.mark.parametrize('kind', ['checkpoints', 'receipts'])
@pytest.mark.parametrize('mutation', ['malformed', 'duplicate', 'reordered'])
def test_skipped_historical_evidence_is_still_structurally_checked(tmp_path, kind, mutation):
    path, evidence, anchor = setup_bundle(tmp_path, 257, 1)
    values = getattr(evidence, kind)
    if mutation == 'malformed':
        values[0]['body']['count'] = True
    elif mutation == 'duplicate':
        values.insert(0, values[0])
    else:
        values.reverse()
    rewrite(path / (kind + '.jsonl'), values)
    with pytest.raises(CasfError):
        verify_bundle(path, public_pins(path), Mode.ANCHORED, anchor=anchor)


@pytest.mark.parametrize('mode', [Mode.INTEGRITY, Mode.ANCHORED])
def test_bundle_shorter_than_trusted_prefix_cannot_pass(tmp_path, mode):
    path, evidence, anchor = setup_bundle(tmp_path)
    rewrite(path / 'records.jsonl', evidence.records[:127])
    metadata = json.loads((path / 'export.json').read_text())
    metadata.update(through=127, record_count=127)
    (path / 'export.json').write_bytes(canonicalize(metadata))
    rewrite(path / 'checkpoints.jsonl', [])
    rewrite(path / 'receipts.jsonl', [])
    report = verify_bundle(path, public_pins(path), mode, anchor=anchor)
    assert report.result is Result.FAIL
    assert 'ANCHOR_INCOMPLETE' in report.diagnostic_codes
    assert report.verified_from == report.verified_through == 0
    assert report.witnessed_through is report.checkpoint is None


def test_anchor_does_not_permit_a_suffix_only_bundle(tmp_path):
    path, evidence, anchor = setup_bundle(tmp_path)
    rewrite(path / 'records.jsonl', evidence.records[128:])
    with pytest.raises(BundleReadError, match='ordered by sequence'):
        verify_bundle(path, public_pins(path), Mode.ANCHORED, anchor=anchor)


def test_incremental_bundle_budget_counts_prefix_too(tmp_path):
    path, _, anchor = setup_bundle(tmp_path)
    with pytest.raises(LimitError):
        verify_bundle(path, public_pins(path), Mode.ANCHORED, anchor=anchor, max_records=128)
