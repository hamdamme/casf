"""Release scenario regressions for status trust and resource budgets."""

import pytest

from casf.bundle import read_bundle
from casf.verifier import Mode, Result, TrustStatus, verify
from tests.unit.test_bundle import _exported
from tests.unit.test_verifier import _anchored, _chain, _manifest_env, _pins, _status_env


def test_missing_status_is_unknown():
    env = _manifest_env()
    report = verify(env, _chain(1), _pins(env['manifest_hash']))
    assert report.trust_status is TrustStatus.UNKNOWN
    assert report.result is Result.FAIL
    assert 'STATUS_MISSING' in report.diagnostic_codes


def test_unrelated_status_cannot_supply_trust():
    env = _manifest_env()
    report = verify(env, _chain(1), _pins(env['manifest_hash']),
                    status_envelopes=[_status_env('ab' * 32)])
    assert report.trust_status is TrustStatus.UNKNOWN
    assert report.result is Result.FAIL


def test_checkpoint_budget_boundary():
    env, records, cps, receipts = _anchored(n=2, anchor_count=2)
    report = verify(env, records, _pins(env['manifest_hash']), mode=Mode.ANCHORED,
                    checkpoint_envelopes=cps, receipt_envelopes=receipts,
                    status_envelopes=[_status_env(env['manifest_hash'])], max_chain_steps=1)
    assert report.result is Result.PASS


def test_checkpoint_budget_stops_before_extra_crypto():
    env, records, cps, receipts = _anchored(n=2, anchor_count=2)
    def checkpoints():
        yield cps[0]
        yield {}  # budget must reject before schema or signature validation
        raise AssertionError('consumed beyond the budget sentinel')
    report = verify(env, records, _pins(env['manifest_hash']), mode=Mode.ANCHORED,
                    checkpoint_envelopes=checkpoints(), receipt_envelopes=receipts,
                    status_envelopes=[_status_env(env['manifest_hash'])], max_chain_steps=1)
    assert report.result is Result.INCONCLUSIVE
    assert 'CHAIN_BUDGET_EXCEEDED' in report.diagnostic_codes


def test_bundle_never_uses_unbounded_read_bytes(tmp_path, monkeypatch):
    _, dest = _exported(tmp_path, 1)
    from pathlib import Path
    def forbidden(*args, **kwargs):
        raise AssertionError('unbounded read_bytes')
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    assert len(read_bundle(dest).records) == 1


def test_status_symlink_rejected(tmp_path):
    _, dest = _exported(tmp_path, 1)
    other = tmp_path / 'other'
    other.write_text('{}\n')
    (dest / 'status.jsonl').symlink_to(other)
    from casf.errors import CasfError
    with pytest.raises(CasfError, match='symlink'):
        read_bundle(dest)

@pytest.mark.parametrize('mutation, code, through', [
    ('duplicate', 'SEQ_GAP', 1), ('reorder', 'SEQ_GAP', 0),
    ('genesis', 'CHAIN_BREAK', 0), ('splice', 'LOG_BINDING', 0),
])
def test_record_mutations(mutation, code, through):
    from copy import deepcopy

    from tests.unit.test_verifier import _record_env
    env = _manifest_env()
    records = _chain(2)
    if mutation == 'duplicate':
        records = [records[0], records[0], records[1]]
    elif mutation == 'reorder':
        records = list(reversed(records))
    else:
        body = deepcopy(records[0]['body'])
        if mutation == 'genesis':
            body['prev_hash'] = 'ab' * 32
        else:
            body['log_id'] = '123e4567-e89b-42d3-a456-426614174111'
        records[0] = _record_env(body)  # valid signature on the changed record
    report = verify(env, records, _pins(env['manifest_hash']),
                    status_envelopes=[_status_env(env['manifest_hash'])])
    assert report.result is Result.FAIL
    assert code in report.diagnostic_codes
    assert report.verified_through == through


