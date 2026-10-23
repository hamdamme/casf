"""SPEC §12 checkpoint production: durable outbox, retry, sealing.

The writer keeps at most one pending checkpoint per log. The signed
checkpoint and its exact extension range land in a durable outbox
before any network submission, retries reuse identical bytes, and
the outbox survives a restart. A final checkpoint covers the whole
committed head and seals appends in the same transaction.
"""

import threading

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.witness import Witness
from casf.witness.http import WitnessService, make_server
from casf.writer import SealedError, Writer
from tests.unit.test_writer import (
    AUTH_PUB,
    LOG,
    LOG_ID,
    WIT,
    ZERO,
    _append,
    _manifest_envelope,
    _writer,
)

TOKEN = "test-bearer-token"  # loopback test credential, never a real one


def _witness(tmp_path, name="wit.db"):
    wit = Witness(tmp_path / name, WIT,
                  authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    wit.register_log(_manifest_envelope())
    return wit


def _pending_records(w, pending):
    _env, from_seq, to_seq = pending
    return list(w.records(LOG_ID))[from_seq - 1:to_seq]


def test_create_checkpoint_covers_committed_prefix(tmp_path):
    w = _writer(tmp_path / "w.db")
    for n in range(1, 4):
        _append(w, n)
    cp = w.create_checkpoint(LOG_ID)
    body = cp["body"]
    assert body["index"] == 0 and body["count"] == 3
    assert body["previous_checkpoint_hash"] == ZERO
    records = list(w.records(LOG_ID))
    assert body["head_hash"] == records[2]["record_hash"]
    assert body["final"] is False
    crypto.verify_checkpoint(crypto.public_key_raw(LOG), body,
                             cp["signature"])
    pending = w.pending_checkpoint(LOG_ID)
    assert pending is not None
    assert pending[0] == cp  # retry reuses identical bytes
    assert pending[1:] == (1, 3)

def test_pending_blocks_second_checkpoint(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    w.create_checkpoint(LOG_ID)
    with pytest.raises(CasfError):
        w.create_checkpoint(LOG_ID)

def test_appends_continue_while_pending(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    w.create_checkpoint(LOG_ID)
    env = _append(w, 2)
    assert env["body"]["seq"] == 2
    assert w.pending_checkpoint(LOG_ID)[0]["body"]["count"] == 1

def test_receipt_flow_advances_to_next_checkpoint(tmp_path):
    w = _writer(tmp_path / "w.db")
    for n in range(1, 3):
        _append(w, n)
    wit = _witness(tmp_path)
    cp = w.create_checkpoint(LOG_ID)
    pending = w.pending_checkpoint(LOG_ID)
    receipt = wit.submit(LOG_ID, cp, _pending_records(w, pending))
    w.record_receipt(LOG_ID, receipt)
    assert w.pending_checkpoint(LOG_ID) is None
    cp2 = w.create_checkpoint(LOG_ID)
    assert cp2["body"]["index"] == 1
    assert cp2["body"]["previous_checkpoint_hash"] == cp["checkpoint_hash"]

def test_record_receipt_rejects_mismatch(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    _append(w, 2)
    wit = _witness(tmp_path)
    cp = w.create_checkpoint(LOG_ID)
    pending = w.pending_checkpoint(LOG_ID)
    receipt = wit.submit(LOG_ID, cp, _pending_records(w, pending))
    bad = dict(receipt)
    bad["body"] = dict(receipt["body"], count=99)
    with pytest.raises(CasfError):
        w.record_receipt(LOG_ID, bad)
    assert w.pending_checkpoint(LOG_ID) is not None

def test_outbox_survives_restart(tmp_path):
    db = tmp_path / "w.db"
    w = _writer(db)
    _append(w, 1)
    cp = w.create_checkpoint(LOG_ID)
    w.close()
    reopened = Writer(db, LOG)
    pending = reopened.pending_checkpoint(LOG_ID)
    assert pending is not None
    assert pending[0] == cp  # identical bytes after recovery

def test_extension_capped_at_128(tmp_path):
    w = _writer(tmp_path / "w.db")
    for n in range(1, 131):
        _append(w, n)
    wit = _witness(tmp_path)
    cp = w.create_checkpoint(LOG_ID)
    assert cp["body"]["count"] == 128  # batches of at most 128
    pending = w.pending_checkpoint(LOG_ID)
    receipt = wit.submit(LOG_ID, cp, _pending_records(w, pending))
    w.record_receipt(LOG_ID, receipt)
    cp2 = w.create_checkpoint(LOG_ID)
    assert cp2["body"]["count"] == 130

def test_final_requires_drain_first(tmp_path):
    w = _writer(tmp_path / "w.db")
    for n in range(1, 131):
        _append(w, n)
    with pytest.raises(CasfError, match="PENDING_DRAIN"):
        w.create_checkpoint(LOG_ID, final=True)

def test_final_checkpoint_seals_appends(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    _append(w, 2)
    wit = _witness(tmp_path)
    cp = w.create_checkpoint(LOG_ID, final=True)
    assert cp["body"]["final"] is True
    assert cp["body"]["count"] == 2  # covers the whole head
    with pytest.raises(SealedError):
        _append(w, 3)
    pending = w.pending_checkpoint(LOG_ID)
    receipt = wit.submit(LOG_ID, cp, _pending_records(w, pending))
    w.record_receipt(LOG_ID, receipt)  # receipt acquisition still works

def test_sealed_append_is_not_restore_error(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    w.create_checkpoint(LOG_ID, final=True)
    try:
        _append(w, 2)
    except SealedError as e:
        assert "RESTORE_BEHIND_WITNESS" not in str(e)
    else:
        raise AssertionError("append after final seal must fail")

def test_submit_pending_end_to_end(tmp_path):
    svc = WitnessService(tmp_path / "wit.db", WIT, token=TOKEN,
                         authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    svc.witness.register_log(_manifest_envelope())
    server = make_server(svc, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        w = _writer(tmp_path / "w.db")
        _append(w, 1)
        _append(w, 2)
        w.create_checkpoint(LOG_ID)
        receipt = w.submit_pending(LOG_ID, url, TOKEN)
        assert receipt["body"]["count"] == 2
        assert w.pending_checkpoint(LOG_ID) is None
        _checkpoint, stored = svc.witness.receipt(
            receipt["body"]["checkpoint_hash"])
        assert stored == receipt
    finally:
        server.shutdown()
        server.server_close()
        svc.close()
