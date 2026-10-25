"""Evidence bundles: portable directory export and import (SPEC §20).

A bundle is a directory holding exactly manifest.json, records.jsonl,
checkpoints.jsonl, receipts.jsonl and export.json (status.jsonl is
optional). Each JSONL line is one canonical envelope followed by LF:
no blank lines, no byte order mark. Records are ordered by sequence.

Import limits apply before parsing: symlinks and nonregular files are
rejected, and every JSONL line is bounded (§9, §20). The export
metadata must agree with the actual record count, so a truncated or
padded records file is caught before verification even starts.
"""

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from casf import crypto
from casf.canonical.jcs import parse
from casf.canonical.limits import MAX_JSONL_LINE_BYTES
from casf.errors import CasfError, LimitError
from casf.types import JsonObject

__all__ = ["Bundle", "read_bundle"]

REQUIRED_FILES = ("manifest.json", "records.jsonl", "checkpoints.jsonl",
                  "receipts.jsonl", "export.json")

_METADATA_FIELDS = {"version", "type", "log_id", "manifest_hash",
                    "through", "record_count", "generated_at"}

_BOM = b"\xef\xbb\xbf"


@dataclass
class Bundle:
    """A validated evidence bundle read from a directory."""
    manifest: JsonObject
    manifest_hash: str
    records: list[JsonObject]
    checkpoints: list[JsonObject]
    receipts: list[JsonObject]
    metadata: JsonObject
    statuses: list[JsonObject] = field(default_factory=list)


def _open_regular(path: Path) -> BinaryIO:
    # O_NONBLOCK avoids hanging on a FIFO; fstat checks the opened object.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError as exc:
        raise CasfError(f"bundle member missing: {path.name}") from exc
    except OSError as exc:
        raise CasfError(f"bundle member inaccessible or symlink: {path.name}") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise CasfError(f"bundle member is not a regular file: {path.name}")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


@dataclass
class _Budget:
    remaining: int

    def consume(self, size: int) -> None:
        self.remaining -= size
        if self.remaining < 0:
            raise LimitError("bundle byte limit exceeded")


def _read_object(path: Path, budget: _Budget) -> JsonObject:
    # Protocol envelope includes a body, digest, and signature.
    with _open_regular(path) as source:
        raw = source.read(min(32768, budget.remaining) + 1)
    budget.consume(len(raw))
    if len(raw) > 32768:
        raise LimitError(f"object byte limit exceeded: {path.name}")
    if raw.startswith(_BOM):
        raise CasfError(f"byte order mark is not allowed: {path.name}")
    value = parse(raw)
    if not isinstance(value, dict):
        raise CasfError(f"expected a JSON object: {path.name}")
    return value


def _read_jsonl(path: Path, max_line_bytes: int, max_objects: int,
                budget: _Budget) -> list[JsonObject]:
    envelopes: list[JsonObject] = []
    with _open_regular(path) as source:
        while True:
            line = source.readline(min(max_line_bytes + 1, budget.remaining) + 1)
            if not line:
                break
            budget.consume(len(line))
            if len(envelopes) >= max_objects:
                raise LimitError(f"object count limit exceeded: {path.name}")
            if len(line.rstrip(b"\n")) > max_line_bytes:
                raise LimitError(f"line over the {max_line_bytes} byte limit: {path.name}")
            if not line.endswith(b"\n"):
                raise CasfError(f"last line must end with LF: {path.name}")
            if line.startswith(_BOM):
                raise CasfError(f"byte order mark is not allowed: {path.name}")
            if line == b"\n":
                raise CasfError(f"blank line is not allowed: {path.name}")
            value = parse(line[:-1])
            if not isinstance(value, dict):
                raise CasfError(f"expected a JSON object line: {path.name}")
            envelopes.append(value)
    return envelopes


def read_bundle(bundle_dir: str | Path, *,
                max_line_bytes: int = MAX_JSONL_LINE_BYTES,
                max_records: int = 1_000_000,
                max_evidence_objects: int = 100_000,
                max_total_bytes: int = 256 * 1024 * 1024) -> Bundle:
    """Read and validate a bundle directory (SPEC §20)."""
    for limit in (max_line_bytes, max_records, max_evidence_objects, max_total_bytes):
        if type(limit) is not int or limit < 1:
            raise ValueError("bundle limits must be positive integers")
    budget = _Budget(max_total_bytes)
    directory = Path(bundle_dir)
    if not directory.is_dir() or os.path.islink(directory):
        raise CasfError("bundle path is not a directory")
    manifest = _read_object(directory / "manifest.json", budget)
    metadata = _read_object(directory / "export.json", budget)
    records = _read_jsonl(directory / "records.jsonl", max_line_bytes, max_records, budget)
    checkpoints = _read_jsonl(directory / "checkpoints.jsonl", 32768, max_evidence_objects, budget)
    receipts = _read_jsonl(directory / "receipts.jsonl", 32768, max_evidence_objects, budget)

    status_path = directory / "status.jsonl"
    statuses = (_read_jsonl(status_path, 32768, max_evidence_objects, budget)
                if os.path.lexists(status_path) else [])

    if set(metadata) != _METADATA_FIELDS:
        raise CasfError("export.json fields must be exactly version, type, "
                        "log_id, manifest_hash, through, record_count, "
                        "generated_at")
    if metadata["version"] != 1 or metadata["type"] != "export":
        raise CasfError("unsupported export metadata")

    body = manifest.get("body")
    manifest_hash = manifest.get("manifest_hash")
    if not isinstance(body, dict) or not isinstance(manifest_hash, str):
        raise CasfError("manifest envelope field types are wrong")
    if crypto.digest_manifest(body) != manifest_hash:
        raise CasfError("manifest_hash does not match the body")
    if metadata["manifest_hash"] != manifest_hash:
        raise CasfError("export metadata disagrees with the manifest")
    if metadata["log_id"] != body.get("log_id"):
        raise CasfError("export metadata disagrees with the manifest log")

    count = len(records)
    if metadata["record_count"] != count or metadata["through"] != count:
        raise CasfError("export metadata disagrees with the record count")
    for index, envelope in enumerate(records, start=1):
        record_body = envelope.get("body")
        if not isinstance(record_body, dict):
            raise CasfError("record envelope field types are wrong")
        if record_body.get("seq") != index:
            raise CasfError("records are not ordered by sequence")

    return Bundle(manifest=manifest, manifest_hash=manifest_hash,
                  records=records, checkpoints=checkpoints,
                  receipts=receipts, metadata=metadata, statuses=statuses)
