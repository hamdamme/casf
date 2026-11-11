# Current implementation evidence: 10 November 2026

The affected local studies completed on the current implementation, preserving
the earlier functional conclusions and their limits. In particular, canonical
H1 still does **not** satisfy its original primary expectation of `FAIL` without
a retained newer checkpoint. These follow-ups do not certify production
readiness or replace the historical WAN, Linux or preprint measurements.

## Source and procedure

The [plan](refresh-plan-2026-11-10.md) was committed before measurement. Runtime
experiments used clean commit `09feba1676e0ba319b4e36cb6c2fa76264842b47`, after
the accepted PR 50 implementation/validation baseline. Harness fixes protect
existing results and report incomplete H3 runs as failures; protocol and
runtime source were unchanged by this refresh. RQ4 measured PR 50's merge
`b3cf12be89455f5515a8ad001295086c91527342` through a tracked-file archive.
Later result/document commits are assembly revisions, not measurement revisions.

The [public evidence directory](../benchmarks/results/current-evidence-2026-11-10/README.md)
contains raw run JSON, original manifest copies, reports, source/import hashes,
commands, timestamps, review counts and checksums. Collection ran sequentially
on 11 November 2026, 01:24:25–01:26:38 UTC, with no concurrent test or benchmark
job in this session. Other host activity was not controlled. All six recorded
commands exited successfully; no measured run was discarded or replaced.

Environment: macOS 15.6.1 arm64, Apple M1, eight logical CPUs, 16 GiB RAM,
APFS on solid-state storage, Python 3.12.11, SQLite 3.54.0 and cryptography
50.0.2, using the unchanged lockfile. Supplemental CPU/filesystem details were
captured after the run; the raw legacy H3 filesystem field `/` is not a valid
filesystem identification. All 39 imported package files matched the source.

## Detection and canonical H1

The [detection matrix](../benchmarks/results/current-evidence-2026-11-10/detection/report.md)
matched all ten declared outcomes: six expected rejections and four expected
nondetections. Truncating an unwitnessed tail, a stolen-key rewrite beyond the
trusted prefix, or joint rollback without an independently retained reference
remains outside the corresponding detection guarantee.

The [H1 rerun](../benchmarks/results/current-evidence-2026-11-10/h1/report.md)
retained the original ten seeds, 24-record restored snapshot, 32-record current
history, batch size eight, local-checkpoint adapter and honest reachable
loopback witness.

| Case | Observed | Interpretation |
| --- | --- | --- |
| Local history restored to 24 | PASS, 10/10 | No independent newer reference; currentness is not established |
| Witness at 32, no retained client pin | INCONCLUSIVE / WITNESS_AHEAD, 10/10 | Original expected FAIL remains unmet; all ten are outcome mismatches |
| Witness at 32, retained client pin at 32 | FAIL / WITNESS_STATE_CONFLICT, 10/10 | Rollback rejected relative to independently retained state |
| Current local, current witnessed and recovered controls | PASS, 10/10 each | All three control conditions passed |

There were no invalid H1 trials. The classifications match the
[original evidence](h1-writer-rollback.md). Current online reports additionally
carry `STATUS_CURRENTNESS_UNCONFIRMED`: supplied signed active status does not
prove globally current revocation knowledge. `PASS` must not erase that caveat.
These are synthetic same-host comparisons, not independently administered
witness deployments. The harness explicitly opts into local-only writer setup;
it does not measure the default verified startup or restore safeguards.

## Local batching measurements

The [local report](../benchmarks/results/current-evidence-2026-11-10/local/report.md)
uses the unchanged manifest: seeds 7–16, 100 warmup records, 1,000 measured
records per run, requested size 1 KiB, batches 128 and 16, in-process witness.
All twenty full integrity checks passed; all runs witnessed through record
1,100 and reported zero submission retries. Measured serialized record
envelopes totaled 1,583,101 bytes per run; requested size is not stored
envelope size. Database allocation varied across runs, as retained in raw rows.

