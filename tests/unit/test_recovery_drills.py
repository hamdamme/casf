"""R04/R06/R09: recover only intact history with independent retained evidence."""

import json
import sqlite3
from dataclasses import replace

import pytest

from casf.canonical.jcs import canonicalize
from casf.cli import main
from casf.errors import CasfError, InconclusiveError
from casf.trust.state import locked_state
from casf.verifier import Mode, Result, verify
from casf.writer import RestoreBehindWitnessError, SealedError, Writer
from tests.unit import test_writer_reconciliation as recovery
from tests.unit.test_cli import _event
from tests.unit.test_cli_verified_startup import initialize, setup
from tests.unit.test_verified_startup import policy, statement, verified
from tests.unit.test_writer import LOG_ID, _append, _verify_db
from tests.unit.test_writer_trust import _pins

history = recovery.history
cli_environment = setup


def test_sqlite_full_during_reconciliation_keeps_hold_and_retries(history, tmp_path, monkeypatch):
    original, witness, backup, _, _, _ = history
    for _ in range(30):
        recovery._accept(original, witness)
    writer = recovery._open(backup)
    before = recovery._journal(writer)
    con = writer._db.connection
    limit = con.execute("PRAGMA page_count").fetchone()[0]
    con.execute(f"PRAGMA max_page_count={limit}")
    recovered = []
    monkeypatch.setattr(writer, "_debug_hook", lambda stage: recovered.append(stage))
    try:
        with pytest.raises(sqlite3.OperationalError) as error:
            recovery._reconcile(writer)
        assert error.value.sqlite_errorcode == sqlite3.SQLITE_FULL
        assert "after_reconciled_pair" in recovered
        assert not con.in_transaction
    finally:
        writer.close()
    recovery._assert_held(backup, before)
    writer = verified(backup, policy(tmp_path))
    try:
        assert recovery._journal(writer) == recovery._journal(original)
        _append(writer, 4)
        recovery._accept(writer, witness)
        assert _verify_db(writer).result is Result.PASS
    finally:
        writer.close()


@pytest.mark.parametrize("damage", ["header", "record_signature"])
def test_corrupt_backup_cannot_replace_independent_state(history, tmp_path, damage):
    original, _, _, _, calls, _ = history
    startup = policy(tmp_path)
    writer = verified(original._db.path, startup)
    backup = tmp_path / "damaged.db"
    writer.backup(backup)
    writer.close()
    state_before = (tmp_path / "state.json").read_bytes()
    calls.clear()
    if damage == "header":
        with backup.open("r+b") as stream:
            stream.write(b"corrupt backup!!")
    else:
        with sqlite3.connect(backup) as con:
            con.execute("DROP TRIGGER records_no_update")
            record = next(original.records(LOG_ID))
            record["signature"] = "A" * 86
            con.execute("UPDATE records SET envelope=? WHERE seq=1", (canonicalize(record),))
    with pytest.raises((CasfError, sqlite3.DatabaseError)):
        verified(backup, replace(startup, initialize_state=False))
    assert not calls
    assert (tmp_path / "state.json").read_bytes() == state_before
    assert _verify_db(original).result is Result.PASS


