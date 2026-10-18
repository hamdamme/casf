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
  model says little about fast server pairs; a two machine wide area
  run remains the open item.
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

- Remote witness over real wide area networks: the runner drives the
  witness over loopback HTTP with an injected round trip delay, which
  covers one controlled network class; an uncontrolled multi machine
  deployment remains unmeasured and no wide area claim is made beyond
  the injected model.
- Multiple concurrent writers in benchmarks: correctness covered by
  T06; throughput under contention not measured yet.
