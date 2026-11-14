"""R10: trust creation and loading agree on finite positive timeouts."""

import json

import pytest
from cryptography.hazmat.primitives import serialization

from casf.canonical.jcs import canonicalize
from casf.cli import _load_trust, main
from casf.errors import SchemaError
from tests.unit.test_writer import AUTH, LOG_ID, _manifest_envelope


@pytest.fixture
def trust_command(tmp_path):
    manifest = tmp_path / 'manifest.json'
    manifest.write_bytes(canonicalize(_manifest_envelope()))
    authority = tmp_path / 'authority.pub'
    authority.write_bytes(AUTH.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    output = tmp_path / 'trust.json'
    return ['admin', 'trust', '--manifest', str(manifest),
            '--authority-public-key', str(authority), '--out', str(output)], output


@pytest.mark.parametrize('timeout', ['0', '-1', 'nan', 'inf', '-inf'])
def test_admin_trust_rejects_invalid_timeout(trust_command, capsys, timeout):
    command, output = trust_command
    # Equals syntax ensures argparse passes negative infinity to the handler.
    assert main([*command, f'--timeout={timeout}']) == 2
    captured = capsys.readouterr()
    assert not output.exists()
    assert not captured.out
    assert 'created trust pins' not in captured.err
    assert 'Traceback' not in captured.err
    assert 'positive and finite' in captured.err


@pytest.mark.parametrize('timeout', ['0.5', '1', '10'])
def test_admin_trust_valid_timeout_roundtrips(trust_command, capsys, timeout):
    command, output = trust_command
    assert main([*command, '--timeout', timeout]) == 0
    assert 'created trust pins' in capsys.readouterr().out
    _, _, policy = _load_trust(str(output), LOG_ID)
    assert policy['query_timeout_seconds'] == float(timeout)


@pytest.mark.parametrize('timeout', [0, -1, True, '1', None])
def test_trust_loader_keeps_timeout_validation(trust_command, capsys, timeout):
    command, output = trust_command
    assert main(command) == 0
    capsys.readouterr()
    trust = json.loads(output.read_text())
    trust['policy']['query_timeout_seconds'] = timeout
    output.write_text(json.dumps(trust))
    with pytest.raises(SchemaError, match='positive and finite'):
        _load_trust(str(output), LOG_ID)