def test_missing_key_preserves_public_evidence_and_prevents_signing(
        cli_environment, tmp_path, capsys):
    common, _, status, trust, _, _ = cli_environment
    assert initialize(cli_environment) == 0
    capsys.readouterr()
    (tmp_path / "log.pem").unlink()
    state_before = (tmp_path / "state.json").read_bytes()
    assert main(["append", *common, "--event", str(_event(tmp_path))]) == 5
    output = capsys.readouterr()
    assert not output.out
    assert output.err
    assert (tmp_path / "state.json").read_bytes() == state_before
    reader = Writer(tmp_path / "writer.db", trust_pins={LOG_ID: _pins()})
    bundle = tmp_path / "evidence"
    try:
        with pytest.raises(CasfError, match="signing key"):
            _append(reader, 1)
        reader.export_bundle(LOG_ID, bundle)
        assert len(list(reader.records(LOG_ID))) == 0
    finally:
        reader.close()
    (bundle / "status.jsonl").write_bytes(status.read_bytes() + b"\n")
    assert main(["verify", str(bundle), "--trust", str(trust),
                 "--state", str(tmp_path / "state.json"), "--mode", "anchored", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["result"] == "PASS"


def test_writer_and_witness_rollback_cannot_replace_retained_checkpoint(history, tmp_path):
    original, witness, backup, _, calls, _ = history
    witness_backup = tmp_path / "witness-backup.db"
    witness._db.backup(witness_backup)
    startup = policy(tmp_path)
    writer = verified(backup, startup)
    old_writer = tmp_path / "old-writer.db"
    writer.backup(old_writer)
    _append(writer, 4)
    checkpoint, _ = recovery._accept(writer, witness)
    writer.close()
    state_before = (tmp_path / "state.json").read_bytes()
    # Restore only this synthetic witness while keeping the same key and transport.
    with sqlite3.connect(witness_backup) as source:
        source.backup(witness._db.connection)
    with pytest.raises(CasfError, match="retained checkpoint"):
        verified(old_writer, replace(startup, initialize_state=False))
    assert calls
    assert (tmp_path / "state.json").read_bytes() == state_before
    with locked_state(str(startup.state_path), _pins().manifest_hash) as state:
        assert state.previous.checkpoint == (checkpoint["body"]["index"],
                                             checkpoint["checkpoint_hash"])
    reader = recovery._open(old_writer)
    before = recovery._journal(reader)
    reader.close()
    recovery._assert_held(old_writer, before)
    # The historical copy still has local integrity; that is not authorization.
    assert verify(original.manifest_envelope(LOG_ID), original.records(LOG_ID), _pins(),
                  mode=Mode.INTEGRITY, status_envelopes=[statement(1)]).result is Result.PASS


def test_old_writer_backup_with_lost_records_is_not_promoted(history, tmp_path):
    original, witness, backup, _, _, _ = history
    startup = policy(tmp_path)
    writer = verified(original._db.path, startup)
    _append(writer, 4)
    recovery._accept(writer, witness)
    writer.close()
    state_before = (tmp_path / "state.json").read_bytes()
    with pytest.raises(RestoreBehindWitnessError):
        verified(backup, replace(startup, initialize_state=False))
    assert (tmp_path / "state.json").read_bytes() == state_before
    reader = recovery._open(backup)
    try:
        assert reader._db.connection.execute("SELECT sealed FROM heads").fetchone()[0] == 1
        with pytest.raises(RestoreBehindWitnessError):
            _append(reader, 4)
    finally:
        reader.close()


@pytest.mark.parametrize("final", [False, True])
def test_unavailable_witness_preserves_pending_bytes_until_verified_retry(
        history, tmp_path, monkeypatch, final):
    original, witness, _, _, _, transport = history
    startup = policy(tmp_path)
    writer = verified(original._db.path, startup)
    record = _append(writer, 4)
    checkpoint = writer.create_checkpoint(LOG_ID, final=final)
    receipt = witness.submit(LOG_ID, checkpoint, [record])
    pending = writer.pending_checkpoint(LOG_ID)
    writer.close()
    state_before = (tmp_path / "state.json").read_bytes()

    def offline(*args, **kwargs):
        raise OSError("synthetic witness outage")

    monkeypatch.setattr("casf.online.http_request", offline)
    with pytest.raises(InconclusiveError):
        verified(original._db.path, replace(startup, initialize_state=False))
    reader = recovery._open(original._db.path)
    try:
        assert reader.pending_checkpoint(LOG_ID) == pending
        assert reader._db.connection.execute("SELECT sealed FROM heads").fetchone()[0] == 3
        with pytest.raises(SealedError):
            _append(reader, 5)
    finally:
        reader.close()
    assert (tmp_path / "state.json").read_bytes() == state_before
    monkeypatch.setattr("casf.online.http_request", transport)
    writer = verified(original._db.path, replace(startup, initialize_state=False))
    try:
        assert writer.pending_checkpoint(LOG_ID) is None
        assert writer._db.connection.execute(
            "SELECT envelope FROM receipts WHERE checkpoint_hash=?",
            (checkpoint["checkpoint_hash"],)).fetchone()[0] == canonicalize(receipt)
        assert _append(writer, 4) == record
        if final:
            with pytest.raises(SealedError):
                _append(writer, 5)
        else:
            _append(writer, 5)
        with locked_state(str(startup.state_path), _pins().manifest_hash) as state:
            assert state.previous.checkpoint == (checkpoint["body"]["index"],
                                                 checkpoint["checkpoint_hash"])
    finally:
        writer.close()
