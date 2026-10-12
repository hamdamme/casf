"""Run a benchmark manifest and write raw rows plus a summary.

Usage: python -m benchmarks.run_manifest MANIFEST [OUT_DIR]

The manifest lists configurations; each runs its seeds and writes one
raw JSON file per run under OUT_DIR (default benchmarks/results/
<name>/), then an analysis report with run level bootstrap intervals
(SPEC §22). A rerun on a second machine (T19) should use its own
OUT_DIR so committed results are never overwritten.
"""

import json
import sys
import time
from pathlib import Path

from benchmarks import analyze, runner

RESULTS = Path(__file__).parent / "results"


def main(argv: list[str]) -> int:
    if len(argv) not in (1, 2):
        print("usage: python -m benchmarks.run_manifest MANIFEST [OUT_DIR]")
        return 2
    manifest_path = Path(argv[0])
    manifest = json.loads(manifest_path.read_text())
    out_root = (Path(argv[1]) if len(argv) == 2
                else RESULTS / manifest["name"])
    out_root.mkdir(parents=True, exist_ok=True)
    sections = []
    for cfg in manifest["configs"]:
        start = time.time()
        summary = runner.run_config(cfg, out_root)
        elapsed = time.time() - start
        report = analyze.summarize(summary["run_metrics"],
                                   seed=int(manifest["analysis_seed"]))
        sections.append(
            f"## {cfg['name']}\n\n"
            f"runs: {summary['runs']}, records per run: "
            f"{summary['records_per_run']}, witnessed through: "
            f"{summary['witnessed_through']}, database bytes: "
            f"{summary['db_bytes']}, wall clock: {elapsed:.1f} s\n\n"
            + analyze.render_markdown(report))
        print(f"{cfg['name']}: {summary['runs']} runs in "
              f"{elapsed:.1f} s -> {out_root}")
    header = (f"# Benchmark report: {manifest['name']}\n\n"
              f"manifest: {manifest_path.name}\n\n")
    (out_root / "report.md").write_text(header + "\n".join(sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
