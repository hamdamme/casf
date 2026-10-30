"""Controlled loopback transport outage experiment for canonical H3.

This research harness drives the real writer, witness HTTP service, and CLI
verifier. It does not change CASF application behavior. Every invocation
creates a new output directory and refuses to overwrite existing evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import platform
import random
import shutil
import socket
import sqlite3
import statistics
import subprocess
import threading
import time
import traceback
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import cryptography

from benchmarks import workload
from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.cli import TOKEN_ENV
from casf.cli import main as cli_main
from casf.errors import CasfError
from casf.lifecycle import sign_status
from casf.witness.http import WitnessService, make_server
from casf.writer import Writer

TOKEN = "synthetic-h3-loopback-token"
ROOT = Path(__file__).resolve().parents[1]


class FaultProxy:
    """HTTP forward proxy with a deterministic accept-and-drop fault gate."""

    def __init__(self, target_port: int) -> None:
        self.target_port = target_port
        self._blocked = threading.Event()
        self._lock = threading.Lock()
        self._blocked_requests = 0
        self._forwarded_requests = 0

        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args: object) -> None:
                pass

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                was_blocked = owner._blocked.is_set()
                if was_blocked:
                    with owner._lock:
                        owner._blocked_requests += 1
                    # The request is deliberately never sent upstream. A
                    # connection close represents the predeclared reset/drop
                    # fault. The gate snapshot prevents late forwarding after
                    # recovery has started.
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                with owner._lock:
                    owner._forwarded_requests += 1
                conn = http.client.HTTPConnection(
                    "127.0.0.1", owner.target_port, timeout=5.0)
                try:
                    conn.request(
                        "POST", self.path, body=body,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": self.headers.get(
                                "Authorization", ""),
                        })
                    response = conn.getresponse()
                    payload = response.read()
                    status = response.status
                finally:
                    conn.close()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.port = int(self._server.server_address[1])
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def blocked_requests(self) -> int:
        with self._lock:
            return self._blocked_requests

    @property
    def forwarded_requests(self) -> int:
        with self._lock:
            return self._forwarded_requests

    def block(self) -> int:
        self._blocked.set()
        return time.monotonic_ns()

    def restore(self) -> int:
        stamp = time.monotonic_ns()
        self._blocked.clear()
        return stamp

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


def _keys(seed: int) -> tuple[Any, Any, Any]:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    def key(role: str) -> Any:
        raw = hashlib.sha256(f"casf-h3-{seed}-{role}".encode()).digest()
        return Ed25519PrivateKey.from_private_bytes(raw)
    return key("authority"), key("log"), key("witness")


def _manifest(log_id: str, seed: int) -> dict[str, Any]:
    authority, log_key, witness_key = _keys(seed)
    authority_pub = crypto.public_key_raw(authority)
    log_pub = crypto.public_key_raw(log_key)
    witness_pub = crypto.public_key_raw(witness_key)
    body = {
        "version": 1, "type": "manifest", "log_id": log_id,
        "issuer_id": crypto.key_id(authority_pub),
        "log_key_id": crypto.key_id(log_pub),
        "log_public_key": crypto.b64url_encode(log_pub),
        "witness_id": crypto.key_id(witness_pub),
        "witness_public_key": crypto.b64url_encode(witness_pub),
        "created_at": workload.TS, "predecessor": None,
    }
    return {"body": body, "manifest_hash": crypto.digest_manifest(body),
            "signature": crypto.sign_manifest(authority, body)}


def _read_counts(db_path: Path, witness: bool = False) -> tuple[int, int]:
    table = "w_state" if witness else "heads"
    count_col = "count"
    index_col = "checkpoint_index" if witness else "count"
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
        row = db.execute(
            f"SELECT {count_col}, {index_col} FROM {table}").fetchone()
    if row is None:
        return 0, 0
    return int(row[0]), int(row[1])


def _save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def _run_cli(bundle: Path, trust: Path, state: Path, mode: str,
             initialize: bool) -> dict[str, Any]:
    argv = ["verify", str(bundle), "--state", str(state), "--trust",
            str(trust), "--mode", mode, "--json"]
    if initialize:
        argv.append("--initialize-state")
    start = time.monotonic_ns()
    from contextlib import redirect_stderr, redirect_stdout
    from io import StringIO
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = cli_main(argv)
    end = time.monotonic_ns()
    out = stdout.getvalue()
    err = stderr.getvalue()
    try:
        report = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        report = None
    return {
        "argv": ["casf", *argv], "started_monotonic_ns": start,
        "ended_monotonic_ns": end, "elapsed_ns": end - start,
        "exit_code": code, "stdout": out, "stderr": err,
        "report": report,
    }


def _record_event(writer: Writer, log_id: str, event: dict[str, Any],
                  schedule_delay: float, scheduled_start: float) -> dict[str, Any]:
    target = scheduled_start + schedule_delay
    remaining = target - time.monotonic()
    if remaining > 0:
        time.sleep(remaining)
    start = time.monotonic_ns()
    envelope = writer.append(log_id, **event)
    end = time.monotonic_ns()
    return {"seq": envelope["body"]["seq"], "event_id": event["event_id"],
            "scheduled_offset_seconds": schedule_delay,
            "commit_monotonic_ns": end, "append_elapsed_ns": end - start}


def _checkpoint(writer: Writer, log_id: str, url: str, timeout: float,
                event_rows: list[dict[str, Any]], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    created_at = time.monotonic_ns()
    env = writer.create_checkpoint(log_id)
    pending = writer.pending_checkpoint(log_id)
    if pending is None:
        raise RuntimeError("checkpoint creation did not produce pending state")
    pending_bytes = canonicalize(pending[0])
    body = env["body"]
    entry: dict[str, Any] = {
        "checkpoint_hash": env["checkpoint_hash"],
        "index": body["index"], "from_seq": pending[1], "to_seq": pending[2],
        "created_monotonic_ns": created_at,
        "pending_checkpoint_sha256": hashlib.sha256(pending_bytes).hexdigest(),
    }
    attempt_start = time.monotonic_ns()
    try:
        receipt = writer.submit_pending(log_id, url, TOKEN, timeout=timeout)
        accepted = time.monotonic_ns()
        entry.update({"receipt_persisted_monotonic_ns": accepted,
                      "receipt_hash": receipt["receipt_hash"],
                      "result": "accepted"})
        for row in event_rows:
            if pending[1] <= row["seq"] <= pending[2]:
                row["witnessed_monotonic_ns"] = accepted
                row["commit_to_witnessed_ns"] = accepted - row["commit_monotonic_ns"]
        attempts.append({"checkpoint_hash": env["checkpoint_hash"],
                         "start_monotonic_ns": attempt_start,
                         "end_monotonic_ns": accepted, "result": "accepted"})
    except CasfError as exc:
        failed = time.monotonic_ns()
        pending_after = writer.pending_checkpoint(log_id)
        same_bytes = (pending_after is not None and
                      canonicalize(pending_after[0]) == pending_bytes)
        entry.update({"result": "failed_pending", "error": str(exc),
                      "failure_monotonic_ns": failed,
                      "same_pending_bytes_after_failure": same_bytes})
        attempts.append({"checkpoint_hash": env["checkpoint_hash"],
                         "start_monotonic_ns": attempt_start,
                         "end_monotonic_ns": failed, "result": "failed",
                         "error": str(exc)})
    return entry


def _make_bundle(root: Path, writer: Writer, log_id: str,
                 manifest: dict[str, Any], name: str,
                 query_timeout: float, authority: Any) -> tuple[Path, Path]:
    bundle = root / name
    writer.export_bundle(log_id, bundle)
    status = sign_status(authority, serial=1,
                         manifest_hash=manifest["manifest_hash"],
                         status="active", issued_at=workload.TS, reason="")
    (bundle / "status.jsonl").write_bytes(canonicalize(status) + b"\n")
    auth_pub = crypto.public_key_raw(authority)
    body = manifest["body"]
    trust = root / "trust.json"
    _save_json(trust, {
        "version": 1,
        "authorities": {crypto.key_id(auth_pub): crypto.b64url_encode(auth_pub)},
        "logs": {log_id: {
            "manifest_hash": manifest["manifest_hash"],
            "witness_id": body["witness_id"],
            "witness_url": "",
            "minimum_status_serial": 1,
        }},
        "policy": {"mode": "integrity", "allow_unwitnessed": False,
                   "query_timeout_seconds": query_timeout,
                   "max_chain_steps": 10000},
    })
    return bundle, trust


def run_condition(root: Path, seed: int, condition: str, config: dict[str, Any],
                  run_order: int) -> dict[str, Any]:
    auth, log_key, witness_key = _keys(seed)
    log_id = workload.run_log_id(seed, 1)
    manifest = _manifest(log_id, seed)
    auth_pub = crypto.public_key_raw(auth)
    events = workload.generate(seed, config["events_per_run"],
                               config["event_target_bytes"])
    run_root = root / f"run-{run_order:02d}-{condition}-seed-{seed}"
    run_root.mkdir()
    run_root.chmod(0o700)
    writer_db = run_root / "writer.sqlite"
    witness_db = run_root / "witness.sqlite"
    writer = Writer(writer_db, log_key)
    writer.create_log(manifest)
    service = WitnessService(
        witness_db, witness_key, token=TOKEN,
        authority_keys={crypto.key_id(auth_pub): auth_pub})
    service.witness.register_log(manifest)
    witness_server = make_server(service, "127.0.0.1", 0)
    server_thread = threading.Thread(target=witness_server.serve_forever,
                                     daemon=True)
    server_thread.start()
    time.sleep(0.05)  # let the real ASGI listener enter its serving loop
    proxy = FaultProxy(int(witness_server.server_address[1]))
    url = f"http://127.0.0.1:{proxy.port}"
    start_clock = time.monotonic()
    rows: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    verifications: dict[str, Any] = {}
    outage: dict[str, Any] | None = None
    last_witnessed_count = 0
    max_backlog = 0
    try:
        # Warmup consists of workload/key preparation above; no measured
        # database operations are discarded or hidden.
        for idx in range(16):
            row = _record_event(writer, log_id, events[idx],
                                idx * config["interarrival_seconds"], start_clock)
            rows.append(row)
            row["witnessed_count_after_commit"] = last_witnessed_count
            row["unwitnessed_backlog_after_commit"] = row["seq"] - last_witnessed_count
            max_backlog = max(max_backlog, row["unwitnessed_backlog_after_commit"])
            if row["seq"] in (8, 16):
                checkpoints.append(_checkpoint(
                    writer, log_id, url, config["submission_timeout_seconds"],
                    rows, attempts))
                last_witnessed_count = row["seq"]
        if any(cp["result"] != "accepted" for cp in checkpoints):
            raise RuntimeError("baseline checkpoint submission failed")
        bundle, trust = _make_bundle(run_root, writer, log_id, manifest,
                                     "baseline-bundle",
                                     config["query_timeout_seconds"], auth)
        trust_obj = json.loads(trust.read_text())
        trust_obj["logs"][log_id]["witness_url"] = url
        _save_json(trust, trust_obj)
        os.environ[TOKEN_ENV] = TOKEN
        verifications["healthy_baseline_online"] = _run_cli(
            bundle, trust, run_root / "state-baseline.json", "online", True)
        if verifications["healthy_baseline_online"]["exit_code"] != 0:
            raise RuntimeError("healthy online baseline did not pass")
        if condition == "outage":
            outage_start = proxy.block()
            outage = {"fault_mode": "proxy_drop_after_body_read",
                      "activated_monotonic_ns": outage_start,
                      "duration_seconds": config["outage_seconds"],
                      "blocked_requests_before": proxy.blocked_requests,
                      "forwarded_requests_before": proxy.forwarded_requests}
            # Attempt query of the already valid record-16 bundle entirely
            # inside the blocked interval, using a distinct verifier state.
            outage_query_start = time.monotonic_ns()
            verifications["online_during_outage"] = _run_cli(
                bundle, trust, run_root / "state-outage-online.json",
                "online", True)
            outage_query_end = time.monotonic_ns()
            if (outage_query_start <= outage_start
                    or outage_query_end <= outage_query_start
                    or proxy.blocked_requests < 1):
                raise RuntimeError("online query was not observed inside the active proxy fault")
            verifications["online_during_outage"]["query_window_within_outage"] = True
            verifications["online_during_outage"]["query_window_start_ns"] = outage_query_start
            verifications["online_during_outage"]["query_window_end_ns"] = outage_query_end
            online_report = verifications["online_during_outage"]["report"]
            if (verifications["online_during_outage"]["exit_code"] != 4
                    or not isinstance(online_report, dict)
                    or online_report.get("result") != "INCONCLUSIVE"
                    or "FRESHNESS_INCONCLUSIVE" not in online_report.get("diagnostic_codes", [])):
                raise RuntimeError("outage online verification had an unexpected outcome")
            witness_while_blocked = _read_counts(witness_db, witness=True)
            if witness_while_blocked != (16, 1):
                raise RuntimeError("witness state changed during blocked access")
            outage["witness_state_after_query"] = {
                "count": witness_while_blocked[0], "checkpoint_index": witness_while_blocked[1]}
            verifications["offline_during_outage"] = _run_cli(
                bundle, trust, run_root / "state-outage-offline.json",
                "integrity", True)
            if verifications["offline_during_outage"]["exit_code"] != 0:
                raise RuntimeError("offline integrity control failed during outage")

        for idx in range(16, config["events_per_run"]):
            row = _record_event(writer, log_id, events[idx],
                                idx * config["interarrival_seconds"], start_clock)
            rows.append(row)
            row["witnessed_count_after_commit"] = last_witnessed_count
            row["unwitnessed_backlog_after_commit"] = row["seq"] - last_witnessed_count
            max_backlog = max(max_backlog, row["unwitnessed_backlog_after_commit"])
            if row["seq"] == 24:
                checkpoints.append(_checkpoint(
                    writer, log_id, url, config["submission_timeout_seconds"],
                    rows, attempts))
                if condition == "healthy" and checkpoints[-1]["result"] != "accepted":
                    raise RuntimeError("healthy checkpoint 24 failed")
                if condition == "healthy":
                    last_witnessed_count = 24
                if condition == "outage" and checkpoints[-1]["result"] != "failed_pending":
                    raise RuntimeError("outage did not retain pending checkpoint 24")
                if condition == "outage":
                    if proxy.blocked_requests < 2:
                        raise RuntimeError("checkpoint submission did not hit the blocked proxy")
                    outage["witness_state_after_failed_submit"] = {
                        "count": _read_counts(witness_db, witness=True)[0],
                        "checkpoint_index": _read_counts(witness_db, witness=True)[1],
                    }
                    if outage["witness_state_after_failed_submit"] != {
                        "count": 16, "checkpoint_index": 1}:
                        raise RuntimeError("failed checkpoint changed durable witness state")
        if condition == "outage":
            # Keep the gate blocked for the complete predeclared interval,
            # including after the final local append.
            elapsed = (time.monotonic_ns() - outage["activated_monotonic_ns"]) / 1e9
            if elapsed < config["outage_seconds"]:
                time.sleep(config["outage_seconds"] - elapsed)
            recovery_start = proxy.restore()
            outage["restored_monotonic_ns"] = recovery_start
            outage["actual_duration_ns"] = recovery_start - outage["activated_monotonic_ns"]
            outage["blocked_requests_after"] = proxy.blocked_requests
            outage["forwarded_requests_after"] = proxy.forwarded_requests
            if outage["actual_duration_ns"] < int(config["outage_seconds"] * 1e9):
                raise RuntimeError("observed outage was shorter than predeclared duration")
            pending_before = writer.pending_checkpoint(log_id)
            if pending_before is None or pending_before[0]["checkpoint_hash"] != checkpoints[-1]["checkpoint_hash"]:
                raise RuntimeError("unexpected pending checkpoint at recovery")
            recovery_begin = time.monotonic_ns()
            receipt = writer.submit_pending(
                log_id, url, TOKEN,
                timeout=config["submission_timeout_seconds"])
            recovered = time.monotonic_ns()
            checkpoints[-1].update({
                "recovered_result": "accepted",
                "receipt_persisted_monotonic_ns": recovered,
                "receipt_hash": receipt["receipt_hash"],
                "recovery_elapsed_ns": recovered - recovery_start,
                "same_checkpoint_hash_retried": receipt["body"]["checkpoint_hash"] == pending_before[0]["checkpoint_hash"],
                "recovery_deadline_monotonic_ns": recovery_start + int(
                    config["recovery_observation_deadline_seconds"] * 1e9),
            })
            if recovered > checkpoints[-1]["recovery_deadline_monotonic_ns"]:
                checkpoints[-1]["deadline_censored"] = True
                raise RuntimeError("recovery receipt arrived after the predeclared deadline")
            for event_row in rows:
                if 17 <= event_row["seq"] <= 24:
                    event_row["witnessed_monotonic_ns"] = recovered
                    event_row["commit_to_witnessed_ns"] = recovered - event_row["commit_monotonic_ns"]
            attempts.append({"checkpoint_hash": checkpoints[-1]["checkpoint_hash"],
                             "start_monotonic_ns": recovery_begin,
                             "end_monotonic_ns": recovered,
                             "result": "recovered_same_pending"})
            last_witnessed_count = 24
            checkpoints.append(_checkpoint(
                writer, log_id, url, config["submission_timeout_seconds"],
                rows, attempts))
            if checkpoints[-1]["result"] != "accepted":
                raise RuntimeError("final checkpoint through 32 failed")
            last_witnessed_count = 32
        else:
            checkpoints.append(_checkpoint(
                writer, log_id, url, config["submission_timeout_seconds"],
                rows, attempts))
            if checkpoints[-1]["result"] != "accepted":
                raise RuntimeError("final checkpoint through 32 failed")
            last_witnessed_count = 32
        final_bundle, final_trust = _make_bundle(
            run_root, writer, log_id, manifest, "final-bundle",
            config["query_timeout_seconds"], auth)
        final_trust_obj = json.loads(final_trust.read_text())
        final_trust_obj["logs"][log_id]["witness_url"] = url
        _save_json(final_trust, final_trust_obj)
        verifications["final_online"] = _run_cli(
            final_bundle, final_trust, run_root / "state-final-online.json",
            "online", True)
        if verifications["final_online"]["exit_code"] != 0:
            raise RuntimeError("final online verification did not pass")
        writer_count, _ = _read_counts(writer_db)
        witness_count, witness_index = _read_counts(witness_db, witness=True)
        if writer_count != 32 or witness_count != 32 or witness_index != 3:
            raise RuntimeError("writer and witness final state are inconsistent")
        for row in rows:
            row.setdefault("witnessed_monotonic_ns", None)
            row.setdefault("commit_to_witnessed_ns", None)
        return {
            "run_index": run_order, "configuration": condition, "seed": seed,
            "log_id": log_id, "status": "complete",
            "event_count": len(rows), "batch_size": config["batch_size"],
            "event_request_sizes_bytes": [len(canonicalize(event)) for event in events],
            "events": rows, "checkpoints": checkpoints,
            "submission_attempts": attempts, "verifications": verifications,
            "outage": outage,
            "proxy_counters": {"blocked_requests": proxy.blocked_requests,
                                "forwarded_requests": proxy.forwarded_requests},
            "final_writer_count": writer_count,
            "final_witness_count": witness_count,
            "final_witness_checkpoint_index": witness_index,
            "max_unwitnessed_backlog_records": max_backlog,
        }
    except Exception as exc:  # noqa: BLE001 - retain every failed run as evidence
        return {
            "run_index": run_order, "configuration": condition, "seed": seed,
            "log_id": log_id, "status": "incomplete", "error": str(exc),
            "traceback": traceback.format_exc(), "events": rows,
            "checkpoints": checkpoints, "submission_attempts": attempts,
            "verifications": verifications, "outage": outage,
            "proxy_counters": {"blocked_requests": proxy.blocked_requests,
                                "forwarded_requests": proxy.forwarded_requests},
        }
    finally:
        proxy.close()
        witness_server.shutdown()
        witness_server.server_close()
        service.close()
        writer.close()


def _paired_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    healthy = {r["seed"]: r for r in rows
               if r["status"] == "complete" and r["configuration"] == "healthy"}
    outage = {r["seed"]: r for r in rows
              if r["status"] == "complete" and r["configuration"] == "outage"}
    paired: list[int] = []
    healthy_latency: list[int] = []
    outage_latency: list[int] = []
    for seed in sorted(set(healthy) & set(outage)):
        # Completion latency for the record 24 checkpoint, paired by workload.
        hcp = next(cp for cp in healthy[seed]["checkpoints"] if cp["to_seq"] == 24)
        ocp = next(cp for cp in outage[seed]["checkpoints"] if cp["to_seq"] == 24)
        h_done = hcp["receipt_persisted_monotonic_ns"]
        o_done = ocp.get("receipt_persisted_monotonic_ns")
        if o_done is None:
            continue
        h_commit = next(e["commit_monotonic_ns"] for e in healthy[seed]["events"]
                        if e["seq"] == 24)
        o_commit = next(e["commit_monotonic_ns"] for e in outage[seed]["events"]
                        if e["seq"] == 24)
        h_latency, o_latency = h_done - h_commit, o_done - o_commit
        healthy_latency.append(h_latency)
        outage_latency.append(o_latency)
        paired.append(o_latency - h_latency)
    def bootstrap(values: list[int], rounds: int = 10000) -> dict[str, Any]:
        if not values:
            return {"n": 0, "median_ns": None, "mean_ns": None,
                    "bootstrap_95_percentile_interval_ns": None}
        rng = random.Random(304991)
        means = sorted(statistics.mean(rng.choices(values, k=len(values)))
                       for _ in range(rounds))
        return {"n": len(values), "median_ns": statistics.median(values),
                "mean_ns": statistics.mean(values),
                "bootstrap_95_percentile_interval_ns": [
                    means[int(rounds * 0.025)], means[int(rounds * 0.975)]]}
    outage_rows = [r for r in rows if r["status"] == "complete"
                   and r["configuration"] == "outage"]
    outage_attempts = [a for r in outage_rows
                       for a in r["submission_attempts"]]
    online_results = [r["verifications"]["online_during_outage"]
                      for r in outage_rows]
    offline_results = [r["verifications"]["offline_during_outage"]
                       for r in outage_rows]
    online_inconclusive = sum(
        result.get("report", {}).get("result") == "INCONCLUSIVE"
        and "FRESHNESS_INCONCLUSIVE" in result.get("report", {}).get(
            "diagnostic_codes", []) for result in online_results)
    offline_pass = sum(result.get("report", {}).get("result") == "PASS"
                       and result.get("exit_code") == 0
                       for result in offline_results)
    return {
        "record24_commit_to_persisted_receipt_latency_ns": {
            "healthy_run_level": bootstrap(healthy_latency),
            "outage_run_level": bootstrap(outage_latency),
            "paired_outage_minus_healthy_run_level_difference": bootstrap(paired),
        },
        "h3b_freshness_and_offline_validity": {
            "outage_runs": len(outage_rows),
            "online_inconclusive_with_freshness_diagnostic": online_inconclusive,
            "offline_integrity_pass": offline_pass,
            "healthy_online_baseline_pass": sum(
                r["verifications"]["healthy_baseline_online"].get("exit_code") == 0
                for r in outage_rows),
            "final_online_pass": sum(
                r["verifications"]["final_online"].get("exit_code") == 0
                for r in outage_rows),
        },
        "backlog_and_recovery": {
            "outage_max_unwitnessed_backlog_records": [
                r["max_unwitnessed_backlog_records"] for r in outage_rows],
            "outage_blocked_request_counts": [
                r["proxy_counters"]["blocked_requests"] for r in outage_rows],
            "outage_recovery_elapsed_ns": [
                next(cp["recovery_elapsed_ns"] for cp in r["checkpoints"]
                     if cp.get("recovered_result") == "accepted")
                for r in outage_rows],
            "failed_outage_submission_attempts": sum(
                a["result"] == "failed" for a in outage_attempts),
            "explicit_same_pending_checkpoint_retries": sum(
                a["result"] == "recovered_same_pending" for a in outage_attempts),
            "automatic_retry_attempts": 0,
        },
    }


def _write_report(path: Path, manifest: dict[str, Any], rows: list[dict[str, Any]],
                  summary: dict[str, Any], environment: dict[str, Any]) -> None:
    if "pilot" in manifest.get("experiment", ""):
        outage_row = next((r for r in rows if r["configuration"] == "outage"), {})
        healthy_row = next((r for r in rows if r["configuration"] == "healthy"), {})
        online = outage_row.get("verifications", {}).get(
            "online_during_outage", {})
        offline = outage_row.get("verifications", {}).get(
            "offline_during_outage", {})
        pending = next((c for c in outage_row.get("checkpoints", [])
                        if c.get("to_seq") == 24), {})
        report = f"""# Canonical H3 feasibility pilot

