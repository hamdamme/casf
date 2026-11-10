"""R03/R07/R10: SPEC report labels, evidence gaps and failure precedence."""

from dataclasses import replace

import pytest

from casf import crypto
from casf.verifier import Mode, Result, verify
from tests.unit.test_verifier import (
    AUTH,
    LOG_PUB,
    WIT_PUB,
    _anchored,
    _chain,
    _manifest_env,
    _pins,
    _status_env,
)


def evidence():
    manifest, records, checkpoints, receipts = _anchored(n=2, anchor_count=2)
    return {'manifest_envelope': manifest, 'records': records,
            'pins': _pins(manifest['manifest_hash']), 'mode': Mode.ANCHORED,
            'checkpoint_envelopes': checkpoints, 'receipt_envelopes': receipts,
            'status_envelopes': [_status_env(manifest['manifest_hash'])]}


@pytest.mark.parametrize('mode', [Mode.INTEGRITY, Mode.ANCHORED])
def test_completed_reports_use_spec_labels_and_versioned_serialization(mode):
    args = evidence()
    args['mode'] = mode
    report = verify(**args)
    output = report.to_dict()
    assert output['report_version'] == 2
    assert report.overall is report.result is Result.PASS
    assert output['overall'] == output['result'] == 'PASS'
    assert output['protocol_status'] == output['signature_status'] == output['chain_status'] == 'VALID'
    assert output['trust_status'] == 'TRUSTED'
    assert output['anchor_status'] == ('NONE' if mode is Mode.INTEGRITY else 'MATCHED')


@pytest.mark.parametrize('missing,code', [
    ('authority', 'ISSUER_UNTRUSTED'), ('status', 'STATUS_MISSING'),
    ('recent_status', 'STATUS_SERIAL_LOW'), ('witness', 'WITNESS_UNTRUSTED'),
    ('checkpoint', 'ANCHOR_MISSING'), ('receipt', 'RECEIPT_MISSING'),
])
def test_missing_required_evidence_is_inconclusive(missing, code):
    args = evidence()
    if missing == 'authority':
        args['pins'] = replace(args['pins'], authority_keys={})
    elif missing == 'witness':
        args['pins'] = replace(args['pins'], witness_keys={})
    elif missing == 'recent_status':
        args['pins'] = replace(args['pins'], minimum_status_serial=2)
    else:
        key = {'status': 'status_envelopes', 'checkpoint': 'checkpoint_envelopes',
               'receipt': 'receipt_envelopes'}[missing]
        args[key] = []
    report = verify(**args)
    assert report.result is Result.INCONCLUSIVE
    assert code in report.diagnostic_codes
    assert report.first_failure_seq is None
    if missing in ('authority', 'witness', 'status', 'recent_status'):
        assert report.trust_status.value == 'UNKNOWN'
    if missing in ('authority', 'witness', 'checkpoint', 'receipt'):
        assert report.signature_status.value == 'NOT_CHECKED'


@pytest.mark.parametrize('kind', ['manifest', 'record', 'checkpoint', 'receipt', 'status'])
@pytest.mark.parametrize('version,protocol', [(2, 'UNSUPPORTED'), (True, 'INVALID'),
                                              (None, 'INVALID'), (0, 'INVALID'), (-1, 'INVALID'),
                                              (1.0, 'INVALID'), ('1', 'INVALID'),
                                              (9007199254740992, 'INVALID')])
def test_versions_have_explicit_protocol_status(kind, version, protocol):
    args = evidence()
    target = {'manifest': args['manifest_envelope'], 'record': args['records'][0],
              'checkpoint': args['checkpoint_envelopes'][0],
              'receipt': args['receipt_envelopes'][0], 'status': args['status_envelopes'][0]}[kind]
    target['body']['version'] = version
    report = verify(**args)
    assert report.result is Result.FAIL
    assert report.protocol_status.value == protocol
    assert report.first_failure_seq == (1 if kind == 'record' else None)
    if protocol == 'UNSUPPORTED':
        assert 'VERSION_UNSUPPORTED' in report.diagnostic_codes


@pytest.mark.parametrize('failure', ['record', 'status', 'revocation'])
def test_failure_dominates_missing_status_and_budgets(failure):
    args = evidence()
    if failure == 'record':
        args['status_envelopes'] = []
        args['records'][1]['signature'] = 'A' * 86
    elif failure == 'status':
        args['status_envelopes'][0]['signature'] = 'A' * 86
        args['max_records'] = 1
    else:
        args['status_envelopes'] = [_status_env(args['manifest_envelope']['manifest_hash'],
                                              status='revoked')]
        args['max_records'] = 1
    report = verify(**args)
    assert report.result is Result.FAIL
    if failure == 'revocation':
        assert report.trust_status.value == 'REVOKED'
    else:
        assert report.signature_status.value == 'INVALID'


