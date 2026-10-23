"""Encrypted key provider (SPEC §16).

Keys are Ed25519, generated from operating system randomness and
stored as encrypted PKCS8 PEM through the cryptography library. The
file is created atomically, never overwrites an existing key, and is
restricted to its owner. Encryption at rest does not protect an
unlocked key from a compromised process, and Python cannot promise
secure memory erasure; both limits are documented in SPEC §16.
"""

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf.errors import CasfError

__all__ = ["generate_key", "load_key"]


def generate_key(role: str, path: str | Path, *,
                 passphrase: bytes) -> None:
    """Create one encrypted key file; refuses to overwrite (§16)."""
    if role not in ("authority", "log", "witness"):
        raise CasfError("role must be authority, log or witness")
    if not passphrase:
        raise CasfError("a passphrase is required")
    target = Path(path)
    key = Ed25519PrivateKey.generate()
    blob = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(passphrase))
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as e:
        raise CasfError("key file already exists; overwrite refused") from e
    try:
        os.write(fd, blob)
        os.fsync(fd)
    finally:
        os.close(fd)


def load_key(path: str | Path, *,
             passphrase: bytes) -> Ed25519PrivateKey:
    """Decrypt a stored key; a wrong passphrase is a stable error."""
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise CasfError("key file could not be read") from e
    try:
        key = serialization.load_pem_private_key(raw, password=passphrase)
    except (ValueError, TypeError) as e:
        raise CasfError("key file could not be decrypted or parsed") from e
    if not isinstance(key, Ed25519PrivateKey):
        raise CasfError("key file is not an Ed25519 private key")
    return key
