# Research protocol

Experimental design for RQ1 to RQ4 and H1 to H3 (SPEC §22-§23).
Status after Phase 8: harnesses implemented and pinned local runs
executed; the full matrix with network delay injection runs on the
dedicated Linux machine before M8.

## Questions and hypotheses

- RQ1 (correctness under the declared model): does verification
  detect every mutation the threat model says must be detectable.
  H1: every in model mutation at any chain position produces FAIL.
- RQ2 (boundaries): which attacks correctly remain undetectable.
  H2: silent tail loss (T18), a false suffix under a stolen writer
  key (T20), and witness rollback against an isolated client (T21)
  pass verification and are documented as boundaries, not detections.
- RQ3 (cost): append, witness round trip, and verification latency
  at fixed record sizes and checkpoint batch sizes. H3: verification
  grows linearly with record count at constant per record cost.
- RQ4 (procedure): an independent rerun of the pinned manifest
  reproduces sizes and counts (T19).

## Detection experiment (Section 23)

Seeded history: 38 records, checkpoint batch 8, witnessed through 32,
seed 41, synthetic 512 byte events. Each case declares attacker
controls, verifier anchor, connectivity, and expected result before
running; one mutation per controlled copy; positions: beginning,
middle, last witnessed record, unwitnessed tail. Cases and results:
benchmarks/attacks.py and benchmarks/results/detection-v1/.

## Performance experiment (Section 22)

Pinned manifest benchmarks/manifest.v1.json: 1 KiB target records,
1000 records per run, 100 warmup appends discarded, checkpoint batch
128 and 16, 10 runs per configuration, local witness. Raw rows and
the report: benchmarks/results/local-subset-v1/. Run level summaries
with bootstrap intervals; record level pooling is never used.
Environment (operating system, Python, SQLite, cryptography, commit)
is pinned inside every raw row.

## Validity controls

Warmup runs are discarded. Local witness runs underestimate
independent deployment cost and say so. Synthetic workloads may not
represent production audit patterns. The author wrote and reviewed
the code and the tests, so assessment bias is possible; external
review of the protocol and the experimental design is sought and is
not claimed as completed. No formal proof and no penetration testing
are claimed from the test suite (SPEC §21).
