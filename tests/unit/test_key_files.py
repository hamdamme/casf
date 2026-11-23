"""Private key storage boundaries, using synthetic encrypted keys only."""

import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.errors import CasfError
from casf.keys import generate_key, load_key

PASS = b"synthetic-key-file-test"


@pytest.mark.parametrize("passphrase", [b"", b"x", b"x" * 15, ("é" * 7).encode()])
def test_short_passphrase_rejected_before_generation_or_filesystem(tmp_path, monkeypatch, passphrase):
    def unexpected_generation():
        pytest.fail("short passphrase reached key generation")

    monkeypatch.setattr(Ed25519PrivateKey, "generate", unexpected_generation)
    path = tmp_path / "missing-directory" / "key.pem"
    with pytest.raises(CasfError, match="^passphrase must be at least 16 bytes$"):
        generate_key("log", path, passphrase=passphrase)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("passphrase", [b"x" * 16, b"x" * 17, b"x" * 64, ("é" * 8).encode()])
def test_acceptable_passphrase_creates_encrypted_pkcs8(tmp_path, passphrase):
    path = tmp_path / "key.pem"
    generate_key("log", path, passphrase=passphrase)
    raw = path.read_bytes()
    assert raw.startswith(b"-----BEGIN ENCRYPTED PRIVATE KEY-----\n")
    key = load_key(path, passphrase=passphrase)
    directly_loaded = serialization.load_pem_private_key(raw, password=passphrase)
    assert isinstance(directly_loaded, Ed25519PrivateKey)
    assert crypto.public_key_raw(key) == crypto.public_key_raw(directly_loaded)
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("passphrase", [b"x", b"old-passphrase", b"x" * 15])
def test_legacy_encrypted_key_accepts_short_passphrase(tmp_path, passphrase):
    original = Ed25519PrivateKey.generate()
    raw = original.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(passphrase),
    )
    path = tmp_path / "legacy-key.pem"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
    loaded = load_key(path, passphrase=passphrase)
    assert crypto.public_key_raw(loaded) == crypto.public_key_raw(original)
    with pytest.raises(CasfError, match="could not be decrypted or parsed"):
        load_key(path, passphrase=b"wrong")
    assert path.read_bytes() == raw


@pytest.mark.parametrize("mode", [0o644, 0o640, 0o606])
def test_load_rejects_shared_key(tmp_path, mode):
    path = tmp_path / "key.pem"
    generate_key("log", path, passphrase=PASS)
    path.chmod(mode)
    with pytest.raises(CasfError, match="owner only"):
        load_key(path, passphrase=PASS)


def test_load_rejects_symlink(tmp_path):
    path = tmp_path / "key.pem"
    generate_key("log", path, passphrase=PASS)
    alias = tmp_path / "alias.pem"
    alias.symlink_to(path)
    with pytest.raises(CasfError):
        load_key(alias, passphrase=PASS)


@pytest.mark.parametrize("operation", ["generate", "load"])
def test_rejects_shared_directory(tmp_path, operation):
    path = tmp_path / "key.pem"
    if operation == "load":
        generate_key("log", path, passphrase=PASS)
    tmp_path.chmod(0o755)
    try:
        with pytest.raises(CasfError, match="owner only"):
            if operation == "load":
                load_key(path, passphrase=PASS)
            else:
                generate_key("log", path, passphrase=PASS)
    finally:
        tmp_path.chmod(0o700)


def test_failed_flush_does_not_publish_partial_key(tmp_path, monkeypatch):
    def fail(_fd):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(os, "fsync", fail)
    path = tmp_path / "key.pem"
    with pytest.raises((CasfError, OSError)):
        generate_key("log", path, passphrase=PASS)
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


def test_existing_key_survives_failed_overwrite(tmp_path):
    path = tmp_path / "key.pem"
    generate_key("log", path, passphrase=PASS)
    original = path.read_bytes()
    with pytest.raises(CasfError):
        generate_key("log", path, passphrase=PASS)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]
