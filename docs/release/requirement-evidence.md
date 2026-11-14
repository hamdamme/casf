# Current requirement evidence guide

The [evidence map](../../tests/requirement_evidence.json) connects R01 through
R12 to specification cases T01 through T22 and named test assertions. The
[traceability audit](../../tests/unit/test_traceability.py) checks that the
mapping matches the specification, targets exist, and assertions or expected
exceptions are present. It rejects self references and paths outside tests.
This structural audit does not establish full specification conformance or
prove the correctness of every assertion.

## Current assertion coverage

| Cases | Linked assertion scope |
| --- | --- |
| T01 to T04 | Canonical bytes, malformed JSON, signature and digest checks, sequence gaps, duplicates, reordered records, genesis and log binding. |
| T05 | Export verification and verified ranges, including eager and streaming parity. |
| T06 and T07 | Concurrent sequencing, parent-controlled kills around append/checkpoint commits, and idempotent retries after lock-holder death. |
| T08 and T09 | Invalid extensions, checkpoint conflicts and concurrent forks. |
| T10 and T11 | Restore below a trusted anchor, nonce checks, replay and inconclusive timeout. |
| T12 and T13 | Version, manifest, key and witness identity binding; status serial and revocation checks. |
| T14 | Linked rotation, sealing and explicit discontinuity. |
| T15 | Export snapshots, restore, malformed bundles, missing WAL and late stream errors. |
| T16 and T17 | Input and work budgets, bounded streaming state and selected secret diagnostic checks. |
| T18 | Expected unwitnessed tail nondetection and explicit suffix reporting. |
| T19 | Repeatable small manifest procedure, output-preservation regressions and captured source/import metadata. The [local follow-up](../../research/current-evidence-2026-11-10.md) separates current measurements from historical full experiments. |
| T20 to T22 | Stolen key boundaries, retained and isolated witness rollback cases, signed equivocation and receipt retry after commit. |

The map supplies exact Python node identifiers. These are coverage statements,
not a claim that every variant of each scenario has been exercised.

PR 20 added
`tests/unit/test_cli.py::test_verify_mismatched_provisioned_witness_id_exit_3`
under T12. It rejects mismatched provisioned witness identity with
`WITNESS_ID_MISMATCH`, exit 3 and no new accepted verifier observation.
The completed duplicate, reorder, genesis, cross log splice, concurrent
export, missing WAL and signed equivocation regressions are linked in the
map; they are not outstanding review tasks.

The writer trust tests add T03, T12, T15 and T17 coverage for explicitly
supplied pins during creation, startup, restore and CLI operations. They reject
forged authority signatures, replaced or unprovisioned manifests and wrong
witness identities. Compatibility calls without pins still perform local-only
validation. Those original assertions alone do not establish writer status checking or
fresh witness reconciliation. Later startup and reconciliation tests are linked
in the same map; see [writer recovery](../writer-recovery.md).

## Streaming and trust boundaries

The CLI uses `open_bundle` and checks the unread tail before accepting a
result or saving state. The verifier retains only checkpoint boundary digests
and bounded protocol evidence. Writer export now streams a snapshot;
`read_bundle` and restore remain eager. The [API decision](../adr/ADR-006-streaming-verification.md) and
[streaming measurements](streaming-validation.md) identify this scope.

Missing authority status reports INCONCLUSIVE with UNKNOWN trust. A signed active status
can pass with `STATUS_CURRENTNESS_UNCONFIRMED`; there is no invented expiry
rule or proof of globally current revocation knowledge. See
[verification](../verification.md).

