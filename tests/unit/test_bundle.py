"""R06 / R09 / T10 / T15 (SPEC §20, §21): bundles, export, restore."""

import json
import os

import pytest

from casf import crypto
from casf.bundle import read_bundle
from casf.errors import CasfError
from casf.verifier import AnchorStatus, Mode, Result, TrustPins, verify
from casf.writer import RestoreBehindWitnessError, Writer
from tests.status import active_status, register_active
from tests.unit.test_writer import (
    AUTH,
    AUTH_PUB,
    LOG,
    LOG_ID,
    LOG_PUB,
    TS,
    WIT,
    WIT_PUB,
    ZERO,
    _append,
    _writer,
)


def _pins(mh):
    return TrustPins(
        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
        witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
        log_id=LOG_ID, manifest_hash=mh)


def _exported(tmp_path, n=3):
    db = tmp_path / "w.db"
    w = _writer(db)
    for i in range(1, n + 1):
        _append(w, i)
    dest = tmp_path / "bundle"
    w.export_bundle(LOG_ID, dest)
    return w, dest


# ---------------- export shape (SPEC §20) ----------------

def test_export_creates_exact_file_set(tmp_path):
    _, dest = _exported(tmp_path)
    names = sorted(os.listdir(dest))
    assert names == ["checkpoints.jsonl", "export.json", "manifest.json",
                     "receipts.jsonl", "records.jsonl"]

def test_export_jsonl_format(tmp_path):
    _, dest = _exported(tmp_path, 2)
    raw = (dest / "records.jsonl").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # no byte order mark
    lines = raw.split(b"\n")
    assert lines[-1] == b""  # one LF per line, no trailing blank line
    assert all(line for line in lines[:-1])  # no blank lines
    assert len(lines) - 1 == 2

def test_export_metadata(tmp_path):
    _, dest = _exported(tmp_path, 3)
    meta = json.loads((dest / "export.json").read_text())
    assert meta["version"] == 1
    assert meta["type"] == "export"
    assert meta["log_id"] == LOG_ID
    assert meta["through"] == 3
    assert meta["record_count"] == 3
    assert set(meta) == {"version", "type", "log_id", "manifest_hash",
                         "through", "record_count", "generated_at"}

def test_export_empty_history(tmp_path):
    _, dest = _exported(tmp_path, 0)
    assert (dest / "records.jsonl").read_bytes() == b""

def test_export_never_overwrites(tmp_path):
    _, dest = _exported(tmp_path)
    with pytest.raises(CasfError):
        _.export_bundle(LOG_ID, dest)

def test_export_verifies_under_verifier(tmp_path):
    _, dest = _exported(tmp_path, 4)
    bundle = read_bundle(dest)
    report = verify(bundle.manifest, bundle.records, _pins(bundle.manifest_hash),
                    mode=Mode.INTEGRITY,
                    status_envelopes=[active_status(AUTH, bundle.manifest["manifest_hash"]) ])
    assert report.result == Result.PASS
    assert report.verified_through == 4

# ---------------- import limits (SPEC §20) ----------------

def test_tampered_export_metadata_rejected(tmp_path):
    _, dest = _exported(tmp_path, 2)
    meta = json.loads((dest / "export.json").read_text())
    meta["record_count"] = 99
    (dest / "export.json").write_text(json.dumps(meta))
    with pytest.raises(CasfError):
        read_bundle(dest)

def test_symlink_rejected(tmp_path):
    _, dest = _exported(tmp_path)
    os.remove(dest / "receipts.jsonl")
    os.symlink("/etc/passwd", dest / "receipts.jsonl")
    with pytest.raises(CasfError):
        read_bundle(dest)

def test_missing_required_file_rejected(tmp_path):
    _, dest = _exported(tmp_path)
    os.remove(dest / "export.json")
    with pytest.raises(CasfError):
        read_bundle(dest)

def test_oversized_line_rejected(tmp_path):
    _, dest = _exported(tmp_path)
    with open(dest / "records.jsonl", "ab") as f:
        f.write(b'{"body":' + b" " * 200000 + b"}\n")
    with pytest.raises(CasfError):
        list(read_bundle(dest).records)

def test_anchored_bundle_verifies(tmp_path):
    """Checkpoints and receipts supplied in the bundle anchor the export."""
    w, dest = _exported(tmp_path, 2)
    mh = w.manifest_envelope(LOG_ID)["manifest_hash"]
    records = list(w.records(LOG_ID))
    head = records[1]["record_hash"]
    cp_body = {
        "version": 1, "type": "checkpoint", "log_id": LOG_ID,
        "manifest_hash": mh, "index": 0, "count": 2, "head_hash": head,
        "previous_checkpoint_hash": ZERO,
        "key_id": crypto.key_id(LOG_PUB), "issued_at": TS, "final": False,
    }
    cp = {"body": cp_body, "checkpoint_hash": crypto.digest_checkpoint(cp_body),
          "signature": crypto.sign_checkpoint(LOG, cp_body)}
    rc_body = {
        "version": 1, "type": "receipt", "witness_id": crypto.key_id(WIT_PUB),
        "log_id": LOG_ID, "manifest_hash": mh,
        "checkpoint_hash": cp["checkpoint_hash"], "checkpoint_index": 0,
        "count": 2, "head_hash": head, "previous_receipt_hash": ZERO,
        "accepted_at": TS,
    }
    rc = {"body": rc_body, "receipt_hash": crypto.digest_receipt(rc_body),
          "signature": crypto.sign_receipt(WIT, rc_body)}
    from casf.canonical.jcs import canonicalize
    (dest / "checkpoints.jsonl").write_bytes(canonicalize(cp) + b"\n")
    (dest / "receipts.jsonl").write_bytes(canonicalize(rc) + b"\n")
    bundle = read_bundle(dest)
    report = verify(bundle.manifest, bundle.records, _pins(mh),
                    mode=Mode.ANCHORED,
                    checkpoint_envelopes=bundle.checkpoints,
                    receipt_envelopes=bundle.receipts,
                    status_envelopes=[active_status(AUTH, bundle.manifest["manifest_hash"]) ])
    assert report.result == Result.PASS
    assert report.anchor_status == AnchorStatus.OK

