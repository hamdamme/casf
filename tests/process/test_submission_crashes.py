"""R05/R06/R09: HTTP acceptance survives a killed verified writer."""

import json

import pytest

from casf.canonical.jcs import canonicalize, parse
from casf.transport import request
from casf.trust.state import locked_state
from casf.verifier import Result
from casf.writer import SealedError
from tests.process.support import CommitBarrier, kill, pause, receive, worker
from tests.status import active_status
from tests.unit.test_verified_startup import verified
from tests.unit.test_witness_server import TOKEN, running
from tests.unit.test_writer import AUTH, LOG_ID, _append, _manifest_envelope, _verify_db, _writer
from tests.unit.test_writer_trust import _pins


def _policy(path, url, *, initialize=False):
    from casf.writer.startup import StartupPolicy

    return StartupPolicy(
        state_path=path,
        status_envelopes=(active_status(AUTH, _manifest_envelope()["manifest_hash"]),),
        witness_url=url, token=TOKEN, initialize_state=initialize)


def _crash_submission(path, state_path, url, stage, pipe):
    import casf.writer as module

    writer = verified(path, _policy(state_path, url))
    if stage == "after_response":
        http_request = module.http_request

        def received(*args, **kwargs):
            status, raw = http_request(*args, **kwargs)
            assert status == 201
            pause(pipe, stage, canonicalize(parse(raw)["receipt"]))

        module.http_request = received
    else:
        writer._db.connection = CommitBarrier(
            writer._db.connection, pipe, stage,
            lambda con: con.execute(
                "SELECT r.envelope FROM receipts r JOIN checkpoints c "
                "ON r.checkpoint_hash=c.checkpoint_hash WHERE c.idx=1").fetchone()[0],
            predicate=lambda con: con.execute("SELECT count(*) FROM receipts").fetchone() == (2,))
    writer.submit_pending(LOG_ID, url, TOKEN)
    raise AssertionError("submission missed crash barrier")


@pytest.mark.parametrize("stage", ["after_response", "before_commit", "after_commit"])
@pytest.mark.parametrize("final", [False, True])
def test_killed_submission_reconciles_receipt_and_retained_state(tmp_path, stage, final):
    path, state_path = tmp_path / "writer.db", tmp_path / "state.json"
    with running(tmp_path) as (service, server):
        witness = service.witness
        witness.install_status(LOG_ID, active_status(AUTH, _pins().manifest_hash))
        url = f"http://127.0.0.1:{server.server_port}"
        writer = _writer(path)
        try:
            _append(writer, 1)
            first = writer.create_checkpoint(LOG_ID)
            writer.record_receipt(LOG_ID, witness.submit(LOG_ID, first, list(writer.records(LOG_ID))))
        finally:
            writer.close()
        writer = verified(path, _policy(state_path, url, initialize=True))
        try:
            _append(writer, 2)
            checkpoint = writer.create_checkpoint(LOG_ID, final=final)
            records = list(writer.records(LOG_ID))
        finally:
            writer.close()
        with worker(_crash_submission, path, state_path, url, stage) as (process, pipe):
            snapshot = receive(pipe, stage)
            kill(process)

        # Observe the two stores before any startup recovery changes them.
        from casf.writer import Writer

        reader = Writer(path)
        try:
            con = reader._db.connection
            committed = stage == "after_commit"
            assert con.execute("SELECT count(*) FROM receipts").fetchone() == (2 if committed else 1,)
            assert con.execute("SELECT state FROM checkpoints WHERE idx=1").fetchone() == (
                "accepted" if committed else "pending",)
            if committed:
                assert reader.pending_checkpoint(LOG_ID) is None
            else:
                pending, start, end = reader.pending_checkpoint(LOG_ID)
                assert canonicalize(pending) == canonicalize(checkpoint)
                assert (start, end) == (2, 2)
                assert con.execute("SELECT attempts FROM outbox").fetchone() == (1,)
            assert list(reader.records(LOG_ID)) == records
        finally:
            reader.close()
        with locked_state(str(state_path), _pins().manifest_hash) as state:
            expected = first if stage == "after_response" else checkpoint
            assert state.previous.checkpoint == (expected["body"]["index"], expected["checkpoint_hash"])

        stored = witness._db.connection.execute(
            "SELECT envelope FROM w_receipts WHERE checkpoint_hash=?",
            (checkpoint["checkpoint_hash"],)).fetchone()[0]
        assert stored == snapshot
        # Retry the original signed checkpoint over real HTTP while its caller
        # is gone. The live witness must return the same receipt with HTTP 200.
        status, raw = request(url, "POST", f"/v1/logs/{LOG_ID}/checkpoints", TOKEN,
                              json.dumps({"checkpoint": checkpoint, "records": records[1:]}).encode(),
                              timeout=10)
        assert status == 200
        assert canonicalize(parse(raw)["receipt"]) == stored
        assert witness._db.connection.execute("SELECT count(*) FROM w_receipts").fetchone() == (2,)

        writer = verified(path, _policy(state_path, url))
        try:
            assert writer.pending_checkpoint(LOG_ID) is None
            assert writer._db.connection.execute(
                "SELECT envelope FROM receipts WHERE checkpoint_hash=?",
                (checkpoint["checkpoint_hash"],)).fetchone() == (stored,)
            assert list(writer.records(LOG_ID)) == records
            with locked_state(str(state_path), _pins().manifest_hash) as state:
                assert state.previous.checkpoint == (1, checkpoint["checkpoint_hash"])
            if final:
                with pytest.raises(SealedError):
                    _append(writer, 3)
            else:
                assert _append(writer, 3)["body"]["seq"] == 3
            assert _verify_db(writer).result == Result.PASS
        finally:
            writer.close()