This is one matched synthetic pilot pair using the separate pilot manifest. It is excluded from measured results and provides no inferential estimate.

- Healthy run: {healthy_row.get('status', 'missing')}; baseline and final online checks: {healthy_row.get('verifications', {}).get('healthy_baseline_online', {}).get('report')} and {healthy_row.get('verifications', {}).get('final_online', {}).get('report')}.
- Outage run: {outage_row.get('status', 'missing')}; online freshness result: {online.get('report')}, exit {online.get('exit_code')}; offline integrity result: {offline.get('report')}, exit {offline.get('exit_code')}.
- Fault delivery: {outage_row.get('proxy_counters')}; witness state during the block: {outage_row.get('outage', {}).get('witness_state_after_failed_submit')}.
- Checkpoint through record 24: initial result {pending.get('result')}; same pending bytes after failure: {pending.get('same_pending_bytes_after_failure')}; same checkpoint accepted after restoration: {pending.get('same_checkpoint_hash_retried')}.
- Maximum pending suffix: {outage_row.get('max_unwitnessed_backlog_records')} records.

These outcomes established that the frozen timeout, outage duration, and recovery deadline were feasible for the measured run. They are not included in the measured analysis.

Reproduction command: `.venv/bin/python -m benchmarks.h3_witness_outage --manifest benchmarks/h3-witness-outage-pilot.v1.json --output benchmarks/results/h3-witness-outage-pilot-v1`

