# Current implementation evidence refresh

Recorded before these follow-up measurements. This plan preserves the original
protocol, frozen manifests, reports, raw measurements and preprint. It defines a
bounded local refresh after the implementation and validation changes through
PR 50 (`b3cf12be89455f5515a8ad001295086c91527342`).

## Impact and selected measurements

| Evidence | Relevant changes | Follow-up |
| --- | --- | --- |
| Detection matrix | Storage constraints, export and verifier diagnostics | All existing declared cases, unchanged expectations |
| Canonical H1 | Writer, storage, verifier and online reconciliation | Original ten seeds, 24-to-32-record rollback, both arms and controls |
| Local performance | Append results, storage transactions, checkpoint and verification paths | Original local manifest: ten seeds each for batches 128 and 16, 100 warmup and 1,000 measured records per run |
| Canonical H3 | Writer, transport, CLI verification and receipt handling | Frozen ten healthy/outage pairs with the original randomized order and three-second fault |
| RQ4 | Source, tests, dependencies, documentation and CI | Original descriptive collector methods, explicitly selecting the PR 50 merge commit |

The local performance rerun retains the historical configuration-block order;
it does not meet SPEC Section 22's randomized-order recommendation. Treat its
timing estimates as descriptive, with possible order and host-load effects.
H3 retains its frozen randomized order. Do not run other tests or benchmarks
concurrently with measurements. Each run uses the harness's fresh stores.

The historical Linux and WAN measurements remain evidence about their recorded
revisions and environments. This refresh does not reproduce their performance,
the full proposed workload matrix, or independently administered witness
operation. No new remote infrastructure is provisioned for this local study.

The harnesses explicitly use `local_only=True` to build and manipulate their
synthetic histories. They measure append/checkpoint/verification behavior, not
the cost or protection of default verified startup. H3 uses manual recovery;
the automatic worker is not exercised. Production startup/worker behavior has
separate regression and process-crash coverage. No throughput improvement,
regression, or causal cross-revision timing claim follows from these reruns.

## Execution and provenance

Commit harness fixes and this plan before running measurements. From a clean
checkout with the locked Python 3.12 environment, set `PYTHONPATH=src`. Record
the exact commit, source import inventory, lock and harness hashes, environment,
commands, UTC start/end times and all exit statuses in a new output directory.
The measurement commit is distinct from later results/document assembly commits.
RQ4 measures the explicit PR 50 revision above, using `git archive`, rather than
the collector's current checkout or the historical manifest's default revision.

Use these commands in order, with `OUT` set to a previously absent directory:

```bash
PYTHONPATH=src .venv/bin/python -m tests.validation_environment --import-mode source --output "$OUT/source-environment.json"
PYTHONPATH=src .venv/bin/python -c 'from pathlib import Path; from benchmarks.attacks import run_matrix; import sys; run_matrix(Path(sys.argv[1]))' "$OUT/detection"
PYTHONPATH=src .venv/bin/python -m benchmarks.h1_writer_rollback benchmarks/h1-writer-rollback.v1.json "$OUT/h1"
PYTHONPATH=src .venv/bin/python -m benchmarks.run_manifest benchmarks/manifest.v1.json "$OUT/local"
PYTHONPATH=src .venv/bin/python -m benchmarks.h3_witness_outage --manifest benchmarks/h3-witness-outage.v1.json --output "$OUT/h3"
PYTHONPATH=src .venv/bin/python -m benchmarks.rq4_burden benchmarks/rq4-operational-burden.v1.json "$OUT/rq4" --repo . --commit b3cf12be89455f5515a8ad001295086c91527342
```

`OUT` is a run label; its date need not equal the UTC execution date. Actual
timestamps belong to the provenance record. Save raw attempts and failures;
never replace a failed run with a successful rerun under the same name. Check
every expected count and result explicitly; an exit status alone is insufficient.
H1's original primary expectation remains `FAIL`; preserve any `INCONCLUSIVE`
outcome as an expectation mismatch, not a detected rollback.

Publish a reviewed subset of JSON measurements, frozen manifest copies, reports
and checksums under a new results directory. Exclude generated databases,
bundles, keys and verifier state. Keep the full raw output separately. Record
any public-file transformation and preserve original hashes. Verify all tracked
historical result files, manifests, protocol and preprint files remain unchanged.

## Reconciliation

Add a dated follow-up that distinguishes functional outcomes, descriptive timing
estimates, repository proxies and unmeasured claims. Link it from the current
research guide. Do not replace historical values or change hypothesis labels in
the original reports/preprint. Report deviations, incomplete runs, retained
limitations and the scope still unmeasured alongside any positive result.
