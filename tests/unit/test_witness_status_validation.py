"""R07/R08/R10: unsupported signed status is schema input, not a DB failure."""

import sqlite3

import pytest
from cryptography.hazmat.primitives import serialization

from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.cli import main
from casf.errors import CasfError, SchemaError
from tests.status import active_status
from tests.unit.test_witness import _witness
from tests.unit.test_writer import AUTH, LOG_ID, WIT, _manifest_envelope

INVALID = ['unknown', 'ACTIVE', '', 'synthetic-secret-status']


def statement(value, serial=2):
    envelope = active_status(AUTH, _manifest_envelope()['manifest_hash'])
    envelope['body'].update(status=value, serial=serial)
    envelope['signature'] = crypto.sign_status(AUTH, envelope['body'])
    return envelope


def retained(connection):
    return connection.execute('SELECT serial, status FROM w_status').fetchall()


@pytest.mark.parametrize('value', INVALID)
def test_unsupported_status_rejected_before_transaction(tmp_path, value):
    witness = _witness(tmp_path)
    connection = witness._db.connection
    queries = []
    connection.set_trace_callback(queries.append)
    try:
        with pytest.raises(SchemaError) as error:
            witness.install_status(LOG_ID, statement(value))
        assert not any(q.upper().startswith('BEGIN') for q in queries)
        assert not connection.in_transaction
        assert retained(connection) == [(1, 'active')]
        if value:
            assert value not in str(error.value)
    finally:
        witness.close()
    with sqlite3.connect(tmp_path / 'wit.db') as reopened:
        assert retained(reopened) == [(1, 'active')]


@pytest.mark.parametrize('value', INVALID)
def test_cli_unsupported_status_returns_schema_category(tmp_path, monkeypatch, capsys, value):
    witness = _witness(tmp_path)
    witness.close()
    key = tmp_path / 'witness.pem'
    password = b'synthetic-status-passphrase'
    key.write_bytes(WIT.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(password)))
    key.chmod(0o600)
    public = tmp_path / 'authority.pub'
    public.write_bytes(AUTH.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    status = tmp_path / 'status.json'
    status.write_bytes(canonicalize(statement(value)))
    monkeypatch.setenv('CASF_PASSPHRASE', password.decode())
    code = main(['admin', 'status', 'install', '--status-file', str(status),
                 '--log-id', LOG_ID, '--authority-public-key', str(public),
                 '--witness-key', str(key), '--db', str(tmp_path / 'wit.db')])
    output = capsys.readouterr()
    assert code == 2
    assert 'local database failure' not in output.err
    assert not output.out
    assert password.decode() not in output.err
    if value:
        assert value not in output.err
    with sqlite3.connect(tmp_path / 'wit.db') as connection:
        assert retained(connection) == [(1, 'active')]


def test_valid_transitions_keep_serial_and_terminal_revocation_rules(tmp_path):
    witness = _witness(tmp_path)
    try:
        assert witness.install_status(LOG_ID, statement('active'))
        with pytest.raises(CasfError, match='serial must increase'):
            witness.install_status(LOG_ID, statement('active'))
        assert retained(witness._db.connection) == [(2, 'active')]
        assert witness.install_status(LOG_ID, statement('revoked', 3))
        with pytest.raises(CasfError, match='terminal'):
            witness.install_status(LOG_ID, statement('active', 4))
        assert retained(witness._db.connection) == [(3, 'revoked')]
    finally:
        witness.close()
