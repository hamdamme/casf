"""R03/R07/R11: authenticate a trusted start and verify only its contiguous suffix."""

from dataclasses import FrozenInstanceError, replace

import pytest

from casf import crypto
from casf.canonical.limits import SAFE_INT_MAX
from casf.errors import InconclusiveError, TrustError
from casf.verifier import Mode, Result, verify
from casf.verifier.anchor import VerificationAnchor
from tests.unit.test_verifier import (
    LOG,
    WIT,
    ZERO,
    _chain,
    _checkpoint_env,
    _manifest_env,
    _pins,
    _receipt_env,
    _record_body,
    _record_env,
    _status_env,
)


def history():
    manifest = _manifest_env()
    mh = manifest['manifest_hash']
    records = _chain(4)
    c0 = _checkpoint_env(0, 2, records[1]['record_hash'], ZERO, mh)
    r0 = _receipt_env(c0)
    c1 = _checkpoint_env(1, 4, records[3]['record_hash'], c0['checkpoint_hash'], mh)
    r1 = _receipt_env(c1, r0['receipt_hash'])
    anchor = VerificationAnchor(c0, r0, expected_checkpoint_hash=c0['checkpoint_hash'])
    return {'manifest_envelope': manifest, 'records': records[2:], 'pins': _pins(mh),
            'mode': Mode.ANCHORED, 'checkpoint_envelopes': [c1], 'receipt_envelopes': [r1],
            'status_envelopes': [_status_env(mh)], 'anchor': anchor}


def test_suffix_matches_full_verification_without_checking_prefix_bodies(monkeypatch):
    args = history()
    anchor = args['anchor']
    full = dict(args, records=_chain(4),
                checkpoint_envelopes=[anchor.checkpoint.to_dict(), *args['checkpoint_envelopes']],
                receipt_envelopes=[anchor.receipt, *args['receipt_envelopes']])
    full.pop('anchor')
    expected = verify(**full)
    seen = []
    original = crypto.verify_record

    def record_check(key, body, signature):
        seen.append(body['seq'])
        original(key, body, signature)

    monkeypatch.setattr(crypto, 'verify_record', record_check)
    report = verify(**args)
    assert report.result is expected.result is Result.PASS
    assert report.checkpoint == expected.checkpoint
    assert report.witnessed_through == expected.witnessed_through == 4
    assert (report.verified_from, report.verified_through) == (3, 4)
    assert seen == [3, 4]
    assert report.assumptions['trusted_prefix_through'] == 2
    assert report.assumptions['prefix_signatures_checked'] is False


@pytest.mark.parametrize('mode', [Mode.INTEGRITY, Mode.ANCHORED])
def test_empty_suffix_does_not_claim_prior_bodies_were_checked(mode):
    args = history()
    args.update(records=[], checkpoint_envelopes=[], receipt_envelopes=[], mode=mode)
    report = verify(**args)
    assert report.result is Result.PASS
    assert report.verified_from == report.verified_through == 0
    if mode is Mode.ANCHORED:
        assert report.witnessed_through == 2 and report.unwitnessed_count == 0


@pytest.mark.parametrize('change,code', [
    ('gap', 'SEQ_GAP'), ('previous', 'CHAIN_BREAK'), ('signature', 'RECORD_SIGNATURE'),
    ('duplicate', 'SEQ_GAP'), ('wrong_log', 'LOG_BINDING'),
])
def test_suffix_rejects_invalid_first_record_at_absolute_sequence(change, code):
    args = history()
    if change == 'gap':
        args['records'] = args['records'][1:]
    elif change == 'previous':
        args['records'][0]['body']['prev_hash'] = 'ab' * 32
    elif change == 'signature':
        args['records'][0]['signature'] = 'A' * 86
    elif change == 'duplicate':
        args['records'] = [_chain(4)[1], *args['records']]
    else:
        args['records'][0]['body']['log_id'] = '123e4567-e89b-42d3-a456-426614174099'
    report = verify(**args)
    assert report.result is Result.FAIL
    assert report.first_failure_seq == 3
    assert report.verified_from == report.verified_through == 0
    assert code in report.diagnostic_codes


@pytest.mark.parametrize('kind', ['checkpoint', 'receipt'])
def test_anchor_signatures_are_checked_before_consuming_suffix(kind):
    args = history()
    cp, rc = args['anchor'].checkpoint.to_dict(), args['anchor'].receipt
    (cp if kind == 'checkpoint' else rc)['signature'] = 'A' * 86
    args['anchor'] = VerificationAnchor(cp, rc, expected_checkpoint_hash=cp['checkpoint_hash'])

    def forbidden():
        pytest.fail('unauthenticated anchor consumed suffix records')
        yield

    args['records'] = forbidden()
    report = verify(**args)
    assert report.result is Result.FAIL
    assert report.signature_status.value == 'INVALID'
    assert 'START_' + kind.upper() + '_SIGNATURE' in report.diagnostic_codes


