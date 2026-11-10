"""R04/R05/R06/R08/R09: durable scheduling never invents a replacement checkpoint."""

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from casf.canonical.jcs import canonicalize, parse
from casf.errors import CasfError, SchemaError, TrustError
from casf.trust.state import locked_state
from casf.writer import ReconciliationRequiredError, Writer
from casf.writer.recovery import hold_writer
from casf.writer.worker import CheckpointWorker
from tests.unit import test_verified_startup as startup_tests
from tests.unit.test_verified_startup import policy, verified
from tests.unit.test_writer import LOG, LOG_ID, _append
from tests.unit.test_writer_trust import _pins

history = startup_tests.history


@pytest.fixture
def environment(history, tmp_path, monkeypatch):
    original, witness, _, _, _, _ = history
    startup = policy(tmp_path)
    writer = verified(original._db.path, startup)
    clock = [1000.0]
    requests, failures = [], []

    def submit(url, method, path, token, body, *, timeout):
        assert not worker.writer._db.connection.in_transaction
        requests.append(body)
        failure = failures.pop(0) if failures else None
        if failure == "offline":
            raise OSError("synthetic outage")
        if failure == "interrupt":
            raise KeyboardInterrupt()
        if isinstance(failure, int):
            return failure, b"temporarily unavailable"
        data = parse(body)
        receipt = witness.submit(LOG_ID, data["checkpoint"], data["records"])
        if failure == "lost_reply":
            raise OSError("response lost after acceptance")
        if failure == "bad_receipt":
            receipt["signature"] = "A" * 86
        return 200, canonicalize({"receipt": receipt})

    monkeypatch.setattr("casf.writer.http_request", submit)
    worker = CheckpointWorker(writer, LOG_ID, clock=lambda: clock[0])
    try:
        yield worker, clock, requests, failures, startup
    finally:
        worker.writer.close()


def arm(environment):
    worker, _, requests, _, _ = environment
    assert worker.tick().state == "witnessed"
    requests.clear()


def reopen(environment):
    worker, clock, _, _, startup = environment
    old = worker.writer
    old.close()
    fresh = verified(old._db.path, replace(startup, initialize_state=False))
    worker.writer = fresh
    return CheckpointWorker(fresh, LOG_ID, clock=lambda: clock[0])


def test_heartbeat_deadline_survives_restart(environment):
    arm(environment)
    worker, clock, requests, _, _ = environment
    clock[0] = 1059
    assert worker.tick().state == "idle"
    worker = reopen(environment)
    assert worker.tick().state == "idle"
    assert not requests
    clock[0] = 1060
    result = worker.tick()
    assert result.state == "witnessed"
    assert result.committed == result.witnessed == 3
    assert result.next_action_at_ms == 1120000
    body = parse(requests[0])["checkpoint"]["body"]
    assert body["count"] == 3 and body["index"] == 4


def test_record_threshold_drains_backlog_in_bounded_batches(environment):
    arm(environment)
    worker, _, requests, _, _ = environment
    for n in range(4, 304):
        _append(worker.writer, n)
    stop = threading.Event()
    results = []

    def observed(result):
        results.append(result)
        if result.backlog == 0:
            stop.set()

    worker.run(stop, on_result=observed)
    assert [len(parse(raw)["records"]) for raw in requests] == [128, 128, 44]
    assert [r.backlog for r in results] == [172, 44, 0]
    assert results[-1].witnessed == 303
    assert worker.tick().state == "idle"


def test_checkpoint_threshold_is_exactly_128_unwitnessed_records(environment):
    arm(environment)
    worker, _, requests, _, _ = environment
    for n in range(4, 131):
        _append(worker.writer, n)
    assert worker.tick().state == "idle"
    assert not requests
    _append(worker.writer, 131)
    assert worker.tick().witnessed == 131
    assert len(parse(requests[0])["records"]) == 128


def test_retry_deadline_and_identical_bytes_survive_restart(environment):
    arm(environment)
    worker, clock, requests, failures, _ = environment
    _append(worker.writer, 4)
    clock[0] = 1060
    failures.extend(["offline", 503])
    first = worker.tick()
    assert first.state == "retry" and first.attempts == 1
    assert first.next_action_at_ms == 1061000
    assert first.committed == 4 and first.witnessed == 3 and first.backlog == 1
    worker = reopen(environment)
    clock[0] = 1060.5
    assert worker.tick().state == "waiting"
    assert len(requests) == 1
    clock[0] = 1061
    second = worker.tick()
    assert second.state == "retry" and second.attempts == 2
    assert second.next_action_at_ms == 1063000
    clock[0] = 1063
    assert worker.tick().witnessed == 4
    assert len(requests) == 3
    assert requests[0] == requests[1] == requests[2]


def test_retry_backoff_is_capped(environment):
    arm(environment)
    original, clock, requests, failures, _ = environment
    worker = CheckpointWorker(original.writer, LOG_ID, retry_max_seconds=4, clock=lambda: clock[0])
    clock[0] = 1060
    failures.extend([429] * 5)
    for delay in (1, 2, 4, 4, 4):
        result = worker.tick()
        assert result.next_action_at_ms == int((clock[0] + delay) * 1000)
        clock[0] += delay
    assert len(set(requests)) == 1


