"""Focused tests for the real-transport canonical H3 experiment harness."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from benchmarks.h3_witness_outage import FaultProxy, execute, run_condition


def test_fault_proxy_forwards_when_healthy_and_drops_during_fault():
    received = []

    class Target(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *_args):
            pass

    target = ThreadingHTTPServer(("127.0.0.1", 0), Target)
    thread = threading.Thread(target=target.serve_forever, daemon=True)
    thread.start()
    proxy = FaultProxy(target.server_port)
    try:
        import http.client

        conn = http.client.HTTPConnection("127.0.0.1", proxy.port, timeout=1)
        conn.request("POST", "/healthy", body=b"first")
        response = conn.getresponse()
        assert response.status == 200
        assert response.read() == b"ok"
        conn.close()
        assert received == [b"first"]
        assert proxy.forwarded_requests == 1

        proxy.block()
        conn = http.client.HTTPConnection("127.0.0.1", proxy.port, timeout=1)
        conn.request("POST", "/blocked", body=b"second")
        with pytest.raises((OSError, http.client.HTTPException)):
            conn.getresponse()
        conn.close()
        assert received == [b"first"]
        assert proxy.blocked_requests == 1
    finally:
        proxy.close()
        target.shutdown()
        target.server_close()
        thread.join(timeout=1)


@pytest.mark.parametrize("condition", ["healthy", "outage"])
def test_one_real_run_exercises_verification_recovery_and_receipts(
        tmp_path: Path, condition: str):
    config = {
        "events_per_run": 32,
        "batch_size": 8,
        "event_target_bytes": 256,
        "interarrival_seconds": 0.001,
        "query_timeout_seconds": 0.2,
        "submission_timeout_seconds": 0.2,
        "outage_seconds": 0.2,
        "recovery_observation_deadline_seconds": 2.0,
    }
    row = run_condition(tmp_path, 71234, condition, config, 0)
    assert row["status"] == "complete", row.get("traceback")
    assert row["final_writer_count"] == 32
    assert row["final_witness_count"] == 32
    assert row["final_witness_checkpoint_index"] == 3
    assert row["verifications"]["healthy_baseline_online"]["exit_code"] == 0
    assert row["verifications"]["final_online"]["exit_code"] == 0
    if condition == "outage":
        during = row["verifications"]["online_during_outage"]
        assert during["exit_code"] == 4
        assert during["report"]["result"] == "INCONCLUSIVE"
        assert "FRESHNESS_INCONCLUSIVE" in during["report"]["diagnostic_codes"]
        assert row["verifications"]["offline_during_outage"]["exit_code"] == 0
        assert row["proxy_counters"]["blocked_requests"] >= 2
        assert row["checkpoints"][2]["same_pending_bytes_after_failure"]
        assert row["checkpoints"][2]["same_checkpoint_hash_retried"]
        assert row["max_unwitnessed_backlog_records"] == 16


def test_experiment_refuses_existing_result_directory(tmp_path: Path):
    output = tmp_path / "already-there"
    output.mkdir()
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        execute(tmp_path / "missing-manifest.json", output)
