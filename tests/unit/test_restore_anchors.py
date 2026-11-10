"""R06/R09: restore uses authenticated external checkpoint evidence."""

import json

import pytest

from casf import crypto
from casf.bundle import read_bundle
from casf.errors import CasfError
from casf.writer import RestoreBehindWitnessError, SealedError, Writer
from tests.unit.test_writer import LOG, LOG_ID, WIT, _append, _writer
from tests.unit.test_writer_integrity_recovery import _witnessed
from tests.unit.test_writer_trust import _pins


def evidence(tmp_path, final=False):
    witness, path = _witnessed(tmp_path, final=final)
    witness.close()
    bundle = read_bundle(path)
    return path, bundle, {LOG_ID: _pins()}


@pytest.mark.parametrize("index,final", [(0, False), (1, False), (1, True)])
def test_restore_accepts_signed_anchor_and_preserves_seal(tmp_path, index, final):
    path, bundle, pins = evidence(tmp_path, final)
    writer = Writer.restore_from_bundle(
        tmp_path / "restored.db", LOG, path, trust_pins=pins,
        anchor_checkpoint=bundle.checkpoints[index], anchor_receipt=bundle.receipts[index])
    try:
        assert len(list(writer.records(LOG_ID))) == 2
        if final:
            with pytest.raises(SealedError):
                _append(writer, 3)
        else:
            assert _append(writer, 3)["body"]["seq"] == 3
    finally:
        writer.close()


@pytest.mark.parametrize("change", [
    "checkpoint_signature", "receipt_signature", "checkpoint_hash", "receipt_hash",
    "receipt_manifest", "receipt_count", "receipt_index", "receipt_head", "receipt_log",
    "untrusted", "missing_receipt", "ambiguous", "journal_conflict",
])
def test_restore_rejects_invalid_signed_anchor_before_creating_store(tmp_path, change):
    path, bundle, pins = evidence(tmp_path)
    checkpoint, receipt = bundle.checkpoints[-1], bundle.receipts[-1]
    extra = {}
    if change == "checkpoint_signature":
        checkpoint["signature"] = crypto.b64url_encode(bytes(64))
    elif change == "receipt_signature":
        receipt["signature"] = crypto.b64url_encode(bytes(64))
    elif change in {"checkpoint_hash", "receipt_hash"}:
        (checkpoint if change == "checkpoint_hash" else receipt)[change] = "ab" * 32
    elif change.startswith("receipt_"):
        field = {"receipt_manifest": "manifest_hash", "receipt_count": "count",
                 "receipt_index": "checkpoint_index", "receipt_head": "head_hash",
                 "receipt_log": "log_id"}[change]
        receipt["body"][field] = (3 if field in {"count", "checkpoint_index"}
                                  else "223e4567-e89b-42d3-a456-426614174000"
                                  if field == "log_id" else "ab" * 32)
        receipt["receipt_hash"] = crypto.digest_receipt(receipt["body"])
        receipt["signature"] = crypto.sign_receipt(WIT, receipt["body"])
    elif change == "untrusted":
        pins = None
    elif change == "missing_receipt":
        receipt = None
    elif change == "ambiguous":
        extra["anchor"] = {"count": 2, "head_hash": checkpoint["body"]["head_hash"]}
    else:
        checkpoint["body"]["issued_at"] = "2026-10-12T00:00:00.000000Z"
        checkpoint["checkpoint_hash"] = crypto.digest_checkpoint(checkpoint["body"])
        checkpoint["signature"] = crypto.sign_checkpoint(LOG, checkpoint["body"])
        receipt["body"]["checkpoint_hash"] = checkpoint["checkpoint_hash"]
        receipt["receipt_hash"] = crypto.digest_receipt(receipt["body"])
        receipt["signature"] = crypto.sign_receipt(WIT, receipt["body"])
    dest = tmp_path / "restored.db"
    with pytest.raises(CasfError, match="journal" if change == "journal_conflict" else None):
        Writer.restore_from_bundle(dest, LOG, path, trust_pins=pins,
                                   anchor_checkpoint=checkpoint, anchor_receipt=receipt, **extra)
    assert not dest.exists()


def test_restore_behind_signed_anchor_is_retained_sealed(tmp_path):
    _path, bundle, pins = evidence(tmp_path)
    old = _writer(tmp_path / "old.db")
    try:
        old_path = old.export_bundle(LOG_ID, tmp_path / "old-bundle")
    finally:
        old.close()
    dest = tmp_path / "restored.db"
    with pytest.raises(RestoreBehindWitnessError):
        Writer.restore_from_bundle(dest, LOG, old_path, trust_pins=pins,
                                   anchor_checkpoint=bundle.checkpoints[-1],
                                   anchor_receipt=bundle.receipts[-1])
    reader = Writer(dest, LOG, trust_pins=pins)
    try:
        with pytest.raises(SealedError):
            _append(reader, 1)
    finally:
        reader.close()


def test_restore_refuses_missing_anchor_journal(tmp_path):
    path, bundle, pins = evidence(tmp_path)
    (path / "checkpoints.jsonl").write_text("")
    (path / "receipts.jsonl").write_text("")
    dest = tmp_path / "restored.db"
    with pytest.raises(CasfError, match="journal"):
        Writer.restore_from_bundle(dest, LOG, path, trust_pins=pins,
                                   anchor_checkpoint=bundle.checkpoints[-1],
                                   anchor_receipt=bundle.receipts[-1])
    assert not dest.exists()


def test_anchor_receipt_recovers_matching_pending_tail(tmp_path):
    path, bundle, pins = evidence(tmp_path)
    (path / "receipts.jsonl").write_text(json.dumps(bundle.receipts[0]) + "\n")
    writer = Writer.restore_from_bundle(
        tmp_path / "restored.db", LOG, path, trust_pins=pins,
        anchor_checkpoint=bundle.checkpoints[-1], anchor_receipt=bundle.receipts[-1])
    try:
        assert writer.pending_checkpoint(LOG_ID) is None
        assert writer.create_checkpoint(LOG_ID)["body"]["index"] == 2
    finally:
        writer.close()