The [implementation reference](../current-reference.md#operational-limits-and-specification-differences)
records differences from the proposed specification, including full startup
verification and restore reconciliation. The [coverage summary](test-coverage-status.md)
records the scope of generated properties, bounded parser mutation campaigns
and the [process crash matrix](../process-crash-testing.md). The latter covers
witness fork competition, exact receipt replay, final seals, atomic retained
state and verified recovery after interrupted HTTP submissions. It does not
establish power-loss durability or exhaustive crash scheduling. See also the
[generated-input guide](../adversarial-testing.md).
An empty remaining review field in the map is not a proof that these broader
requirements have been satisfied.

## Validation review

The [supported matrix](validation-matrix.md) runs the complete mapped suite on
Ubuntu x86_64 and macOS arm64, with Python 3.12–3.14 and both dependency modes.
The source/wheel import guards support the environment provenance part of T19;
they do not repeat historical benchmark measurements. Retained JUnit reports,
actual property statistics and seeded campaign summaries identify the checks
executed for a revision. A missing, skipped or failed required check remains
unresolved even if its test identifier appears in this map.

The current implementation and process-crash assertions cover the previously
open startup, trust, restore, scheduling, storage and public API work. This
review does not claim exhaustive specification conformance: deployment trust
provisioning, unavailable newer authority status, witness disaster recovery,
storage hardware and approval of any later release remain explicit boundaries.
The published rc2 approval is recorded in the [publication evidence](publication-0.1.0rc2.md).

## Evidence and historical record

The [current checklist](checklist-v0.1.md) identifies hosted validation and
candidate boundaries. Maintainer acceptance of historical benchmark scope and
limited external review is recorded in [Phase 3 closeout](phase3-closeout-2026-10-28.md).
It is no longer an unresolved research scope decision. Later artifacts need
their own checks; historical measurements are not current candidate results.

The [previous review page](https://github.com/hamdamme/casf/blob/93ba4325675c948b108a0281c2b0d97c713decdc/docs/release/requirement-evidence.md),
[Session 3 record](session3-validation.md), and
[streaming validation](streaming-validation.md) preserve the initial scopes,
corrections and dated validation. No original experimental output was changed.

## Team A remediation

The [remediation record](team-a-remediation.md) links CASF-01/02 and H01/H02/H03
to wrong-type, status/receipt, retry-identity, redaction and no-connection
assertions. T16/T17/T18 mappings identify the new tests. Broader
[production gates](production-readiness-gates.md) remain separate.

## Generated recovery sequences

`tests/property/test_recovery_sequences.py::TestRecoverySequences::runTest`
adds R04/R05/R09 evidence through generated operation sequences: idempotent
events, exact pending bytes, lost witness replies, duplicate submissions, forged
receipt rejection, writer/witness restarts and backup inspection. Independent
model assertions compare committed records and accepted witness heads after each
operation. The configured budget is 40 examples with at most 30 steps each, not
a claim that 1,200 steps were executed. Actual Hypothesis results are recorded in
validation output. This stateful unittest is listed here separately because the
existing machine-readable traceability audit targets top-level pytest functions.
The tests use explicit local-only mode; verified-startup and retained-state
rollback protection remain covered by `tests/unit/test_recovery_drills.py`.

## Unsupported witness status regression

The finding reported at `517aa3b6a962bdf82cefbe48c47d982c4bec4918` was
reproduced on main `79ed8d9cf8102ac2d30365af396d4f5df033e28b`. Correctly
signed serial-2 `unknown`, `ACTIVE` and empty-string statements produced raw
SQLite errors and CLI exit 5. New API/CLI regressions initially gave six failures
and three passes; the longer synthetic marker already failed generic length
validation, and valid transitions already passed.

The enum check now raises SchemaError before BEGIN IMMEDIATE, after the existing
signature/issuer checks. The targeted witness suite passed 32 tests after the fix.
Assertions check no transaction starts, active serial 1 survives reopening,
untrusted values/passphrases are absent from diagnostics, and active serial
advancement plus terminal revocation still work. T13/T17 map the exact tests.
No CLI catch, protocol schema, wire bytes or database constraint was changed.

## Administrative trust timeout regression

On baseline `587ab06361d12e2d1dd4095109d0416b5362ca45`, timeout 0/-1
created unusable trust files, and nan/inf/-inf raised an uncaught JSON ValueError.
The five invalid-value regressions failed before the fix; eight valid-value and
loader cases already passed. All 13 pass with a shared validation helper used
by trust creation and loading. Assertions cover exit 2, no output file or success
message, no traceback, and accepted-file roundtrips for 0.5, 1 and 10 seconds.
The existing reader rule and trust format are unchanged; T16 names the tests.

## Backup destination sidecars

The report against `517aa3b6a962bdf82cefbe48c47d982c4bec4918` was reproduced
on main `faebcff39bc1ba93fbaaf1804cd18caf61759f37`: source payload 1, published
backup payload 2 from a preserved WAL, and local integrity PASS. Before the fix,
29 new regression cases failed and nine controls passed. The guards reject
preexisting main/WAL/SHM paths (including dangling symlinks), sidecars created
during copy, and collisions at publication or directory sync. Tests retain
source rows and existing artifacts, exercise writer/witness migrations, and
compare clean backup/migration rows with the source. All 137 targeted backup,
migration, recovery and process-crash tests passed after the fix. T15 lists the
new tests; no schema, signed bytes, trust rules or live-source WAL mode changed.
