"""The manual rehearsal must create private, strict-TLS synthetic fixtures."""
import importlib.util
from pathlib import Path

import pytest
from cryptography import x509


@pytest.fixture(scope='module')
def rehearsal():
    path = Path(__file__).resolve().parents[2] / 'examples' / 'two_host_rehearsal.py'
    spec = importlib.util.spec_from_file_location('two_host_rehearsal', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_is_private_and_cannot_overwrite_existing_data(tmp_path, rehearsal):
    root = tmp_path / 'private'
    result = rehearsal.prepare(root, '127.0.0.1')
    assert result['log_id']
    for path in root.rglob('*'):
        assert path.stat().st_mode & 0o077 == 0
    original = (root / 'writer/key.pem').read_bytes()
    with pytest.raises(FileExistsError):
        rehearsal.prepare(root, '127.0.0.1')
    assert (root / 'writer/key.pem').read_bytes() == original
    assert not (root / 'witness').joinpath('revoked.json').exists()
    assert {p.name for p in (root / 'public').iterdir()} == {'manifest.json'}


def test_certificates_include_strict_validation_extensions(tmp_path, rehearsal):
    rehearsal.make_certificates(tmp_path, '127.0.0.1')
    ca = x509.load_pem_x509_certificate((tmp_path / 'ca.pem').read_bytes())
    usage = ca.extensions.get_extension_for_class(x509.KeyUsage)
    assert usage.critical and usage.value.key_cert_sign
    ski = ca.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value.digest
    for name in ('valid', 'rotated', 'expired', 'wrong-host'):
        cert = x509.load_pem_x509_certificate((tmp_path / f'{name}.pem').read_bytes())
        aki = cert.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier).value
        assert aki.key_identifier == ski
        assert not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
