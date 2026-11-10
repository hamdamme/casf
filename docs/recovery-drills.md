# Recovery drills

These deterministic drills exercise the experimental reference implementation
with synthetic keys and temporary local databases. They support SPEC sections
17–18 and requirements R04, R06, R09 and R10. Exact revision, platform and test
results belong to the PR checks; the table describes the acceptance assertions.

## Failure matrix

| Failure | Required result and retry | Automated evidence |
|---|---|---|
| SQLite storage exhaustion during append | Return `SQLITE_FULL`, preserve committed records and event identity, then accept exactly one retry with the same event ID after capacity is restored. | [Storage drills](../tests/unit/test_recovery_storage.py), `test_sqlite_full_preserves_history_and_same_event_retry` |
| SQLite storage exhaustion during journal recovery | Roll back all newly recovered pairs, preserve the durable write hold across restart, then reconcile the original witness chain before writing. | [Recovery drills](../tests/unit/test_recovery_drills.py), `test_sqlite_full_during_reconciliation_keeps_hold_and_retries` |
| Failed or interrupted backup | No incomplete copy appears at the requested destination. Source history remains valid; a retry creates a verifiable copy. Existing files and dangling symlinks are never replaced. | [Backup drills](../tests/unit/test_backup_failures.py), including process exit, copy failure, publication race and file/directory sync failures |
| Corrupt backup | Reject invalid SQLite headers and invalid signed records before witness queries or changes to independent retained state. Close failed database connections. CLI inspection returns local error 5 without a traceback. | [Recovery drills](../tests/unit/test_recovery_drills.py), `test_corrupt_backup_cannot_replace_independent_state`; [storage drills](../tests/unit/test_recovery_storage.py) |
| Lost signing key | Refuse append; preserve existing history and retained state. Public evidence remains exportable and verifiable without the private key. | [Recovery drills](../tests/unit/test_recovery_drills.py), `test_missing_key_preserves_public_evidence_and_prevents_signing` |
| Writer rollback with lost records | Reject promotion against a newer witness and retain the terminal record-loss seal. Never sign replacement records at the lost positions. | [Recovery drills](../tests/unit/test_recovery_drills.py), `test_old_writer_backup_with_lost_records_is_not_promoted` |
| Writer and witness rollback | Independent retained checkpoint state rejects the older fresh witness view and leaves writing held. Local integrity alone remains insufficient. | [Recovery drills](../tests/unit/test_recovery_drills.py), `test_writer_and_witness_rollback_cannot_replace_retained_checkpoint` |
| Unavailable witness | Preserve exact pending checkpoint bytes and the write hold. After reconnecting, recover the matching accepted receipt, persist its external checkpoint, and retain any final seal. | [Recovery drills](../tests/unit/test_recovery_drills.py), `test_unavailable_witness_preserves_pending_bytes_until_verified_retry` |

Run the new drills in an environment with the locked development and witness
dependencies installed:

```sh
python -m pytest tests/unit/test_recovery_storage.py tests/unit/test_backup_failures.py tests/unit/test_recovery_drills.py -q
```

The broader existing suite also covers missing WAL state, malformed bundles,
missing receipt links, fresh-response replay, status persistence failure and
process exit during journal insertion. See the
[requirement evidence map](../tests/requirement_evidence.json).

## Operating procedure

1. Preserve the affected store and independently retained state. Work from a
   separate copy; do not delete status or checkpoint state to force startup.
2. Resolve local capacity or I/O failures before retrying. An append with an
   uncertain commit outcome must be looked up or retried with the same event ID.
3. Create backups with `Writer.backup`, then verify a separate restored copy
   before promotion. Keep records, trust configuration, retained state and key
   backups in their intended separate administrative locations. Record the
   manifest, last witnessed checkpoint, package version and backup time.
4. Reopen a recovered writer through `Writer.open_verified` with independent
   pins, signed status and the retained state file. Missing records require a
   complete trusted backup; witness digests cannot recreate payloads.
5. Restore a lost key only from its protected backup. If the original key or
   required history cannot be recovered, follow the documented discontinuous
   epoch procedure. A replacement key cannot continue the old log identity.
6. A rolled-back witness must not resume signing unless completeness against
   previously acknowledged receipts can be established independently. If that
   cannot be established, retire its identity. The rollback tests demonstrate
   client detection, not automatic witness disaster recovery.

## Backup failure boundaries

Backups copy into a private `.casf-backup-*` directory beside the requested
destination. The file has mode 600. After the SQLite copy closes and the file
is flushed, a hard link publishes the complete file without overwriting any
existing destination. The staging directory is removed and the destination
directory is flushed before success is returned. This requires local filesystem
support for hard links and directory synchronization on macOS or Linux.

A process kill can leave a private staging directory. It is not a published
backup and must not be promoted. Remove that particular leftover only after
confirming no backup process is using it. Ordinary exceptions clean up staging.
A failure after publication, including directory synchronization failure, can
leave a complete destination even though the operation reported an error.
Inspect and verify it; retry to a new path instead of deleting or overwriting it
automatically. Publication atomicity does not establish hardware durability.

## Limits

SQLite `max_page_count` produces real `SQLITE_FULL` errors without filling the
host disk. Backup copy and sync failures inject `ENOSPC`; process tests terminate
at selected boundaries. These are not physical power-loss tests or an exhaustive
filesystem/device failure campaign. Deployment-specific storage testing and
the broader process crash/concurrency matrix remain separate acceptance work.
Full specification conformance and release readiness are not established by
these drills alone.
