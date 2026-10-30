# Canonical H3: witness outage experiment

## Question

CASF SPEC §22 states canonical H3 as: network outages increase time to witnessed completion and may prevent a freshness conclusion. This experiment examines two outcomes separately:

- **H3a:** Does an outage increase time from local commit to persisted witness receipt?
- **H3b:** Does witness unreachability prevent an online freshness conclusion while valid historical evidence remains verifiable offline?

The historical research protocol used H3 for linear verification cost. That is a different hypothesis. Its measurements and historical labels are unchanged; the fixed delay experiment is not treated as outage evidence.

## Method

The frozen configuration is [`benchmarks/h3-witness-outage.v1.json`](../benchmarks/h3-witness-outage.v1.json). The feasibility pilot is kept separate in [`benchmarks/results/h3-witness-outage-pilot-v1/`](../benchmarks/results/h3-witness-outage-pilot-v1/) and excluded from the measured results.

Ten seeds were run once in each condition, in the recorded randomized order. Each run used fresh writer, witness, and verifier databases and synthetic keys. Paired runs used the same seeded events. Each workload contained 32 synthetic requests with a 256 byte target, a planned 10 millisecond interval, and checkpoint batches of eight. The writer first committed and witnessed records 1 through 16.

For the outage condition, a loopback HTTP proxy accepted and read each complete request, then closed the connection without forwarding it while blocked. Healthy requests went through the same proxy. The witness process and durable database remained running. The fault started after the record 16 baseline verification and lasted three seconds. One attempt to submit the checkpoint through record 24 was made while blocked. Local appends continued through record 32. The exact pending checkpoint was explicitly submitted once after connectivity returned; the writer then checkpointed through record 32. The writer has no automatic retry worker, and this manual recovery is not described as automatic behavior.

During the outage, online verification queried the already valid record 16 bundle with a separate verifier state. Its complete CLI invocation occurred while the proxy remained blocked. Offline integrity verification of that same bundle used another state file. The test measured local receipt persistence, rather than assuming that request transmission meant witness completion.

## Results

All 20 measured runs completed: ten healthy and ten outage runs. No run was excluded. Run level observations and raw verification output are in [`benchmarks/results/h3-witness-outage-v1/`](../benchmarks/results/h3-witness-outage-v1/); the frozen pilot is outside this analysis.

| Record 24 local commit to persisted receipt | Healthy | Outage |
| --- | ---: | ---: |
| Median across ten runs | 10.042 ms | 2983.300 ms |
| Mean across ten runs | 9.801 ms | 2979.736 ms |

The paired outage minus healthy mean difference was 2969.935 ms, with a median paired difference of 2972.824 ms. The run pair bootstrap 95 percent percentile interval for the mean difference was 2963.087 to 2975.774 ms. The interval is calculated across the ten independent seed pairs, not across records.

H3a is supported within this tested scope: the measured completion interval increased in the outage condition. This does not establish an outage independent maximum or general network behavior.

For H3b, all ten outage verifications returned `INCONCLUSIVE`, included `FRESHNESS_INCONCLUSIVE`, and exited with status 4. Offline integrity verification passed in all ten. Baseline online verification and final online verification after recovery passed in all ten outage runs. Each online PASS also included `STATUS_CURRENTNESS_UNCONFIRMED`; the experiment did not establish currentness of the authority status.

The witness database stayed at 16 records and checkpoint index 1 after the blocked query and failed record 24 submission. Each failed delivery left the exact pending checkpoint bytes available for retry. There were ten failed outage submissions and ten explicit retries of the same checkpoint; automatic retries: zero. Local appends continued, and the maximum observed unwitnessed suffix was 16 records. The median time from restored connectivity to persisted receipt was 14.561 ms. The suffix measures pending records, not data loss; no data loss was observed or inferred.

H3b is supported within this tested scope: a valid historical bundle remained verifiable offline, but the verifier could not establish the witness's current view during unreachability.

## Environment and reproduction

The run environment was macOS 15.6.1 arm64, Python 3.12.11, SQLite 3.54.0, cryptography 50.0.2, eight logical CPUs, and 16 GiB physical memory. The volume report showed 228 GiB total and 22 GiB available at capture; its filesystem type was not confirmed. The supplement was captured after the runs because the initial memory and filesystem queries did not return usable values. Exact system output, source hashes, lock hash, commit, status, and run order are in `environment.json` within the measured results directory. The commit was `1948a982cef52eabbf5cfdb3846d6e9b75ef7413`. All benchmark inputs are synthetic.

The measured run command was:

```sh
.venv/bin/python -m benchmarks.h3_witness_outage --manifest benchmarks/h3-witness-outage.v1.json --output benchmarks/results/h3-witness-outage-v1
```

That output directory now exists and the runner refuses to overwrite it. To repeat the experiment with the frozen manifest, select a new output directory, such as `benchmarks/results/h3-witness-outage-reproduction-v1`. Per run JSON records append durations and commit times, checkpoint creation and coverage, every submission result, receipt persistence, proxy counters, witness snapshots, verification reports and diagnostics, exit codes, and errors. `SHA256SUMS.txt` lists the stored artifact digests.

## Limitations

This is a controlled single host loopback test of one fault: the proxy closes a request after reading it and does not forward it. It uses one checkpoint batch size, 32 synthetic events, ten seed pairs, a three second outage, a 0.5 second request budget, and zero automatic online retries. Recovery was a single explicit API call. The study does not measure other outages, such as a separate host partition, delayed response, connection refusal, witness process failure, or lost response after witness acceptance. It does not test wide area behavior, production workloads, a maximum safe outage duration, larger scale, or the full configuration matrix proposed in SPEC §22.

The results support H3a and H3b only under the declared experiment conditions. They do not establish universal outage tolerance, guaranteed availability, or that the unwitnessed suffix is lost.