def test_missing_witness_pin_cannot_authorize_incremental_integrity():
    args = history()
    args['pins'] = replace(args['pins'], witness_keys={})
    args['mode'] = Mode.INTEGRITY
    report = verify(**args)
    assert report.result is Result.INCONCLUSIVE
    assert report.trust_status.value == 'UNKNOWN'
    assert report.verified_through == 0


@pytest.mark.parametrize('field,value', [('count', 3), ('head_hash', 'ab' * 32), ('checkpoint_index', 1)])
def test_anchor_constructor_rejects_inconsistent_receipt(field, value):
    args = history()
    cp, rc = args['anchor'].checkpoint.to_dict(), args['anchor'].receipt
    rc['body'][field] = value
    rc['receipt_hash'] = crypto.digest_receipt(rc['body'])
    rc['signature'] = crypto.sign_receipt(WIT, rc['body'])
    with pytest.raises(TrustError):
        VerificationAnchor(cp, rc, expected_checkpoint_hash=cp['checkpoint_hash'])


def test_explicit_anchor_pin_is_required_and_cannot_be_replaced():
    args = history()
    with pytest.raises(TrustError):
        VerificationAnchor(args['anchor'].checkpoint.to_dict(), args['anchor'].receipt,
                           expected_checkpoint_hash='ff' * 32)


def test_suffix_record_budget_counts_only_new_records():
    args = history()
    args['max_records'] = 1
    report = verify(**args)
    assert report.result is Result.INCONCLUSIVE
    assert (report.verified_from, report.verified_through) == (3, 3)
    assert 'RECORD_BUDGET_EXCEEDED' in report.diagnostic_codes


@pytest.mark.parametrize('kind', ['record', 'checkpoint'])
def test_final_start_rejects_any_extension(kind):
    args = history()
    cp = args['anchor'].checkpoint.to_dict()
    cp['body']['final'] = True
    cp['checkpoint_hash'] = crypto.digest_checkpoint(cp['body'])
    cp['signature'] = crypto.sign_checkpoint(LOG, cp['body'])
    args['anchor'] = VerificationAnchor(cp, _receipt_env(cp), expected_checkpoint_hash=cp['checkpoint_hash'])
    if kind == 'checkpoint':
        extension = _checkpoint_env(1, 2, cp['body']['head_hash'], cp['checkpoint_hash'],
                                    cp['body']['manifest_hash'])
        args.update(records=[], checkpoint_envelopes=[extension], receipt_envelopes=[])
    report = verify(**args)
    assert report.result is Result.FAIL
    assert ('RECORD_AFTER_FINAL' if kind == 'record' else 'CHECKPOINT_AFTER_FINAL') in report.diagnostic_codes


@pytest.mark.parametrize('kind', ['same', 'conflict', 'newer'])
def test_retained_checkpoint_remains_binding(kind):
    args = history()
    cp = args['anchor'].checkpoint
    args['retained_checkpoint'] = ((cp.index, cp.digest) if kind == 'same' else
                                    (cp.index, 'ff' * 32) if kind == 'conflict' else (3, 'ff' * 32))
    report = verify(**args)
    assert report.result is (Result.PASS if kind == 'same' else Result.FAIL)
    if kind != 'same':
        assert 'WITNESS_STATE_CONFLICT' in report.diagnostic_codes


@pytest.mark.parametrize('outcome', ['fresh', 'ahead', 'behind', 'timeout'])
def test_incremental_online_view_keeps_freshness_rules(outcome):
    from types import SimpleNamespace

    args = history()
    cp = args['checkpoint_envelopes'][0]
    args['mode'] = Mode.ONLINE

    def query():
        if outcome == 'timeout':
            raise InconclusiveError('synthetic timeout')
        index = {'fresh': 1, 'ahead': 2, 'behind': 0}[outcome]
        return SimpleNamespace(body={'checkpoint_index': index, 'checkpoint_hash': cp['checkpoint_hash']})

    args['online_query'] = query
    report = verify(**args)
    assert report.result is {'fresh': Result.PASS, 'ahead': Result.INCONCLUSIVE,
                             'behind': Result.FAIL, 'timeout': Result.INCONCLUSIVE}[outcome]


def test_anchor_owns_input_and_returns_detached_snapshots():
    args = history()
    cp, rc = args['anchor'].checkpoint.to_dict(), args['anchor'].receipt
    anchor = VerificationAnchor(cp, rc, expected_checkpoint_hash=cp['checkpoint_hash'])
    cp['signature'] = rc['signature'] = 'A' * 86
    anchor.receipt['signature'] = 'A' * 86
    anchor.checkpoint.to_dict()['signature'] = 'A' * 86
    with pytest.raises(FrozenInstanceError):
        anchor.checkpoint = args['anchor'].checkpoint
    assert verify(**dict(args, anchor=anchor)).result is Result.PASS