def test_lost_receipt_response_reuses_original_acceptance(environment):
    arm(environment)
    worker, clock, requests, failures, _ = environment
    _append(worker.writer, 4)
    clock[0] = 1060
    failures.append("lost_reply")
    assert worker.tick().state == "retry"
    pending = worker.writer.pending_checkpoint(LOG_ID)[0]
    clock[0] = 1061
    result = worker.tick()
    assert result.state == "witnessed" and result.witnessed == 4
    assert requests[0] == requests[1]
    assert worker.writer._db.connection.execute(
        "SELECT COUNT(*) FROM checkpoints WHERE checkpoint_hash=?",
        (pending["checkpoint_hash"],)).fetchone() == (1,)


def test_interrupted_attempt_retains_retry_deadline(environment):
    arm(environment)
    worker, clock, requests, failures, _ = environment
    clock[0] = 1060
    failures.append("interrupt")
    with pytest.raises(KeyboardInterrupt):
        worker.tick()
    worker = reopen(environment)
    clock[0] = 1060.5
    result = worker.tick()
    assert result.state == "waiting" and result.attempts == 1
    assert result.next_action_at_ms == 1061000
    clock[0] = 1061
    assert worker.tick().state == "witnessed"
    assert requests[0] == requests[1]


def test_failed_external_receipt_save_stops_worker(environment, monkeypatch):
    from casf.trust.state import StateTransaction

    arm(environment)
    worker, clock, requests, _, _ = environment
    clock[0] = 1060

    def fail(*args, **kwargs):
        raise OSError("synthetic retained-state failure")

    monkeypatch.setattr(StateTransaction, "save", fail)
    with pytest.raises(OSError):
        worker.run(threading.Event())
    assert len(requests) == 1
    assert worker.writer.pending_checkpoint(LOG_ID) is not None
    assert worker.writer._db.connection.execute("SELECT sealed FROM heads").fetchone() == (3,)
    with pytest.raises(TrustError):
        worker.tick()


def test_pending_final_checkpoint_retries_and_stops(environment):
    arm(environment)
    worker, clock, requests, failures, _ = environment
    _append(worker.writer, 4)
    pending = worker.writer.seal_log(LOG_ID)
    failures.append("offline")
    assert worker.tick().state == "retry"
    clock[0] += 1
    result = worker.run(threading.Event())
    assert result.state == "sealed" and result.backlog == 0
    assert all(parse(raw)["checkpoint"] == pending for raw in requests)
    assert worker.tick().state == "sealed"
    assert len(requests) == 2


@pytest.mark.parametrize("failure", [401, 409, "bad_receipt"])
def test_permanent_errors_stop_without_reporting_witnessed(environment, failure):
    arm(environment)
    worker, clock, requests, failures, _ = environment
    clock[0] = 1060
    failures.append(failure)
    with pytest.raises(CasfError):
        worker.run(threading.Event())
    assert len(requests) == 1
    assert worker.writer.pending_checkpoint(LOG_ID) is not None


@pytest.mark.parametrize("reason", ["revoked", "held"])
def test_worker_rechecks_authority_and_write_hold(environment, reason):
    arm(environment)
    worker, _, requests, _, startup = environment
    if reason == "revoked":
        with locked_state(str(startup.state_path), _pins().manifest_hash) as state:
            state.save(2, None, revoked=True)
    else:
        hold_writer(worker.writer, LOG_ID)
    with pytest.raises(TrustError if reason == "revoked" else ReconciliationRequiredError):
        worker.tick()
    assert not requests


def test_worker_requires_verified_startup(history):
    original, _, _, _, _, _ = history
    writer = Writer(original._db.path, LOG, local_only=True)
    try:
        with pytest.raises(TrustError):
            CheckpointWorker(writer, LOG_ID)
    finally:
        writer.close()


@pytest.mark.parametrize("value", [0, -1, True, float("inf"), float("nan"), 86401])
def test_worker_rejects_invalid_duration(environment, value):
    with pytest.raises(SchemaError):
        CheckpointWorker(environment[0].writer, LOG_ID, interval_seconds=value)


def test_backward_clock_change_clamps_wait(environment):
    arm(environment)
    worker, clock, requests, _, _ = environment
    clock[0] = 900
    assert worker.tick().next_action_at_ms == 960000
    clock[0] = 960
    assert worker.tick().state == "witnessed"
    assert len(requests) == 1


def test_competing_verified_workers_submit_only_one_checkpoint(environment):
    arm(environment)
    worker, clock, requests, _, startup = environment
    clock[0] = 1060
    barrier = threading.Barrier(2)
    def work():
        writer = None
        try:
            writer = verified(worker.writer._db.path, replace(startup, initialize_state=False))
            other = CheckpointWorker(writer, LOG_ID, clock=lambda: clock[0])
            barrier.wait(5)
            return other.tick().state
        finally:
            if writer is not None:
                writer.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(work) for _ in range(2)]
        outcomes = [future.result(timeout=15) for future in futures]
    assert sorted(outcomes) == ["idle", "witnessed"]
    assert len(requests) == 1
