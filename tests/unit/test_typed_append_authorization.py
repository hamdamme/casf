"""Typed append shares verified startup and retained-state authorization."""

import pytest

from casf.errors import TrustError
from casf.trust.state import locked_state
from casf.writer import EventRequest, WitnessState
from tests.unit import test_verified_startup as startup_tests
from tests.unit.test_append_contract import EVENT_ID, event
from tests.unit.test_verified_startup import policy, verified
from tests.unit.test_writer import LOG_ID, _manifest_envelope

history = startup_tests.history


@pytest.mark.parametrize("change", ["revoked", "newer_status", "wrong_log"])
def test_typed_append_retains_all_verified_authorization_checks(history, tmp_path, change):
    _, _, backup, _, calls, _ = history
    writer = verified(backup, policy(tmp_path))
    calls.clear()
    try:
        result = writer.append_event(LOG_ID, EventRequest(**event(event_id=EVENT_ID[:-1] + "4")))
        assert result.record["body"]["seq"] == 4
        assert result.witness_state is WitnessState.COMMITTED_LOCAL
        assert not calls  # authorization does not turn append into a network operation
        if change != "wrong_log":
            with locked_state(str(tmp_path / "state.json"), _manifest_envelope()["manifest_hash"]) as state:
                state.save(2, state.previous.checkpoint, revoked=change == "revoked")
        log_id = LOG_ID[:-1] + "1" if change == "wrong_log" else LOG_ID
        with pytest.raises(TrustError):
            writer.append_event(log_id, EventRequest(**event(event_id=EVENT_ID[:-1] + "5")))
        assert len(list(writer.records(LOG_ID))) == 4
        assert not calls
    finally:
        writer.close()
