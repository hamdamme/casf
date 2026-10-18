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

Second machine execution (T19): the same manifest ran on an Ubuntu
laptop (Linux 6.14, Python 3.12.3); record counts, witnessed counts,
and database sizes are byte identical to the committed macOS rows,
so the procedure reproduces across machines
(benchmarks/results/local-subset-v1-linux/). Latencies differ by
hardware, as expected: append p50 is 11.3 ms on the laptop against
0.68 ms on the Mac.

Extended matrix (benchmarks/manifest.v2.json,
benchmarks/results/linux-matrix-v2/): on the laptop, 1 KiB records
append at about 75 records per second, 4 KiB at 60, 16 KiB at 39;
full verification grows linearly at about 1 ms per 1 KiB record
(10.1 s for 10100 records, H3 holds). The 25 ms injected round trip
moves witness p50 from 196 ms to 209 ms: on this slow hardware the
witness signature processing dominates the network term, an honest
observation that limits how strongly the delay model generalizes.
Total wall clock for the full matrix was about 2.2 hours on that
machine (RQ4 evidence).

## Validity controls

Warmup runs are discarded. Local witness runs underestimate
independent deployment cost and say so. Synthetic workloads may not
represent production audit patterns. The author wrote and reviewed
the code and the tests, so assessment bias is possible; external
review of the protocol and the experimental design is sought and is
not claimed as completed. No formal proof and no penetration testing
are claimed from the test suite (SPEC §21).