def test_early_schema_failure_does_not_claim_signatures_chain_or_anchor():
    args = evidence()
    args['manifest_envelope'] = {}
    args['mode'] = Mode.ONLINE
    report = verify(**args)
    assert report.protocol_status.value == 'INVALID'
    assert report.signature_status.value == report.chain_status.value == 'NOT_CHECKED'
    assert report.anchor_status.value == 'INCOMPLETE'
    assert report.freshness_status.value == 'INCONCLUSIVE'


@pytest.mark.parametrize('kind', ['authority', 'witness'])
def test_conflicting_pin_identity_is_not_missing_trust(kind):
    args = evidence()
    if kind == 'authority':
        issuer = args['manifest_envelope']['body']['issuer_id']
        args['pins'] = replace(args['pins'], authority_keys={issuer: WIT_PUB})
    else:
        wid = args['manifest_envelope']['body']['witness_id']
        args['pins'] = replace(args['pins'], witness_keys={wid: LOG_PUB})
    report = verify(**args)
    assert report.result is Result.FAIL
    assert report.trust_status.value == 'CONFLICT'


def test_unknown_signed_status_cannot_authorize_trust():
    manifest = _manifest_env()
    status = _status_env(manifest['manifest_hash'], status='unrecognized')
    report = verify(manifest, _chain(1), _pins(manifest['manifest_hash']), status_envelopes=[status])
    assert report.result is Result.FAIL
    assert report.protocol_status.value == 'INVALID'
    assert report.trust_status.value == 'UNKNOWN'
    assert report.observed_status_serial == 0


def test_malformed_manifest_key_is_a_report_not_an_exception():
    manifest = _manifest_env()
    manifest['body']['log_public_key'] = 'A'
    manifest['manifest_hash'] = crypto.digest_manifest(manifest['body'])
    manifest['signature'] = crypto.sign_manifest(AUTH, manifest['body'])
    report = verify(manifest, [], _pins(manifest['manifest_hash']))
    assert report.result is Result.FAIL
    assert report.protocol_status.value == 'INVALID'


def test_relabeling_an_authority_key_cannot_authorize_its_signatures():
    from tests.unit.test_verifier import WIT

    args = evidence()
    issuer = args['manifest_envelope']['body']['issuer_id']
    args['pins'] = replace(args['pins'], authority_keys={issuer: WIT_PUB})
    args['manifest_envelope']['signature'] = crypto.sign_manifest(WIT, args['manifest_envelope']['body'])
    args['status_envelopes'][0]['signature'] = crypto.sign_status(WIT, args['status_envelopes'][0]['body'])
    report = verify(**args)
    assert report.result is Result.FAIL
    assert report.trust_status.value == 'CONFLICT'
    assert 'ISSUER_KEY_ID_MISMATCH' in report.diagnostic_codes


@pytest.mark.parametrize('mode', [Mode.INTEGRITY, Mode.ANCHORED])
def test_unknown_coverage_and_unchecked_dimensions_are_explicit(mode):
    args = evidence()
    args['mode'] = mode
    args['max_records'] = 1
    report = verify(**args)
    assert report.result is Result.INCONCLUSIVE
    assert report.verified_from == report.verified_through == 1
    assert report.signature_status.value == report.chain_status.value == 'NOT_CHECKED'
    assert report.witnessed_through is report.unwitnessed_count is None


@pytest.mark.parametrize('reverse', [False, True])
def test_older_status_cannot_be_hidden_by_a_sufficient_statement(reverse):
    args = evidence()
    args['pins'] = replace(args['pins'], minimum_status_serial=2)
    mh = args['manifest_envelope']['manifest_hash']
    statuses = [_status_env(mh, serial=1), _status_env(mh, serial=2)]
    args['status_envelopes'] = statuses[::-1] if reverse else statuses
    report = verify(**args)
    assert report.result is Result.INCONCLUSIVE
    assert report.trust_status.value == 'UNKNOWN'
    assert report.observed_status_serial == 2
    assert 'STATUS_SERIAL_LOW' in report.diagnostic_codes


@pytest.mark.parametrize('missing', ['authority', 'witness', 'status'])
def test_retained_revocation_survives_missing_trust(missing):
    args = evidence()
    args['retained_revoked'] = True
    if missing == 'authority':
        args['pins'] = replace(args['pins'], authority_keys={})
    elif missing == 'witness':
        args['pins'] = replace(args['pins'], witness_keys={})
    else:
        args['status_envelopes'] = []
    report = verify(**args)
    assert report.result is Result.FAIL
    assert report.trust_status.value == 'REVOKED'
    assert 'STATUS_REVOKED_RETAINED' in report.diagnostic_codes
