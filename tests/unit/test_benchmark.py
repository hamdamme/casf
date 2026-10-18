"""R12 / T19 (SPEC §22, §23): benchmark harness integrity.

The workload generator is deterministic under a fixed seed and
reports the actual minimum body size honestly instead of pretending
an impossible 256 byte target was met. The runner writes raw
measurements with the environment pinned, and rerunning the same
manifest reproduces the procedure (T19). Analysis uses run level
summaries with bootstrap intervals, never record level pooling.
"""

import json
import threading

import pytest

from benchmarks import analyze, runner, workload


def test_generator_deterministic_per_seed():
    a = workload.generate(seed=7, count=10, target_bytes=1024)
    b = workload.generate(seed=7, count=10, target_bytes=1024)
    c = workload.generate(seed=8, count=10, target_bytes=1024)
    assert a == b  # fixed seed list reproduces the workload
    assert a != c
    assert len(a) == 10
    for event in a:
        assert set(event) == {"event_id", "actor", "event_type",
                              "payload", "attributes"}


def test_generator_reports_honest_minimum():
    # 256 bytes cannot hold the fixed record fields (SPEC §22)
    events, minimum = workload.generate_with_minimum(seed=7, count=3,
                                                     target_bytes=256)
    assert minimum > 256  # actual minimum reported, never faked
    assert events  # workload still produced at the achievable size


def test_runner_smoke_produces_raw_rows(tmp_path):
    cfg = {
        "name": "smoke", "seeds": [7], "runs": 1, "warmup": 2,
        "records": 20, "target_bytes": 1024, "checkpoint_batch": 8,
        "witness": "local",
    }
    summary = runner.run_config(cfg, tmp_path / "out")
    raw = (tmp_path / "out" / "smoke-run-0.json").read_text()
    row = json.loads(raw)
    assert row["config"]["records"] == 20
    assert row["config"]["seed"] == 7
    assert len(row["append_latency_ns"]) == 20
    assert row["verify_seconds"] > 0
    assert row["db_bytes"] > 0 and row["witness_bytes"] > 0
    env = row["environment"]
    for key in ("os", "python", "sqlite", "cryptography", "commit"):
        assert key in env
    assert summary["runs"] == 1
    assert summary["records_per_run"] == 20


def test_runner_witness_consistency(tmp_path):
    cfg = {
        "name": "consistency", "seeds": [11], "runs": 1, "warmup": 0,
        "records": 10, "target_bytes": 512, "checkpoint_batch": 4,
        "witness": "local",
    }
    summary = runner.run_config(cfg, tmp_path / "out")
    # 10 records in batches of 4: 4 + 4 + 2, witnessed through 10
    assert summary["witnessed_through"] == 10
    assert summary["checkpoints_accepted"] == 3


def test_manifest_rerun_reproduces_procedure(tmp_path):
    """T19: the same manifest yields the same sizes and counts."""
    cfg = {
        "name": "t19", "seeds": [7], "runs": 1, "warmup": 0,
        "records": 15, "target_bytes": 1024, "checkpoint_batch": 5,
        "witness": "local",
    }
    first = runner.run_config(cfg, tmp_path / "a")
    second = runner.run_config(cfg, tmp_path / "b")
    assert first["witnessed_through"] == second["witnessed_through"]
    assert first["total_record_bytes"] == second["total_record_bytes"]
    assert first["db_bytes"] == second["db_bytes"]


def test_analysis_bootstrap_uses_run_level():
    runs = [
        {"append_p50_ms": 1.0, "records_per_second": 900.0},
        {"append_p50_ms": 1.2, "records_per_second": 950.0},
        {"append_p50_ms": 0.9, "records_per_second": 880.0},
        {"append_p50_ms": 1.1, "records_per_second": 920.0},
    ]
    report = analyze.summarize(runs, seed=1)
    p50 = report["append_p50_ms"]
    assert p50["mean"] == pytest.approx(1.05)
    assert p50["ci_low"] <= p50["mean"] <= p50["ci_high"]
    assert p50["n_runs"] == 4  # run level, not record level


