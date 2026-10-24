# Release notes, 0.1.0.dev0 release candidate

Prepared under C12 (SPEC §27). These notes are drafted for review;
nothing is published by this file. Status reviewed on 2026-10-24;
experiment results retain their original recorded environments.

## What this is

CASF is an experimental cryptographic audit and signing framework:
an append oriented record chain with canonical JSON, Ed25519
signatures, a witness service that accepts only valid extensions,
and a verifier that runs offline from pinned public keys. This
candidate covers the full local profile: writer with transactional
SQLite storage, witness with durable receipts over HTTP, online
freshness queries, export bundles and restore drills, sealing and
epoch rotation, a command line interface with stable exit codes, and
the benchmark and attack harnesses used for the research evaluation.

## Verified state at this candidate

- The dependency update in commit `b96fa4a` passed 213 tests on each
  of Python 3.12, 3.13, and 3.14 on macOS. [PR 4 CI](https://github.com/hamdamme/casf/actions/runs/40066783179)
  passed all three versions on Linux, including lint, typing, tests,
  builds, and installation of the wheel in a fresh environment.
- The current wheel checks cover import and CLI startup. The
  [historical rehearsal](checklist-v0.1.md#clean-install-rehearsal-log)
  records key generation, initialization, append, export, and
  integrity verification with result PASS on 2026-10-12.
- Detection matrix (benchmarks/results/detection-v1/): all ten
  predeclared cases match expectations, including the documented
  boundaries T18, T20, and T21.
- Benchmark subset (benchmarks/results/local-subset-v1/): pinned
  manifest, ten runs per configuration, run level bootstrap
  intervals. [Linux replication](../../benchmarks/results/local-subset-v1-linux/report.md)
  contains 20 recorded runs across the two configurations.
- The [Linux matrix](../../benchmarks/results/linux-matrix-v2/report.md)
  contains 40 recorded runs across four configurations, including
  the 25 ms injected delay case.
- The [wide area matrix](../../benchmarks/results/wide-area-v3/report.md)
  contains 20 recorded runs across two batch sizes. The raw files
  record 12 runs at `84c5444` and eight at `52688fd`. The latter
  commit only added preliminary result files; experiment code and
  configuration were unchanged between those commits.

## Explicitly not claimed

- No formal proof, no penetration testing, no external audit.
- Rollback protection for the unwitnessed tail (T18), detection of a
  false suffix written with a stolen writer key (T20), and detection
  of witness rollback by an isolated client with no retained pin
  (T21) are documented boundaries, not features.
- Benchmark observations cover the recorded machines, workloads,
  and one wide area network path. They do not establish general
  deployment throughput. Writer geography was not recorded for the
  wide area runs; their append rate excludes witness completion time.

## Known open items before any 1.0 discussion

- Resolve the HTTP server conflict under D05.
- Review the locked dependencies and their licenses, and address the
  build warning about license metadata.
- Obtain final maintainer approval of release artifact hashes and notes.
- Maintainer test submission to the private vulnerability reporting
  channel.
- External review of the protocol and experimental design, sought
  and not yet received.
