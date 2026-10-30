# Research protocol

Experimental design for RQ1 to RQ4 and H1 to H3 (SPEC §22-§23).
Historical experiment status recorded on 2026-10-24: local experiments,
Linux replication, the Linux matrix with injected delay, and the wide
area matrix are present. Their raw files retain the original environments
and commit identifiers. The canonical outage hypothesis in SPEC §22 was
tested separately on 2026-10-29; its method and results are recorded in
`h3-witness-outage.md`. Release approval remains separate.

## Questions and hypotheses

- RQ1 (correctness under the declared model): does verification
  detect every mutation the threat model says must be detectable.
  H1: every in model mutation at any chain position produces FAIL.
- RQ2 (boundaries): which attacks correctly remain undetectable.
  H2: silent tail loss (T18), a false suffix under a stolen writer
  key (T20), and witness rollback against an isolated client (T21)
  pass verification and are documented as boundaries, not detections.
- RQ3 (cost): append, witness round trip, and verification latency
  at fixed record sizes and checkpoint batch sizes. Historical protocol
  H3 predicted linear verification cost. Its evidence remains in the
  extended matrix below and is not the canonical H3 in SPEC §22.
- RQ4 (procedure): an independent rerun of the pinned manifest
  reproduces sizes and counts (T19).

Canonical SPEC §22 H3 predicts that network outages increase time to
witnessed completion and may prevent a freshness conclusion. It was
tested as two outcomes, H3a and H3b, in the separate controlled outage
experiment. Historical protocol labels in old reports remain unchanged.

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
(10.1 s for 10100 records, consistent with historical protocol H3).
The 25 ms injected round trip moves witness p50 from 196 ms to 209 ms:
on this slow hardware the
witness signature processing dominates the network term, an honest
observation that limits how strongly the delay model generalizes.
Total wall clock for the full matrix was about 2.2 hours on that
machine. This records run duration; elapsed time alone does not establish
reproducibility. RQ4 evidence is the independent rerun of the pinned manifest,
which reproduced record counts and database sizes as described above.

Wide area matrix (benchmarks/manifest.v3.json,
benchmarks/results/wide-area-v3/): writer on a Dell Linux machine,
witness on an AWS Lightsail instance in Frankfurt
(eu-central-1), 20 runs, zero failures. RQ3: a witnessed checkpoint round
trip cost about 1.18 s at batch 128 and 0.67 s at batch 16 on this
path, while append throughput stayed at 1273 to 1462 records per
second because checkpoint submission is asynchronous. RQ3:
batching cuts total witness time per 10000 records from about 420 s
(626 submissions) to about 95 s (80 submissions), roughly 9.5 ms
against 42 ms per record, in exchange for a longer pending
unwitnessed suffix (128 against 16 records). The longer suffix is a security
trade off relevant to RQ2; this measurement does not test H2. One path only;
no general wide area claim is made.

## Canonical H3 outage experiment (SPEC §22)

The controlled loopback experiment is specified in
`benchmarks/h3-witness-outage.v1.json`; the feasibility pilot is separate
and excluded. Ten matched seed pairs were measured, with fresh writer,
witness, and verifier state for each run. Each run used 32 synthetic
events, checkpoint batches of eight, and the same event schedule in both
conditions. The proxy accepted and read blocked HTTP requests, then closed
the connection without forwarding. The witness process and database
remained intact.

H3a was supported within this tested scope. For record 24, the median time
from local commit to persisted receipt was 10.042 ms in healthy runs and
2983.300 ms in outage runs. The paired mean difference was 2969.935 ms;
its run pair bootstrap 95 percent interval was 2963.087 to 2975.774 ms.
The full nanosecond values are retained in the machine readable summary.

H3b was supported within this tested scope. All ten outage attempts to
verify the already valid baseline bundle online returned INCONCLUSIVE
with `FRESHNESS_INCONCLUSIVE` and exit status 4. Offline integrity
verification passed in all ten runs. Healthy baseline and recovered final
online verification passed in all ten outage runs. Each online PASS also
reported `STATUS_CURRENTNESS_UNCONFIRMED`; the experiment does not establish
currentness of authority status.

The checkpoint through record 24 remained pending with the same signed
bytes after each failed delivery. Local appends continued through record
32, producing a maximum observed unwitnessed suffix of 16 records. After
connectivity returned, one explicit retry per run persisted the receipt;
the median recovery time was 14.561 ms. This is manual recovery through
the existing API, not automatic retry behavior. No data loss was observed
or inferred.

The test covers one accept and close loopback fault, one host, one batch
size, a short synthetic workload, and ten seed pairs. It does not establish
wide area outage behavior, a maximum safe outage length, availability for
other failure modes, or the full matrix proposed by SPEC §22. The results
and raw evidence are in `benchmarks/results/h3-witness-outage-v1/`;
pilot evidence is in `benchmarks/results/h3-witness-outage-pilot-v1/`.

## Recorded experiment commits

The [Linux replication](../benchmarks/results/local-subset-v1-linux/report.md)
contains 20 raw run files and the [Linux matrix](../benchmarks/results/linux-matrix-v2/report.md)
contains 40; all record commit `e8fba21`.

The [wide area matrix](../benchmarks/results/wide-area-v3/report.md)
contains 12 runs recording `84c5444` and eight recording `52688fd`.
The latter commit only added preliminary result files. Package code,
benchmark code, and configuration were unchanged between the two commits.
Both precede the runner retry change in `f91d40a`. The different commit
identifiers are retained as part of the experiment provenance.

## Validity controls

Warmup runs are discarded. Local witness runs underestimate
independent deployment cost and say so. Synthetic workloads may not
represent production audit patterns. The author wrote and reviewed
the code and the tests, so assessment bias is possible; external
review of the protocol and the experimental design is sought and is
not claimed as completed. No formal proof and no penetration testing
are claimed from the test suite (SPEC §21).
