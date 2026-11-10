"""R02/R04/R08/R09: verified startup and preservation of restore evidence."""

import json
import os
import sqlite3

import pytest

from casf import crypto
from casf.bundle import read_bundle
from casf.canonical.jcs import canonicalize
from casf.errors import CasfError
from casf.witness import Witness
from casf.writer import SealedError, Writer
from tests.status import register_active
from tests.unit.test_writer import (
    AUTH,
    AUTH_PUB,
    LOG,
    LOG_ID,
    MP,
    WIT,
    _append,
    _manifest_envelope,
    _writer,
)


def _crash_during_restore(db, bundle):
    from casf.writer.validation import ManifestContext

    original = ManifestContext.record

    def interrupted(self, value, seq, previous):
        if seq == 2:
            os._exit(76)
        return original(self, value, seq, previous)

    ManifestContext.record = interrupted
    Writer.restore_from_bundle(db, LOG, bundle)


def _witnessed(tmp_path, *, final=False):
    writer = _writer(tmp_path / "writer.db")
    witness = Witness(tmp_path / "witness.db", WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(witness, _manifest_envelope(), AUTH)
    for n in (1, 2):
        _append(writer, n)
        checkpoint = writer.create_checkpoint(LOG_ID, final=final and n == 2)
        receipt = witness.submit(LOG_ID, checkpoint, [list(writer.records(LOG_ID))[-1]])
        writer.record_receipt(LOG_ID, receipt)
    dest = writer.export_bundle(LOG_ID, tmp_path / "bundle")
    writer.close()
    return witness, dest


@pytest.mark.parametrize("change", [
    "body", "signature", "key_id", "sequence", "request_digest", "event_id",
    "record_hash", "orphan", "missing_head",
])
def test_startup_rejects_corrupt_records_and_indexes(tmp_path, change):
    db = tmp_path / "writer.db"
    writer = _writer(db)
    _append(writer, 1)
    _append(writer, 2)
    writer.close()
    with sqlite3.connect(db) as con:
        con.execute("DROP TRIGGER records_no_update")
        blob = con.execute("SELECT envelope FROM records WHERE seq = 1").fetchone()[0]
        env = json.loads(blob)
        if change == "body":
            env["body"]["payload"] = {"changed": True}
        elif change == "signature":
            env["signature"] = crypto.b64url_encode(bytes(64))
        elif change == "key_id":
            env["body"]["key_id"] = "ab" * 32
            env["record_hash"] = crypto.digest_record(env["body"])
            env["signature"] = crypto.sign_record(LOG, env["body"])
        elif change == "sequence":
            env["body"]["seq"] = 9
        elif change in {"request_digest", "event_id", "record_hash"}:
            con.execute(f"UPDATE records SET {change} = ? WHERE seq = 1", ("ab" * 32,))
        elif change == "orphan":
            con.execute("UPDATE records SET log_id = 'orphan' WHERE seq = 1")
        else:
            con.execute("DELETE FROM heads")
        con.execute("UPDATE records SET envelope = ? WHERE seq = 1", (canonicalize(env),))
    with pytest.raises(CasfError):
        Writer(db, LOG)


def test_startup_checks_records_without_a_private_key(tmp_path):
    db = tmp_path / "writer.db"
    writer = _writer(db)
    original = _append(writer, 1)
    writer.close()
    reader = Writer(db)
    try:
        assert list(reader.records(LOG_ID)) == [original]
    finally:
        reader.close()


@pytest.mark.parametrize("change", [
    "seal", "checkpoint_index", "checkpoint_count", "checkpoint_signature",
    "receipt_signature", "missing_receipt", "orphan_receipt", "state", "outbox",
])
def test_startup_rejects_corrupt_checkpoint_journal(tmp_path, change):
    witness, _dest = _witnessed(tmp_path, final=True)
    witness.close()
    db = tmp_path / "writer.db"
    with sqlite3.connect(db) as con:
        if change == "seal":
            con.execute("UPDATE heads SET sealed = 0")
        elif change == "checkpoint_index":
            con.execute("UPDATE checkpoints SET idx = 9 WHERE idx = 1")
        elif change == "checkpoint_count":
            con.execute("UPDATE checkpoints SET count = 0 WHERE idx = 1")
        elif change in {"checkpoint_signature", "receipt_signature"}:
            table = "checkpoints" if change.startswith("checkpoint") else "receipts"
            rowid, blob = con.execute(f"SELECT rowid, envelope FROM {table} LIMIT 1").fetchone()
            env = json.loads(blob)
            env["signature"] = crypto.b64url_encode(bytes(64))
            con.execute(f"UPDATE {table} SET envelope = ? WHERE rowid = ?",
                        (canonicalize(env), rowid))
        elif change == "missing_receipt":
            con.execute("DELETE FROM receipts")
        elif change == "orphan_receipt":
            blob = con.execute("SELECT envelope FROM receipts LIMIT 1").fetchone()[0]
            con.execute("INSERT INTO receipts VALUES (?, ?)", ("ab" * 32, blob))
        elif change == "state":
            con.execute("UPDATE checkpoints SET state = 'pending' WHERE idx = 1")
        else:
            con.execute("INSERT INTO outbox VALUES (?, ?, 1, 2, 0, 0)",
                        (LOG_ID, "ab" * 32))
    with pytest.raises(CasfError):
        Writer(db, LOG)


def test_startup_rejects_pending_outbox_range_change(tmp_path):
    db = tmp_path / "writer.db"
    writer = _writer(db)
    _append(writer, 1)
    writer.create_checkpoint(LOG_ID)
    writer.close()
    with sqlite3.connect(db) as con:
        con.execute("UPDATE outbox SET from_seq = 0")
    with pytest.raises(CasfError, match="outbox"):
        Writer(db, LOG)


def test_restore_preserves_empty_final_history(tmp_path):
    writer = _writer(tmp_path / "writer.db")
    witness = Witness(tmp_path / "witness.db", WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(witness, _manifest_envelope(), AUTH)
    try:
        cp = writer.seal_log(LOG_ID)
        writer.record_receipt(LOG_ID, witness.submit(LOG_ID, cp, []))
        dest = writer.export_bundle(LOG_ID, tmp_path / "bundle")
        restored = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, dest,
                                              anchor=cp["body"])
        try:
            assert list(restored.records(LOG_ID)) == []
            with pytest.raises(SealedError):
                _append(restored, 1)
        finally:
            restored.close()
    finally:
        writer.close()
        witness.close()


def test_restore_accepts_a_matching_older_anchor(tmp_path):
    witness, dest = _witnessed(tmp_path)
    witness.close()
    bundle = read_bundle(dest)
    restored = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, dest,
                                          anchor=bundle.checkpoints[0]["body"])
    try:
        assert _append(restored, 3)["body"]["seq"] == 3
    finally:
        restored.close()


