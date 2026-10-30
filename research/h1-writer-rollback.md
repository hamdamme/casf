# H1 writer rollback experiment

Canonical hypothesis (CASF SPEC 001 Section 22): a signed chain with an
external witness (C) detects restoration below the witness retained
state when the witness remains honest and reachable; an isolated signed
chain with only local checkpoints (B) cannot distinguish the same old
valid snapshot from its original history without a newer independent
reference.

This experiment differs from T21: T21 rolls back witness state; here
the witness state is preserved and only the writer store is rolled
back.

Status: executed on 2026-10-29. Raw per run results and the generated
summary live in `benchmarks/results/h1-writer-rollback-v1/`. The
predeclared manifest is `benchmarks/h1-writer-rollback.v1.json`.

## Method

Per run: both arms build the same seeded 24 record history with
checkpoint batch 8, then extend to 32 records. Arm B never contacts a
witness; arm C submits every checkpoint and records receipts. Complete
writer snapshots are taken at 24 and at 32 through the SQLite backup
interface. The writer is then rolled back to the 24 record snapshot
while the witness retains state at 32. Verification runs in a fresh
context per case. Ten independent runs with fixed seeds; fresh
databases per run.

Configuration B production note: the CASF writer accepts at most one
unwitnessed checkpoint (the outbox rule), so a local checkpoint only
profile is not a supported production configuration. B's local
checkpoints were produced by a research-only harness adapter
(`make_local_checkpoint` in `benchmarks/h1_writer_rollback.py`) as
valid signed protocol objects stored beside the writer database, and
evaluated by a research-only consistency check. Production code,
protocol bytes, trust rules, and cryptography were not changed. This
limitation is itself a finding (see below).

The decisive measurement boundary is the verification call, including
the witness round trip for online cases.

## Results

All ten runs produced identical classifications; no invalid trials, no
infrastructure failures.

| case | expected | observed | classification |
| --- | --- | --- | --- |
| B current control | PASS | PASS | as declared, 10 of 10 |
| C current control | PASS | PASS | as declared, 10 of 10 |
| B restored old snapshot | PASS, currentness not established | PASS | as declared, 10 of 10 |
| C restored old snapshot, no retained pin | FAIL | INCONCLUSIVE (WITNESS_AHEAD) | outcome mismatch, 10 of 10 |
| C restored old snapshot, retained pin at 32 | FAIL | FAIL (WITNESS_STATE_CONFLICT) | detection, 10 of 10 |
| C recovered control | PASS | PASS | as declared, 10 of 10 |

For every primary C case the witness was reachable during the decisive
query and returned an authenticated fresh view at count 32, checkpoint
index 3, while the presented evidence anchored at count 24, index 2.
The restored snapshot remained a valid signed history; its integrity
and anchor checks passed.

## Interpretation

The predeclared primary expectation was rejection with FAIL. The
observed outcome was INCONCLUSIVE with WITNESS_AHEAD in all ten runs.
Per the predeclared classification rules, INCONCLUSIVE is not counted
as a detection, so the primary C expectation was not met.

Investigation of the cause: the restored 24 record snapshot is an
authentic prefix of the witnessed history, so no proven mismatch exists
between the evidence and the witness state. The specification maps
proven mismatches to FAIL and missing evidence to INCONCLUSIVE
(Section 15). A witness view ahead of the presented evidence means the
client cannot verify the intervening records, which the witness does
not retain; the verifier therefore refuses to certify the old snapshot
as current instead of declaring it false. This behavior matches
Sections 7 and 15 as written.

The practical protection still holds: in no run was the rolled back
snapshot accepted as current. The difference is in the signal: without
retained client state the verifier reports "cannot confirm currentness"
rather than "rollback detected". With a retained checkpoint pin at 32,
the same restored snapshot produces FAIL with WITNESS_STATE_CONFLICT
in all ten runs, which is a positive detection.

## Verdict on H1 in this scope

- Arm B: supported. The isolated chain validated the restored snapshot
  and could not distinguish it from current history in 10 of 10 runs.
- Arm C, primary configuration (no retained pin): not supported as
  predeclared. The observed INCONCLUSIVE blocks acceptance but is not
  the predeclared rejection.
- Arm C with a retained checkpoint pin: supported. Detection with FAIL
  in 10 of 10 runs.

Overall: H1 is partially supported within the tested conditions.
Detection as a positive failure signal requires verifier retained
state; the witness alone converts silent acceptance into a freshness
refusal. The H1 wording in Section 22 ("detects restoration") is
stronger than the Section 15 result semantics for a client without
retained state; reconciling that wording is a documentation question
for the maintainer, not a code defect found by this experiment.

## Findings beyond the hypothesis

1. Configuration B is not expressible through the production writer
   beyond one unwitnessed checkpoint. If a local checkpoint only
   profile is ever intended, it needs a reviewed design; this
   experiment used an explicit research adapter instead.
2. Section 22 H1 wording and Section 15 result semantics diverge for
   the no retained pin case (documented above).

## Limitations

Loopback execution on one machine; a controlled functional experiment,
not proof of separate administrative operation. One record size near
512 bytes; 24 and 32 record scale; no outage, loss, or delay
injection; synthetic events and test keys. Ten runs cover the declared
configuration only. The broader Section 22 matrix (outages, larger
histories, concurrency) remains unmeasured by this experiment.

## Reproduction

```
PYTHONPATH=src .venv/bin/python -m benchmarks.h1_writer_rollback \
  benchmarks/h1-writer-rollback.v1.json \
  benchmarks/results/h1-writer-rollback-v1
```

The harness refuses to overwrite an existing results directory; remove
or rename it before a rerun. Runs were executed with the working tree
source through PYTHONPATH=src because the development environment also
holds an installed 0.1.0rc1 package copy; the recorded
casf_module_path and casf_source_tree_sha256 in the raw results
identify the tested code.

## Artifact checksums

- manifest sha256: af144a3032c21cadb560c54310e6ae5fda4550e47add52900a818131aa01d4b3
- runs.v1.json sha256: 5c08f6499d8ef0e8b51cf43580323bcd0df5b4de0f646b584e275700daaae159
- report.md sha256: dbbc1f3795b13008da556ed0b88f2e6d94c800376c70495eddad5e6292625f68
