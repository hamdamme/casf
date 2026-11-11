# Verified writer startup and retained status

This decision records its implementation-time context. Statements about separate
work refer to that stage; use the [current reference](../current-reference.md)
and [completion tracker](../release/completion-tracker.md) for present behavior
and acceptance status.

Date: 2026-11-10. Scope: SPEC Sections 15–19; R02, R06, R07 and R09.

## Default write authorization

Use `Writer.open_verified` to open a signing writer and
`Writer.initialize_verified` to establish a new log. Both require independent
trust pins, supplied signed authority status, a protected external state file,
and a witness endpoint. They verify the complete local history, reconcile a
fresh witness view and durably retain status and checkpoint observations before
returning a writer that may append. Initialization witnesses an empty checkpoint
before the first record. A retry can resubmit those exact bootstrap bytes.

Direct `Writer(path, key)` calls fail closed. Existing research and component
tests must explicitly pass `local_only=True` to use the low-level writer.
Keyless opens remain available for inspection and evidence retrieval. Offline
restore returns a keyless reader by default; promoting the store requires
verified startup. An explicit local-only restore retains the old behavior.
No signed bytes, fixtures or historical results change.

CLI init, append, checkpoint, submit and seal use verified startup by default.
They require `--trust`, `--status-file` and `--state`, using the witness endpoint
in the trust configuration. First observation requires `--initialize-state`.
`--local-only` is an explicit compatibility mode, not verified startup.

## Terminal revocation and cross-store failure

The retained state entry adds an optional boolean `revoked`. Existing entries
without it decode as false; true cannot be cleared by later saves. Older
readers reject the extra field instead of ignoring a revocation. Authenticated
revocation remains terminal even below the retained or provisioned serial
minimum. Its observation never advances the accepted checkpoint.

Startup takes the external state lock before writer recovery. It commits a
write hold before evaluating status or contacting the witness. Authenticated
status observations persist even if later recovery fails. The startup checkpoint
is saved before releasing the database hold; each subsequent accepted receipt
also advances the external checkpoint before reporting success; a save failure leaves the database
held. If the external checkpoint persists but SQLite commit fails, retry must
recover evidence through that retained checkpoint. No atomic transaction across
the two stores is claimed. Each subsequent append/checkpoint rechecks retained
status under the same state lock, so an already open verified writer cannot
ignore a revocation observed by another process.

## Recovery locking correction

SPEC Section 17 forbids witness calls while holding a writer transaction.
ADR-007's initial transaction description conflicted with that rule. Replace
the network transaction with a bounded advisory recovery lock and a durable
database hold. Fetch witness evidence without a SQLite transaction, then
revalidate local history and apply evidence in one write transaction. A concurrent
receipt update may cause recovery to retry or fail; it cannot authorize an
unverified continuation. Ordinary WAL reads and unrelated logs remain available.

## Limits

Supplied signed status is not proof that a newer revocation was not withheld.
Independent state must be retained outside the database's backup/rollback
domain. Explicit local-only operations and arbitrary file-administrator changes
are outside verified-startup authorization. Background scheduling, complete
failure-matrix testing and release acceptance remain separate work.

Follow-up: [ADR-009](ADR-009-checkpoint-worker.md) adds an explicitly run
foreground checkpoint worker; startup itself still starts no background task.