def test_process_exit_during_restore_never_commits_partial_history(tmp_path):
    witness, dest = _witnessed(tmp_path)
    witness.close()
    db = tmp_path / "interrupted.db"
    process = MP.Process(target=_crash_during_restore, args=(db, dest))
    process.start()
    process.join(30)
    assert process.exitcode == 76
    with sqlite3.connect(db) as con:
        for table in ("manifests", "heads", "records", "checkpoints", "receipts", "outbox"):
            assert con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    reopened = Writer(db, LOG)
    try:
        with pytest.raises(CasfError, match="unknown log"):
            _append(reopened, 3)
    finally:
        reopened.close()


def test_restore_preserves_final_seal_and_evidence(tmp_path):
    witness, dest = _witnessed(tmp_path, final=True)
    try:
        original = read_bundle(dest)
        restored = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, dest)
        try:
            with pytest.raises(SealedError):
                _append(restored, 3)
            with pytest.raises(SealedError):
                restored.create_checkpoint(LOG_ID)
            exported = read_bundle(restored.export_bundle(LOG_ID, tmp_path / "again"))
            assert exported.checkpoints == original.checkpoints
            assert exported.receipts == original.receipts
        finally:
            restored.close()
        reopened = Writer(tmp_path / "restored.db", LOG)
        try:
            with pytest.raises(SealedError):
                _append(reopened, 3)
        finally:
            reopened.close()
    finally:
        witness.close()


def test_restore_continues_checkpoint_and_receipt_chains(tmp_path):
    witness, dest = _witnessed(tmp_path)
    try:
        original = read_bundle(dest)
        restored = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, dest)
        try:
            record = _append(restored, 3)
            cp = restored.create_checkpoint(LOG_ID)
            assert cp["body"]["index"] == 2
            assert cp["body"]["previous_checkpoint_hash"] == original.checkpoints[-1]["checkpoint_hash"]
            receipt = witness.submit(LOG_ID, cp, [record])
            restored.record_receipt(LOG_ID, receipt)
            exported = read_bundle(restored.export_bundle(LOG_ID, tmp_path / "again"))
            assert exported.receipts[:2] == original.receipts
            assert exported.receipts[-1] == receipt
        finally:
            restored.close()
    finally:
        witness.close()


