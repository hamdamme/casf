"""Bundle framing requires canonical bytes, independently of signature validity."""

import json
from dataclasses import replace

import pytest

from benchmarks.streaming import generate
from casf.bundle import BundleReadError, read_bundle
from casf.canonical.jcs import canonicalize
from casf.canonical.limits import ENVELOPE_LIMITS
from casf.verifier import Mode, Result, verify_bundle
from casf.writer import Writer
from tests.local_mode import local_cli
from tests.unit.test_cli import _trust
from tests.unit.test_streaming import public_pins
from tests.unit.test_writer import LOG, LOG_ID, _writer


@pytest.mark.parametrize(
    "member", ["records.jsonl", "checkpoints.jsonl", "receipts.jsonl", "status.jsonl"]
)
@pytest.mark.parametrize("encoding", ["whitespace", "key-order", "escaped-key", "CRLF"])
def test_all_jsonl_members_require_canonical_bytes(tmp_path, member, encoding):
    path = tmp_path / "bundle"
    generate(path, 2)
    pins = public_pins(path)
    assert verify_bundle(path, pins, Mode.ANCHORED).result is Result.PASS
    selected = path / member
    raw = selected.read_bytes()
    first, rest = raw.split(b"\n", 1)
    value = json.loads(first)
    if encoding == "whitespace":
        changed = b" \t" + first + b" \t\n" + rest
    elif encoding == "key-order":
        changed = (
            json.dumps(dict(reversed(list(value.items()))), separators=(",", ":")).encode()
            + b"\n"
            + rest
        )
    elif encoding == "escaped-key":
        changed = first.replace(b'"type"', b'"\\u0074ype"', 1) + b"\n" + rest
    else:
        changed = raw.replace(b"\n", b"\r\n")
    assert changed != raw
    assert json.loads(changed.split(b"\n")[0]) == value
    selected.write_bytes(changed)
    with pytest.raises(BundleReadError, match="canonical"):
        read_bundle(path)
    with pytest.raises(BundleReadError, match="canonical"):
        verify_bundle(path, pins, Mode.ANCHORED)


def test_noncanonical_tail_is_checked_after_early_verdict(tmp_path):
    path = tmp_path / "bundle"
    generate(path, 2)
    lines = (path / "records.jsonl").read_bytes().splitlines(keepends=True)
    lines[-1] = b" " + lines[-1]
    (path / "records.jsonl").write_bytes(b"".join(lines))
    with pytest.raises(BundleReadError, match="canonical"):
        verify_bundle(path, replace(public_pins(path), authority_keys={}))


def test_cli_and_restore_reject_noncanonical_records(tmp_path, capsys):
    writer = _writer(tmp_path / "writer.db")
    try:
        writer.append(
            LOG_ID,
            event_id="123e4567-e89b-42d3-a456-426614174001",
            actor="synthetic",
            event_type="review",
            payload={},
            attributes={},
        )
        path = tmp_path / "bundle"
        writer.export_bundle(LOG_ID, path)
        trust = _trust(tmp_path, writer.manifest_envelope(LOG_ID))
    finally:
        writer.close()
    raw = (path / "records.jsonl").read_bytes()
    (path / "records.jsonl").write_bytes(raw.replace(b"\n", b"\r\n"))
    assert (
        local_cli(
            [
                "verify",
                str(path),
                "--trust",
                str(trust),
                "--json",
                "--state",
                str(tmp_path / "state.json"),
                "--initialize-state",
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert "canonical" in output.err
    assert '"result": "PASS"' not in output.out
    assert not (tmp_path / "state.json").exists()
    restored = tmp_path / "restored.db"
    with pytest.raises(BundleReadError, match="canonical"):
        Writer.restore_from_bundle(restored, LOG, path, local_only=True)
    assert not restored.exists()


def test_canonical_export_retains_maximum_body_depth_and_unicode(tmp_path):
    writer = _writer(tmp_path / "writer.db")
    payload = {"\ue000": "é", "\U00010000": "non-BMP"}
    # body at depth 1, payload at depth 2, fourteen more object containers.
    for _ in range(14):
        payload = {"nested": payload}
    try:
        writer.append(
            LOG_ID,
            event_id="123e4567-e89b-42d3-a456-426614174001",
            actor="synthetic",
            event_type="review",
            payload=payload,
            attributes={},
        )
        path = tmp_path / "bundle"
        writer.export_bundle(LOG_ID, path)
    finally:
        writer.close()
    bundle = read_bundle(path)
    assert bundle.records[0]["body"]["payload"] == payload
    assert (path / "records.jsonl").read_bytes() == canonicalize(
        bundle.records[0], ENVELOPE_LIMITS
    ) + b"\n"
