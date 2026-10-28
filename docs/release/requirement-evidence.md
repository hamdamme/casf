# Requirement evidence review

Review date: 2026-10-25.

The explicit [evidence map](../../tests/requirement_evidence.json) connects
R01 through R12 to the specification test cases, and T01 through T22 to
named Python test functions. Each case records what its assertions check and
any remaining review. Existing research artifacts and frozen vectors are
preserved.

The [audit](../../tests/unit/test_traceability.py) checks that the requirement
mapping matches the specification, every mandatory case has targets, and each
target exists with an assertion or expected exception. It rejects references
to itself, missing functions, and paths outside tests. Comments containing an
identifier no longer count as evidence. Regression tests exercise these
rejections.

This structural audit cannot establish that an assertion is correct, that it
covers every scenario, or that a test ran successfully. The full suite and
human review remain necessary. An empty remaining review field means no gap
was recorded in this initial mapping review; it is not a completeness proof.

## Requirement links

| Requirement | Specification cases |
| --- | --- |
| R01 | T01, T02 |
| R02 | T03, T04 |
| R03 | T05 |
| R04 | T06, T07 |
| R05 | T08, T09 |
| R06 | T10, T11 |
| R07 | T12, T13 |
| R08 | T14 |
| R09 | T15 |
| R10 | T16, T17 |
| R11 | T18 |
| R12 | T19 |

## Assertion scope and remaining review

| Case | What the linked assertions check | Remaining review |
| --- | --- | --- |
| T01 | Reject ambiguous JSON and invalid Unicode. | None recorded in this initial review. |
| T02 | Compare exact canonical bytes and reject values outside the profile. | None recorded in this initial review. |
| T03 | Reject altered bodies, wrong keys, and wrong domains. | None recorded in this initial review. |
| T04 | Reject sequence gaps, broken predecessors, and wrong log binding. | Dedicated duplicate sequence, reorder, wrong genesis, and cross log splice cases still need an assertion review. |
| T05 | Verify an export and report the verified range. | The installed wheel passed integrity, anchored, and online CLI verification on synthetic public evidence; see the [fresh wheel rehearsal](install-rehearsal-2026-10-27.md). This does not replace the remaining full release install and artifact rehearsal. |
| T06 | Concurrent appends preserve sequence and event id uniqueness. | None recorded in this initial review. |
| T07 | Process exits before insert, before commit, and after commit preserve retry semantics. | None recorded in this initial review. |
| T08 | Reject invalid extensions and conflicting checkpoint reuse without advancing state. | None recorded in this initial review. |
| T09 | Accept at most one of two concurrent signed forks. | None recorded in this initial review. |
| T10 | An old restored database is incomplete against a newer anchor. | None recorded in this initial review. |
| T11 | Replay and wrong nonce fail; timeout is inconclusive. | None recorded in this initial review. |
| T12 | Reject unknown versions, wrong keys, and replaced manifests. | None recorded in this initial review. |
| T13 | Reject revocation and status serial rollback. | The stale offline policy case needs a dedicated assertion review; signature validity does not establish current revocation knowledge. |
| T14 | Verify rotation links, reject sealed appends, and expose emergency discontinuity. | None recorded in this initial review. |
| T15 | Export and restore verify; malformed bundles fail. | Concurrent export and missing WAL recovery need dedicated evidence review. |
| T16 | Bound input size, nesting, and concurrent HTTP work. | Excessive checkpoint chain traversal needs a dedicated assertion review. |
| T17 | Secret markers are absent from CLI and server diagnostics. | None recorded in this initial review. |
| T18 | Integrity may pass after unwitnessed tail loss; report unwitnessed suffixes. | None recorded in this initial review. |
| T19 | A repeated small manifest preserves procedure and records environment metadata. | Small automated runs do not establish a fresh environment rerun of every published benchmark manifest. |
| T20 | A stolen key cannot hide a prefix rewrite from an anchor but can sign a false suffix. | None recorded in this initial review. |
| T21 | Retained state detects witness rollback; an isolated client can miss it. | A dedicated witness equivocation scenario still needs review. |
| T22 | Retry after witness commit and process exit returns the same receipt. | None recorded in this initial review. |

## Escaping assertion correction

The control character escaping test previously ended its comparison with
`or True`. An incorrect byte result could pass. The test now compares against
literal expected bytes, including the unescaped DEL character. A local
mutation check substituted an incorrect byte result and confirmed that the
assertion failed. The original frozen canonicalization vectors are unchanged.

The requirement evidence gate remains open until the listed review items are
resolved or their limitations are explicitly accepted under the release
criteria. Updating the mapping does not approve a release.


## Session 3 follow up

The [Session 3 record](session3-validation.md) describes runtime fixes,
new scenario tests, and isolated package rehearsals. The JSON evidence map
now includes the new tests. The table above preserves the initial review;
its remaining review column is not the current task list.

The duplicate, reordered, genesis, log splice, concurrent export, missing WAL,
and signed witness equivocation scenarios now have explicit assertions.
Missing authority status yields UNKNOWN trust and an overall failure.
Signed active status records a currentness limitation; no wall clock expiry
rule or globally current revocation knowledge is invented.

The chain, receipt, and status budgets are enforced, and bundle parsing uses
bounded reads before parsing with total byte and count budgets. The reader
still retains decoded record objects, so it is bounded rather than constant
memory in record count. The public package rehearsal and historical benchmark
scope still require final release acceptance; see the current JSON map.


## Streaming verification follow up

The [streaming API decision](../adr/ADR-006-streaming-verification.md)
preserves the eager reader for compatibility while the CLI uses an owned
record stream. The verifier retains only digests requested by bounded
checkpoint evidence. New assertions cover EOF metadata checks, late errors
before state saving, record mutations, checkpoint boundary comparisons,
file ownership, and memory scaling with a fixed protocol footprint.

The initial and Session 3 reviews above remain historical records. Their
record retention limitation is addressed for the streaming entry point;
`read_bundle` and restore deliberately retain their eager API. See the
[validation record](streaming-validation.md) for measured bounds, completed
checks, and remaining limitations. External review and unrelated release
acceptance are still separate requirements.

## Provisioned witness identity regression

The local commit `67f358d` adds
`test_verify_mismatched_provisioned_witness_id_exit_3`. It checks that the CLI
rejects a trust entry whose witness identity differs from the signed
manifest, reports `WITNESS_ID_MISMATCH`, and does not create verifier state.
The focused test passed locally. This commit has not been pushed or merged,
so this evidence is not yet part of the GitHub main branch. Broader review
coverage and the release gates above remain open.