@pytest.mark.parametrize('kind, code', [
    ('invalid', 'STATUS_SIGNATURE'), ('stale', 'STATUS_SERIAL_LOW'),
    ('revoked', 'STATUS_REVOKED'), ('issuer', 'STATUS_ISSUER'),
])
def test_status_rejection_cases(kind, code):
    from casf import crypto
    from tests.unit.test_verifier import AUTH, WIT
    env = _manifest_env()
    mh = env['manifest_hash']
    pins = _pins(mh, minimum_status_serial=2 if kind == 'stale' else 1)
    status = _status_env(mh, signer=WIT if kind == 'invalid' else AUTH,
                         status='revoked' if kind == 'revoked' else 'active')
    if kind == 'issuer':
        status['body']['issuer_id'] = 'ab' * 32
        status['signature'] = crypto.sign_status(AUTH, status['body'])
    report = verify(env, _chain(1), pins, status_envelopes=[status])
    assert report.result is Result.FAIL
    assert report.trust_status is not TrustStatus.OK
    assert code in report.diagnostic_codes


def test_old_signed_active_status_does_not_claim_current_revocation_knowledge():
    env = _manifest_env()
    report = verify(env, _chain(1), _pins(env['manifest_hash']),
                    status_envelopes=[_status_env(env['manifest_hash'])])
    assert report.result is Result.PASS
    assert report.trust_status is TrustStatus.OK
    assert 'STATUS_CURRENTNESS_UNCONFIRMED' in report.diagnostic_codes


@pytest.mark.parametrize('reverse', [False, True])
def test_revocation_cannot_be_overridden_by_active_or_invalid_status(reverse):
    env = _manifest_env()
    mh = env['manifest_hash']
    statements = [_status_env(mh, status='revoked'), _status_env(mh, serial=2), {}]
    report = verify(env, _chain(1), _pins(mh),
                    status_envelopes=reversed(statements) if reverse else statements)
    assert report.result is Result.FAIL
    assert report.trust_status is TrustStatus.REVOKED


def test_receipt_budget_stops_before_extra_validation():
    env, records, cps, receipts = _anchored(n=2, anchor_count=2)
    report = verify(env, records, _pins(env['manifest_hash']), mode=Mode.ANCHORED,
                    checkpoint_envelopes=cps, receipt_envelopes=receipts + [{}],
                    status_envelopes=[_status_env(env['manifest_hash'])], max_chain_steps=1)
    assert report.result is Result.INCONCLUSIVE
    assert 'CHAIN_BUDGET_EXCEEDED' in report.diagnostic_codes


@pytest.mark.parametrize('limit', [0, -1, True, 1.5])
def test_invalid_chain_budget_rejected(limit):
    env = _manifest_env()
    with pytest.raises(ValueError, match='positive integer'):
        verify(env, [], _pins(env['manifest_hash']), max_chain_steps=limit)


def test_bundle_count_and_byte_budgets(tmp_path):
    from casf.errors import LimitError
    _, dest = _exported(tmp_path, 2)
    with pytest.raises(LimitError, match='count limit'):
        read_bundle(dest, max_records=1)
    assert len(read_bundle(dest, max_records=2).records) == 2
    total = sum(p.stat().st_size for p in dest.iterdir())
    assert len(read_bundle(dest, max_total_bytes=total).records) == 2
    with pytest.raises(LimitError, match='byte limit'):
        read_bundle(dest, max_total_bytes=total - 1)


@pytest.mark.parametrize('member', ['manifest.json', 'status.jsonl', 'checkpoints.jsonl'])
def test_oversized_protocol_input_rejected(tmp_path, member):
    from casf.errors import LimitError
    _, dest = _exported(tmp_path, 1)
    (dest / member).write_bytes(b' ' * 32769 + b'\n')
    with pytest.raises(LimitError, match='limit'):
        read_bundle(dest)


def test_nonregular_bundle_member_does_not_block(tmp_path):
    import os

    from casf.errors import CasfError
    _, dest = _exported(tmp_path, 1)
    (dest / 'records.jsonl').unlink()
    os.mkfifo(dest / 'records.jsonl')
    with pytest.raises(CasfError, match='regular'):
        read_bundle(dest)


