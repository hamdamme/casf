# Ed25519 verification profile and public-key rejection

Status: adopted for the rc4 correction; release approval remains separate.

## Context

A raw 32-byte public key is not necessarily a usable Ed25519 identity.
With the identity point as public key, `R = identity, S = 0` satisfies
verification for every message. An authority signature over a manifest does
not make its embedded log key safe. This affects published rc2 and rc3 and
the historical rc4 artifacts built from `3333d00`.

Chalkias, Garillot and Nikolaenko, [Taming the many EdDSAs](https://eprint.iacr.org/2020/1244),
explain how decoding, scalar bounds and cofactor rules distinguish Ed25519
verification implementations. CASF must state and test its selected profile.

## Decision

- Use pure Ed25519 over the existing domain plus raw digest, never Ed25519ph
  or Ed25519ctx. Keep signing and curve operations in `cryptography`.
- Retain the pinned library's cofactorless verification equation
  `[S]B = R + [k]A`, where `k = SHA-512(R || A || M) mod L` and
  `L = 2^252 + 27742317777372353535851937790883648493`. Require `0 <= S < L`;
  never reduce a supplied signature scalar modulo L to accept it.
- Reject small-order public keys in shared `load_public_key`, before backend
  verification. Compare the seven encodings from libsodium 1.0.18's
  [`ge25519_has_small_order`](https://github.com/jedisct1/libsodium/blob/1.0.18/src/libsodium/crypto_core/ed25519/ref10/ed25519_ref10.c)
  with the sign bit cleared. Also reject every noncanonical `y >= 2^255 - 19`.
  Both checks raise `SchemaError("Ed25519 public key has small order")`.
  The noncanonical guard is broader than mathematical small-order rejection.
- Preserve the backend's remaining decoding and signature checks. This is
  not prime-subgroup membership validation: mixed-order public keys satisfying
  the chosen equation remain accepted. Do not add a blanket rejection of
  small-order R values. The edge vectors freeze these distinctions.
- Keep domains, digests, key identifiers, signature bytes and existing frozen
  vectors unchanged. Add explicit rejection/acceptance vectors; do not rewrite
  signed evidence to make a rejected key pass.

## Consequences and validation

Manifest, record, checkpoint, receipt, latest-view and status verification share
the key boundary, as do witness registration and predecessor authentication.
Real-authority manifests carrying identity log keys fail with
`MANIFEST_KEY_SCHEMA`; no records are accepted. Invalid authority or witness
pins cannot authorize evidence. Normal generated keys remain compatible.

The [edge vectors](../../vectors/v1/ed25519_edge_cases.json), unit tests and
advisory regressions cover sign-bit variants, all noncanonical y encodings,
scalar bounds, the cofactorless equation and universal-signature attempts.
Dependency changes must preserve these outcomes in the supported matrix.
This tightens invalid-key acceptance in casf-v1 without changing valid wire bytes.
The changed runtime requires new rc4 artifacts and installation checks; prior
candidate validation cannot approve this implementation.
