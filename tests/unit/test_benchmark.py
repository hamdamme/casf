"""R12 / T19 (SPEC §22, §23): benchmark harness integrity.

The workload generator is deterministic under a fixed seed and
reports the actual minimum body size honestly instead of pretending
an impossible 256 byte target was met. The runner writes raw
measurements with the environment pinned, and rerunning the same
manifest reproduces the procedure (T19). Analysis uses run level
summaries with bootstrap intervals, never record level pooling.
"""

import json

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
