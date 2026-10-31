"""Tests for the RQ4 operational burden collection harness."""

import json
import subprocess
from pathlib import Path

import pytest

from benchmarks import rq4_burden

MANIFEST = Path("benchmarks/rq4-operational-burden.v1.json")


def test_line_stats_counts_total_and_non_blank(tmp_path):
    target = tmp_path / "mod.py"
    target.write_text("a = 1\n\n   \nb = 2\n")
    stats = rq4_burden._line_stats([target])
    assert stats == {"files": 1, "total_lines": 4, "non_blank_lines": 2}


def test_py_files_excludes_pycache(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "skip.py").write_text("y = 2\n")
    assert [p.name for p in rq4_burden._py_files(tmp_path)] == ["ok.py"]


def test_test_function_count(tmp_path):
    (tmp_path / "test_demo.py").write_text(
        "# def test_comment(): pass\n"
        "example = 'def test_string(): pass'\n"
        "def test_one():\n    pass\n\n"
        "    def test_nested():\n        pass\n\n"
        "async def test_async():\n    pass\n\n"
        "def helper():\n    pass\n")
    stats = rq4_burden.test_size(tmp_path)
    assert stats["test_functions"] == 3
    assert stats["files"] == 1


def test_dependency_surface_counts(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["cryptography>=41.0"]\n'
        '[project.optional-dependencies]\nwitness = ["uvicorn==0.54.0"]\n'
        '[dependency-groups]\nbuild = ["build>=1.2"]\n')
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "casf"\nsource = { editable = "." }\n\n'
        '[[package]]\nname = "cryptography"\n'
        'source = { registry = "https://pypi.org/simple" }\n\n'
        '[[package]]\nname = "uvicorn"\n'
        'source = { registry = "https://pypi.org/simple" }\n')
    surface = rq4_burden.dependency_surface(tmp_path)
    assert surface["direct_runtime"] == ["cryptography>=41.0"]
    assert surface["direct_external_total"] == 3
    assert surface["locked_external_packages"] == 2


def test_spec_burden_unique_ids(tmp_path):
    spec = tmp_path / "docs/specification"
    spec.mkdir(parents=True)
    (spec / "CASF_SPEC_001.md").write_text(
        "R01 R02 R01 again T01 T22 T01 C00 C12 C00 M0 M8 M0")
    adr = tmp_path / "docs/adr"
    adr.mkdir()
    (adr / "one.md").write_text("x")
    (adr / "two.md").write_text("x")
    burden = rq4_burden.spec_burden(tmp_path)
    assert burden["requirement_ids"] == ["R01", "R02"]
    assert burden["test_ids"] == ["T01", "T22"]
    assert burden["task_ids"] == ["C00", "C12"]
    assert burden["milestone_ids"] == ["M0", "M8"]
    assert burden["adr_documents"] == 2


def test_ci_versions_from_matrix_arrays(tmp_path):
    workflows = tmp_path / ".github/workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        'jobs:\n  a:\n    strategy:\n      matrix:\n'
        '        python-version: ["3.12", "3.13"]\n'
        '    steps:\n      - run: uv==0.13.5\n'
        '      - run: echo "${{ matrix.python-version }}"\n')
    surface = rq4_burden.ci_surface(tmp_path)
    assert surface["ci_python_versions"] == ["3.12", "3.13"]
    assert surface["workflow_files"] == ["ci.yml"]


def test_installation_burden_counts_bash_blocks(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "installation.md").write_text(
        "# guide\n\n```bash\none\n```\n\ntext\n\n```bash\ntwo\n```\n\n"
        "```json\nnot counted\n```\n")
    burden = rq4_burden.installation_burden(tmp_path)
    assert burden["bash_command_blocks"] == 2
    assert burden["guide_lines"] == 15


def test_collect_against_repository_matches_manifest_methods():
    artifact = rq4_burden.collect(MANIFEST)
    declared = set(json.loads(MANIFEST.read_text())["metrics"])
    assert set(artifact["measurements"]) == declared
    assert set(artifact["metric_methods"]) == declared
    dep = artifact["measurements"]["dependencies"]
    assert dep["locked_external_packages"] >= 1
    assert "cryptography>=41.0" in dep["direct_runtime"]
    assert artifact["environment"]["measured_commit"] == (
        "7c388d385242238a40e572ed67e7e5fc9a1ab194")
    assert artifact["collector"]["version"] == rq4_burden.COLLECTOR_VERSION
    assert artifact["collector"]["sha256"]


def test_collect_uses_only_selected_commit_tracked_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    files = {
        "src/casf/core.py": "committed = True\n",
        "tests/test_core.py": "def test_committed():\n    pass\n",
        "benchmarks/runner.py": "# committed benchmark\n",
        "docs/specification/CASF_SPEC_001.md": "R01 T01 C00 M0\n",
        "docs/installation.md": "```bash\nrun\n```\n",
        "docs/adr/one.md": "adr\n",
        "docs/release/one.md": "release\n",
        "research/one.md": "research\n",
        "pyproject.toml": '[project]\ndependencies = []\n',
        "uv.lock": "",
        ".github/workflows/ci.yml": 'python-version: ["3.12"]\n',
    }
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (repo / "benchmarks/results/result").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"],
                   cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo,
                   check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "snapshot"], cwd=repo,
                   check=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                            text=True, capture_output=True, check=True).stdout.strip()

    (repo / "src/casf/core.py").write_text("modified working tree\n")
    (repo / "src/casf/untracked.py").write_text("untracked = True\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "experiment": "snapshot-test",
        "research_question_id": "RQ4",
        "question_source": "test",
        "question_text": "test",
        "metrics": {name: {"method": "test"} for name in (
            "source_size", "test_size", "benchmark_size",
            "documentation_size", "dependencies", "spec_burden",
            "ci_surface", "installation_burden", "maintenance_history")},
        "interpretation_limits": [],
    }))

    result = rq4_burden.collect(manifest, repo=repo, measured_commit=commit)
    source = result["measurements"]["source_size"]
    assert source["total"]["files"] == 1
    assert source["total"]["total_lines"] == 1
    assert result["environment"]["measured_commit"] == commit
    assert result["environment"]["snapshot_method"].startswith("git archive")


def test_run_collection_writes_artifacts_and_refuses_overwrite(tmp_path):
    out = tmp_path / "rq4-results"
    artifact = rq4_burden.run_collection(MANIFEST, out)
    written = json.loads((out / "measurements.v1.json").read_text())
    assert written["experiment"] == "rq4-operational-burden-v1"
    assert written["measurements"]["source_size"]["total"]["files"] > 0
    report = (out / "report.md").read_text()
    assert "## Measured values" in report
    assert "## Interpretation limits" in report
    assert "## Environment" in report
    assert artifact["collector"]["sha256"]
    with pytest.raises(SystemExit):
        rq4_burden.run_collection(MANIFEST, out)