@pytest.mark.parametrize("change", [
    "checkpoint_signature", "checkpoint_key", "checkpoint_head", "checkpoint_chain",
    "receipt_signature", "receipt_binding", "receipt_chain", "extra_receipt",
    "early_final",
])
def test_restore_rejects_invalid_checkpoint_evidence(tmp_path, change):
    witness, dest = _witnessed(tmp_path)
    witness.close()
    bundle = read_bundle(dest)
    checkpoints, receipts = bundle.checkpoints, bundle.receipts
    cp, rc = checkpoints[0], receipts[0]
    if change == "checkpoint_signature":
        cp["signature"] = crypto.b64url_encode(bytes(64))
    elif change == "checkpoint_key":
        cp["body"]["key_id"] = "ab" * 32
    elif change == "checkpoint_head":
        cp["body"]["head_hash"] = "ab" * 32
    elif change == "checkpoint_chain":
        cp["body"]["previous_checkpoint_hash"] = "ab" * 32
    elif change == "receipt_signature":
        rc["signature"] = crypto.b64url_encode(bytes(64))
    elif change == "receipt_binding":
        rc["body"]["count"] = 0
    elif change == "receipt_chain":
        rc["body"]["previous_receipt_hash"] = "ab" * 32
    elif change == "extra_receipt":
        receipts.append(rc)
    else:
        cp["body"]["final"] = True
    if change in {"checkpoint_key", "checkpoint_head", "checkpoint_chain", "early_final"}:
        cp["checkpoint_hash"] = crypto.digest_checkpoint(cp["body"])
        cp["signature"] = crypto.sign_checkpoint(LOG, cp["body"])
    if change in {"receipt_binding", "receipt_chain"}:
        rc["receipt_hash"] = crypto.digest_receipt(rc["body"])
        rc["signature"] = crypto.sign_receipt(WIT, rc["body"])
    (dest / "checkpoints.jsonl").write_bytes(b"".join(canonicalize(x) + b"\n" for x in checkpoints))
    (dest / "receipts.jsonl").write_bytes(b"".join(canonicalize(x) + b"\n" for x in receipts))
    restored_path = tmp_path / "restored.db"
    with pytest.raises(CasfError):
        Writer.restore_from_bundle(restored_path, LOG, dest)
    assert not restored_path.exists(), "failed restore must not leave a usable partial database"


def test_restore_replays_a_supplied_pending_final_checkpoint(tmp_path):
    witness, dest = _witnessed(tmp_path)
    try:
        writer = Writer(tmp_path / "writer.db", LOG)
        pending = writer.seal_log(LOG_ID)
        writer.close()
        # Bundles may carry a signed pending checkpoint without inventing a receipt.
        with (dest / "checkpoints.jsonl").open("ab") as stream:
            stream.write(canonicalize(pending) + b"\n")
        restored = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, dest)
        try:
            assert restored.pending_checkpoint(LOG_ID) == (pending, 3, 2)
            with pytest.raises(SealedError):
                _append(restored, 3)
            receipt = witness.submit(LOG_ID, pending, [])
            restored.record_receipt(LOG_ID, receipt)
            assert restored.pending_checkpoint(LOG_ID) is None
        finally:
            restored.close()
    finally:
        witness.close()


def test_export_cannot_silently_drop_a_pending_final_seal(tmp_path):
    writer = _writer(tmp_path / "writer.db")
    _append(writer, 1)
    pending = writer.seal_log(LOG_ID)
    try:
        with pytest.raises(CasfError, match="final checkpoint receipt is pending"):
            writer.export_bundle(LOG_ID, tmp_path / "bundle")
        assert not (tmp_path / "bundle").exists()
        writer.backup(tmp_path / "backup.db")
        backup = Writer(tmp_path / "backup.db", LOG)
        try:
            assert backup.pending_checkpoint(LOG_ID)[0] == pending
            with pytest.raises(SealedError):
                _append(backup, 2)
        finally:
            backup.close()
    finally:
        writer.close()


@pytest.mark.parametrize("anchor", [
    {"count": True, "head_hash": "ab" * 32},
    {"count": -1, "head_hash": "ab" * 32},
    {"count": 1, "head_hash": "ab" * 32},
    {"count": 1},
])
def test_restore_rejects_invalid_or_conflicting_anchor(tmp_path, anchor):
    witness, dest = _witnessed(tmp_path)
    witness.close()
    with pytest.raises(CasfError):
        Writer.restore_from_bundle(tmp_path / "restored.db", LOG, dest, anchor=anchor)


@pytest.mark.parametrize("operation", ["append", "checkpoint"])
def test_wrong_signing_key_cannot_extend_existing_log(tmp_path, operation):
    writer = _writer(tmp_path / "writer.db")
    writer.close()
    wrong = Writer(tmp_path / "writer.db", WIT)
    try:
        with pytest.raises(CasfError, match="key"):
            if operation == "append":
                _append(wrong, 1)
            else:
                wrong.create_checkpoint(LOG_ID)
        assert list(wrong.records(LOG_ID)) == []
        assert wrong.pending_checkpoint(LOG_ID) is None
    finally:
        wrong.close()
