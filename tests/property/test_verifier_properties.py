"""R02/R03/R07/R11: generated history mutations and trusted suffix equivalence."""

from copy import deepcopy

from hypothesis import given
from hypothesis import strategies as st

from casf import crypto
from casf.verifier import Mode, Result, VerificationAnchor, verify
from tests.property.strategies import objects, profile
from tests.unit.test_verifier import (
    ZERO,
    _checkpoint_env,
    _manifest_env,
    _pins,
    _receipt_env,
    _record_body,
    _record_env,
    _status_env,
)


def history(payloads):
    manifest = _manifest_env()
    mh = manifest['manifest_hash']
    previous = crypto.genesis_hash(mh)
    records = []
    for seq, payload in enumerate(payloads, 1):
        body = _record_body(seq, previous, mh)
        body['payload'] = payload
        record = _record_env(body)
        records.append(record)
        previous = record['record_hash']
    return manifest, records


def check(manifest, records, **kwargs):
    mh = manifest['manifest_hash']
    return verify(manifest, iter(records), _pins(mh), status_envelopes=[_status_env(mh)], **kwargs)


@profile
@given(st.lists(objects, min_size=2, max_size=12), st.data())
def test_middle_sequence_mutations_report_exact_failure(payloads, data):
    manifest, original = history(payloads)
    index = data.draw(st.integers(0, len(original) - 2), label='mutation index')
    for mutation in ('delete', 'duplicate', 'swap'):
        records = deepcopy(original)
        if mutation == 'delete':
            del records[index]
            failure = index + 1
        elif mutation == 'duplicate':
            records.insert(index + 1, records[index])
            failure = index + 2
        else:
            records[index:index + 2] = reversed(records[index:index + 2])
            failure = index + 1
        report = check(manifest, records)
        assert report.result is Result.FAIL
        assert 'SEQ_GAP' in report.diagnostic_codes
        assert report.first_failure_seq == failure
        assert report.verified_through == failure - 1
        assert report.verified_from == (1 if failure > 1 else 0)


@profile
@given(st.lists(objects, min_size=1, max_size=12), st.data())
def test_record_mutations_cannot_retain_a_successful_signature(payloads, data):
    manifest, original = history(payloads)
    index = data.draw(st.integers(0, len(original) - 1), label='mutation index')
    for mutation, code in [('body', 'RECORD_HASH_MISMATCH'), ('digest', 'RECORD_HASH_MISMATCH'),
                           ('signature', 'RECORD_SIGNATURE'), ('link', 'CHAIN_BREAK')]:
        records = deepcopy(original)
        record = records[index]
        if mutation == 'body':
            record['body']['actor'] += '-changed'
        elif mutation == 'digest':
            record['record_hash'] = 'f' * 64 if record['record_hash'] != 'f' * 64 else ZERO
        elif mutation == 'signature':
            signature = bytearray(crypto.b64url_decode(record['signature']))
            signature[0] ^= 1
            record['signature'] = crypto.b64url_encode(bytes(signature))
        else:
            record['body']['prev_hash'] = 'f' * 64
            records[index] = _record_env(record['body'])  # A valid signature cannot repair linkage.
        report = check(manifest, records)
        assert report.result is Result.FAIL and code in report.diagnostic_codes
        assert report.first_failure_seq == index + 1
        assert report.verified_through == index


@profile
@given(st.lists(objects, min_size=1, max_size=12), st.data())
def test_truncated_history_needs_external_evidence(payloads, data):
    manifest, records = history(payloads)
    cut = data.draw(st.integers(0, len(records) - 1), label='prefix count')
    offline = check(manifest, records[:cut])
    assert offline.result is Result.PASS  # Integrity alone cannot establish completeness.
    assert offline.witnessed_through is None
    cp = _checkpoint_env(0, len(records), records[-1]['record_hash'], ZERO, manifest['manifest_hash'])
    anchored = check(manifest, records[:cut], mode=Mode.ANCHORED,
                     checkpoint_envelopes=[cp], receipt_envelopes=[_receipt_env(cp)])
    assert anchored.result is Result.FAIL
    assert anchored.anchor_status.value == 'INCOMPLETE'
    assert 'ANCHOR_INCOMPLETE' in anchored.diagnostic_codes


@profile
@given(st.lists(objects, min_size=1, max_size=12), st.data())
def test_full_and_incremental_reports_agree_on_generated_suffixes(payloads, data):
    manifest, records = history(payloads)
    mh = manifest['manifest_hash']
    cut = data.draw(st.integers(0, len(records)), label='trusted count')
    head = records[cut - 1]['record_hash'] if cut else crypto.genesis_hash(mh)
    first = _checkpoint_env(0, cut, head, ZERO, mh)
    first_receipt = _receipt_env(first)
    last = _checkpoint_env(1, len(records), records[-1]['record_hash'], first['checkpoint_hash'], mh)
    last_receipt = _receipt_env(last, first_receipt['receipt_hash'])
    full = check(manifest, records, mode=Mode.ANCHORED,
                 checkpoint_envelopes=[first, last], receipt_envelopes=[first_receipt, last_receipt])
    anchor = VerificationAnchor(first, first_receipt, expected_checkpoint_hash=first['checkpoint_hash'])
    suffix = check(manifest, records[cut:], mode=Mode.ANCHORED, anchor=anchor,
                   checkpoint_envelopes=[last], receipt_envelopes=[last_receipt])
    assert full.result is suffix.result is Result.PASS
    assert full.checkpoint == suffix.checkpoint
    assert full.witnessed_through == suffix.witnessed_through == len(records)
    assert suffix.verified_from == (cut + 1 if cut < len(records) else 0)
    assert suffix.verified_through == (len(records) if cut < len(records) else 0)
    assert suffix.assumptions['trusted_prefix_through'] == cut
    assert suffix.assumptions['prefix_signatures_checked'] is False


@profile
@given(st.lists(objects, min_size=1, max_size=12), st.integers(1, 12))
def test_record_work_budget_never_consumes_beyond_one_sentinel(payloads, budget):
    manifest, records = history(payloads)
    consumed = []

    def stream():
        for record in records:
            consumed.append(record['body']['seq'])
            assert len(consumed) <= budget + 1
            yield record

    report = check(manifest, stream(), max_records=budget)
    assert len(consumed) == min(len(records), budget + 1)
    assert report.verified_through == min(len(records), budget)
    assert report.result is (Result.PASS if len(records) <= budget else Result.INCONCLUSIVE)
    if len(records) > budget:
        assert 'RECORD_BUDGET_EXCEEDED' in report.diagnostic_codes
