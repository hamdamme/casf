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
| `Cryptographic_Audit_Framework_Technical_Documentation.docx` (docs 01–05) | Original design documentation |
| `auditfw/` Python package + `demo.py` | Exploratory prototype implementation |
| Early design notes | Secondary context (as used by SPEC 001) |

## Disposition table
| Original item (source) | Disposition | SPEC 001 treatment | Reason |
|---|---|---|---|
| SHA-256 hash chaining, `prev_hash` linkage (docs 01/02) | Clarified | §11 record schema; `prev_hash` bound to record digest domain | Domain-separated encoding fixed; original chain logic sound |
| Ed25519 signatures over canonical body (docs 01/02) | Clarified | §9/§11 pure Ed25519, digest-then-sign with domain | Original mixed "sign over body" rule made precise |
| Sorted-key JSON canonicalization (doc 01) | Replaced | §9 RFC 8785 JCS + restricted data profile (no floats) | Sorted-key JSON is not an interoperable standard |
| HMAC-SHA-256 layer for trusted components (docs 01/02/04) | Removed | §2: excluded from public verification protocol | HMAC holder can forge; breaks the public-verification boundary |
| AES-256-GCM encryption at rest (docs 01/04) | Deferred | Out of v1 scope (§2); confidentiality not a CASF guarantee | Storage encryption is an operator concern, not protocol |
| Signed checkpoints of chain head (docs 01/02) | Replaced | §12 checkpoint objects; §13 stateful external witness + receipts | Local checkpoints alone give no rollback protection (SPEC §7) |
| SQLite storage, serialized sequencing (docs 02/04) | Retained + expanded | §17 transactional schema, idempotency, crash rules, WAL/FULL | Original single-lock design insufficient for durability claims |
| Key registry + rotation keeping old keys (docs 01/02) | Replaced | §10 manifest bootstrap; §16 epoch-based rotation | Per-entry `key_version` lookup replaced by manifest-pinned keys |
| Independent verifier + CLI (docs 02/05) | Retained + expanded | §15 verification algorithm; §19 CLI with 5 exit categories | Original OK/FAIL insufficient; enum-based report required |
| Truncation detection via checkpoint (docs 02/05) | Replaced | §13 witness receipts; §15 anchored/online modes | Detection now requires external trusted reference |
| Tamper test matrix (doc 05, 8 steps) | Replaced | §21 adversarial matrix T01–T22 | Original matrix lacked fork, crash, replay, equivocation cases |
| Exploratory prototype `auditfw/` package | Superseded | — | Byte formats differ fundamentally; archived as prototype (see below) |
| Research review (5 references, H1–H3 direction) | Retained + expanded | §4 literature context; §22 RQ1–RQ4, H1–H3 | Spec formalizes the evaluation methodology |

## Original requirements with no SPEC 001 equivalent
None. Every normative element of docs 01–05 maps to a SPEC 001 section;
HMAC and AES-GCM are explicitly excluded by decision (§2), not lost.

## Prototype disposition
The existing `auditfw/` implementation and `demo.py` **do not conform**
to casf-v1 (JCS encoding, domain separation, witness protocol differ).
They are archived as an exploratory prototype — tagged `exploratory-prototype`
— and retained in repository history as development evidence. They are
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
