# Implementation Plan

## Phase 0 — Design (done)
- [x] Threat model and crypto selection (`01-technical-description.md`)
- [x] Entry format and `sealed_body` definition fixed on paper first
- [x] Canonical encoding decision (sorted-key compact JSON)

## Phase 1 — Core chain
1. `chain.py`: `canonical()`, `entry_digest()`, `HashChain.append`.
2. `storage.py`: SQLite schema, `next_seq_and_prev` under a lock.
3. Unit test: append N entries, recompute the chain manually, match.

## Phase 2 — Cryptography
4. `keys.py`: registry, Ed25519 generate/rotate, public bundle export.
5. Keep the `Signer` seam minimal so HSM/KMS adapters can replace it.
6. Wire signing into `append` over `sealed_body`, passing
   `version=key_version`.
7. `seal.py`: HMAC trail seal/verify.
8. `atrest.py`: AES-GCM with random 12-byte nonces; round-trip test.

## Phase 3 — Tamper evidence
9. `verify.py`: `Verifier` with layered checks (link -> hash -> HMAC ->
   signature -> checkpoint), `TamperedError(seq, reason)`.
10. `checkpoints.py`: signed head checkpoints.
11. Adversarial test matrix: modify / delete / reorder / truncate /
    swap-key-version / flip-HMAC — each must be caught at the right seq.

## Phase 4 — Tooling
12. `cli.py`: `auditfw-verify` with exit codes 0/1/2.
13. `demo.py`: full lifecycle (keys -> rotate -> log -> checkpoint ->
    export -> verify -> tamper demos).

## Phase 5 — Hardening (backlog)
- [ ] PostgreSQL `LogStorage` backend
- [ ] External anchoring of checkpoints (transparency log / object-lock
      storage) so checkpoint-authority compromise is detectable
- [ ] Encrypted private keys in registry (password / KMS envelope)
- [ ] REST verification API (FastAPI) wrapping `Verifier`
- [ ] Hypothesis property-based tests for the verifier

## Decisions log
- Signing passes `version=key_version` into `Signer.sign`; old code
  signed with the active key while labeling the entry otherwise — fixed.
- Timestamps are writer-local; verifiers needing backdating resistance
  should cross-check against an external receipting service.
