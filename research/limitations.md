# Limitations

Current interpretation of the recorded evidence, using the canonical labels
in the [research guide](README.md). Original reports and measurements remain
unchanged. No stronger claim is made than those observations support.

## Boundaries confirmed by the detection matrix

The matrix (benchmarks/results/detection-v1/) confirms these attacks
correctly remain undetectable offline:

- Silent loss of the unwitnessed tail passes integrity and anchored
  verification (T18). No rollback protection is claimed without an
  external anchor.
- A false suffix written with a stolen writer key after the last
  witnessed checkpoint passes anchored verification offline when the policy
  explicitly allows unwitnessed records (T20).
  Rewriting inside the witnessed prefix is detected as divergent.
- Witness rollback against an isolated client holding no earlier pin
  is not detectable; detection holds only for a client that retained
  a checkpoint pin (T21). This is a conditional failure, and no
  unconditional detection is claimed.

## Method limitations

- The extended matrix ran on one old laptop; its absolute numbers
  reflect that hardware and are reported alongside the macOS subset
  rather than generalized. On that hardware the witness processing
  cost dominates the injected 25 ms network delay, so the delay
  model says little about fast server pairs. This fixed delay remains
  separate from the canonical outage experiment below.
- The wide area matrix measured exactly one network path (one
  writer, one Lightsail witness in Frankfurt (eu-central-1),
  writer geography not recorded in the artifacts); its round trip
  numbers describe that path and are not a general wide area claim.
- Workloads are synthetic fixed size events; production audit
  patterns may differ.
- Ten runs per configuration is the SPEC minimum; the extended
  matrix met it on a second machine, wider hardware diversity is
  still open.
- Maintainer development and test review create assessment bias. Limited
  external review examined witness and online behavior and part of the
  verifier; it did not cover the entire implementation or benchmark methods.
  The [scope record](../docs/release/phase3-closeout-2026-10-28.md#review-coverage)
  lists unexamined areas. No independent security audit is claimed.
- SQLite append only triggers guard honest writers; an attacker
  holding the database file can drop them, which is why integrity
  rests on the hash chain and the witness, not on the triggers
  (confirmed by the tamper cases, which drop the triggers first).

## Canonical H1 and H2 scope

The [H1 comparison](h1-writer-rollback.md) did not fully meet its original
expected result: without a retained client checkpoint, the honest reachable
witness returned INCONCLUSIVE with WITNESS_AHEAD rather than FAIL in ten
runs. With the retained checkpoint, all ten returned WITNESS_STATE_CONFLICT.
This distinction is retained; refusal to accept is not relabeled as the
predeclared positive failure classification.

Canonical H2 is supported only for successful client submit time per record
in one matched historical remote workload. It does not isolate server CPU
cost. Configured batch limits are not measurements of record loss and do not
bound backlog during arbitrary outages. See the [batching interpretation](README.md#batching-interpretation).

## Canonical H3 outage experiment

The recorded experiment in `benchmarks/results/h3-witness-outage-v1/` supports
both canonical H3 outcomes within its tested scope. Ten matched loopback
runs showed a longer record 24 commit to persisted receipt interval during
the fixed three second outage; all ten online freshness attempts became
inconclusive while offline integrity checks passed. The experiment did
not observe data loss. Authority status currentness remained unconfirmed
even when online witness freshness passed.

The evidence uses one host, one accept and close fault mode, one batch size,
32 synthetic events, ten seed pairs, and a manual recovery call. It does
not cover wide area partitions, delayed responses, connection refusal,
witness process failure, an automatic recovery worker, larger workloads,
or the full SPEC §22 matrix. The [October 31 follow up](h3-witness-outage-review-2026-10-31.md)
records later transport behavior separately; the two result sets are not pooled.
The historical injected delay runs are not
outage evidence. See `h3-witness-outage.md` for the method, measurements,
and separate H3a and H3b conclusions.

## Omitted configurations and reasons

- Broader wide area coverage remains unmeasured. The
  [recorded wide area matrix](../benchmarks/results/wide-area-v3/report.md)
  contains 20 runs on one path to a witness in Frankfurt. Writer
  geography is missing, so these results cannot establish behavior
  across locations or network conditions. The injected delay matrix
  remains a separate controlled experiment.
- Multiple concurrent writers in benchmarks: correctness covered by
  T06; throughput under contention not measured yet.
