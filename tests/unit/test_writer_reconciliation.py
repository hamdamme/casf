"""R02/R05/R06/R08/R09: fresh recovery never resumes an unverified history."""

import os
import sqlite3

import pytest

from casf import crypto
from casf.canonical.jcs import canonicalize, parse
from casf.errors import CasfError, InconclusiveError, TrustError
from casf.writer import BusyError, RestoreBehindWitnessError, SealedError, Writer
from tests.unit.test_witness import _witness
from tests.unit.test_writer import LOG, LOG_ID, WIT, _append, _manifest_envelope
from tests.unit.test_writer_trust import _pins


def _open(path, **kwargs):
    return Writer(path, LOG, trust_pins={LOG_ID: _pins()}, **kwargs)


def _accept(writer, witness, *, final=False):
    checkpoint = writer.create_checkpoint(LOG_ID, final=final)
    _, start, stop = writer.pending_checkpoint(LOG_ID)
    receipt = witness.submit(LOG_ID, checkpoint, list(writer.records(LOG_ID))[start - 1:stop])
    writer.record_receipt(LOG_ID, receipt)
    return checkpoint, receipt


def _journal(writer):
    con = writer._db.connection
    return tuple(con.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
                 for table in ("checkpoints", "receipts", "outbox"))


@pytest.fixture
def history(tmp_path, monkeypatch):
    writer = _open(tmp_path / "writer.db")
    writer.create_log(_manifest_envelope())
    witness = _witness(tmp_path)
    for n in range(1, 4):
        _append(writer, n)
    pairs = [_accept(writer, witness)]
    backup = tmp_path / "backup.db"
    writer.backup(backup)
    pairs.extend(_accept(writer, witness) for _ in range(2))
    calls = []

    def transport(url, method, path, token, body, *, timeout):
        calls.append((method, path, timeout))
        if method == "POST":
            nonce = crypto.b64url_decode(parse(body)["nonce"])
            return 200, canonicalize(witness.latest(LOG_ID, nonce))
        cp, rc = witness.receipt(path.rsplit("/", 1)[-1])
        return 200, canonicalize({"checkpoint": cp, "receipt": rc})

    monkeypatch.setattr("casf.online.http_request", transport)
    # The public operation owns nonce generation and signature verification.
    monkeypatch.setattr("casf.writer.recovery.http_request", transport)
    yield writer, witness, backup, pairs, calls, transport
    writer.close()
    witness.close()


def _reconcile(writer, **kwargs):
    return writer.reconcile_witness(LOG_ID, "https://witness.example", "test-token", **kwargs)


def _assert_held(path, expected):
    writer = _open(path)
    try:
        assert _journal(writer) == expected
        assert len(list(writer.records(LOG_ID))) == 3
        with pytest.raises(SealedError):
            _append(writer, 4)
        with pytest.raises(SealedError):
            writer.create_checkpoint(LOG_ID)
    finally:
        writer.close()


def test_recovers_missing_journal_and_continues_original_chain(history):
    original, witness, backup, pairs, calls, _ = history
    writer = _open(backup)
    try:
        view = _reconcile(writer, retained_checkpoint=(1, pairs[1][0]["checkpoint_hash"]))
        assert view.checkpoint == pairs[-1][0]
        assert _journal(writer) == _journal(original)
        assert [call[0] for call in calls] == ["POST", "GET"]
        _append(writer, 4)
        cp, _ = _accept(writer, witness)
        assert cp["body"]["index"] == 3
    finally:
        writer.close()


def test_keyless_reconciliation_is_idempotent(history):
    original, _, backup, _, calls, _ = history
    writer = Writer(backup, trust_pins={LOG_ID: _pins()})
    try:
        _reconcile(writer)
        _reconcile(writer)
        assert _journal(writer) == _journal(original)
        assert [call[0] for call in calls] == ["POST", "GET", "POST"]
    finally:
        writer.close()


