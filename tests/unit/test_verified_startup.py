"""R02/R06/R07/R09: signing requires trusted, durable startup authorization."""

from dataclasses import replace

import pytest

from casf import crypto
from casf.errors import CasfError, TrustError
from casf.writer import Writer
from tests.unit import test_writer_reconciliation as recovery_tests
from tests.unit.test_writer import AUTH, LOG, LOG_ID, WIT, _append, _manifest_envelope
from tests.unit.test_writer_trust import _pins

history = recovery_tests.history


def test_signing_constructor_requires_explicit_startup_or_local_mode(tmp_path):
    with pytest.raises(TrustError, match="open_verified"):
        Writer(tmp_path / "writer.db", LOG)
    assert not (tmp_path / "writer.db").exists()


def policy(tmp_path, *, statuses=None, initialize=True):
    from casf.writer.startup import StartupPolicy
    from tests.status import active_status
    from tests.unit.test_writer import AUTH, _manifest_envelope

    return StartupPolicy(
        state_path=tmp_path / "state.json",
        status_envelopes=tuple(statuses if statuses is not None else [
            active_status(AUTH, _manifest_envelope()["manifest_hash"])]),
        witness_url="https://witness.example", token="synthetic-startup-token",
        initialize_state=initialize)


def verified(path, startup):
    return Writer.open_verified(path, LOG, trust_pins={LOG_ID: _pins()}, startup=startup)


def test_verified_startup_recovers_journal_and_retains_checkpoint(history, tmp_path):
    from casf.trust.state import locked_state

    _, _, backup, pairs, _, _ = history
    writer = verified(backup, policy(tmp_path))
    try:
        _append(writer, 4)
        with locked_state(str(tmp_path / "state.json"), _pins().manifest_hash) as state:
            assert state.previous.status_serial == 1
            assert state.previous.checkpoint == (2, pairs[-1][0]["checkpoint_hash"])
    finally:
        writer.close()


@pytest.mark.parametrize("statuses", [[], [{}]])
def test_missing_or_invalid_status_does_not_resume(history, tmp_path, statuses):
    _, _, backup, _, calls, _ = history
    with pytest.raises(TrustError):
        verified(backup, policy(tmp_path, statuses=statuses))
    assert not calls
    reader = Writer(backup)
    try:
        assert len(list(reader.records(LOG_ID))) == 3
        assert reader._db.connection.execute("SELECT sealed FROM heads").fetchone()[0] == 3
    finally:
        reader.close()


def statement(serial, status="active"):
    from casf.lifecycle import sign_status

    return sign_status(AUTH, serial=serial, status=status,
                       manifest_hash=_manifest_envelope()["manifest_hash"],
                       issued_at="2026-11-10T00:00:00.000000Z", reason="synthetic test")


@pytest.mark.parametrize("serial", [1, 4])
def test_revocation_is_terminal_across_restart_and_open_writers(history, tmp_path, serial):
    from casf.trust.state import locked_state

    _, _, backup, pairs, calls, _ = history
    writer = verified(backup, policy(tmp_path, statuses=[statement(3)]))
    calls.clear()
    try:
        with pytest.raises(TrustError):
            verified(backup, policy(tmp_path, statuses=[statement(serial, "revoked")],
                                    initialize=False))
        with pytest.raises(TrustError, match="revoked"):
            _append(writer, 4)
        with pytest.raises(TrustError, match="revoked"):
            writer.create_checkpoint(LOG_ID)
        with pytest.raises(TrustError):
            verified(backup, policy(tmp_path, statuses=[statement(5)], initialize=False))
        assert not calls
        with locked_state(str(tmp_path / "state.json"), _pins().manifest_hash) as state:
            assert state.previous.revoked is True
            assert state.previous.status_serial == 5
            assert state.previous.checkpoint == (2, pairs[-1][0]["checkpoint_hash"])
    finally:
        writer.close()


@pytest.mark.parametrize("kind", ["forged", "unrelated", "wrong_issuer"])
def test_unauthenticated_status_cannot_poison_retained_state(history, tmp_path, kind):
    _, _, backup, _, calls, _ = history
    value = statement(100, "revoked")
    if kind == "forged":
        value["signature"] = crypto.b64url_encode(bytes(64))
    else:
        field = "manifest_hash" if kind == "unrelated" else "issuer_id"
        value["body"][field] = "ab" * 32
        value["signature"] = crypto.sign_status(AUTH, value["body"])
    with pytest.raises(TrustError):
        verified(backup, policy(tmp_path, statuses=[value]))
    assert not calls
    assert not (tmp_path / "state.json").exists()
    writer = verified(backup, policy(tmp_path))
    writer.close()


