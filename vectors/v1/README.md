# Conformance vectors v1

Frozen at the M1 gate (SPEC §21). All values are deterministic known
answers; the Ed25519 keys derive from fixed seeds and are test keys
only, never for deployment (SPEC §16).

| File | Content |
|---|---|
| `jcs_kat.json` | Canonical byte hex for representative JSON values. Independently cross checked against the rfc8785 reference package on 2026-10-11; frozen. |
| `jcs_reject.json` | Malformed wire input and the exact error each case must raise, at parse or canonicalize stage. |
| `crypto_kat.json` | Test keys, schema valid bodies for all six protocol objects, domain digests, genesis hash, signatures, and negative cases. |

`generate_kat.py` regenerates `crypto_kat.json` and `jcs_reject.json`
deterministically and refuses to run if `jcs_kat.json` drifts from the
implementation. Any intentional change to these files means the wire
profile changed and requires an ADR plus a new profile version
(SPEC reading and document control).

Consumed by `tests/conformance/test_vectors.py`.
