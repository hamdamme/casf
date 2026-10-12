# Release notes, 0.1.0.dev0 release candidate

Prepared under C12 (SPEC §27). These notes are drafted for review;
nothing is published by this file.

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

- 207 tests green: unit, property, conformance vectors, writer crash
  points, witness state transitions, online freshness, lifecycle,
  CLI, benchmark harness, attack harness, and the requirement
  traceability audit.
- Clean install rehearsal passed: wheel built from this commit
  installs into a fresh environment and runs key generation, log
  initialization, append, export, and verification (integrity mode,
  result PASS, exit code 0).
- Detection matrix (benchmarks/results/detection-v1/): all ten
  predeclared cases match expectations, including the documented
  boundaries T18, T20, and T21.
- Benchmark subset (benchmarks/results/local-subset-v1/): pinned
  manifest, ten runs per configuration, run level bootstrap
  intervals.

## Explicitly not claimed

- No formal proof, no penetration testing, no external audit.
- Rollback protection for the unwitnessed tail (T18), detection of a
  false suffix written with a stolen writer key (T20), and detection
  of witness rollback by an isolated client with no retained pin
  (T21) are documented boundaries, not features.
- Benchmark numbers are local smoke level references, not deployment
  throughput claims; the full matrix with network delay injection is
  pending on the Linux runner.

## Known open items before any 1.0 discussion

- Full benchmark matrix with network emulation on the Linux machine.
- Maintainer test submission to the private vulnerability reporting
  channel.
- External review of the protocol and experimental design, sought
  and not yet received.
