# D01 — Source Reconciliation: Original Technical Documentation vs CASF SPEC 001

**Date:** 2026-10-10
**Status:** CLOSED — original documentation located and dispositioned
**Authority:** CASF SPEC 001 §3, decision register D01

## Context
CASF SPEC 001 (rev 0.9) was drafted without access to the original
`Cryptographic_Audit_Framework_Technical_Documentation.docx` and treated
early design notes as secondary evidence. The original file has
now been located. This document performs the required section-by-section
disposition per SPEC §3: every original requirement is classified
**retained, clarified, replaced, deferred, or removed**, with reasons.

## Sources reconciled
| Source | Role |
|---|---|
| [Original Word document](../historical/Cryptographic_Audit_Framework_Technical_Documentation.docx) (docs 01–05) | Original design documentation |
| `auditfw/` Python package + `demo.py` | Exploratory prototype implementation |
| Early design notes | Secondary context (as used by SPEC 001) |

## Disposition table
| Original item (source) | Disposition | SPEC 001 treatment | Reason |
|---|---|---|---|
| SHA-256 hash chaining, `prev_hash` linkage (docs 01/02) | Clarified | §11 record schema; `prev_hash` bound to record digest domain | Domain-separated encoding fixed; original chain logic sound |
| Ed25519 signatures over canonical body (docs 01/02) | Clarified | §9/§11 pure Ed25519, digest-then-sign with domain | Original mixed "sign over body" rule made precise |
| Sorted key JSON canonicalization (doc 01) | Replaced | §9 RFC 8785 JCS + restricted data profile (no floats) | Sorted key JSON is not an interoperable standard |
| HMAC-SHA-256 layer for trusted components (docs 01/02/04) | Removed | §2: excluded from public verification protocol | HMAC holder can forge; breaks the public verification boundary |
| AES-256-GCM encryption at rest (docs 01/04) | Deferred | Out of v1 scope (§2); confidentiality not a CASF guarantee | Storage encryption is an operator concern, not protocol |
| Signed checkpoints of chain head (docs 01/02) | Replaced | §12 checkpoint objects; §13 stateful external witness + receipts | Local checkpoints alone give no rollback protection (SPEC §7) |
| SQLite storage, serialized sequencing (docs 02/04) | Retained + expanded | §17 transactional schema, idempotency, crash rules, WAL/FULL | Original single lock design insufficient for durability claims |
| Key registry + rotation keeping old keys (docs 01/02) | Replaced | §10 manifest bootstrap; §16 epoch based rotation | Per-entry `key_version` lookup replaced by manifest pinned keys |
| Independent verifier + CLI (docs 02/05) | Retained + expanded | §15 verification algorithm; §19 CLI with 6 exit categories | Original OK/FAIL insufficient; enum based report required |
| Truncation detection via checkpoint (docs 02/05) | Replaced | §13 witness receipts; §15 anchored/online modes | Detection now requires external trusted reference |
| Tamper acceptance procedure (doc 05) | Replaced | §21 adversarial matrix T01–T22 | Original matrix lacked fork, crash, replay, equivocation cases |
| Exploratory prototype `auditfw/` package | Superseded | — | Byte formats differ fundamentally; archived as prototype (see below) |
| Research review (5 references, H1–H3 direction) | Retained + expanded | §4 literature context; §22 RQ1–RQ4, H1–H3 | Spec formalizes the evaluation methodology |

## Original backlog disposition clarified 11 November 2026

The initial table did not enumerate every item in the original hardening backlog.
The following rows complete that disposition without expanding the release scope.

| Original item | Current treatment | Evidence or boundary |
| --- | --- | --- |
| PostgreSQL storage backend | Deferred; SQLite is the supported adapter | SPEC §§2 and 17; no PostgreSQL adapter is advertised. |
| External anchoring | Replaced by one stateful witness and independently retained verifier state | SPEC §§13–15; no transparency log or object-lock integration is claimed. |
| Encrypted private keys | Implemented with encrypted PKCS8 files | [Key administration](../administration.md); native HSM/KMS integration remains excluded. |
| REST verification API using FastAPI | Excluded from the current release | Library/CLI verification and witness HTTP endpoints have distinct purposes; no general verification REST service is advertised. |
| Hypothesis property tests | Implemented with bounded scope | [Generated-input guide](../adversarial-testing.md); not an exhaustive state-machine proof. |
| Replaceable RSA/ECDSA and SHA-3 algorithms | Excluded from casf-v1 | SPEC §2 excludes arbitrary algorithm negotiation; fixed Ed25519/SHA-256 bytes remain authoritative. |
| Python 3.10 minimum | Replaced by Python 3.12–3.14 validation | Package metadata and [validation matrix](../release/validation-matrix.md). |
| CLI exit codes 0/1/2 | Replaced by codes 0–5 | SPEC §19 and [verification guide](../verification.md); operational errors are distinguished. |

HMAC and payload AES-GCM are explicit scope decisions, not unimplemented current
requirements. The original document is preserved unchanged in the
[historical archive](../historical/README.md), including its source digest.

## Prototype disposition
The existing `auditfw/` implementation and `demo.py` **do not conform**
to casf-v1 (JCS encoding, domain separation, witness protocol differ).
The prototype is retained in [repository history](https://github.com/hamdamme/casf/tree/ba417691b4a748692d98b799494a5aeefd737129/auditfw)
as development evidence. The previously named `exploratory-prototype` tag is not
present on the remote; use this pinned source revision instead. These files are
not part of the CASF conformance surface.

## Claim-language migration
| Original phrasing (docs 01/05) | Permitted per SPEC §29 claim discipline |
|---|---|
| "tamper-evident audit logs" | "cryptographically verifiable audit records" |
| "immediately detectable" tampering | "detectable under stated assumptions A1–A6" |
| "tamper-proof" (never claimed in docs, banned going forward) | prohibited without specific evidence |
| "integrity-protected, attributable" | "per-record signatures under a pinned key; attribution = authorized key signed bytes" |

## Decision
D01 is **closed**. CASF SPEC 001 rev 0.9 is adopted as the governing
baseline, superseding docs 01–05 as normative references. Docs 01–05
remain in the repository as historical design context only.
