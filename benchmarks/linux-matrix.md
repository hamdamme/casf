# Linux research reproduction

The additional Linux machine evaluation is deferred. Routine Ubuntu CI remains
enabled; it checks correctness and installed packages, not representative
deployment performance. No new Linux benchmark was run for this documentation
update.

The [original local replication](results/local-subset-v1-linux/report.md) and
[Linux matrix](results/linux-matrix-v2/report.md) retain their recorded revisions,
environments and measurements. The
[earlier run sheet](https://github.com/hamdamme/casf/blob/6441e4569e8c420f5e8a71e55950af88ce46f336/benchmarks/linux-matrix.md)
is historical; its fixed test count, reused output paths and database-size
comparison are not instructions for the current candidate.

## Procedure for a future authorized run

Select a clean source commit and record why these configurations are being
rerun. Install Python 3.12–3.14 and the locked witness/development dependencies
using the [dependency guide](../docs/dependencies.md). Record the actual OS,
architecture, CPU, RAM, storage/filesystem, Python, SQLite and cryptography
versions. A commit hash alone does not identify imported code or hardware.

From the repository root:

```bash
CASF_LINUX_RESULTS="$(mktemp -d /tmp/casf-linux-results-XXXXXX)"
PYTHONPATH=src .venv/bin/python -m tests.validation_environment \
  --import-mode source --output "$CASF_LINUX_RESULTS/environment.json"
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
PYTHONPATH=src .venv/bin/python -m benchmarks.run_manifest \
  benchmarks/manifest.v1.json "$CASF_LINUX_RESULTS/local"
PYTHONPATH=src .venv/bin/python -m benchmarks.run_manifest \
  benchmarks/manifest.v2.json "$CASF_LINUX_RESULTS/matrix"
```

Require a clean inventory and a fully passing suite before measurement. The
expected test total comes from the selected revision; there is no permanent
numeric threshold. Run measurements sequentially after tests finish. Preserve
all command exits, logs, failures and interruptions in the new output root.

The local manifest has ten seeds for each of two batch sizes. The extended
manifest has four configurations, ten runs each, including a loopback witness
with a configured 25 ms delay. These are a historical subset, not the full
matrix proposed in SPEC Section 22. Configuration-block order is retained;
its possible order/host-load effects must accompany timing interpretations.

## Evidence and comparisons

Compare seeds, requested record counts, checkpoint counts, witnessed prefixes,
verification outcomes and retry counts with the declared procedure. Explain
differences rather than changing expected outcomes after observing them.
Database allocation can vary with SQLite, storage schema and environment;
cross-revision byte equality is not a valid acceptance criterion. Latencies
are observations of the identified host and workload, not portability promises.

Keep frozen manifest copies, exact commands, timestamps, runtime/import
inventory, complete raw rows, reports and checksums. Verify them before
publishing a reviewed subset in a new results directory. Exclude private keys,
databases and retained verifier state. Interrupted output is retained under its
original name; a rerun gets a new directory and is not silently substituted.

The historical WAN study is separate evidence. An injected loopback delay
does not reproduce that path; see the [remote evaluation boundary](wide-area.md).
