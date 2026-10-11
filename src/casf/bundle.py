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
from dataclasses import dataclass
from pathlib import Path

from casf import crypto
from casf.canonical.jcs import parse
from casf.canonical.limits import MAX_JSONL_LINE_BYTES
from casf.errors import CasfError
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


def _read_regular(path: Path) -> bytes:
    if os.path.islink(path):
        raise CasfError(f"bundle member is a symlink: {path.name}")
    try:
        st = path.stat()
    except FileNotFoundError as e:
        raise CasfError(f"bundle member missing: {path.name}") from e
    if not stat.S_ISREG(st.st_mode):
        raise CasfError(f"bundle member is not a regular file: {path.name}")
    return path.read_bytes()


def _read_object(path: Path) -> JsonObject:
    raw = _read_regular(path)
    if raw.startswith(_BOM):
        raise CasfError(f"byte order mark is not allowed: {path.name}")
    value = parse(raw)
    if not isinstance(value, dict):
        raise CasfError(f"expected a JSON object: {path.name}")
    return value


def _read_jsonl(path: Path, max_line_bytes: int) -> list[JsonObject]:
    raw = _read_regular(path)
    if raw.startswith(_BOM):
        raise CasfError(f"byte order mark is not allowed: {path.name}")
    if raw == b"":
        return []
    lines = raw.split(b"\n")
    if lines[-1] != b"":
        raise CasfError(f"last line must end with LF: {path.name}")
    envelopes: list[JsonObject] = []
    for line in lines[:-1]:
        if len(line) > max_line_bytes:
            raise CasfError(
                f"line over the {max_line_bytes} byte limit: {path.name}")
        if line == b"":
            raise CasfError(f"blank line is not allowed: {path.name}")
        value = parse(line)
        if not isinstance(value, dict):
            raise CasfError(f"expected a JSON object line: {path.name}")
        envelopes.append(value)
    return envelopes


def read_bundle(bundle_dir: str | Path, *,
                max_line_bytes: int = MAX_JSONL_LINE_BYTES) -> Bundle:
    """Read and validate a bundle directory (SPEC §20)."""
    directory = Path(bundle_dir)
    if not directory.is_dir() or os.path.islink(directory):
        raise CasfError("bundle path is not a directory")
    manifest = _read_object(directory / "manifest.json")
    metadata = _read_object(directory / "export.json")
    records = _read_jsonl(directory / "records.jsonl", max_line_bytes)
    checkpoints = _read_jsonl(directory / "checkpoints.jsonl", max_line_bytes)
    receipts = _read_jsonl(directory / "receipts.jsonl", max_line_bytes)

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
                  receipts=receipts, metadata=metadata)
