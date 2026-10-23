"""Benchmark analysis (SPEC §22).

Summaries are computed over run level values, never by pooling
individual records, and every metric carries a bootstrap interval so
single fast or slow runs cannot dominate the claim.
"""

import random

RESAMPLES = 2000


def _bootstrap_interval(values: list[float],
                        rng: random.Random) -> tuple[float, float]:
    n = len(values)
    means = sorted(
        sum(rng.choice(values) for _ in range(n)) / n
        for _ in range(RESAMPLES))
    low = means[int(0.025 * RESAMPLES)]
    high = means[min(int(0.975 * RESAMPLES), RESAMPLES - 1)]
    return low, high


def summarize(runs: list[dict], seed: int) -> dict:
    """Mean and bootstrap interval per metric across runs."""
    rng = random.Random(seed)
    report: dict = {}
    for key in runs[0]:
        values = [float(r[key]) for r in runs]
        mean = sum(values) / len(values)
        low, high = _bootstrap_interval(values, rng)
        report[key] = {
            "mean": mean,
            "ci_low": low,
            "ci_high": high,
            "n_runs": len(values),
        }
    return report


def render_markdown(report: dict) -> str:
    """Render the summary as a plain markdown table."""
    lines = [
        "| metric | mean | 95% interval | runs |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, stats in report.items():
        lines.append(
            f"| {name} | {stats['mean']:.4f} | "
            f"[{stats['ci_low']:.4f}, {stats['ci_high']:.4f}] | "
            f"{stats['n_runs']} |")
    return "\n".join(lines) + "\n"
