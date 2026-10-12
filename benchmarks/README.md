# Benchmarks

Benchmark harness for the research evaluation (SPEC §22-§23).
Synthetic data only.

Layout:

- `workload.py` — deterministic seeded event generator. Pads each
  request to a target size and reports the honest minimum stored
  record size measured through the real writer path.
- `runner.py` — runs one configuration against a fresh writer and
  local witness, measures append latency per record, witness
  round trips per checkpoint, and one final full verification, then
  writes raw measurements per run with the environment pinned.
- `analyze.py` — run level summaries with bootstrap intervals;
  record level pooling is never used.
- `run_manifest.py` — runs a manifest file and writes raw rows plus
  a markdown report under `results/`.
- `manifest.v1.json` — the pinned local subset (1 KiB records,
  1000 records per run, 10 runs per configuration).
- `results/` — raw run output and reports.

Run the local subset:

```
python -m benchmarks.run_manifest benchmarks/manifest.v1.json
```

The full matrix with network delay injection runs on the Linux
machine; this subset is the smoke level reference for it.
