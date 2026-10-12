# Limitations

Declared limitations and negative findings. Never overwrite with
stronger claims than the experiments support (SPEC §23). Updated at
the end of Phase 8.

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

- All measurements are local: one machine, local witness, no network
  delay injection yet. Local witness runs underestimate independent
  deployment cost. The delayed network matrix is planned for the
  Linux machine before M8.
- Workloads are synthetic fixed size events; production audit
  patterns may differ.
- Ten runs per configuration is the SPEC minimum; wider replication
  is planned on the Linux machine.
- Self authored code and self reviewed tests create assessment bias;
  external review has not happened and is not claimed.
- SQLite append only triggers guard honest writers; an attacker
  holding the database file can drop them, which is why integrity
  rests on the hash chain and the witness, not on the triggers
  (confirmed by the tamper cases, which drop the triggers first).

## Omitted configurations and reasons

- Record sizes below 1 KiB and above 1 KiB: deferred to the Linux
  matrix to keep the local subset a smoke level reference.
- Remote witness over real networks: deferred; the in process and
  loopback transports cannot represent wide area delay honestly.
- Multiple concurrent writers in benchmarks: correctness covered by
  T06; throughput under contention not measured yet.