| Metric, mean across ten runs | Batch 128 | Batch 16 |
| --- | ---: | ---: |
| Per-run median append latency | 1.6594 ms | 1.6578 ms |
| Records / summed append-call time | 592.7904/s | 594.4329/s |
| Per-run median successful submit time | 58.0398 ms | 7.9425 ms |
| Full integrity verification | 0.5059 s | 0.5028 s |
| Summed successful submit time per run | 0.457759 s | 0.502140 s |
| Timed checkpoint submissions per run | 8 | 63 |

The generated report supplies run-level bootstrap 95% intervals for its four
metrics. Append throughput excludes checkpoint submissions and is not an
end-to-end ingestion rate. Submission timings exclude receipt persistence and
do not isolate witness CPU. The untimed warmup checkpoint adds one accepted
checkpoint per run. Configurations ran in historical block order, so host drift
or order effects are not controlled; this differs from SPEC Section 22's
randomized-order recommendation. No causal cross-revision timing comparison
or new WAN H2 estimate is claimed. Configured batch size is not measured loss
or a maximum backlog under an arbitrary outage.

## Canonical H3 outage

The [H3 follow-up](../benchmarks/results/current-evidence-2026-11-10/h3/report.md)
completed all twenty runs in the frozen randomized order, with no incomplete
runs. All healthy baselines and final online checks passed. All ten outage
online checks returned `INCONCLUSIVE`, `FRESHNESS_INCONCLUSIVE`, exit 4;
all ten offline checks passed. Each outage retained identical pending bytes,
recovered the same checkpoint explicitly, and finished at record 32 and
checkpoint index 3.

Record 24 commit-to-persisted-receipt medians were 9.451 ms healthy and
2,991.997 ms during the three-second fault. The mean paired difference was
2,979.187 ms, with a run-pair bootstrap 95% interval of
2,973.493–2,983.929 ms. Observed maximum pending backlog was 16 records in
each outage; median recovery after restoration was 21.226 ms. There were ten
failed submissions, ten explicit same-checkpoint retries and zero automatic
retries. Request sizes were 256 bytes; this is not signed-record envelope size.

The functional interpretation agrees with the original and
[October 31 follow-up](h3-witness-outage-review-2026-10-31.md). These timing
values are separate observations, not a performance regression comparison.
The fault still consists of one loopback accept-and-drop mode with manual
recovery. The original feasibility pilot was not rerun; generated-report pilot
references remain historical. Automatic worker costs, other transport faults,
maximum safe outage duration and physical power-loss behavior are unmeasured.

## RQ4 repository snapshot

The [current collection](../benchmarks/results/current-evidence-2026-11-10/rq4/report.md)
uses the same descriptive methods as the [original RQ4 record](rq4-operational-burden.md),
with an explicit command-line commit override. The frozen manifest still names
its historical default; the current result and provenance identify the actual
selected revision. This is a source snapshot, not a pass/fail experiment.

| Proxy | Original measured revision | PR 50 merge revision |
| --- | ---: | ---: |
| Python source files / lines | 23 / 4,457 | 38 / 7,803 |
| Test files / AST test definitions | 38 / 310 | 92 / 649 |
| Documentation files / lines under docs | 24 / 2,461 | 50 / 4,835 |
| Architecture decisions | 2 | 11 |
| Direct external / locked external packages | 9 / 24 | 9 / 24 |

AST definitions are not pytest cases. The collector reports Python versions
but does not enumerate the twelve OS/dependency validation jobs; see the
[validation matrix](../docs/release/validation-matrix.md). Calendar spans,
commit-message matches and line counts do not measure labor, review quality,
cognitive burden, usability or monetary cost. Increased implementation/test
size is descriptive and does not itself establish quality or maintainability.

## Preservation and remaining scope

All 193 recorded historical result, manifest, protocol and preprint files were
verified unchanged; all 525 original H3 runtime-file checksums were verified.
The public subset omits databases, bundles, keys and verifier state while
retaining the raw JSON measurements unchanged. Its checksum list covers that
subset, not downloadable copies of excluded state.

Historical Linux/WAN runs, the full proposed A/B/C comparison and workload
matrix, independent witness administration, default startup and automatic
worker performance remain outside this refresh. The preprint has not been
regenerated with these values. The private document demo, current operating
instructions, critical-change review and exact release artifacts have separate
acceptance work. This evidence refresh does not authorize a release.
