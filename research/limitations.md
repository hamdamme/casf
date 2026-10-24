# Limitations

Declared limitations and negative findings. Never overwrite with
stronger claims than the experiments support (SPEC §23). Updated
with the second machine matrix results.

## Boundaries confirmed by the detection matrix

The matrix (benchmarks/results/detection-v1/) confirms these attacks
correctly remain undetectable offline:

- Silent loss of the unwitnessed tail passes integrity and anchored
  verification (T18). No rollback protection is claimed without an
  external anchor.
- A false suffix written with a stolen writer key after the last
  witnessed checkpoint passes anchored verification offline (T20).
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
  model says little about fast server pairs.
- The wide area matrix measured exactly one network path (one
  writer, one Lightsail witness in Frankfurt (eu-central-1),
  writer geography not recorded in the artifacts); its round trip
  numbers describe that path and are not a general wide area claim.
- Workloads are synthetic fixed size events; production audit
  patterns may differ.
- Ten runs per configuration is the SPEC minimum; the extended
  matrix met it on a second machine, wider hardware diversity is
  still open.
- Self authored code and self reviewed tests create assessment bias;
  external review has not happened and is not claimed.
- SQLite append only triggers guard honest writers; an attacker
  holding the database file can drop them, which is why integrity
  rests on the hash chain and the witness, not on the triggers
  (confirmed by the tamper cases, which drop the triggers first).

## Omitted configurations and reasons

- Broader wide area coverage remains unmeasured. The
  [recorded wide area matrix](../benchmarks/results/wide-area-v3/report.md)
  contains 20 runs on one path to a witness in Frankfurt. Writer
  geography is missing, so these results cannot establish behavior
  across locations or network conditions. The injected delay matrix
  remains a separate controlled experiment.
- Multiple concurrent writers in benchmarks: correctness covered by
  T06; throughput under contention not measured yet.
