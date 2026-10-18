# CASF Cryptographic Audit & Signing Framework

An embeddable Python mechanism for producing and independently checking
audit histories, with conditional rollback detection using independently
retained witness state.

**Status:** design review draft (CASF SPEC 001 rev 0.9). An exploratory
prototype exists under the `exploratory prototype` tag; the casf-v1
wire profile is proposed and not yet frozen.

## The problem
Ordinary stored logs can be edited, reordered, or restored to an older
valid snapshot without reliable evidence in the restored copy itself.
CASF addresses integrity evidence and conditional detection of missing
history. It does not make storage physically immutable, and successful
verification is not proof that every real world event was recorded.

## What CASF provides
- Per-record Ed25519 signatures and SHA-256 hash chaining (domain separated, RFC 8785 JCS encoding)
- A stateful, independently operated witness that accepts only valid chain extensions and issues chained receipts
- Independent verification from an exported evidence bundle using only public trust material
- Verification modes integrity, anchored, online — with separate, enum typed results (PASS / FAIL / INCONCLUSIVE)
- Epoch based key rotation and terminal revocation
- An applied research evaluation (RQ1–RQ4, H1–H3) of local vs. independently witnessed checkpoints

## Explicit limits (read before using)
- Detection claims are conditional on assumptions A1–A6 in the specification (SPEC §6)
- A compromised writer can sign false new events; the witnessed prefix constrains what can match retained history
- The unwitnessed suffix after the last accepted checkpoint carries exposure (SPEC §7)
- The witness sees full record payloads in v1 minimize sensitive fields
- CASF provides no legal nonrepudiation, no completeness guarantee for events never submitted, and no confidentiality guarantee

## Repository layout
| Path | Content |
|---|---|
| `ROADMAP.md` | Phase plan and session status (details in SPEC §24/§27) |
| `docs/specification/` | CASF SPEC 001 (governing design document) + D01 source reconciliation |
| `docs/adr/` | Architecture decision records |
| `docs/01..05` | Historical design context (superseded by SPEC 001) |
| `src/casf/` | casf-v1 implementation (per milestone plan) |
| `vectors/v1/` | Frozen conformance vectors (M1 gate) |
| `tests/` | Unit / property / conformance / integration / adversarial suites |
| `benchmarks/` | Workloads, attack harnesses, configs, raw results (M7) |
| `research/` | Research protocol, results, limitations |

## Claim discipline
Public descriptions of this project must follow SPEC §29: say
"cryptographically verifiable audit records with conditional rollback
detection using independently retained witness state." Do not say
"tamper-proof", "guaranteed complete", "forward secure", "globally
fork free", "compliant", "audited", or "novel cryptography" without
separate, specific evidence.

## License
Apache-2.0 (proposed, pending D07 confirmation).
