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
| T19 | Repeatable small manifest procedure and captured environment metadata. Historical full experiments remain separate evidence. |
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
