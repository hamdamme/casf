# Benchmarks

Benchmark harness for the research evaluation (SPEC §22-§23).
Synthetic data only.

For new experiments, install from `uv.lock` using the
[dependency guide](../docs/dependencies.md). Keep the lockfile with the commit
used for each run. This setup does not change the recorded environments or
results of earlier experiments. Choose a new output directory for each new
experiment to preserve existing evidence.

The [current implementation follow-up](results/current-evidence-2026-11-10/README.md)
records a separate local rerun with source/import provenance and explicit
historical comparisons. The manifest and detection runners refuse existing
output directories; the configuration runner refuses existing row files.
An incomplete H3 run retains its evidence and makes the experiment exit with
failure. Always inspect raw outcomes as well as process exit status.

Layout:

- `workload.py` — deterministic seeded event generator. Pads each
  request to a target size and reports the honest minimum stored
  record size measured through the real writer path.
- `runner.py` — runs one configuration against a fresh writer and
  witness, measures append latency per record, witness round trips
  per checkpoint, and one final full verification, then writes raw
  measurements per run with the environment pinned. The witness runs
  in process ("local") or over loopback HTTP with an optional
  injected round trip delay ("http" plus witness_delay_ms).
- `analyze.py` — run level summaries with bootstrap intervals;
  record level pooling is never used.
- `run_manifest.py` — runs a manifest file and writes raw rows plus
  a markdown report under `results/`.
- `attacks.py` — detection experiment (SPEC §23): predeclared cases,
  one mutation per controlled copy, positions across the chain, T18
  boundaries, T20 stolen writer key, T21 witness rollback. Results
  in `results/detection-v1/`.
- `manifest.v1.json` — the pinned local subset (1 KiB records,
  1000 records per run, 10 runs per configuration).
- `results/` — raw run output and reports.

Run the local subset:

```
PYTHONPATH=src .venv/bin/python -m benchmarks.run_manifest benchmarks/manifest.v1.json /tmp/casf-local-new-run
```

The second argument sets a new output directory. Choose an unused path for each
run, including replication on a second machine (T19). The default historical
output directory already exists in a checkout and must not be reused.

The [Linux run sheet](linux-matrix.md) separates future reproduction from
historical results. Its extended manifest includes a loopback witness with
25 ms injected delay. The [remote evaluation guide](wide-area.md) records the
historical cloud study and the transport/provisioning work required before a
new remote run. Additional Linux performance/cloud evaluation is deferred; neither guide
claims new remote measurements or authorizes infrastructure provisioning.
