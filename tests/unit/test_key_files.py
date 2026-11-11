"""Private key storage boundaries, using synthetic encrypted keys only."""

import os

import pytest

from casf.errors import CasfError
from casf.keys import generate_key, load_key

PASS = b"synthetic-key-file-test"


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