@pytest.mark.parametrize('mode', list(Mode))
@pytest.mark.parametrize('status', ['missing', 'revoked', 'retained_revoked'])
def test_incremental_never_bypasses_status_trust(mode, status):
    args = history()
    args['mode'] = mode
    mh = args['manifest_envelope']['manifest_hash']
    if status == 'missing':
        args['status_envelopes'] = []
    elif status == 'revoked':
        args['status_envelopes'] = [_status_env(mh, status='revoked')]
    else:
        args['retained_revoked'] = True
    if mode is Mode.ONLINE:
        # Offline trust remains a separate requirement even with a fresh view.
        from types import SimpleNamespace
        cp = args['checkpoint_envelopes'][0]
        args['online_query'] = lambda: SimpleNamespace(
            body={'checkpoint_index': 1, 'checkpoint_hash': cp['checkpoint_hash']})
    report = verify(**args)
    assert report.result is (Result.INCONCLUSIVE if status == 'missing' else Result.FAIL)
    assert report.trust_status.value == ('UNKNOWN' if status == 'missing' else 'REVOKED')


@pytest.mark.parametrize('field', ['key_id', 'manifest_hash', 'log_id', 'witness_id'])
def test_anchor_cannot_change_manifest_bindings(field):
    args = history()
    cp = args['anchor'].checkpoint.to_dict()
    if field != 'witness_id':
        cp['body'][field] = ('123e4567-e89b-42d3-a456-426614174099' if field == 'log_id'
                             else 'ab' * 32)
        cp['checkpoint_hash'] = crypto.digest_checkpoint(cp['body'])
        cp['signature'] = crypto.sign_checkpoint(LOG, cp['body'])
    rc = _receipt_env(cp)
    rc['body']['log_id'] = cp['body']['log_id']
    if field == 'witness_id':
        rc['body']['witness_id'] = 'ab' * 32
    rc['receipt_hash'] = crypto.digest_receipt(rc['body'])
    rc['signature'] = crypto.sign_receipt(WIT, rc['body'])
    args['anchor'] = VerificationAnchor(cp, rc, expected_checkpoint_hash=cp['checkpoint_hash'])
    report = verify(**args)
    assert report.result is Result.FAIL
    assert 'START_BINDING' in report.diagnostic_codes
    assert report.verified_through == 0


@pytest.mark.parametrize('count', [0, 4000, SAFE_INT_MAX])
def test_arbitrary_trusted_start_and_sequence_boundary(count):
    args = history()
    mh = args['manifest_envelope']['manifest_hash']
    head = crypto.genesis_hash(mh) if count == 0 else 'ab' * 32
    cp = _checkpoint_env(9, count, head, 'cd' * 32, mh)
    rc = _receipt_env(cp, 'ef' * 32)
    args.update(anchor=VerificationAnchor(cp, rc, expected_checkpoint_hash=cp['checkpoint_hash']),
                checkpoint_envelopes=[], receipt_envelopes=[], records=[], max_records=1,
                allow_unwitnessed=True)
    report = verify(**args)
    assert report.result is Result.PASS and report.verified_through == 0
    if count == SAFE_INT_MAX:
        args['records'] = [{}]
        report = verify(**args)
        assert report.result is Result.FAIL and 'SEQ_OVERFLOW' in report.diagnostic_codes
        assert report.first_failure_seq is None
    else:
        args['records'] = [_record_env(_record_body(count + 1, head, mh))]
        report = verify(**args)
        assert report.result is Result.PASS
        assert report.verified_from == report.verified_through == count + 1
        assert report.unwitnessed_count == 1


@pytest.mark.parametrize('mode', [Mode.INTEGRITY, Mode.ANCHORED])
def test_retained_state_before_start_requires_history(mode):
    args = history()
    cp, rc = args['checkpoint_envelopes'][0], args['receipt_envelopes'][0]
    previous = args['anchor'].checkpoint
    args.update(anchor=VerificationAnchor(cp, rc, expected_checkpoint_hash=cp['checkpoint_hash']),
                records=[], checkpoint_envelopes=[], receipt_envelopes=[], mode=mode,
                retained_checkpoint=(previous.index, previous.digest))
    report = verify(**args)
    assert report.result is Result.INCONCLUSIVE
    assert 'RETAINED_CHECKPOINT_UNAVAILABLE' in report.diagnostic_codes


def test_integrity_start_cannot_replace_retained_checkpoint():
    args = history()
    args.update(mode=Mode.INTEGRITY, retained_checkpoint=(0, 'ab' * 32))
    report = verify(**args)
    assert report.result is Result.FAIL
    assert 'WITNESS_STATE_CONFLICT' in report.diagnostic_codes


