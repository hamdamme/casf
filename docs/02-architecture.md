# Architecture

```
app --> HashChain.append(payload) --> sealed_body --> HMAC --> Ed25519 sign
                                         |                    |
                                         v                    v
                                  LogStorage (SQLite, serialized seq)
                                         |
                     +-----------------+--------------------+
                     v                 v                    v
               export JSONL     CheckpointService     AtRestEncryption
               (verify target)  (signed head hash)   (AES-GCM blob)

verifier: auditfw-verify CLI --> Verifier(public_bundle, hmac_key, checkpoint)
```

## Write path
1. `LogStorage.next_seq_and_prev()` — single-writer lock + SQLite
   transaction yields gap-free `seq` and the previous head hash. This
   is the concurrency control point.
2. `HashChain.append` builds the entry, computes `entry_hash`
   (SHA-256 over the core fields), then seals: HMAC first, then the
   Ed25519 signature — both over the identical `sealed_body`.
3. The sealed entry is inserted into SQLite in the same critical section.
4. Periodically, `CheckpointService.create` signs
   `{head_seq, head_hash}` and publishes the checkpoint out-of-band.

## Verification path
`Verifier.verify_entries` walks the chain in order and checks, per entry:
1. `prev_hash` linkage (reorder/delete/insert),
2. `entry_hash` recomputation (in-place modification),
3. HMAC against the shared key (cheap tamper screen),
4. Ed25519 signature under `pub[key_version]` (attribution; key
   versions resolve historical keys),
then compares the head against the trusted checkpoint (truncation).

The first failing check raises `TamperedError(seq, reason)`.

## Key management
- `KeyRegistry` stores all key versions; `rotate()` marks a new active
  key but never deletes old ones.
- `export_public_bundle()` is the only artifact verifiers need.
  Private keys never leave the registry; production deployments should
  back it with an HSM/KMS — the `Signer` interface is the seam for that.

## Storage
SQLite for the writer (transactions + single-writer locking). For
PostgreSQL: replace `LogStorage` with a sequence/advisory-lock backed
table; the rest of the framework is unchanged.
