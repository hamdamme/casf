# Conformance vectors v1

Frozen at the M1 gate (SPEC §21). All values are deterministic known
answers; the Ed25519 keys derive from fixed seeds and are test keys
only, never for deployment (SPEC §16).

| File | Content |
|---|---|
| `jcs_kat.json` | Canonical byte hex for representative JSON values. Independently cross checked against the rfc8785 reference package on 2026-10-11; frozen. |
| `jcs_reject.json` | Malformed wire input and the exact error each case must raise, at parse or canonicalize stage. |
| `crypto_kat.json` | Test keys, schema valid bodies for all six protocol objects, domain digests, genesis hash, signatures, and negative cases. |
| `ed25519_edge_cases.json` | Primitive acceptance/rejection vectors for SPEC §9 and ADR-018: small-order keys, noncanonical encodings, cofactorless verification and scalar bounds. |

`generate_kat.py` regenerates `crypto_kat.json` and `jcs_reject.json`
deterministically and refuses to run if `jcs_kat.json` drifts from the
implementation. Any intentional change to these files means the wire
profile changed and requires an ADR plus a new profile version
(SPEC reading and document control).

Consumed by `tests/conformance/test_vectors.py`.

The added Ed25519 vectors retain the twelve message/key/signature triples from
[ed25519-speccheck](https://github.com/novifinancial/ed25519-speccheck/tree/65519336fda78a3d016e947df6d82848aca0c9da),
the Apache-2.0 implementation accompanying Chalkias, Garillot and Nikolaenko's
[Taming the many EdDSAs](https://eprint.iacr.org/2020/1244). Attribution and source
identity are retained in the JSON; the Apache license is provided in
[LICENSE](../../LICENSE). CASF adds names, explanations and expected outcomes,
plus an RFC 8032 positive control and synthetic boundary cases. `SchemaError`
means key rejection before verification; `InvalidSignature` means backend
rejection; `ACCEPT` means primitive verification succeeds. These raw-message
vectors do not replace CASF domain tests. ADR-018 adds invalid-key rejection
without changing the existing frozen bytes or the casf-v1 wire profile.
