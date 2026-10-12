"""Benchmark runner (SPEC §22).

Each configuration run starts from a fresh database pair, discards a
warmup, then measures append latency per record, witness round trips
per checkpoint, and one final full verification. Every run writes its
raw measurements to its own JSON file with the environment pinned, so
the procedure can be rerun and compared (T19).
"""

import contextlib
import http.client
import json
import platform
import sqlite3
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cryptography

from benchmarks import workload
from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.verifier import Mode, TrustPins, verify
from casf.witness import Witness
from casf.witness.http import WitnessService, make_server
from casf.writer import Writer

TOKEN = "bench-witness-token"  # synthetic credential, never a real one


def _authority_keys() -> dict:
    auth_pub = crypto.public_key_raw(workload.seeded_key("authority"))
    return {crypto.key_id(auth_pub): auth_pub}


def _environment() -> dict:
    try:
        commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "cryptography": cryptography.__version__,
        "commit": commit,
    }


def _manifest():
    auth = workload.seeded_key("authority")
    log_pub = crypto.public_key_raw(workload.seeded_key("log"))
    wit_pub = crypto.public_key_raw(workload.seeded_key("witness"))
    auth_pub = crypto.public_key_raw(auth)
    body = {
        "version": 1, "type": "manifest", "log_id": workload.LOG_ID,
        "issuer_id": crypto.key_id(auth_pub),
        "log_key_id": crypto.key_id(log_pub),
        "log_public_key": crypto.b64url_encode(log_pub),
        "witness_id": crypto.key_id(wit_pub),
        "witness_public_key": crypto.b64url_encode(wit_pub),
        "created_at": workload.TS, "predecessor": None,
    }
    return {
        "body": body,
        "manifest_hash": crypto.digest_manifest(body),
        "signature": crypto.sign_manifest(auth, body),
    }


def _checkpoint_cycle(writer, submit, witness_lat):
    """Create, submit, and store one checkpoint; returns its count."""
    writer.create_checkpoint(workload.LOG_ID)
    pending = writer.pending_checkpoint(workload.LOG_ID)
    if pending is None:  # pragma: no cover - create made it pending
        raise RuntimeError("pending checkpoint missing")
    envelope, from_seq, to_seq = pending
    records = [env for seq, env in enumerate(
                   writer.records(workload.LOG_ID), start=1)
               if from_seq <= seq <= to_seq]
    start = time.perf_counter_ns()
    receipt = submit(envelope, records)
    witness_lat.append(time.perf_counter_ns() - start)
    writer.record_receipt(workload.LOG_ID, receipt)
    body = envelope["body"]
    return int(body["count"])


