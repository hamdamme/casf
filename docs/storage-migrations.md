# SQLite storage and migration

Current source creates **schema version 1** stores. Writer and witness stores
have different application identities. Opening checks the version, complete
DDL, SQLite integrity and foreign-key relationships. Unversioned, future,
wrong-kind or modified schemas are refused before changing journal settings.
New stores initialize their schema and version markers in one transaction.

Keys are non-null. Log/event identifiers have fixed lengths; digests are
64 lowercase hexadecimal characters. Counts, indexes, seals, states and retry
values have type and range checks. Envelopes remain nonempty BLOBs. Records,
heads and checkpoints reference their manifests; receipts reference stored
checkpoints. Pending submissions and timers reference checkpoints in the same
log. Witness status references its manifest. Append-only guards remain active.
These checks constrain local storage. They do not authenticate lookup columns,
prove freshness, or prevent a file administrator from replacing the database.

## Upgrade an unversioned store

This is a breaking storage change from the earlier experimental source.
Use the new source or a separately checked package containing this command.
The older `0.1.0rc1` artifacts do not contain it. Wire objects and evidence
bundles still use the unchanged `casf-v1` interpretation.

1. Stop every process writing either store, including checkpoint workers and
   witness services. Retain a complete SQLite backup and independently retained
   trust/high-water state. Do not copy only a live database's main file.
2. Copy each unversioned store to a **new, unused path**:

   ```bash
   casf storage migrate --source writer-v0.db --destination writer-v1.db --kind writer --json
   casf storage migrate --source witness-v0.db --destination witness-v1.db --kind witness --json
   ```

3. Keep the source files. Migration reports success only after a constrained
   copy has been committed, flushed and published. It does not select the new
   files in any service configuration, authenticate the historical evidence,
   or update external retained state.
4. Validate the new files with existing keys, independently provisioned trust
   and retained state. Reopen the writer through
   [verified startup](writer-recovery.md), using the migrated witness at the
   provisioned endpoint. Confirm pending receipts, final seals and counts;
   then update service paths and resume. Preserve the old files for recovery.
   Never reset retained state or use local-only mode to bypass a failed check.

For library callers:

```python
from casf.storage import migrate_database

migrate_database("writer-v0.db", "writer-v1.db", kind="writer")
```

The migration recognizes the earlier writer layout with or without
`checkpoint_schedule`, and the witness layout with or without `w_status`.
A missing optional table is created empty: missing status does not authorize
a witness operation. Every existing row and envelope byte is copied unchanged.
Already versioned stores should use the SQLite backup operation. Custom or
unknown schemas require a separately reviewed migration.

## Failure and recovery

Migration uses a private disk snapshot through SQLite's
[backup API](https://www.sqlite.org/backup.html), including committed WAL data.
A failed constraint, unsupported schema, disk error or interrupted copy cannot
partially upgrade the source. Rows enter the destination schema in one
transaction. Publication refuses an existing file, directory or symlink,
including a destination created during the copy. The main file and its `-wal`
and `-shm` names must all be unused; dangling symlinks also cause refusal.
Backup rechecks before publication and after directory synchronization, and
never deletes an existing sidecar. Keep other processes away from the destination
until the operation finishes.

A sidecar arriving during publication causes failure even if the new main file
is already visible. Preserve those artifacts and retry at a genuinely unused
path; do not delete a sidecar or trust the published copy merely because local
integrity passes. Stale WAL can contain different but correctly signed history.

On failure, leave the source and external state intact and inspect the error.
Do not drop constraints or edit signed envelopes to make migration succeed.
A process killed before publication may leave a private `.casf-migrate-*` or
`.casf-backup-*` directory; remove it only after confirming no migration is
running. A directory-flush error after publication may leave a complete
version 1 destination. Check that file before choosing another destination;
never automatically overwrite or promote it. Migration does not atomically
switch a live service, and filesystem/hardware durability assumptions remain.

The [decision](adr/ADR-010-storage-migrations.md),
[frozen fixture stores](../tests/fixtures/storage-v0/README.md) and
[regressions](../tests/unit/test_storage_migrations.py) record the supported
transition. New constraints follow SQLite's
[foreign-key rules](https://www.sqlite.org/foreignkeys.html); they complement
CASF's signature and retained-state checks.