def test_newer_status_survives_witness_failure_and_blocks_old_writer(history, tmp_path, monkeypatch):
    _, _, backup, _, _, _ = history
    writer = verified(backup, policy(tmp_path))

    def offline(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr("casf.online.http_request", offline)
    try:
        with pytest.raises(CasfError):
            verified(backup, policy(tmp_path, statuses=[statement(3)], initialize=False))
        with pytest.raises(TrustError, match="newer authority status"):
            _append(writer, 4)
        with pytest.raises(TrustError):
            verified(backup, policy(tmp_path, initialize=False))
    finally:
        writer.close()


@pytest.mark.parametrize("after_save", [False, True])
def test_state_save_failure_keeps_journal_held_until_retry(history, tmp_path, monkeypatch, after_save):
    from casf.trust.state import StateTransaction

    original, _, backup, _, _, _ = history
    before = Writer(backup)
    journal = recovery_tests._journal(before)
    before.close()
    save = StateTransaction.save

    def failed_save(self, serial, checkpoint, **kwargs):
        if checkpoint is not None:
            if after_save:
                save(self, serial, checkpoint, **kwargs)
            raise OSError("simulated state durability failure")
        return save(self, serial, checkpoint, **kwargs)

    monkeypatch.setattr(StateTransaction, "save", failed_save)
    with pytest.raises(OSError):
        verified(backup, policy(tmp_path))
    recovery_tests._assert_held(backup, journal)
    monkeypatch.setattr(StateTransaction, "save", save)
    writer = verified(backup, policy(tmp_path, initialize=False))
    try:
        assert recovery_tests._journal(writer) == recovery_tests._journal(original)
        _append(writer, 4)
    finally:
        writer.close()


def test_wrong_signing_key_fails_before_network(history, tmp_path):
    _, _, backup, _, calls, _ = history
    with pytest.raises(TrustError, match="writer key"):
        Writer.open_verified(backup, WIT, trust_pins={LOG_ID: _pins()}, startup=policy(tmp_path))
    assert not calls


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", ".recovery.lock"])
def test_state_cannot_replace_database_or_sidecars(history, tmp_path, suffix):
    _, _, backup, _, calls, _ = history
    with pytest.raises(TrustError, match="separate"):
        verified(backup, replace(policy(tmp_path), state_path=str(backup) + suffix))
    assert not calls
    reader = Writer(backup)
    reader.close()


def test_default_offline_restore_is_keyless(history, tmp_path):
    writer, _, _, _, _, _ = history
    bundle = tmp_path / "bundle"
    writer.export_bundle(LOG_ID, bundle)
    restored = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, bundle)
    try:
        with pytest.raises(CasfError, match="signing key"):
            _append(restored, 4)
        assert len(list(restored.records(LOG_ID))) == 3
    finally:
        restored.close()


def test_caller_policy_mutation_does_not_change_authorized_serial(history, tmp_path):
    _, _, backup, _, _, _ = history
    supplied = policy(tmp_path)
    writer = verified(backup, supplied)
    try:
        supplied.status_envelopes[0]["body"]["serial"] = 999
        assert writer._startup_policy.status_envelopes[0]["body"]["serial"] == 1
        assert "synthetic-startup-token" not in repr(writer._startup_policy)
    finally:
        writer.close()


@pytest.mark.parametrize("failure", [False, True])
def test_verified_receipt_updates_retained_checkpoint_before_success(history, tmp_path,
                                                                    monkeypatch, failure):
    from casf.trust.state import StateTransaction, locked_state

    _, witness, backup, _, _, _ = history
    writer = verified(backup, policy(tmp_path))
    cp = writer.create_checkpoint(log_id=LOG_ID)
    rc = witness.submit(LOG_ID, cp, [])
    save = StateTransaction.save

    def failing_save(self, serial, checkpoint, **kwargs):
        if checkpoint is not None and checkpoint[0] == 3:
            raise OSError("receipt state save failed")
        return save(self, serial, checkpoint, **kwargs)

    try:
        if failure:
            monkeypatch.setattr(StateTransaction, "save", failing_save)
            with pytest.raises(OSError, match="receipt state"):
                writer.record_receipt(LOG_ID, rc)
            assert writer.pending_checkpoint(LOG_ID)[0] == cp
            assert writer._db.connection.execute("SELECT sealed FROM heads").fetchone()[0] == 3
            with pytest.raises(TrustError):
                _append(writer, 4)
        else:
            writer.record_receipt(LOG_ID, rc)
            with locked_state(str(tmp_path / "state.json"), _pins().manifest_hash) as state:
                assert state.previous.checkpoint == (3, cp["checkpoint_hash"])
    finally:
        writer.close()
