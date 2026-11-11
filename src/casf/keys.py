"""Encrypted key provider (SPEC §16).

Keys are Ed25519, generated from operating system randomness and
stored as encrypted PKCS8 PEM through the cryptography library. The
file is created atomically, never overwrites an existing key, and is
restricted to its owner. Encryption at rest does not protect an
unlocked key from a compromised process, and Python cannot promise
secure memory erasure; both limits are documented in SPEC §16.
"""

import os
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf.errors import CasfError

__all__ = ["generate_key", "load_key"]

MAX_KEY_BYTES = 16384


def _owner_only(fd: int, *, directory: bool = False) -> None:
    info = os.fstat(fd)
    regular = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not regular or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise CasfError("private keys require owner only files and directory")


@contextmanager
def _key_directory(path: Path) -> Iterator[int]:
    try:
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise CasfError("key directory could not be opened") from exc
    try:
        _owner_only(fd, directory=True)
        yield fd
    finally:
        os.close(fd)


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
    with _key_directory(target) as directory:
        temporary = ".casf-key-" + secrets.token_hex(16)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(blob)
                stream.flush()
                os.fsync(stream.fileno())
            # A hard link publishes complete bytes without replacing any entry.
            try:
                os.link(temporary, target.name, src_dir_fd=directory,
                        dst_dir_fd=directory, follow_symlinks=False)
            except FileExistsError as exc:
                raise CasfError("key file already exists; overwrite refused") from exc
        finally:
            os.unlink(temporary, dir_fd=directory)
        os.fsync(directory)


def load_key(path: str | Path, *,
             passphrase: bytes) -> Ed25519PrivateKey:
    """Decrypt a stored key; a wrong passphrase is a stable error."""
    target = Path(path)
    try:
        with _key_directory(target) as directory:
            fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=directory)
            with os.fdopen(fd, "rb") as stream:
                _owner_only(stream.fileno())
                raw = stream.read(MAX_KEY_BYTES + 1)
    except OSError as e:
        raise CasfError("key file could not be read") from e
    if len(raw) > MAX_KEY_BYTES:
        raise CasfError("key file exceeds its size limit")
    try:
        key = serialization.load_pem_private_key(raw, password=passphrase)
    except (ValueError, TypeError) as e:
        raise CasfError("key file could not be decrypted or parsed") from e
    if not isinstance(key, Ed25519PrivateKey):
        raise CasfError("key file is not an Ed25519 private key")
    return key