# ---------------- restore (SPEC §18, §20) ----------------

def test_restore_continues_chain(tmp_path):
    _, dest = _exported(tmp_path, 3)
    w2 = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, dest)
    env = _append(w2, 4)
    assert env["body"]["seq"] == 4
    from tests.unit.test_writer import _verify_db
    assert _verify_db(w2).result == Result.PASS

def test_restore_refuses_existing_db(tmp_path):
    _, dest = _exported(tmp_path, 1)
    existing = tmp_path / "exists.db"
    _writer(existing)
    with pytest.raises(CasfError):
        Writer.restore_from_bundle(existing, LOG, dest)

def test_restore_behind_anchor_stops_writes(tmp_path):
    _, dest = _exported(tmp_path, 2)  # export covers seq 1-2
    anchor = {"count": 5, "head_hash": "ab" * 32}  # witness is ahead
    with pytest.raises(RestoreBehindWitnessError, match="RESTORE_BEHIND_WITNESS"):
        Writer.restore_from_bundle(tmp_path / "r.db", LOG, dest, anchor=anchor)

def test_restore_behind_anchor_refuses_append(tmp_path):
    _, dest = _exported(tmp_path, 2)
    anchor = {"count": 5, "head_hash": "ab" * 32}
    try:
        Writer.restore_from_bundle(tmp_path / "r.db", LOG, dest, anchor=anchor)
    except RestoreBehindWitnessError:
        pass
    w = Writer(tmp_path / "r.db", LOG)
    with pytest.raises(RestoreBehindWitnessError):
        _append(w, 9)


def test_t10_restored_old_db_reports_incomplete_against_newer_anchor(
        tmp_path):
    """R06 / T10 (SPEC §21): restore an old writer database and
    compare it with a newer external anchor; the verifier must report
    the evidence as incomplete instead of passing silently."""
    from casf.witness import Witness
    from tests.unit.test_writer import _manifest_envelope

    witness = Witness(tmp_path / "wit.db", WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(witness, _manifest_envelope(), AUTH)
    w = _writer(tmp_path / "w.db")
    for n in range(1, 5):
        _append(w, n)
    cp1 = w.create_checkpoint(LOG_ID)
    _env, from_seq, to_seq = w.pending_checkpoint(LOG_ID)
    r1 = witness.submit(LOG_ID, cp1,
                        list(w.records(LOG_ID))[from_seq - 1:to_seq])
    w.record_receipt(LOG_ID, r1)
    backup = tmp_path / "backup.db"
    w.backup(backup)

    # time passes: the live log advances to 8 under a second anchor
    for n in range(5, 9):
        _append(w, n)
    cp2 = w.create_checkpoint(LOG_ID)
    _env, from_seq, to_seq = w.pending_checkpoint(LOG_ID)
    r2 = witness.submit(LOG_ID, cp2,
                        list(w.records(LOG_ID))[from_seq - 1:to_seq])
    w.record_receipt(LOG_ID, r2)
    mh = w.manifest_envelope(LOG_ID)["manifest_hash"]
    w.close()
    witness.close()

    # restore the old copy; compare against the newer external anchor
    old = Writer(backup, LOG)
    old_records = list(old.records(LOG_ID))
    manifest = old.manifest_envelope(LOG_ID)
    old.close()
    assert len(old_records) == 4

    stale = verify(manifest, old_records, _pins(mh), mode=Mode.ANCHORED,
                   checkpoint_envelopes=[cp1, cp2],
                   receipt_envelopes=[r1, r2], allow_unwitnessed=True,
                    status_envelopes=[active_status(AUTH, manifest["manifest_hash"]) ])
    assert stale.result == Result.FAIL
    assert stale.anchor_status == AnchorStatus.INCOMPLETE
    assert "ANCHOR_INCOMPLETE" in stale.diagnostic_codes

    # the same old evidence against its own anchor still verifies
    current = verify(manifest, old_records, _pins(mh), mode=Mode.ANCHORED,
                     checkpoint_envelopes=[cp1], receipt_envelopes=[r1],
                    status_envelopes=[active_status(AUTH, manifest["manifest_hash"]) ])
    assert current.result == Result.PASS
