# Streaming verification measurements

Recorded 2026-10-27 on macOS ARM with Python 3.13.17. Synthetic workloads
measure implementation behavior, not production capacity or a security proof.
Baseline: `1c7b7ee280fdb86b7d1ba1c304acc1d69017f004`. The candidate algorithm
is identified by the source hashes in `source-hashes.json`. Source comments
and documentation were refined during the measurement batch; the measured
algorithm was unchanged. No historical benchmark files were replaced.

## Procedure

Input generation completed before any measurement process. Each record has
a 1024 character synthetic payload field and valid signatures and linkage.
The generator uses fresh ephemeral test keys and saves only public evidence;
it reproduces the workload shape rather than identical signed bytes.
All baseline and candidate runs at each configuration consumed the same files,
confirmed by SHA256 hashes in `runs.json`.

Each configuration uses one fresh process with tracemalloc for Python peak
allocation, plus three fresh processes without tracing for timing. Timing
covers bundle reading and complete requested verification, including signatures,
checkpoint comparisons, and EOF checks. Imports, trust loading, input creation,
and output hashing are outside the timed section. Baseline and candidate order
alternates across timing trials. Timing is measured on a development machine,
not a dedicated performance host. Report medians; three trials do not establish
statistical significance. Peak allocation has one observation per configuration.

The fixed family anchors only the first 128 records with one checkpoint and
receipt. Later records are an explicitly allowed unwitnessed suffix. This
isolates record memory growth and does not claim full anchoring. The growing
family anchors all records with a checkpoint every 128 records and a final
partial batch. At 16384 records it contains 128 checkpoints and 128 receipts.
Both families run integrity and anchored verification. Online verification is
covered by regression tests; no online latency claim is made here.

`runs.json` contains all 96 runs. Absolute source checkout prefixes are
normalized to `baseline` and `repo`; numeric measurements are unchanged. RSS is
also recorded in bytes on macOS, but includes interpreter imports and native
allocations across the process lifetime. The table below uses traced Python
peak bytes divided by 1048576. It excludes native allocations and OS file cache.

## Results

| Evidence | Mode | Records | Before peak MiB | After peak MiB | Before median seconds | After median seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| fixed | integrity | 128 | 0.759 | 0.316 | 0.082 | 0.082 |
| fixed | integrity | 2048 | 7.635 | 0.317 | 1.203 | 1.204 |
| fixed | integrity | 16384 | 58.802 | 0.318 | 9.541 | 9.640 |
| fixed | anchored | 128 | 0.759 | 0.315 | 0.083 | 0.083 |
| fixed | anchored | 2048 | 7.634 | 0.318 | 1.289 | 1.262 |
| fixed | anchored | 16384 | 58.802 | 0.318 | 9.727 | 9.423 |
| growing | integrity | 128 | 0.757 | 0.316 | 0.082 | 0.083 |
| growing | integrity | 2048 | 7.700 | 0.384 | 1.235 | 1.210 |
| growing | integrity | 16384 | 59.357 | 0.886 | 9.772 | 9.466 |
| growing | anchored | 128 | 0.758 | 0.316 | 0.084 | 0.086 |
| growing | anchored | 2048 | 7.700 | 0.386 | 1.196 | 1.195 |
| growing | anchored | 16384 | 59.355 | 0.916 | 9.617 | 9.589 |

The fixed protocol family demonstrates that record storage no longer scales
with total record count on the streaming path. The growing family shows the
remaining bounded protocol cost. Its peak is not constant as protocol evidence
increases. The implementation retains at most the configured evidence budgets
and checkpoint traversal limit, plus one decoded record and parser workspace.
Raising those budgets raises the memory ceiling. Histories beyond the configured
limits reject or return the existing inconclusive budget result; they are not
silently accepted or discarded.

At 16384 records the median time change ranges from about 3 percent faster to
1 percent slower. These observations do not indicate a meaningful regression.
They cover these workload sizes and machine only. They do not establish maximum
safe budgets, concurrency performance, adversarial worst case timing, or general
throughput. The eager compatibility reader still intentionally retains records.

## Reproduction

Use separate source directories for the baseline commit and candidate with the
same locked Python environment. Set PYTHONPATH to the selected implementation's
`src` for each measurement. Run the candidate `benchmarks/streaming.py` harness.
Generation additionally requires the candidate repository root on PYTHONPATH
for its existing test fixture helpers.

```sh
PYTHONPATH="$candidate/src:$candidate" "$python" "$candidate/benchmarks/streaming.py" generate "$inputs/fixed-16384" --count 16384 --anchor-records 128
PYTHONPATH="$baseline/src" "$python" "$candidate/benchmarks/streaming.py" measure "$inputs/fixed-16384" --reader eager --mode anchored
PYTHONPATH="$candidate/src" "$python" "$candidate/benchmarks/streaming.py" measure "$inputs/fixed-16384" --reader stream --mode anchored
```

Set the shell variables to explicit local directories and the locked Python
interpreter. Repeat at 128, 2048, and 16384 records. Omit `--anchor-records`
for the growing family. Repeat with `--mode integrity`. Add `--no-trace` for
timing, three times per configuration, alternating implementation order.
Do not generate input inside a measurement process.