def test_recovers_from_empty_checkpoint_journal(history):
    original, _, backup, _, calls, _ = history
    with sqlite3.connect(backup) as con:
        con.execute("DELETE FROM receipts")
        con.execute("DELETE FROM checkpoints")
    writer = _open(backup)
    try:
        _reconcile(writer)
        assert _journal(writer) == _journal(original)
        assert len(calls) == 3
    finally:
        writer.close()


@pytest.mark.parametrize("final", [False, True])
def test_recovers_exact_pending_receipt(history, final):
    writer, witness, _, _, _, _ = history
    cp = writer.create_checkpoint(LOG_ID, final=final)
    receipt = witness.submit(LOG_ID, cp, [])
    _reconcile(writer)
    assert writer.pending_checkpoint(LOG_ID) is None
    assert writer._db.connection.execute(
        "SELECT envelope FROM receipts WHERE checkpoint_hash=?", (cp["checkpoint_hash"],)
    ).fetchone()[0] == canonicalize(receipt)
    if final:
        with pytest.raises(SealedError):
            _append(writer, 4)
    else:
        _append(writer, 4)


@pytest.mark.parametrize("final", [False, True])
def test_preserves_unaccepted_pending_tail(history, final):
    writer, _, _, _, _, _ = history
    writer.create_checkpoint(LOG_ID, final=final)
    pending = writer.pending_checkpoint(LOG_ID)
    before = _journal(writer)
    _reconcile(writer)
    assert _journal(writer) == before
    assert writer.pending_checkpoint(LOG_ID) == pending
    if final:
        with pytest.raises(SealedError):
            _append(writer, 4)
    else:
        _append(writer, 4)


def test_record_loss_is_terminal_even_after_witness_rollback(history, monkeypatch):
    original, witness, backup, pairs, _, _ = history
    writer = _open(backup)
    before = _journal(writer)
    _append(original, 4)
    _accept(original, witness)
    try:
        with pytest.raises(RestoreBehindWitnessError):
            _reconcile(writer)
    finally:
        writer.close()
    _assert_held(backup, before)
    # A later stale witness cannot clear an already observed record-loss seal.
    monkeypatch.setattr(witness, "latest", lambda *_: pytest.fail("terminal hold queried witness"))
    writer = _open(backup)
    try:
        with pytest.raises(RestoreBehindWitnessError):
            _reconcile(writer, retained_checkpoint=(0, pairs[0][0]["checkpoint_hash"]))
    finally:
        writer.close()


@pytest.mark.parametrize("failure", ["offline", "missing", "replay", "bad_signature",
                                     "bad_receipt_link", "wrong_lookup", "interrupt"])
def test_failed_recovery_preserves_journal_and_blocks_restart(history, monkeypatch, failure):
    _, witness, backup, _, _, transport = history
    writer = _open(backup)
    before = _journal(writer)

    def broken(url, method, path, token, body, *, timeout):
        if failure == "offline":
            raise OSError("offline")
        if failure == "interrupt":
            raise KeyboardInterrupt()
        if failure == "missing" and method == "GET":
            return 404, b"{}"
        status, payload = transport(url, method, path, token, body, timeout=timeout)
        data = parse(payload)
        if method == "POST":
            if failure == "replay":
                return 200, canonicalize(witness.latest(LOG_ID, b"x" * 32))
            if failure == "bad_signature":
                data["checkpoint"]["signature"] = crypto.b64url_encode(bytes(64))
        elif failure == "bad_receipt_link":
            receipt = data["receipt"]
            receipt["body"]["previous_receipt_hash"] = "ab" * 32
            receipt["receipt_hash"] = crypto.digest_receipt(receipt["body"])
            receipt["signature"] = crypto.sign_receipt(WIT, receipt["body"])
        elif failure == "wrong_lookup":
            cp, rc = witness.receipt(witness.latest(LOG_ID, b"x" * 32)["body"]["checkpoint_hash"])
            data = {"checkpoint": cp, "receipt": rc}
        return status, canonicalize(data)

    monkeypatch.setattr("casf.online.http_request", broken)
    monkeypatch.setattr("casf.writer.recovery.http_request", broken)
    try:
        with pytest.raises(KeyboardInterrupt if failure == "interrupt" else CasfError):
            _reconcile(writer)
    finally:
        writer.close()
    _assert_held(backup, before)
    monkeypatch.setattr("casf.online.http_request", transport)
    monkeypatch.setattr("casf.writer.recovery.http_request", transport)
    writer = _open(backup)
    try:
        _reconcile(writer)
        _append(writer, 4)
    finally:
        writer.close()


