"""A typed handle never grants permission beyond the writer's retained policy."""

import pytest

from casf.api import EventRequest, open_log
from casf.errors import TrustError
from casf.trust.state import locked_state
from tests.unit import test_verified_startup as startup_tests
from tests.unit.test_event_models import event
from tests.unit.test_verified_startup import policy, verified
from tests.unit.test_writer import LOG_ID, _manifest_envelope

history = startup_tests.history


@pytest.mark.parametrize('change', ['revoked', 'newer_status'])
@pytest.mark.parametrize('operation', ['append', 'checkpoint', 'seal', 'submit'])
def test_handle_rechecks_authorization_before_every_mutation(history, tmp_path, change, operation):
    _, _, backup, _, calls, _ = history
    writer = verified(backup, policy(tmp_path))
    log = open_log(writer, LOG_ID)
    calls.clear()
    try:
        before = list(writer.records(LOG_ID))
        with locked_state(str(tmp_path / 'state.json'), _manifest_envelope()['manifest_hash']) as state:
            state.save(2, state.previous.checkpoint, revoked=change == 'revoked')
        with pytest.raises(TrustError):
            if operation == 'append':
                log.append(EventRequest(**event(event_id='123e4567-e89b-42d3-a456-426600000004')))
            elif operation == 'checkpoint':
                log.create_checkpoint()
            elif operation == 'seal':
                log.seal_log()
            else:
                log.submit_pending('https://witness.example', 'synthetic-token')
        assert list(writer.records(LOG_ID)) == before
        assert not calls
    finally:
        writer.close()
