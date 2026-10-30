# Canonical H3 controlled witness outage experiment

## Question and scope

Canonical H3 in CASF SPEC §22 is: “Network outages increase time to witnessed completion and may prevent a freshness conclusion.” This report tests H3a (witnessed completion time) and H3b (online freshness during unreachability) separately. It does not test the historical protocol H3 about linear verification cost.

The fault was one controlled loopback HTTP mode. The proxy accepted the connection, read the complete request body, and closed the connection without forwarding it while blocked. The same proxy path forwarded healthy requests. The witness process and its durable SQLite state remained running. This does not model a separate host or generalize to every network failure.

## Frozen method

The measured manifest is `benchmarks/h3-witness-outage.v1.json`; it specifies ten matched seeds, ten independent fresh writer, witness, and verifier contexts per condition, 32 synthetic events, a fixed 256 byte target event request, a 10 millisecond intended arrival interval, checkpoint batches of eight, a 0.5 second client budget, no automatic online retries, a three second outage, and a ten second recovery deadline. The randomized order was seeded with 20261029 and is recorded in `run-order.json`. Each run generates keys deterministically from its seed; healthy and outage members of a pair use the same seed and event requests.

Warmup was a separately reported feasibility pilot. It is excluded from measured analysis. Database creation, key generation, and log registration were completed before timing. CASF protocol operations were not discarded as warmup. The outage configuration witnessed records 1–16 before the outage, attempted checkpoint 24 once while blocked, continued local appends through record 32, explicitly retried the identical pending checkpoint after restoration, then witnessed record 32. A separate state file was used for each CLI verification.

## Results

Measured configurations completed 20 of 20 runs; 0 runs were incomplete and are retained in their per-run files. The H3a endpoint measure is record 24 commit to the writer’s durable persistence of a valid receipt for its covering checkpoint. This run-level measure is paired by workload seed; records are not treated as independent replications.

| Measure | Healthy | Outage |
| --- | ---: | ---: |
| Record 24 commit to persisted receipt, run-level median | 10041875.0 ns | 2983300375.0 ns |
| Run-level mean | 9800683.2 ns | 2979735579.2 ns |
| Descriptive median of per-run median append latency | 1392572.5 ns | 1241853.5 ns |

Paired outage minus healthy difference for the record 24 completion measure: n=10, mean 2969934896 ns, median 2972824375.5 ns, bootstrap 95% percentile interval [2963087004.3, 2975774041.9] ns. The bootstrap resamples independent run pairs. This is evidence for H3a only within this configuration.

For H3b, 10 of 10 outage runs returned online `INCONCLUSIVE` with `FRESHNESS_INCONCLUSIVE` and exit status 4 for the already valid baseline bundle. Offline integrity verification passed in 10 of those runs. The witness count remained 16 at checkpoint index 1 after both the online query and failed checkpoint submission. Baseline and final online verification passed in 10 and 10 outage runs respectively. Their reports also carried `STATUS_CURRENTNESS_UNCONFIRMED`; this experiment did not establish authority status currentness.

Maximum unwitnessed backlog in the outage runs was 16 records. It is an observed pending suffix, not observed data loss. Recovery duration from restoration until receipt persistence had run-level median 14561396.0 ns. Recovery was explicit: one manual call to the existing pending checkpoint submission API, followed by the next normal checkpoint submission. No built-in automatic retry worker is claimed.

There were 10 checkpoint submission failures during outages and 10 explicit same-checkpoint recovery submissions; automatic retry attempts: 0. Attempt level evidence remains in each raw run JSON.

## Interpretation

H3a: SUPPORTED within the tested scope. The conclusion is limited to the measured paired loopback configuration and the completion measure above.

H3b: SUPPORTED within the tested scope. Online unreachability did not convert valid historical evidence into a corruption verdict.

## Reproduction and provenance

Command used for the measured run: `.venv/bin/python -m benchmarks.h3_witness_outage --manifest benchmarks/h3-witness-outage.v1.json --output benchmarks/results/h3-witness-outage-v1`

The measured output directory now exists and the runner will refuse to overwrite it. To execute the frozen manifest again, choose a new output directory, for example: `.venv/bin/python -m benchmarks.h3_witness_outage --manifest benchmarks/h3-witness-outage.v1.json --output benchmarks/results/h3-witness-outage-reproduction-v1`

Environment and source status are recorded in `environment.json`. Its post run, read only supplement reports 16 GiB of physical memory and the mounted data volume; filesystem type was not confirmed. Raw per-run event timing, checkpoint attempts, pending byte digests, receipt persistence, proxy counters, witness snapshots, verification stdout, stderr, reports, exit codes, and incomplete run errors are stored as JSON in `run-*.json`. SHA-256 digests are listed in `SHA256SUMS.txt`.

The separate pilot is in `benchmarks/results/h3-witness-outage-pilot-v1/` and is not included in the measured result counts or statistical intervals.

## Limitations

This is a single-host loopback functional fault experiment with one accept-and-drop transport mode, ten seed pairs, short fixed synthetic workload, one checkpoint batch size, no retry loop, and explicit manual recovery. It does not establish performance across machines, availability under other failures, a maximum safe outage duration, production workload behavior, or the full configuration matrix proposed by SPEC §22. Historical fixed-delay results are not outage results. The historical research protocol H3 about linear verification cost is a separate label and is unchanged by this experiment.