Run JSON preserves full CLI output, diagnostics, exit codes, monotonic timestamps, and errors. Environment provenance is in `environment.json`; hashes are in `SHA256SUMS.txt`.
"""
        path.write_text(report)
        return
    analysis = summary["paired_analysis"]
    latency = analysis["record24_commit_to_persisted_receipt_latency_ns"]
    delta = latency["paired_outage_minus_healthy_run_level_difference"]
    h3b = analysis["h3b_freshness_and_offline_validity"]
    append_by_run: dict[str, list[int]] = {"healthy": [], "outage": []}
    for row in rows:
        if row["status"] != "complete":
            continue
        append_by_run[row["configuration"]].append(
            int(statistics.median(e["append_elapsed_ns"] for e in row["events"])))
    outage_runs = [r for r in rows if r["configuration"] == "outage"
                   and r["status"] == "complete"]
    recovery = analysis["backlog_and_recovery"]["outage_recovery_elapsed_ns"]
    failed_attempts = analysis["backlog_and_recovery"][
        "failed_outage_submission_attempts"]
    explicit_retries = analysis["backlog_and_recovery"][
        "explicit_same_pending_checkpoint_retries"]
    report = f"""# Canonical H3 controlled witness outage experiment

## Question and scope

Canonical H3 in CASF SPEC §22 is: “Network outages increase time to witnessed completion and may prevent a freshness conclusion.” This report tests H3a (witnessed completion time) and H3b (online freshness during unreachability) separately. It does not test the historical protocol H3 about linear verification cost.

