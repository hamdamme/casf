"""Evidence bundles: portable directory export and import (SPEC §20).

A bundle is a directory holding exactly manifest.json, records.jsonl,
checkpoints.jsonl, receipts.jsonl and export.json (status.jsonl is
optional). Each JSONL line is one canonical envelope followed by LF:
no blank lines, no byte order mark. Records are ordered by sequence.

Import limits apply before parsing: symlinks and nonregular files are
rejected, and every JSONL line is bounded (§9, §20). The export
metadata must agree with the actual record count. Streaming callers must
consume records to EOF before accepting a result; open_bundle owns the file
until its context exits. read_bundle retains its eager list API.
"""

import os
import stat
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from casf import crypto
from casf.canonical.jcs import parse
from casf.canonical.limits import MAX_JSONL_LINE_BYTES
from casf.errors import CasfError, LimitError
from casf.types import JsonObject

__all__ = ["Bundle", "BundleReadError", "StreamingBundle", "open_bundle", "read_bundle"]

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


class BundleReadError(CasfError):
    """Malformed bundle input, including errors discovered during iteration."""


@dataclass
class StreamingBundle:
    """Context owned record iterator and bounded protocol evidence.

    records is consumed once. Exhaust it before accepting a verification
    report, even if the verifier returns early. It cannot outlive the context.
    """
    manifest: JsonObject
    manifest_hash: str
    records: Generator[JsonObject, None, None]
    checkpoints: list[JsonObject]
    receipts: list[JsonObject]
    metadata: JsonObject
    statuses: list[JsonObject]


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


def _iter_jsonl(source: BinaryIO, path: Path, max_line_bytes: int,
                max_objects: int, budget: _Budget) -> Iterator[JsonObject]:
    count = 0
    while True:
        try:
            line = source.readline(min(max_line_bytes + 1, budget.remaining) + 1)
        except OSError as exc:
            raise OSError("cannot read bundle member") from exc
        if not line:
            break
        budget.consume(len(line))
        if count >= max_objects:
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
        count += 1
        yield value


def _read_jsonl(path: Path, max_line_bytes: int, max_objects: int,
                budget: _Budget) -> list[JsonObject]:
    with _open_regular(path) as source:
        return list(_iter_jsonl(source, path, max_line_bytes, max_objects, budget))


def _records(source: BinaryIO, path: Path, max_line_bytes: int,
             max_records: int, budget: _Budget, metadata: JsonObject) -> Generator[JsonObject, None, None]:
    count = 0
    try:
        for count, envelope in enumerate(
                _iter_jsonl(source, path, max_line_bytes, max_records, budget), start=1):
            record_body = envelope.get("body")
            if not isinstance(record_body, dict):
                raise CasfError("record envelope field types are wrong")
            if record_body.get("seq") != count:
                raise CasfError("records are not ordered by sequence")
            yield envelope
        if metadata["record_count"] != count or metadata["through"] != count:
            raise CasfError("export metadata disagrees with the record count")
    except LimitError:
        raise
    except CasfError as exc:
        raise BundleReadError(str(exc)) from exc


def _prepare_bundle(bundle_dir: str | Path, *,
                max_line_bytes: int = MAX_JSONL_LINE_BYTES,
                max_records: int = 1_000_000,
                max_evidence_objects: int = 100_000,
                max_total_bytes: int = 256 * 1024 * 1024) -> tuple[StreamingBundle, BinaryIO]:
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

    source = _open_regular(directory / "records.jsonl")
    records = _records(source, directory / "records.jsonl", max_line_bytes,
                       max_records, budget, metadata)
    return StreamingBundle(manifest=manifest, manifest_hash=manifest_hash,
                           records=records, checkpoints=checkpoints,
                           receipts=receipts, metadata=metadata, statuses=statuses), source


@contextmanager
def open_bundle(bundle_dir: str | Path, *,
                max_line_bytes: int = MAX_JSONL_LINE_BYTES,
                max_records: int = 1_000_000,
                max_evidence_objects: int = 100_000,
                max_total_bytes: int = 256 * 1024 * 1024) -> Iterator[StreamingBundle]:
    """Open bounded evidence and stream records from an owned file descriptor.

    Schema and count errors in records can be raised during consumption.
    LimitError remains distinct. All errors must be handled before accepting
    a report. Context exit closes the iterator and descriptor, including on
    early verification failure. Other evidence lists have explicit budgets.
    """
    try:
        bundle, source = _prepare_bundle(
            bundle_dir, max_line_bytes=max_line_bytes, max_records=max_records,
            max_evidence_objects=max_evidence_objects, max_total_bytes=max_total_bytes)
    except LimitError:
        raise
    except CasfError as exc:
        raise BundleReadError(str(exc)) from exc
    try:
        yield bundle
    finally:
        bundle.records.close()
        source.close()


def read_bundle(bundle_dir: str | Path, *,
                max_line_bytes: int = MAX_JSONL_LINE_BYTES,
                max_records: int = 1_000_000,
                max_evidence_objects: int = 100_000,
                max_total_bytes: int = 256 * 1024 * 1024) -> Bundle:
    """Compatibility API: eagerly validate and materialize all records.

    Use open_bundle for verification with bounded record memory.
    """
    with open_bundle(bundle_dir, max_line_bytes=max_line_bytes, max_records=max_records,
                     max_evidence_objects=max_evidence_objects,
                     max_total_bytes=max_total_bytes) as bundle:
        return Bundle(manifest=bundle.manifest, manifest_hash=bundle.manifest_hash,
                      records=list(bundle.records), checkpoints=bundle.checkpoints,
                      receipts=bundle.receipts, metadata=bundle.metadata, statuses=bundle.statuses)
