"""RQ4 operational burden evidence collection (SPEC 001 Section 22).

Canonical RQ4: what operational burden and implementation complexity
does the constrained approach impose on a solo maintained project?

This is a descriptive study, not a hypothesis test. Every value is
measured from the repository at collection time by this script,
following the counting methods predeclared in
benchmarks/rq4-operational-burden.v1.json. The manifest contains no
numbers; nothing here is hand entered.

Per SPEC Section 23 the collected values are complexity proxies, not
objective measures of usability or total cost. The generated report
carries that caveat verbatim from the manifest.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = Path("docs/specification/CASF_SPEC_001.md")
INSTALL_PATH = Path("docs/installation.md")
CI_WORKFLOW = Path("ci.yml")


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _py_files(root: Path, recursive: bool = True) -> list[Path]:
    pattern = "**/*.py" if recursive else "*.py"
    return sorted(p for p in root.glob(pattern)
                  if "__pycache__" not in p.parts)


def _line_stats(files: list[Path]) -> dict:
    total = non_blank = 0
    for f in files:
        lines = _lines(f)
        total += len(lines)
        non_blank += sum(1 for line in lines if line.strip())
    return {"files": len(files), "total_lines": total,
            "non_blank_lines": non_blank}


def source_size(root: Path) -> dict:
    """Per module and total line counts under the source directory."""
    modules: dict[str, dict] = {}
    for child in sorted(root.iterdir()):
        if child.is_dir() and "__pycache__" not in child.parts:
            modules[child.name] = _line_stats(_py_files(child))
    top = _line_stats(_py_files(root, recursive=False))
    modules["(top level)"] = top
    return {"root": str(root), "modules": modules,
            "total": _line_stats(_py_files(root))}


def test_size(root: Path) -> dict:
    files = _py_files(root)
    stats = _line_stats(files)
    stats["test_functions"] = sum(
        1 for f in files for line in _lines(f)
        if line.lstrip().startswith("def test_"))
    return stats


def markdown_size(root: Path, recursive: bool = True) -> dict:
    pattern = "**/*.md" if recursive else "*.md"
    return _line_stats(sorted(root.glob(pattern)))


def dependency_surface(repo: Path) -> dict:
    pyproject = tomllib.loads((repo / "pyproject.toml").read_text("utf-8"))
    project = pyproject["project"]
    groups = pyproject.get("dependency-groups", {})
    lock_text = (repo / "uv.lock").read_text("utf-8")
    locked_external = 0
    for chunk in lock_text.split("[[package]]")[1:]:
        name = re.search(r'^name = "([^"]+)"', chunk, re.MULTILINE)
        editable = re.search(r"^source = \{ editable", chunk, re.MULTILINE)
        if name and not editable:
            locked_external += 1
    return {
        "direct_runtime": sorted(project.get("dependencies", [])),
        "optional_extras": {k: sorted(v) for k, v in
                            project.get("optional-dependencies", {}).items()},
        "dependency_groups": {k: sorted(v) for k, v in groups.items()},
        "direct_external_total": len(project.get("dependencies", [])) + sum(
            len(v) for v in project.get("optional-dependencies", {}).values())
        + sum(len(v) for v in groups.values()),
        "locked_external_packages": locked_external,
    }


def spec_burden(repo: Path) -> dict:
    text = (repo / SPEC_PATH).read_text("utf-8")
    ids = {prefix: sorted(set(re.findall(rf"\b{prefix}\d{{{digits}}}\b",
                                         text)))
           for prefix, digits in (("R", 2), ("T", 2), ("C", 2), ("M", 1))}
    return {"requirement_ids": ids["R"], "test_ids": ids["T"],
            "task_ids": ids["C"], "milestone_ids": ids["M"],
            "adr_documents": len(list((repo / "docs/adr").glob("*.md")))}


def ci_surface(repo: Path) -> dict:
    workflows = sorted((repo / ".github/workflows").glob("*.yml"))
    text = (repo / ".github/workflows" / CI_WORKFLOW).read_text("utf-8")
    arrays = re.findall(r"python-version:\s*\[([^\]]+)\]", text)
    versions = sorted({v for array in arrays
                       for v in re.findall(r'"([\d.]+)"', array)})
    return {"workflow_files": [w.name for w in workflows],
            "ci_python_versions": versions}


def installation_burden(repo: Path) -> dict:
    lines = _lines(repo / INSTALL_PATH)
    return {"guide_lines": len(lines),
            "bash_command_blocks": sum(1 for line in lines
                                       if line.strip() == "```bash")}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=True).stdout.strip()


def maintenance_history(repo: Path) -> dict:
    commits = int(_git(repo, "log", "--oneline").count("\n") + 1)
    merges = _git(repo, "log", "--oneline", "--grep=Merge pull request")
    first = _git(repo, "log", "--reverse", "--format=%as").splitlines()[0]
    latest = _git(repo, "log", "-1", "--format=%as")
    span = (int(_git(repo, "log", "-1", "--format=%ct"))
            - int(_git(repo, "log", "--reverse", "--format=%ct")
                  .splitlines()[0])) // 86400
    return {
        "commits_at_head": commits,
        "merged_pull_requests": len(merges.splitlines()) if merges else 0,
        "first_commit_date": first,
        "latest_commit_date": latest,
        "calendar_span_days": span,
        "release_documents": len(list((repo / "docs/release").glob("*.md"))),
        "committed_result_directories": len(
            [d for d in (repo / "benchmarks/results").iterdir()
             if d.is_dir()]),
    }


def _environment(repo: Path) -> dict:
    try:
        status = _git(repo, "status", "--porcelain")
        commit = _git(repo, "rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError):
        status, commit = "unknown", "unknown"
    lock = repo / "uv.lock"
    harness = Path(__file__)
    return {
        "commit": commit,
        "working_tree_status": status if status else "clean",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "dependency_lock_sha256": hashlib.sha256(
            lock.read_bytes()).hexdigest() if lock.exists() else None,
        "harness_sha256": hashlib.sha256(harness.read_bytes()).hexdigest(),
    }


def collect(manifest_path: Path, repo: Path = REPO_ROOT) -> dict:
    cfg = json.loads(Path(manifest_path).read_text("utf-8"))
    src = repo / "src/casf"
    return {
        "experiment": cfg["experiment"],
        "research_question_id": cfg["research_question_id"],
        "question_source": cfg["question_source"],
        "question_text": cfg["question_text"],
        "manifest_sha256": hashlib.sha256(
            Path(manifest_path).read_bytes()).hexdigest(),
        "metric_methods": {k: v["method"]
                           for k, v in cfg["metrics"].items()},
        "interpretation_limits": cfg["interpretation_limits"],
        "measurements": {
            "source_size": source_size(src),
            "test_size": test_size(repo / "tests"),
            "benchmark_size": _line_stats(_py_files(repo / "benchmarks",
                                                    recursive=False)),
            "documentation_size": {
                "docs": markdown_size(repo / "docs"),
                "research_top_level": markdown_size(repo / "research",
                                                    recursive=False),
            },
            "dependencies": dependency_surface(repo),
            "spec_burden": spec_burden(repo),
            "ci_surface": ci_surface(repo),
            "installation_burden": installation_burden(repo),
            "maintenance_history": maintenance_history(repo),
        },
        "environment": _environment(repo),
    }


def _render_report(artifact: dict) -> str:
    m = artifact["measurements"]
    dep = m["dependencies"]
    spec = m["spec_burden"]
    hist = m["maintenance_history"]
    src = m["source_size"]["total"]
    docs = m["documentation_size"]

    def row(label: str, value: object) -> str:
        return f"| {label} | {value} |"

    lines = [
        "# RQ4 operational burden evidence (SPEC Section 22)", "",
        f"question source: {artifact['question_source']}",
        f"manifest sha256: {artifact['manifest_sha256']}", "",
        ("Descriptive collection only; no hypothesis and no pass or fail "
         "expectation. All values measured at collection time."), "",
        "## Measured values", "",
        "| metric | value |",
        "| --- | --- |",
        row("source modules under src/casf",
            len(m["source_size"]["modules"])),
        row("source files", src["files"]),
        row("source total lines", src["total_lines"]),
        row("source non blank lines", src["non_blank_lines"]),
        row("test files", m["test_size"]["files"]),
        row("test total lines", m["test_size"]["total_lines"]),
        row("test functions", m["test_size"]["test_functions"]),
        row("benchmark harness files", m["benchmark_size"]["files"]),
        row("benchmark harness total lines",
            m["benchmark_size"]["total_lines"]),
        row("docs markdown files", docs["docs"]["files"]),
        row("docs markdown lines", docs["docs"]["total_lines"]),
        row("research top level markdown files",
            docs["research_top_level"]["files"]),
        row("direct runtime dependencies",
            f"{len(dep['direct_runtime'])} ({', '.join(dep['direct_runtime'])})"),
        row("direct external dependencies total (runtime, extras, groups)",
            dep["direct_external_total"]),
        row("locked external packages", dep["locked_external_packages"]),
        row("specification requirement ids", len(spec["requirement_ids"])),
        row("specification test ids", len(spec["test_ids"])),
        row("specification task ids", len(spec["task_ids"])),
        row("specification milestone ids", len(spec["milestone_ids"])),
        row("architecture decision records", spec["adr_documents"]),
        row("ci workflow files", len(m["ci_surface"]["workflow_files"])),
        row("ci python versions", ", ".join(m["ci_surface"]["ci_python_versions"])),
        row("installation guide lines",
            m["installation_burden"]["guide_lines"]),
        row("installation bash command blocks",
            m["installation_burden"]["bash_command_blocks"]),
        row("commits at measured commit", hist["commits_at_head"]),
        row("merged pull requests", hist["merged_pull_requests"]),
        row("first commit date", hist["first_commit_date"]),
        row("latest commit date", hist["latest_commit_date"]),
        row("calendar span days", hist["calendar_span_days"]),
        row("release documents", hist["release_documents"]),
        row("committed result directories", hist["committed_result_directories"]),
        "", "## Source size by module", "",
        "| module | files | total lines | non blank lines |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, stats in m["source_size"]["modules"].items():
        lines.append(f"| {name} | {stats['files']} | {stats['total_lines']} "
                     f"| {stats['non_blank_lines']} |")
    lines += ["", "## Interpretation limits", ""]
    for item in artifact["interpretation_limits"]:
        lines.append(f"- {item}")
    env = artifact["environment"]
    lines += ["", "## Environment", ""]
    for key in sorted(env):
        lines.append(f"- {key}: {env[key]}")
    lines.append("")
    return "\n".join(lines)


def run_collection(manifest_path: Path, out_dir: Path) -> dict:
    out = Path(out_dir)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing directory: {out}")
    artifact = collect(manifest_path)
    out.mkdir(parents=True)
    (out / "measurements.v1.json").write_text(json.dumps(artifact, indent=2))
    (out / "report.md").write_text(_render_report(artifact))
    return artifact


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv)
    artifact = run_collection(args.manifest, args.out_dir)
    m = artifact["measurements"]
    print(f"source lines: {m['source_size']['total']['total_lines']}  "
          f"test functions: {m['test_size']['test_functions']}  "
          f"locked external packages: "
          f"{m['dependencies']['locked_external_packages']}  "
          f"commits: {m['maintenance_history']['commits_at_head']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