The fault was one controlled loopback HTTP mode. The proxy accepted the connection, read the complete request body, and closed the connection without forwarding it while blocked. The same proxy path forwarded healthy requests. The witness process and its durable SQLite state remained running. This does not model a separate host or generalize to every network failure.

## Frozen method

The measured manifest is `benchmarks/h3-witness-outage.v1.json`; it specifies ten matched seeds, ten independent fresh writer, witness, and verifier contexts per condition, 32 synthetic events, a fixed 256 byte target event request, a 10 millisecond intended arrival interval, checkpoint batches of eight, a 0.5 second client budget, no automatic online retries, a three second outage, and a ten second recovery deadline. The randomized order was seeded with {manifest['run_order_seed']} and is recorded in `run-order.json`. Each run generates keys deterministically from its seed; healthy and outage members of a pair use the same seed and event requests.

Warmup was a separately reported feasibility pilot. It is excluded from measured analysis. Database creation, key generation, and log registration were completed before timing. CASF protocol operations were not discarded as warmup. The outage configuration witnessed records 1–16 before the outage, attempted checkpoint 24 once while blocked, continued local appends through record 32, explicitly retried the identical pending checkpoint after restoration, then witnessed record 32. A separate state file was used for each CLI verification.

## Results

Measured configurations completed {summary['complete_runs']} of {summary['total_runs']} runs; {summary['incomplete_runs']} runs were incomplete and are retained in their per-run files. The H3a endpoint measure is record 24 commit to the writer’s durable persistence of a valid receipt for its covering checkpoint. This run-level measure is paired by workload seed; records are not treated as independent replications.

