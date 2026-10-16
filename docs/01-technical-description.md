# Technical Description

## Problem
Backend systems handling sensitive operations need audit logs that remain
trustworthy even if the log store, a database admin, or an attacker with
host access modifies them. Conventional logs provide no integrity
guarantees: entries can be altered, deleted, reordered, or backdated
without detection.

## Goals
1. **Tamper evidence** — any modification, deletion, insertion, or
   reordering of entries is detectable, with the first tamper point
   precisely located.
2. **Attributability** — every entry is digitally signed; a valid
   signature proves which key version produced it.
3. **Independent verification** — any third party verifies a log using
   only an out-of-band public key bundle; the logging system itself is
   not trusted.
4. **Survivable key rotation** — rotating signing keys never invalidates
   historical records.
5. **Truncation resistance** — signed checkpoints of the chain head
   reveal suffix deletion.

## Non-goals
- Confidentiality of log *content* is provided at rest (AES-GCM) but the
  framework is not an access control system.
- Availability: a compromised writer can always stop logging. The
  framework guarantees evidence of *what was logged*, not that logging
  continued.

## Threat model
| Adversary capability | Defense |
|---|---|
| Modify an entry in place | entry_hash + signature + HMAC |
| Delete/reorder entries | prev_hash chain linkage |
| Truncate the log suffix | signed checkpoints |
| Forge new entries | signatures (writer key required) |
| Backdate entries | timestamp bound into signed body |
| Read log files at rest | AES-256-GCM encryption |

Trusted components: the writer process (holds signing key and HMAC key)
and the checkpoint authority (receives signed checkpoints out-of-band).

## Cryptographic choices
- **SHA-256** for chain hashing; **SHA-256 HMAC** for shared key sealing.
- **Ed25519** signatures: deterministic, misuse resistant, 64-byte
  signatures. (ECDSA/RSA can be substituted behind the same `Signer`
  interface; SHA-3 digests are available via `hashlib.sha3_256` where
  compliance requires them.)
- **AES-256-GCM** for encryption at rest with random 96-bit nonces —
  safe under the birthday bound for any realistic volume.
- **Canonical JSON** (sorted keys, compact separators) guarantees a
  single byte encoding for hashing and signing.

## Entry format
```json
{
  "seq": 1,
  "event_id": "uuid",
  "timestamp": 1728614400000,
  "payload": { "...": "application event" },
  "prev_hash": "SHA-256 of previous entry body, or GENESIS",
  "key_version": "v1",
  "entry_hash": "SHA-256 of {seq,event_id,timestamp,payload,prev_hash,key_version}",
  "hmac": "HMAC-SHA-256 over sealed_body (all fields except hmac/signature)",
  "signature": "Ed25519 over sealed_body"
}
```
`sealed_body` = all fields except `hmac` and `signature`. Writer and
verifier share this exact definition (`chain.sealed_body`).

## Package layout (normative)
```
cryptographic_audit_framework/
├── pyproject.toml          # package metadata; requires-python >=3.10
├── requirements.txt        # cryptography>=41.0 (sole dependency)
├── README.md
├── demo.py                 # runnable end-to-end acceptance demo
├── auditfw/                # the importable package
│   ├── __init__.py         # re-exports the public API
│   ├── chain.py            # canonical(), entry_digest(), sealed_body(), HashChain
│   ├── keys.py             # KeyRegistry, Signer
│   ├── seal.py             # seal_trail(), verify_trail()
│   ├── atrest.py           # AtRestEncryption
│   ├── storage.py          # LogStorage (SQLite)
│   ├── checkpoints.py      # CheckpointService
│   ├── verify.py           # Verifier, TamperedError
│   └── cli.py              # main(argv=None) -> int
└── docs/                   # this specification set
```

## Checkpoint format (normative)
```json
{
  "created_at": 1728614400,
  "note": "hourly",
  "head_seq": 3,
  "head_hash": "SHA-256 hex of the head entry's entry_hash",
  "signature": "Ed25519 (hex) over canonical({created_at,note,head_seq,head_hash})",
  "key_version": "v3"
}
```
The signature covers all fields except `signature` and `key_version`.