@pytest.mark.parametrize('allowed', [False, True])
def test_unwitnessed_suffix_still_requires_explicit_policy(allowed):
    args = history()
    args.update(checkpoint_envelopes=[], receipt_envelopes=[], allow_unwitnessed=allowed)
    report = verify(**args)
    assert report.result is (Result.PASS if allowed else Result.FAIL)
    assert report.unwitnessed_count == 2 and report.witnessed_through == 2
    assert report.anchor_status.value == 'PARTIAL_ANCHOR'


@pytest.mark.parametrize('kind,field,code', [
    ('checkpoint', 'index', 'CHECKPOINT_INDEX_GAP'),
    ('checkpoint', 'previous_checkpoint_hash', 'CHECKPOINT_CHAIN_BREAK'),
    ('receipt', 'previous_receipt_hash', 'RECEIPT_CHAIN_BREAK'),
    ('receipt', 'count', 'RECEIPT_CHECKPOINT_MISMATCH'),
    ('receipt', 'head_hash', 'RECEIPT_CHECKPOINT_MISMATCH'),
    ('receipt', 'checkpoint_index', 'RECEIPT_CHECKPOINT_MISMATCH'),
])
def test_extension_chains_and_receipt_binding(kind, field, code):
    args = history()
    env = args[kind + '_envelopes'][0]
    env['body'][field] = 9 if type(env['body'][field]) is int else 'ab' * 32
    digest = crypto.digest_checkpoint if kind == 'checkpoint' else crypto.digest_receipt
    sign = crypto.sign_checkpoint if kind == 'checkpoint' else crypto.sign_receipt
    env[kind + '_hash'] = digest(env['body'])
    env['signature'] = sign(LOG if kind == 'checkpoint' else WIT, env['body'])
    report = verify(**args)
    assert report.result is Result.FAIL and code in report.diagnostic_codes


def test_suffix_iterator_error_propagates_without_partial_report():
    args = history()

    def broken():
        yield args['records'][0]
        raise OSError('synthetic read failure')

    with pytest.raises(OSError, match='synthetic read failure'):
        verify(**dict(args, records=broken()))


def test_extension_budget_is_bounded_and_does_not_count_start():
    args = history()
    assert verify(**dict(args, max_chain_steps=1)).result is Result.PASS

    def extensions():
        yield args['checkpoint_envelopes'][0]
        yield {}  # Budget sentinel; must not be parsed or followed.
        pytest.fail('unbounded checkpoint consumption')

    report = verify(**dict(args, max_chain_steps=1, checkpoint_envelopes=extensions()))
    assert report.result is Result.INCONCLUSIVE
    assert 'CHAIN_BUDGET_EXCEEDED' in report.diagnostic_codes


@pytest.mark.parametrize('field', ['count', 'head_hash', 'checkpoint_index'])
def test_full_verification_rejects_signed_receipt_field_mismatch(field):
    args = history()
    anchor = args.pop('anchor')
    args.update(records=_chain(4),
                checkpoint_envelopes=[anchor.checkpoint.to_dict(), *args['checkpoint_envelopes']],
                receipt_envelopes=[anchor.receipt, *args['receipt_envelopes']])
    rc = args['receipt_envelopes'][-1]
    rc['body'][field] = 'ab' * 32 if field == 'head_hash' else 9
    rc['receipt_hash'] = crypto.digest_receipt(rc['body'])
    rc['signature'] = crypto.sign_receipt(WIT, rc['body'])
    report = verify(**args)
    assert report.result is Result.FAIL
    assert 'RECEIPT_CHECKPOINT_MISMATCH' in report.diagnostic_codes


@pytest.mark.parametrize('extension', ['record', 'checkpoint'])
def test_full_verification_rejects_extensions_after_final(extension):
    args = history()
    anchor = args.pop('anchor')
    cp = anchor.checkpoint.to_dict()
    cp['body']['final'] = True
    cp['checkpoint_hash'] = crypto.digest_checkpoint(cp['body'])
    cp['signature'] = crypto.sign_checkpoint(LOG, cp['body'])
    args.update(records=_chain(4), checkpoint_envelopes=[cp], receipt_envelopes=[_receipt_env(cp)])
    if extension == 'checkpoint':
        args['records'] = args['records'][:2]
        args['checkpoint_envelopes'].append(_checkpoint_env(
            1, 2, cp['body']['head_hash'], cp['checkpoint_hash'], cp['body']['manifest_hash']))
    report = verify(**args)
    assert report.result is Result.FAIL
    assert ('RECORD_AFTER_FINAL' if extension == 'record' else 'CHECKPOINT_AFTER_FINAL') in report.diagnostic_codes