| Measure | Healthy | Outage |
| --- | ---: | ---: |
| Record 24 commit to persisted receipt, run-level median | {latency['healthy_run_level']['median_ns']} ns | {latency['outage_run_level']['median_ns']} ns |
| Run-level mean | {latency['healthy_run_level']['mean_ns']} ns | {latency['outage_run_level']['mean_ns']} ns |
| Descriptive median of per-run median append latency | {statistics.median(append_by_run['healthy']) if append_by_run['healthy'] else 'n/a'} ns | {statistics.median(append_by_run['outage']) if append_by_run['outage'] else 'n/a'} ns |

Paired outage minus healthy difference for the record 24 completion measure: n={delta['n']}, mean {delta['mean_ns']} ns, median {delta['median_ns']} ns, bootstrap 95% percentile interval {delta['bootstrap_95_percentile_interval_ns']} ns. The bootstrap resamples independent run pairs. This is evidence for H3a only within this configuration.

For H3b, {h3b['online_inconclusive_with_freshness_diagnostic']} of {h3b['outage_runs']} outage runs returned online `INCONCLUSIVE` with `FRESHNESS_INCONCLUSIVE` and exit status 4 for the already valid baseline bundle. Offline integrity verification passed in {h3b['offline_integrity_pass']} of those runs. The witness count remained 16 at checkpoint index 1 after both the online query and failed checkpoint submission. Baseline and final online verification passed in {h3b['healthy_online_baseline_pass']} and {h3b['final_online_pass']} outage runs respectively.

