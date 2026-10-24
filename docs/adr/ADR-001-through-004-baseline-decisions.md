# Architecture Decision Records — Baseline Gate Decisions

**Date:** 2026-10-10 · **Status:** APPROVED 2026-10-11 (maintainer decision)

## ADR-001 (closes D02): One fixed witness, full record disclosure
**Decision:** Approve. One pinned, stateful witness per log; it receives
complete record envelopes (payloads included).
**Rationale:** Simplest protocol that answers RQ1; privacy/bandwidth cost
is acknowledged (SPEC §13, residual risks) and becomes a measured outcome.
**Consequence:** Witness operator must be a separate administrative trust
domain (D06) before any deployment claim.

## ADR-002 (closes D03): Restricted JCS profile, pure Ed25519
**Decision:** Approve. RFC 8785 JCS; floats forbidden; safe integers only;
pure Ed25519 (not Ed25519ph) with explicit domain separation.
**Rationale:** JCS gives an interoperable, citable serialization rule;
banning floats removes a whole class of canonicalization ambiguity.
**Consequence:** M1 must cross check canonicalization against an
independent JCS implementation before vectors freeze.

## ADR-003 (closes D04): Epoch-based rotation, terminal revocation
**Decision:** Approve. Rotation = new log epoch with predecessor evidence;
in-log key replacement prohibited; revocation is terminal per manifest.
**Rationale:** Prevents silent trust substitution; keeps verification
semantics simple and reviewable by one maintainer.
**Consequence:** Long-lived high volume logs need epoch planning;
documented in §16.

## ADR-004 (D05 conditions outstanding): Dependency and runtime selection
**Decision:** Approve, with exact pins recorded at M0 CI setup.
- Runtime matrix: Python 3.12, 3.13, 3.14 (to be exercised in CI before advertising)
- crypto: `cryptography` (pinned, reviewed version)
- JCS: a maintained RFC 8785 implementation, or a conformance tested in-module implementation if no suitable library exists
- HTTP (witness extra only): standard library `http.server` is NOT acceptable for the reference service; select a maintained minimal ASGI/WSGI stack at M0
- SQLite via stdlib `sqlite3`; WAL + synchronous=FULL
**Consequence:** pyproject lockfile becomes part of reproducibility evidence (R12).

## Decision status

The approvals recorded on 2026-10-11 establish the design decisions below.
Approval does not establish that every implementation or deployment condition
has been satisfied. The following status review was recorded on 2026-10-24.

| Decision | Gate | Status |
|---|---|---|
| ADR-001/D02 | M0 | Approved. Separate witness administration under D06 remains required before deployment claims. |
| ADR-002/D03 | M1 | Approved. The [vector record](../../vectors/v1/README.md) and [changelog](../../CHANGELOG.md) record the independent canonicalization comparison and frozen vectors. |
| ADR-003/D04 | M0 | Approved. Epoch planning remains an operational consequence. |
| ADR-004/D05 | M0 | Approved with conditions. Dependency pins and HTTP stack requirements remain outstanding; D05 completion is not established. |

## Outstanding D05 conditions

The current [witness transport](../../src/casf/witness/http.py) uses
`http.server`, which conflicts with the HTTP stack requirement in ADR-004.
Resolving this conflict requires an implementation change or a separately
approved decision amendment.

The [package configuration](../../pyproject.toml) and
[requirements file](../../requirements.txt) specify minimum dependency
versions. No dependency lockfile is tracked. Exact dependency pins and the
required lockfile remain outstanding reproducibility evidence for R12.

The [CI configuration](../../.github/workflows/ci.yml) includes Python 3.12,
3.13, and 3.14. Configuration alone does not establish successful runs for
that matrix; this documentation review did not verify CI execution results.