def _http_submit(port: int):
    """Checkpoint submission over loopback HTTP (SPEC §13 wire path)."""
    def submit(envelope: dict, records: list) -> dict:
        request = json.dumps(
            {"checkpoint": envelope, "records": records}).encode()
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        try:
            conn.request(
                "POST", f"/v1/logs/{workload.LOG_ID}/checkpoints",
                body=request,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {TOKEN}"})
            resp = conn.getresponse()
            payload = resp.read()
            status = resp.status
        finally:
            conn.close()
        data = json.loads(payload)
        if status not in (200, 201) or not isinstance(data, dict) \
                or not isinstance(data.get("receipt"), dict):
            raise RuntimeError(f"witness rejected the submission: {status}")
        return data["receipt"]
    return submit


class _DelayProxy:
    """Loopback proxy that injects a controlled round trip delay.

    The proxy sleeps half the delay before forwarding and half before
    answering, so witness processing time stays inside the measured
    round trip, matching a real network path (SPEC §22).
    """

    def __init__(self, target_port: int, delay_ms: float) -> None:
        half = delay_ms / 2000.0

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: object) -> None:
                pass

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers["Content-Length"]))
                time.sleep(half)
                conn = http.client.HTTPConnection(
                    "127.0.0.1", target_port, timeout=120)
                try:
                    conn.request(
                        "POST", self.path, body=body,
                        headers={"Content-Type": "application/json",
                                 "Authorization":
                                     self.headers.get("Authorization", "")})
                    resp = conn.getresponse()
                    payload = resp.read()
                    status = resp.status
                finally:
                    conn.close()
                time.sleep(half)
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

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@contextlib.contextmanager
def _witness_stack(root: Path, cfg: dict):
    """Yield (submit, register, witness_db_path) for the transport.

    "local" calls the witness in process; "http" drives the real HTTP
    service over loopback, optionally behind the delay proxy.
    """
    mode = str(cfg.get("witness", "local"))
    delay = float(cfg.get("witness_delay_ms", 0))
    if delay < 0:
        raise ValueError("witness_delay_ms must be zero or positive")
    if mode == "local":
        witness = Witness(root / "witness.db", workload.seeded_key("witness"),
                          authority_keys=_authority_keys())
        try:
            yield (lambda env, recs: witness.submit(
                       workload.LOG_ID, env, recs),
                   witness.register_log, root / "witness.db")
        finally:
            witness.close()
    elif mode == "http":
        service = WitnessService(root / "witness.db",
                                 workload.seeded_key("witness"),
                                 token=TOKEN,
                                 authority_keys=_authority_keys())
        server = make_server(service, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        proxy = (_DelayProxy(int(server.server_address[1]), delay)
                 if delay else None)
        port = proxy.port if proxy else int(server.server_address[1])
        try:
            yield (_http_submit(port), service.witness.register_log,
                   root / "witness.db")
        finally:
            if proxy:
                proxy.close()
            server.shutdown()
            server.server_close()
            service.close()
    else:
        raise ValueError(f"unknown witness mode {mode!r}")


def _run_once(cfg: dict, seed: int, run_index: int) -> dict:
    records = int(cfg["records"])
    batch = int(cfg["checkpoint_batch"])
    target = int(cfg["target_bytes"])
    delay_ms = float(cfg.get("witness_delay_ms", 0))
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        writer = Writer(root / "bench.db", workload.seeded_key("log"))
        try:
            with _witness_stack(root, cfg) as (
                    submit, register, witness_db):
                manifest = _manifest()
                writer.create_log(manifest)
                register(manifest)
                witness_lat: list[int] = []
                witnessed_through = 0
                checkpoints = 0

                warmup = int(cfg.get("warmup", 0))
                if warmup:
                    for event in workload.generate(seed + 1, warmup,
                                                   target):
                        writer.append(workload.LOG_ID, **event)
                    # Drain the warmup so measured checkpoints start clean.
                    witnessed_through = _checkpoint_cycle(
                        writer, submit, witness_lat)
                    checkpoints += 1
                    witness_lat.clear()  # warmup round trip is unmeasured

                appended: list[dict] = []
                latency: list[int] = []
                for i, event in enumerate(
                        workload.generate(seed, records, target), start=1):
                    start = time.perf_counter_ns()
                    appended.append(writer.append(workload.LOG_ID, **event))
                    latency.append(time.perf_counter_ns() - start)
                    if i % batch == 0:
                        witnessed_through = _checkpoint_cycle(
                            writer, submit, witness_lat)
                        checkpoints += 1
                if records % batch:
                    witnessed_through = _checkpoint_cycle(
                        writer, submit, witness_lat)
                    checkpoints += 1

                start = time.perf_counter()
                envelope = writer.manifest_envelope(workload.LOG_ID)
                auth_pub = crypto.public_key_raw(
                    workload.seeded_key("authority"))
                wit_pub = crypto.public_key_raw(
                    workload.seeded_key("witness"))
                pins = TrustPins(
                    authority_keys={crypto.key_id(auth_pub): auth_pub},
                    witness_keys={crypto.key_id(wit_pub): wit_pub},
                    log_id=workload.LOG_ID,
                    manifest_hash=envelope["manifest_hash"])
                report = verify(envelope, writer.records(workload.LOG_ID),
                                pins, mode=Mode.INTEGRITY)
                verify_seconds = time.perf_counter() - start

                return {
                    "config": {
                        "name": cfg["name"], "seed": seed, "run": run_index,
                        "records": records, "target_bytes": target,
                        "checkpoint_batch": batch, "warmup": warmup,
                        "witness": cfg.get("witness", "local"),
                        "witness_delay_ms": delay_ms,
                    },
                    "append_latency_ns": latency,
                    "witness_latency_ns": witness_lat,
                    "verify_seconds": verify_seconds,
                    "verify_result": str(report.result),
                    "db_bytes": (root / "bench.db").stat().st_size,
                    "witness_bytes": witness_db.stat().st_size,
                    "total_record_bytes": sum(
                        len(canonicalize(env)) for env in appended),
                    "witnessed_through": witnessed_through,
                    "checkpoints_accepted": checkpoints,
                    "environment": _environment(),
                }
        finally:
            writer.close()


def _metrics(row: dict) -> dict:
    latency = sorted(row["append_latency_ns"])
    p50 = latency[len(latency) // 2] / 1e6 if latency else 0.0
    witness = sorted(row["witness_latency_ns"])
    witness_p50 = witness[len(witness) // 2] / 1e6 if witness else 0.0
    seconds = sum(row["append_latency_ns"]) / 1e9
    return {
        "append_p50_ms": p50,
        "records_per_second": (row["config"]["records"] / seconds
                               if seconds else 0.0),
        "witness_p50_ms": witness_p50,
        "verify_seconds": row["verify_seconds"],
    }


def run_config(cfg: dict, out_dir: Path) -> dict:
    """Run one configuration for its seeds and write raw JSON rows."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in cfg["seeds"]]
    runs = int(cfg["runs"])
    last: dict = {}
    metrics: list[dict] = []
    files: list[str] = []
    for i in range(runs):
        row = _run_once(cfg, seeds[i % len(seeds)], i)
        path = out / f"{cfg['name']}-run-{i}.json"
        path.write_text(json.dumps(row, indent=2))
        files.append(path.name)
        metrics.append(_metrics(row))
        last = row
    return {
        "name": cfg["name"],
        "runs": runs,
        "records_per_run": int(cfg["records"]),
        "witnessed_through": last["witnessed_through"],
        "checkpoints_accepted": last["checkpoints_accepted"],
        "db_bytes": last["db_bytes"],
        "witness_bytes": last["witness_bytes"],
        "total_record_bytes": last["total_record_bytes"],
        "run_metrics": metrics,
        "run_files": files,
    }