Maximum unwitnessed backlog in the outage runs was {max((r['max_unwitnessed_backlog_records'] for r in outage_runs), default='n/a')} records. It is an observed pending suffix, not observed data loss. Recovery duration from restoration until receipt persistence had run-level median {statistics.median(recovery) if recovery else 'n/a'} ns. Recovery was explicit: one manual call to the existing pending checkpoint submission API, followed by the next normal checkpoint submission. No built-in automatic retry worker is claimed.

There were {failed_attempts} checkpoint submission failures during outages and {explicit_retries} explicit same-checkpoint recovery submissions; automatic retry attempts: 0. Attempt level evidence remains in each raw run JSON.

## Interpretation

H3a: {('SUPPORTED within the tested scope' if delta['n'] >= 2 and delta['bootstrap_95_percentile_interval_ns'][0] > 0 else 'UNRESOLVED within the tested scope')}. The conclusion is limited to the measured paired loopback configuration and the completion measure above.

H3b: {('SUPPORTED within the tested scope' if h3b['outage_runs'] > 0 and h3b['online_inconclusive_with_freshness_diagnostic'] == h3b['outage_runs'] and h3b['offline_integrity_pass'] == h3b['outage_runs'] else 'PARTIALLY SUPPORTED or UNRESOLVED; see counts above')}. Online unreachability did not convert valid historical evidence into a corruption verdict.