def test_analysis_markdown_has_no_placeholders(tmp_path):
    runs = [{"append_p50_ms": 1.0, "records_per_second": 900.0,
             "witness_p50_ms": 2.0, "verify_seconds": 0.01}]
    report = analyze.summarize(runs, seed=1)
    text = analyze.render_markdown(report)
    assert "append_p50_ms" in text
    assert "TODO" not in text and "placeholder" not in text.lower()


def test_manifest_cli_honors_output_dir(tmp_path):
    """T19 reruns on a second machine must not overwrite the
    committed results of the first machine."""
    from benchmarks import run_manifest

    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({
        "name": "cli", "analysis_seed": 1,
        "configs": [{"name": "cli-smoke", "seeds": [7], "runs": 1,
                     "warmup": 0, "records": 10, "target_bytes": 512,
                     "checkpoint_batch": 4, "witness": "local"}]}))
    out = tmp_path / "second-machine"
    assert run_manifest.main([str(manifest), str(out)]) == 0
    assert (out / "cli-smoke-run-0.json").exists()
    assert (out / "report.md").exists()
    assert run_manifest.main([]) == 2  # usage error


def test_runner_http_witness_with_injected_delay(tmp_path):
    """RQ2 (SPEC §22): the witness may run over loopback HTTP with a
    controlled delay, so wide area cost is measured, not assumed."""
    cfg = {
        "name": "http", "seeds": [7], "runs": 1, "warmup": 0,
        "records": 10, "target_bytes": 512, "checkpoint_batch": 5,
        "witness": "http", "witness_delay_ms": 20,
    }
    summary = runner.run_config(cfg, tmp_path / "out")
    row = json.loads((tmp_path / "out" / "http-run-0.json").read_text())
    assert row["config"]["witness"] == "http"
    assert row["config"]["witness_delay_ms"] == 20
    assert summary["witnessed_through"] == 10
    assert summary["checkpoints_accepted"] == 2
    # each round trip paid at least the injected delay
    assert row["witness_latency_ns"]
    assert min(row["witness_latency_ns"]) >= 20 * 1e6


def test_runner_http_witness_rejects_bad_delay(tmp_path):
    cfg = {
        "name": "http-bad", "seeds": [7], "runs": 1, "warmup": 0,
        "records": 5, "target_bytes": 512, "checkpoint_batch": 5,
        "witness": "http", "witness_delay_ms": -1,
    }
    with pytest.raises(ValueError, match="witness_delay_ms"):
        runner.run_config(cfg, tmp_path / "out")


def test_runner_remote_witness_two_runs(tmp_path, monkeypatch):
    """RQ2/RQ3: the witness may live behind a real network URL.

    Each run uses its own log id, because the remote witness keeps
    its state between runs and would otherwise see a fork."""
    from benchmarks import witness_server

    monkeypatch.setenv("CASF_BENCH_TOKEN", "remote-bench-token")
    service, server = witness_server.build_server(
        "127.0.0.1", 0, token="remote-bench-token",
        seeds=[7, 8], runs=2, db_path=tmp_path / "wit.db")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        cfg = {
            "name": "remote", "seeds": [7, 8], "runs": 2, "warmup": 0,
            "records": 10, "target_bytes": 512, "checkpoint_batch": 5,
            "witness": "remote", "witness_url": url,
            "witness_token_env": "CASF_BENCH_TOKEN",
        }
        summary = runner.run_config(cfg, tmp_path / "out")
        assert summary["witnessed_through"] == 10
        assert summary["checkpoints_accepted"] == 2
        row0 = json.loads(
            (tmp_path / "out" / "remote-run-0.json").read_text())
        row1 = json.loads(
            (tmp_path / "out" / "remote-run-1.json").read_text())
        assert row0["config"]["witness"] == "remote"
        assert row0["config"]["witness_url"] == url
        assert row0["config"]["log_id"] != row1["config"]["log_id"]
        assert row0["witness_latency_ns"]  # real round trips measured
        assert row0["witness_bytes"] == 0  # remote store not measurable
    finally:
        server.shutdown()
        server.server_close()
        service.close()


def test_witness_server_requires_token_env(tmp_path, monkeypatch):
    from benchmarks import witness_server

    monkeypatch.delenv("CASF_BENCH_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        witness_server.main(["--port", "0", "--token-env",
                             "CASF_BENCH_TOKEN", "--seeds", "7",
                             "--runs", "1"])
