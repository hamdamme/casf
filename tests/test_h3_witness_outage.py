"""Focused tests for the real-transport canonical H3 experiment harness."""

import json
import shlex
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from benchmarks.h3_witness_outage import FaultProxy, execute, run_condition
from casf.witness import Witness


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


@pytest.mark.parametrize("condition, recovery_delay", [("healthy", 0), ("outage", 0),
                                                       ("outage", 0.3)])
def test_one_real_run_exercises_verification_recovery_and_receipts(
        tmp_path: Path, monkeypatch, condition: str, recovery_delay: float):
    submit = Witness._submit
    delayed = []

    def delayed_submit(self, log_id, checkpoint, records):
        if checkpoint["body"]["index"] == 2:
            delayed.append(checkpoint["checkpoint_hash"])
            time.sleep(recovery_delay)
        return submit(self, log_id, checkpoint, records)

    monkeypatch.setattr(Witness, "_submit", delayed_submit)
    config = {
        "events_per_run": 32,
        "batch_size": 8,
        "event_target_bytes": 256,
        "interarrival_seconds": 0.001,
        # The proxy enforces the outage independently of client timeouts.
        # Allow normal scheduler/crypto latency on shared CI runners.
        "query_timeout_seconds": 2.0,
        "submission_timeout_seconds": 2.0,
        "outage_seconds": 0.2,
        "recovery_observation_deadline_seconds": 10.0,
    }
    row = run_condition(tmp_path, 71234, condition, config, 0)
    assert row["status"] == "complete", row.get("traceback")
    assert len(delayed) == 1
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


def test_incomplete_experiment_preserves_evidence_and_returns_failure(tmp_path, monkeypatch):
    from benchmarks import h3_witness_outage as h3

    manifest = tmp_path / "manifest with spaces.json"
    config = json.loads((h3.ROOT / "benchmarks/h3-witness-outage.v1.json").read_text())
    config.update({
        "experiment": "h3-failed-runs", "seeds": [7],
        "run_order": [{"configuration": c, "seed": 7} for c in ("healthy", "outage")],
    })
    manifest.write_text(json.dumps(config))

    def failed_run(output, seed, condition, config, index):
        return {"run_index": index, "seed": seed, "configuration": condition,
                "status": "incomplete", "error": "simulated transport failure"}

    monkeypatch.setattr(h3, "run_condition", failed_run)
    output = tmp_path / "new results"
    with pytest.raises(SystemExit, match="incomplete experiment"):
        execute(manifest, output)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["incomplete_runs"] == 2
    assert summary["complete_runs"] == 0
    assert len(list(output.glob("run-??.json"))) == 2
    assert (output / "SHA256SUMS.txt").is_file()
    environment = json.loads((output / "environment.json").read_text())
    command = shlex.split(environment["exact_command"])
    assert command[-4:] == ["--manifest", str(manifest), "--output", str(output)]
    assert environment["exact_command"] in (output / "report.md").read_text()