## Reproduction and provenance

Command: `.venv/bin/python -m benchmarks.h3_witness_outage --manifest benchmarks/h3-witness-outage.v1.json --output benchmarks/results/h3-witness-outage-v1`

Environment and source status are recorded in `environment.json`. Raw per-run event timing, checkpoint attempts, pending byte digests, receipt persistence, proxy counters, witness snapshots, verification stdout, stderr, reports, exit codes, and incomplete run errors are stored as JSON in `run-*.json`. SHA-256 digests are listed in `SHA256SUMS.txt`.

The separate pilot is in `benchmarks/results/h3-witness-outage-pilot-v1/` and is not included in the measured result counts or statistical intervals.

## Limitations

This is a single-host loopback functional fault experiment with one accept-and-drop transport mode, ten seed pairs, short fixed synthetic workload, one checkpoint batch size, no retry loop, and explicit manual recovery. It does not establish performance across machines, availability under other failures, a maximum safe outage duration, production workload behavior, or the full configuration matrix proposed by SPEC §22. Historical fixed-delay results are not outage results. The historical research protocol H3 about linear verification cost is a separate label and is unchanged by this experiment.
"""
    path.write_text(report)


def _environment(manifest_path: Path, run_order: list[dict[str, Any]]) -> dict[str, Any]:
    def command(argv: list[str]) -> str:
        try:
            return subprocess.run(argv, capture_output=True, text=True,
                                  check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return "unavailable"
    cpu = platform.processor() or command(
        ["sysctl", "-n", "machdep.cpu.brand_string"])
    try:
        disk = shutil.disk_usage(ROOT)
        storage = {"total_bytes": disk.total, "used_bytes": disk.used,
                   "free_bytes": disk.free}
    except OSError:
        storage = None
    filesystem_type = command(["stat", "-f", "%T", str(ROOT)])
    try:
        status = subprocess.run(["git", "status", "--short", "--branch"],
                                cwd=ROOT, capture_output=True, text=True,
                                check=True).stdout
        commit = command(["git", "rev-parse", "HEAD"])
    except (OSError, subprocess.CalledProcessError):
        status, commit = "unavailable", "unavailable"
    lock = ROOT / "uv.lock"
    source_files = [
        "benchmarks/h3_witness_outage.py",
        "benchmarks/h3-witness-outage.v1.json",
        "benchmarks/workload.py",
        "tests/test_h3_witness_outage.py",
        "src/casf/writer/__init__.py",
        "src/casf/cli/__init__.py",
        "src/casf/online.py",
        "src/casf/verifier/__init__.py",
        "src/casf/witness/http.py",
        "src/casf/witness/server.py",
    ]
    try:
        diff_bytes = subprocess.run(
            ["git", "diff", "--binary", "HEAD"], cwd=ROOT,
            capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        diff_bytes = b""
    return {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "commit": commit, "git_status": status,
        "os": platform.platform(), "machine": platform.machine(),
        "cpu": cpu, "logical_cpu_count": os.cpu_count(),
        "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
        "cryptography": cryptography.__version__,
        "uv_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest()
        if lock.exists() else None,
        "tested_source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in source_files if (ROOT / name).is_file()},
        "tracked_worktree_diff_sha256": hashlib.sha256(diff_bytes).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "run_order": run_order,
        "filesystem_type": filesystem_type,
        "storage": storage,
        "memory": command(["sysctl", "-n", "hw.memsize"]),
        "exact_command": ".venv/bin/python -m benchmarks.h3_witness_outage --manifest <frozen-manifest> --output <new-directory>",
    }


def execute(manifest_path: Path, output: Path) -> None:
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing result directory: {output}")
    manifest = json.loads(manifest_path.read_text())
    config = manifest["configuration"]
    seeds = list(manifest["seeds"])
    order = list(manifest["run_order"])
    expected_order = {(condition, seed) for seed in seeds
                      for condition in ("healthy", "outage")}
    if len(order) != len(expected_order) or {
            (item.get("configuration"), item.get("seed")) for item in order
    } != expected_order:
        raise SystemExit("manifest run order must contain each healthy/outage seed pair exactly once")
    output.mkdir(parents=True)
    output.chmod(0o700)
    shutil.copyfile(manifest_path, output / "manifest.json")
    order_rows: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for i, item in enumerate(order):
        order_rows.append({"position": i, **item})
        row = run_condition(output, int(item["seed"]), item["configuration"],
                            config, i)
        results.append(row)
        _save_json(output / f"run-{i:02d}.json", row)
        print(f"{i + 1}/{len(order)} {item['configuration']} seed={item['seed']} "
              f"status={row['status']}", flush=True)
    _save_json(output / "run-order.json", order_rows)
    environment = _environment(manifest_path, order_rows)
    _save_json(output / "environment.json", environment)
    summary = {
        "experiment": manifest["experiment"], "status": "complete"
        if all(row["status"] == "complete" for row in results) else "incomplete",
        "total_runs": len(results),
        "complete_runs": sum(row["status"] == "complete" for row in results),
        "incomplete_runs": sum(row["status"] != "complete" for row in results),
        "h3a": "outage versus healthy witnessed-completion time; paired at run level",
        "h3b": "online freshness result during outage versus offline validity",
        "paired_analysis": _paired_summary(results),
        "results": [{"run_index": r["run_index"], "configuration": r["configuration"],
                     "seed": r["seed"], "status": r["status"],
                     "error": r.get("error")} for r in results],
    }
    _save_json(output / "summary.json", summary)
    _write_report(output / "report.md", manifest, results, summary, environment)
    checksum_lines = []
    for item in sorted(p for p in output.rglob("*") if p.is_file()
                       and p.name != "SHA256SUMS.txt"):
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        checksum_lines.append(f"{digest}  {item.relative_to(output)}")
    (output / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    execute(args.manifest, args.output)


if __name__ == "__main__":
    main()