def test_export_snapshot_during_concurrent_append(tmp_path, monkeypatch):
    from casf import crypto
    from casf.writer import Writer
    from tests.status import active_status
    from tests.unit.test_bundle import _pins as writer_pins
    from tests.unit.test_writer import AUTH, LOG, LOG_ID, _append, _writer
    db = tmp_path / 'writer.db'
    writer = _writer(db)
    _append(writer, 1)
    original = writer.records
    def records(log_id):
        other = Writer(db, LOG)
        try:
            _append(other, 2)
        finally:
            other.close()
        yield from original(log_id)
    monkeypatch.setattr(writer, 'records', records)
    try:
        dest = writer.export_bundle(LOG_ID, tmp_path / 'snapshot')
        bundle = read_bundle(dest)
        report = verify(bundle.manifest, bundle.records, writer_pins(bundle.manifest_hash),
                        status_envelopes=[active_status(AUTH, bundle.manifest_hash)])
        assert report.result is Result.PASS
        assert report.verified_through == bundle.metadata['through'] == 1
        assert len(list(original(LOG_ID))) == 2
        assert crypto.digest_manifest(bundle.manifest['body']) == bundle.manifest_hash
    finally:
        writer.close()


def test_missing_wal_copy_is_incomplete_against_external_anchor(tmp_path):
    import shutil

    from casf import crypto
    from casf.witness import Witness
    from casf.writer import Writer
    from tests.status import active_status
    from tests.unit.test_bundle import _pins as writer_pins
    from tests.unit.test_writer import AUTH, AUTH_PUB, LOG, LOG_ID, WIT, _append, _writer
    db = tmp_path / 'live.db'
    writer = _writer(db)
    witness = Witness(tmp_path / 'wit.db', WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    try:
        con = writer._db.connection
        con.execute('PRAGMA wal_autocheckpoint=0')
        con.execute('PRAGMA wal_checkpoint(TRUNCATE)')  # baseline contains the manifest
        _append(writer, 1)
        manifest = writer.manifest_envelope(LOG_ID)
        from tests.status import register_active
        from tests.unit.test_writer import AUTH
        register_active(witness, manifest, AUTH)
        cp = writer.create_checkpoint(LOG_ID)
        receipt = witness.submit(LOG_ID, cp, list(writer.records(LOG_ID)))
        assert db.with_name('live.db-wal').stat().st_size > 0
        copy = tmp_path / 'incomplete.db'
        shutil.copyfile(db, copy)  # deliberately omit only this synthetic WAL
        restored = Writer(copy, LOG)
        try:
            report = verify(manifest, restored.records(LOG_ID),
                            writer_pins(manifest['manifest_hash']), mode=Mode.ANCHORED,
                            checkpoint_envelopes=[cp], receipt_envelopes=[receipt],
                            status_envelopes=[active_status(AUTH, manifest['manifest_hash'])])
            assert report.result is Result.FAIL
            assert 'ANCHOR_INCOMPLETE' in report.diagnostic_codes
        finally:
            restored.close()
    finally:
        writer.close()
        witness.close()


def test_signed_witness_equivocation_retained_and_isolated_clients():
    from casf import crypto
    from casf.online import verify_latest_response
    from tests.unit.test_verifier import (
        LOG_ID,
        TS,
        WIT,
        WIT_PUB,
        ZERO,
        _checkpoint_env,
        _receipt_env,
        _record_env,
    )
    env, _records_a, cps_a, rcs_a = _anchored(n=2, anchor_count=2)
    mh = env['manifest_hash']
    records_b = _chain(2)
    body = dict(records_b[1]['body'])
    body['payload'] = {'fork': True}
    records_b[1] = _record_env(body)
    cp_b = _checkpoint_env(0, 2, records_b[1]['record_hash'], ZERO, mh)
    rc_b = _receipt_env(cp_b)
    def signed_view(cp, rc, nonce):
        latest = {'version': 1, 'type': 'latest', 'nonce': crypto.b64url_encode(nonce),
                  'witness_id': crypto.key_id(WIT_PUB), 'log_id': LOG_ID,
                  'manifest_hash': mh, 'checkpoint_hash': cp['checkpoint_hash'],
                  'receipt_hash': rc['receipt_hash'], 'checkpoint_index': 0, 'count': 2,
                  'head_hash': cp['body']['head_hash'], 'final': False, 'responded_at': TS}
        return verify_latest_response(
            {'body': latest, 'signature': crypto.sign_latest(WIT, latest),
             'checkpoint': cp, 'receipt': rc}, nonce, WIT_PUB, LOG_ID)
    view_a = signed_view(cps_a[0], rcs_a[0], b'a' * 32)
    view_b = signed_view(cp_b, rc_b, b'b' * 32)
    assert view_a.body['checkpoint_hash'] != view_b.body['checkpoint_hash']
    options = {"mode": Mode.ONLINE, "checkpoint_envelopes": [cp_b],
               "receipt_envelopes": [rc_b], "status_envelopes": [_status_env(mh)],
               "online_query": lambda: view_b}
    isolated = verify(env, records_b, _pins(mh), **options)
    assert isolated.result is Result.PASS
    retained = verify(env, records_b, _pins(mh),
                      retained_checkpoint=(0, cps_a[0]['checkpoint_hash']), **options)
    assert retained.result is Result.FAIL
    assert 'WITNESS_STATE_CONFLICT' in retained.diagnostic_codes


def test_cli_missing_status_reports_unknown(tmp_path, capsys):
    from casf.cli import main
    from tests.unit.test_cli import _exported as exported
    from tests.unit.test_cli import _trust
    from tests.unit.test_writer import _manifest_envelope
    _, dest = exported(tmp_path, capsys)
    (dest / 'status.jsonl').unlink()
    trust = _trust(tmp_path, _manifest_envelope())
    assert main(['verify', str(dest), '--state', str(tmp_path / 'state.json'),
                 '--initialize-state', '--trust', str(trust), '--json']) == 3
    import json
    report = json.loads(capsys.readouterr().out)
    assert report['trust_status'] == 'UNKNOWN'
    assert 'STATUS_MISSING' in report['diagnostic_codes']


def test_cli_honors_chain_budget(tmp_path, capsys):
    import json

    from casf.canonical.jcs import canonicalize
    from casf.cli import main
    from tests.unit.test_cli import _exported as exported
    from tests.unit.test_cli import _trust
    from tests.unit.test_writer import _manifest_envelope
    _, dest = exported(tmp_path, capsys)
    trust = _trust(tmp_path, _manifest_envelope(), mode='anchored')
    cfg = json.loads(trust.read_text())
    cfg['policy']['max_chain_steps'] = 1
    trust.write_text(json.dumps(cfg))
    cp_file = dest / 'checkpoints.jsonl'
    cp_file.write_bytes(cp_file.read_bytes() + canonicalize({}) + b'\n')
    assert main(['verify', str(dest), '--state', str(tmp_path / 'state.json'),
                 '--initialize-state', '--trust', str(trust), '--json']) == 4
    report = json.loads(capsys.readouterr().out)
    assert report['result'] == 'INCONCLUSIVE'
    assert 'CHAIN_BUDGET_EXCEEDED' in report['diagnostic_codes']


def test_cli_rejects_invalid_chain_budget(tmp_path, capsys):
    import json

    from casf.cli import main
    from tests.unit.test_cli import _exported as exported
    from tests.unit.test_cli import _trust
    from tests.unit.test_writer import _manifest_envelope
    _, dest = exported(tmp_path, capsys)
    trust = _trust(tmp_path, _manifest_envelope())
    cfg = json.loads(trust.read_text())
    cfg['policy']['max_chain_steps'] = True
    trust.write_text(json.dumps(cfg))
    assert main(['verify', str(dest), '--state', str(tmp_path / 'state.json'),
                 '--initialize-state', '--trust', str(trust)]) == 2


def test_cli_honors_bundle_count_limit(tmp_path, capsys):
    from casf.cli import main
    from tests.unit.test_cli import _exported as exported
    from tests.unit.test_cli import _trust
    from tests.unit.test_writer import _manifest_envelope
    _, dest = exported(tmp_path, capsys)
    trust = _trust(tmp_path, _manifest_envelope())
    assert main(['verify', str(dest), '--state', str(tmp_path / 'state.json'),
                 '--initialize-state', '--trust', str(trust), '--max-records', '1']) == 2
    assert 'count limit' in capsys.readouterr().err


def test_verifier_record_budget():
    env = _manifest_env()
    report = verify(env, _chain(2), _pins(env['manifest_hash']),
                    status_envelopes=[_status_env(env['manifest_hash'])], max_records=1)
    assert report.result is Result.INCONCLUSIVE
    assert report.verified_through == 1
    assert 'RECORD_BUDGET_EXCEEDED' in report.diagnostic_codes
