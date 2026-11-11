# CASF research guide

This is the current guide to research terminology and evidence. Canonical
labels follow [CASF SPEC 001 section 22](../docs/specification/CASF_SPEC_001.md#22-benchmark-and-applied-research-methodology).
Original reports, raw measurements and the historical protocol retain their
original labels and numbers. The [preprint](preprint/README.md) presents the
research interpretation, not a performance certification of current software.

The [10 November implementation follow-up](current-evidence-2026-11-10.md)
reruns the affected local detection, rollback, batching and outage studies and
refreshes RQ4 at an identified revision. Its [raw evidence](../benchmarks/results/current-evidence-2026-11-10/README.md)
is separate from the historical records below. H1's primary expectation remains
unmet; the historical WAN/Linux results and preprint are unchanged.

## Canonical questions and hypotheses

| Label | Question or hypothesis | Evidence and outcome |
| --- | --- | --- |
| RQ1 | Which rollback and fork cases become detectable with independent witness state? | [Detection matrix](../benchmarks/results/detection-v1/report.md) and [H1](h1-writer-rollback.md). The full proposed three configuration comparison was not completed. |
| RQ2 | What latency, throughput, storage and network costs does witnessing add? | Historical local, Linux and wide area reports measure selected metrics. The full metric set and a witness performance baseline are absent. |
| RQ3 | How do batching and outages affect the pending unwitnessed suffix? | Matched wide area batching measurements and the controlled H3 outage. Configured batching bounds are not measured record loss or a bound on an arbitrary outage backlog. |
| RQ4 | What operational burden and implementation complexity does CASF introduce? | Addressed descriptively through repository complexity and process proxies. Developer hours, cognitive load, usability, and total cost were not measured. See [RQ4](rq4-operational-burden.md). |
| H1 | A witnessed configuration detects restoration below honest reachable witness state, while an isolated signed local history cannot distinguish the old valid snapshot. | Tested, but the original expected outcome was not fully met. Local history passed in 10 of 10 runs; witness without a retained pin returned INCONCLUSIVE with WITNESS_AHEAD in 10 of 10, rather than the expected FAIL; a retained pin gave FAIL with WITNESS_STATE_CONFLICT in 10 of 10. |
| H2 | Larger checkpoint batches reduce witness overhead per record while increasing the pending suffix under comparable loads. | Supported within the matched historical workload for successful client submit elapsed time per record. Server processing was not isolated. See the interpretation below. |
| H3 | Outages increase time to witnessed completion and can prevent a freshness conclusion. | Supported within ten matched pairs under one three second loopback outage, one batch size and manual recovery. See [original H3](h3-witness-outage.md) and the separately recorded [transport follow up](h3-witness-outage-review-2026-10-31.md). |

Only H1, H2 and H3 are canonical hypotheses. RQ4 is a research question,
not an additional hypothesis. Its [collector report](../benchmarks/results/rq4-operational-burden-v1/report.md)
measures the selected tracked snapshot at `7c388d385242238a40e572ed67e7e5fc9a1ab194`;
it does not count today's checkout or quantify human effort.

## Historical label crosswalk

The [historical protocol](protocol.md) used a different numbering scheme.
Its body is retained as a historical record, including its original summaries.

| Historical label | Historical meaning | Relationship to the canonical scheme |
| --- | --- | --- |
| RQ1 and H1 | Detection correctness and rejection of in model mutations | Informs canonical RQ1; historical H1 is not the canonical rollback comparison. |
| RQ2 and H2 | Security boundaries and expected nondetection cases | Informs canonical RQ1 and its limitations; not canonical H2 batching. |
| RQ3 and H3 | Computational cost and predicted linear verification cost | Informs canonical RQ2; historical H3 is not the outage hypothesis. |
| RQ4 | Reproducibility of selected outputs on another machine | A separate procedure result, not canonical RQ4 operational burden. Elapsed run time alone is not reproducibility evidence. |

The later section explicitly titled canonical H3 in that historical protocol
already uses the specification's outage meaning. Separate local RQ2 drafts
are unfinished work and are not part of the canonical evaluated evidence.

## Batching interpretation

The wide area raw files contain ten runs per batch size, each with 10,000
measured records, the same target event size and matched seeds. The measured
mean sum of successful client submit round trips is **93.86 seconds** for
batch 128 and **477.64 seconds** for batch 16, or **9.39** and **47.76
milliseconds per measured record**. There are 79 and 625 timed calls;
accepted checkpoint counts of 80 and 626 include an untimed warmup checkpoint.
These are client elapsed times, not isolated witness CPU measurements.

The configured pending suffix values are 128 and 16 records under this
batching procedure. They are not measured loss, nor a maximum outage backlog.
The runner's append throughput excludes checkpoint submission time; it is
not evidence of an automatic asynchronous submission worker in CASF.
The older report's approximate 95 and 420 second summary remains historical.
The preprint's values above derive from the preserved raw sums, not from
replacing or rerunning those measurements.

The two recorded source revisions changed only result files between them.
The path to one witness in Frankfurt and missing writer geography limit
interpretation. See [the source report](../benchmarks/results/wide-area-v3/report.md),
[manifest](../benchmarks/manifest.v3.json), and
[preprint results](preprint/CASF_Preprint.md#56-wide-area-batching-result).

## Practical demonstrations and review

The private PDF demonstration is separate from the synthetic benchmarks.
Integrity and anchored verification passed; an external SHA 256 comparison
matched the original file and rejected a modified copy. Online success was
reported from an earlier interactive demonstration and was not independently
rerun during evidence collection. Authority status currentness remained
unconfirmed. No screenshots were captured.

A copied signed record with one body field changed was rejected with
`RECORD_HASH_MISMATCH` and exit status 1. The unchanged envelope digest failed
comparison before signature verification; this is not evidence that the
signature check produced that diagnostic. Private demonstration materials
remain outside this repository.

Limited external review covered witness and online behavior and part of the
verifier. The [recorded scope and dispositions](../docs/release/phase3-closeout-2026-10-28.md#review-coverage)
identify areas not reviewed. This was not an independent security audit.
See [limitations](limitations.md) and [provenance](preprint/historical-provenance.md)
for boundaries on interpretation and reproducibility.
