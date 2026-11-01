"""Locked, atomic verifier state on local macOS and Linux filesystems."""

import json
import os
import re
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from casf.canonical.jcs import parse
from casf.canonical.limits import SAFE_INT_MAX
from casf.errors import CasfError

MAX_STATE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class SavedState:
    status_serial: int
    checkpoint: tuple[int, str] | None = None


def _digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _integer(value: object, minimum: int) -> bool:
    return type(value) is int and minimum <= value <= SAFE_INT_MAX


def _decode(raw: bytes) -> dict[str, SavedState]:
    try:
        data = parse(raw)
        if not isinstance(data, dict) or set(data) != {"version", "manifests"}:
            raise ValueError("state fields")
        if type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("state version")
        manifests = data["manifests"]
        if not isinstance(manifests, dict):
            raise TypeError("manifest map")
        result = {}
        for digest, entry in manifests.items():
            if not _digest(digest) or not isinstance(entry, dict):
                raise ValueError("manifest entry")
            if set(entry) != {"status_serial", "checkpoint"}:
                raise ValueError("entry fields")
            serial, cp = entry["status_serial"], entry["checkpoint"]
            if not _integer(serial, 1):
                raise ValueError("status serial")
            checkpoint = None
            if cp is not None:
                if not isinstance(cp, dict) or set(cp) != {"index", "hash"}:
                    raise ValueError("checkpoint fields")
                if not _integer(cp["index"], 0) or not _digest(cp["hash"]):
                    raise ValueError("checkpoint values")
                checkpoint = (cast(int, cp["index"]), cast(str, cp["hash"]))
            result[digest] = SavedState(cast(int, serial), checkpoint)
        return result
    except (CasfError, ValueError, TypeError, RecursionError) as e:
        raise CasfError("verifier state is malformed; restore trusted state") from e


def _secure(fd: int, *, directory: bool = False) -> None:
    info = os.fstat(fd)
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not expected or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise CasfError("verifier state requires owner only files and directory")
    if not directory and info.st_nlink != 1:
        raise CasfError("verifier state must not have hard links")


class StateTransaction:
    """Read and save while the caller holds the stable sidecar lock."""

    def __init__(self, directory: int, name: str, manifest_hash: str,
                 entries: dict[str, SavedState]) -> None:
        self.directory = directory
        self.name = name
        self.manifest_hash = manifest_hash
        self.entries = entries
        self.previous = entries.get(manifest_hash)

    def save(self, status_serial: int, checkpoint: tuple[int, str] | None) -> None:
        previous = self.previous
        if previous is not None:
            if status_serial < previous.status_serial:
                raise CasfError("verifier state cannot decrease the status serial")
            if previous.checkpoint is not None:
                if checkpoint is None:
                    checkpoint = previous.checkpoint
                elif (checkpoint[0] < previous.checkpoint[0]
                      or (checkpoint[0] == previous.checkpoint[0]
                          and checkpoint[1] != previous.checkpoint[1])):
                    raise CasfError("verifier state cannot replace retained history")
        entries = dict(self.entries)
        entries[self.manifest_hash] = SavedState(status_serial, checkpoint)
        payload = {"version": 1, "manifests": {
            digest: {"status_serial": entry.status_serial,
                     "checkpoint": None if entry.checkpoint is None else {
                         "index": entry.checkpoint[0], "hash": entry.checkpoint[1]}}
            for digest, entry in entries.items()}}
        raw = json.dumps(payload, sort_keys=True, allow_nan=False).encode() + b"\n"
        if len(raw) > MAX_STATE_BYTES:
            raise CasfError("verifier state exceeds its size limit")
        _decode(raw)
        temporary = ".casf-state-" + secrets.token_hex(16)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.name,
                       src_dir_fd=self.directory, dst_dir_fd=self.directory)
            os.fsync(self.directory)
        finally:
            try:
                os.unlink(temporary, dir_fd=self.directory)
            except FileNotFoundError:
                pass
        self.entries = entries
        self.previous = entries[self.manifest_hash]


@contextmanager
def locked_state(path: str, manifest_hash: str, *, initialize: bool = False
                 ) -> Iterator[StateTransaction]:
    """Hold one lock from state read through verification and durable save."""
    try:
        import fcntl
    except ImportError as e:
        raise CasfError("verifier state locking requires macOS or Linux") from e
    if not _digest(manifest_hash):
        raise CasfError("verifier state requires a valid manifest hash")
    target = Path(path)
    directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _secure(directory, directory=True)
        lock = os.open(target.name + ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
                       | os.O_NONBLOCK, 0o600, dir_fd=directory)
        try:
            _secure(lock)
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
            except FileNotFoundError:
                entries = {}
            else:
                with os.fdopen(fd, "rb") as stream:
                    _secure(stream.fileno())
                    raw = stream.read(MAX_STATE_BYTES + 1)
                if len(raw) > MAX_STATE_BYTES:
                    raise CasfError("verifier state exceeds its size limit")
                entries = _decode(raw)
            exists = manifest_hash in entries
            if exists and initialize:
                raise CasfError("verifier state already exists; omit --initialize-state")
            if not exists and not initialize:
                raise CasfError("verifier state is missing; restore it or explicitly initialize")
            yield StateTransaction(directory, target.name, manifest_hash, entries)
        finally:
            os.close(lock)
    finally:
        os.close(directory)