@pytest.mark.parametrize("retained", [(3, "ab" * 32), (2, "ab" * 32), (0, "ab" * 32)])
def test_rejects_retained_checkpoint_rollback_or_fork(history, retained):
    _, _, backup, _, _, _ = history
    writer = _open(backup)
    before = _journal(writer)
    try:
        with pytest.raises(CasfError, match="retained"):
            _reconcile(writer, retained_checkpoint=retained)
    finally:
        writer.close()
    _assert_held(backup, before)


def test_chain_budget_preserves_hold(history):
    _, _, backup, _, calls, _ = history
    writer = _open(backup)
    before = _journal(writer)
    try:
        with pytest.raises(InconclusiveError, match="budget"):
            _reconcile(writer, max_chain_steps=1)
        assert len(calls) == 1
    finally:
        writer.close()
    _assert_held(backup, before)


def test_reconciliation_requires_independent_pins(history):
    _, _, backup, _, calls, _ = history
    writer = Writer(backup, LOG)
    try:
        with pytest.raises(TrustError):
            _reconcile(writer)
        assert not calls
    finally:
        writer.close()


@pytest.mark.parametrize("kwargs", [
    {"timeout": True}, {"timeout": 0}, {"timeout": float("inf")},
    {"max_chain_steps": True}, {"max_chain_steps": 0},
    {"retained_checkpoint": (True, "ab" * 32)},
    {"retained_checkpoint": (-1, "ab" * 32)},
    {"retained_checkpoint": (0, "AB" * 32)},
    {"retained_checkpoint": [0, "ab" * 32]},
])
def test_invalid_configuration_never_queries_witness(history, kwargs):
    _, _, backup, _, calls, _ = history
    writer = _open(backup)
    try:
        with pytest.raises(CasfError):
            _reconcile(writer, **kwargs)
        assert not calls
    finally:
        writer.close()


def test_requests_share_one_deadline(history, monkeypatch):
    _, _, backup, _, calls, transport = history
    clock = [0.0]
    monkeypatch.setattr("casf.writer.recovery.time.monotonic", lambda: clock[0])

    def delayed(*args, **kwargs):
        result = transport(*args, **kwargs)
        clock[0] += 4.0 if args[1] == "POST" else 7.0
        return result

    monkeypatch.setattr("casf.online.http_request", delayed)
    monkeypatch.setattr("casf.writer.recovery.http_request", delayed)
    writer = _open(backup)
    before = _journal(writer)
    try:
        with pytest.raises(InconclusiveError, match="time budget"):
            _reconcile(writer, timeout=10.0)
        assert [call[2] for call in calls] == [10.0, 6.0]
    finally:
        writer.close()
    _assert_held(backup, before)


def test_competing_writer_cannot_append_during_reconciliation(history, monkeypatch):
    _, _, backup, _, _, transport = history
    writer = _open(backup)
    other = _open(backup, busy_timeout_ms=0, max_retries=0)

    def concurrent(*args, **kwargs):
        assert len(list(other.records(LOG_ID))) == 3
        with pytest.raises(BusyError):
            _append(other, 4)
        return transport(*args, **kwargs)

    monkeypatch.setattr("casf.online.http_request", concurrent)
    try:
        _reconcile(writer)
        _append(other, 4)
    finally:
        writer.close()
        other.close()


def test_late_journal_failure_rolls_back_all_recovered_pairs(history, monkeypatch):
    _, _, backup, _, _, _ = history
    writer = _open(backup)
    before = _journal(writer)
    completed = []

    def interrupt(stage):
        if stage == "after_reconciled_pair":
            completed.append(stage)
            if len(completed) == 2:
                raise OSError("simulated storage failure")

    monkeypatch.setattr(writer, "_debug_hook", interrupt)
    try:
        with pytest.raises(OSError, match="storage failure"):
            _reconcile(writer)
        assert len(completed) == 2
    finally:
        writer.close()
    _assert_held(backup, before)


