"""R07/R10: CLI reports retain specific exits and never accept incomplete trust."""

import json

import pytest

from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.cli import main
from casf.trust.state import locked_state
from tests.unit import test_report_contract as report_tests
from tests.unit.test_cli import _trust
from tests.unit.test_writer import AUTH

cli_bundle = report_tests.cli_bundle


@pytest.mark.parametrize('case,exit_code,overall', [
    ('missing_authority', 3, 'INCONCLUSIVE'), ('missing_status', 3, 'INCONCLUSIVE'),
    ('stale_status', 3, 'INCONCLUSIVE'), ('missing_receipt', 4, 'INCONCLUSIVE'),
    ('missing_anchor', 4, 'INCONCLUSIVE'), ('bad_status', 2, 'FAIL'),
    ('unsupported_status', 3, 'FAIL'), ('unsupported_record', 3, 'FAIL'),
    ('bad_signature', 1, 'FAIL'), ('revoked', 3, 'FAIL'),
])
def test_cli_reports_verdict_and_preserves_checkpoint_on_nonpass(
        cli_bundle, tmp_path, capsys, case, exit_code, overall):
    bundle, manifest, _checkpoint = cli_bundle
    trust = _trust(tmp_path, manifest, mode='anchored')
    status_path = bundle / 'status.jsonl'
    if case in ('missing_authority', 'stale_status'):
        config = json.loads(trust.read_text())
        if case == 'missing_authority':
            config['authorities'] = {}
        else:
            config['logs'][manifest['body']['log_id']]['minimum_status_serial'] = 2
        trust.write_text(json.dumps(config))
    elif case == 'missing_status':
        status_path.unlink()
    elif case == 'missing_receipt':
        (bundle / 'receipts.jsonl').write_bytes(b'')
    elif case == 'missing_anchor':
        (bundle / 'checkpoints.jsonl').write_bytes(b'')
        (bundle / 'receipts.jsonl').write_bytes(b'')
    elif case in ('bad_status', 'unsupported_status', 'revoked'):
        status = json.loads(status_path.read_bytes())
        if case == 'unsupported_status':
            status['body']['version'] = 2
        else:
            status['body']['status'] = 'revoked' if case == 'revoked' else 'unexpected'
        status['signature'] = crypto.sign_status(AUTH, status['body'])
        status_path.write_bytes(canonicalize(status) + b'\n')
    else:
        path = bundle / 'records.jsonl'
        records = [json.loads(line) for line in path.read_bytes().splitlines()]
        if case == 'unsupported_record':
            records[0]['body']['version'] = 2
        else:
            records[0]['signature'] = 'A' * 86
        path.write_bytes(b''.join(canonicalize(record) + b'\n' for record in records))
    state_path = tmp_path / 'retained.json'
    with locked_state(str(state_path), manifest['manifest_hash'], initialize=True) as state:
        state.save(1, None)
    assert main(['verify', str(bundle), '--trust', str(trust), '--state', str(state_path),
                 '--mode', 'anchored', '--json']) == exit_code
    output = capsys.readouterr()
    assert not output.err
    report = json.loads(output.out)
    assert report['overall'] == report['result'] == overall
    assert report['report_version'] == 2
    with locked_state(str(state_path), manifest['manifest_hash']) as state:
        assert state.previous.checkpoint is None
        assert state.previous.revoked is (case == 'revoked')