def test_rejects_valid_but_different_local_pending_checkpoint(history):
    _, _, backup, _, _, _ = history
    writer = _open(backup)
    # A final checkpoint cannot equal the witness's nonfinal heartbeat.
    writer.create_checkpoint(LOG_ID, final=True)
    before = _journal(writer)
    try:
        with pytest.raises(CasfError, match="pending journal"):
            _reconcile(writer)
    finally:
        writer.close()
    _assert_held(backup, before)


def test_rejects_fresh_witness_behind_local_journal(history, monkeypatch):
    writer, witness, _, pairs, _, _ = history
    before = _journal(writer)
    latest = witness.latest

    def stale(log_id, nonce):
        response = latest(log_id, nonce)
        cp, rc = pairs[0]
        response["checkpoint"], response["receipt"] = cp, rc
        response["body"].update(checkpoint_index=0, checkpoint_hash=cp["checkpoint_hash"],
                                receipt_hash=rc["receipt_hash"])
        response["signature"] = crypto.sign_latest(WIT, response["body"])
        return response

    monkeypatch.setattr(witness, "latest", stale)
    with pytest.raises(CasfError, match="behind the accepted"):
        _reconcile(writer)
    assert _journal(writer) == before
    with pytest.raises(SealedError):
        _append(writer, 4)


def test_valid_signatures_cannot_reconcile_different_records(history, tmp_path):
    _, _, _, _, _, _ = history
    writer = _open(tmp_path / "fork.db")
    writer.create_log(_manifest_envelope())
    for n in range(10, 13):
        _append(writer, n)
    before = _journal(writer)
    try:
        with pytest.raises(CasfError, match="head disagrees"):
            _reconcile(writer)
    finally:
        writer.close()
    _assert_held(tmp_path / "fork.db", before)


def test_no_checkpoint_response_does_not_resume_writes(history, monkeypatch):
    from casf.errors import NoCheckpointError

    _, _, backup, _, _, _ = history
    writer = _open(backup)
    before = _journal(writer)
    monkeypatch.setattr("casf.online.http_request",
                        lambda *a, **k: (404, b'{"code":"NO_CHECKPOINT"}'))
    try:
        with pytest.raises(NoCheckpointError):
            _reconcile(writer)
    finally:
        writer.close()
    _assert_held(backup, before)


def _crash_recovery(path, url):
    writer = _open(path)
    writer._debug_hook = lambda stage: os._exit(73) if stage == "after_reconciled_pair" else None
    writer.reconcile_witness(LOG_ID, url, "test-bearer-token")


def test_http_recovery_survives_process_exit_after_journal_insert(tmp_path):
    import multiprocessing

    from tests.unit.test_verify_online import TOKEN, _evidence, _service

    service, server = _service(tmp_path)
    original = writer = process = None
    try:
        original, _, _, _ = _evidence(tmp_path, service, records=3, witnessed=1)
        backup = tmp_path / "http-backup.db"
        original.backup(backup)
        _accept(original, service.witness)
        _accept(original, service.witness, final=True)
        writer = _open(backup)
        before = _journal(writer)
        writer.close()
        writer = None
        url = f"http://127.0.0.1:{server.server_port}"
        process = multiprocessing.get_context("spawn").Process(
            target=_crash_recovery, args=(backup, url))
        process.start()
        process.join(15)
        assert process.exitcode == 73
        _assert_held(backup, before)
        writer = _open(backup)
        view = writer.reconcile_witness(LOG_ID, url, TOKEN)
        assert view.body["final"] is True
        assert _journal(writer) == _journal(original)
        with pytest.raises(SealedError):
            _append(writer, 4)
    finally:
        if process is not None and process.is_alive():
            process.terminate()
            process.join(5)
        if writer is not None:
            writer.close()
        if original is not None:
            original.close()
        server.shutdown()
        server.server_close()
        service.close()
