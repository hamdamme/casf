# Versioned SQLite stores and explicit migration

This decision records its implementation-time context. Statements about separate
work refer to that stage; use the [current reference](../current-reference.md)
and [completion tracker](../release/completion-tracker.md) for present behavior
and acceptance status.

SPEC §§17 and 20 require relationships, exact length checks and versioned,
transactional migrations that preserve authenticated bytes. Earlier stores
have no version marker or foreign keys. Silently adding tables cannot install
constraints on existing tables. This decision replaces that initialization
behavior without changing the casf-v1 wire format or trust rules.

New writer and witness stores use schema version 1 (`PRAGMA user_version`),
with distinct application IDs (`CASF` and `CASW`). Opening an existing store
checks its version, identity and complete schema before permitting use.
Unknown versions, altered schemas and unversioned stores are refused; opening
never silently upgrades them. Declared relationships, non-null keys, digest
lengths, stored types, ranges and state values constrain new writes. Startup
also checks SQLite integrity and foreign-key violations. These are accidental
corruption checks, not authentication or protection against an administrator.

The explicit migration copies a recognized unversioned writer or witness store
to a separate destination. A SQLite backup snapshot includes committed WAL
content. All rows are copied into the new schema in one transaction, preserving
every envelope BLOB, lookup value, seal and pending retry value. Constraint
failures abort the copy. A complete flushed database is published without
replacing an existing path, using the existing backup publication procedure.
The source remains the rollback copy. Migration neither repairs evidence nor
updates external retained state; verified writer startup remains mandatory.

Recognized inputs are the unversioned schemas before and after addition of
`checkpoint_schedule` (writer) or `w_status` (witness). Missing optional tables
start empty; an absent witness status grants no active authority. Published
synthetic SQL fixture stores pin the input layout and authenticated bytes.
Already versioned stores use backup instead of migration. Unknown/custom
layouts require a separately reviewed migration, never best-effort copying.

Operators stop all writers and witness services before migrating and keep the
source and external state until validation and cutover succeed. The copy API
provides a consistent snapshot, not atomic replacement of a running service.
Interruptions before publication leave no destination; a hard process exit may
leave private staging files. A directory-flush error after publication may
leave a complete destination that must be checked before retrying. Filesystem
and hardware durability assumptions are unchanged.

Affected requirements: R04, R08, R09. Regression coverage includes both legacy
layouts, byte preservation, state and retry preservation, invalid relationships,
unknown schemas, interruptions and publication failures. Historical research
outputs and cryptographic vectors are unchanged; later experiment reruns use
new output locations.

## Destination sidecar publication checks

A stale destination WAL can replace the effective history of a newly published
main database with different, independently valid records. Local integrity
verification is not sufficient to prove that a backup matches its source.

Backup and migration refuse an existing main file, `-wal`, or `-shm`, including
dangling symlinks, without deleting any artifact. Backup rechecks after copying,
before the exclusive hard link, and checks sidecars again after publication and
directory synchronization before acknowledging success. Migration uses the same
publication path and also checks before reading/copying its source. The live
source retains WAL mode; its SQLite backup snapshot procedure is unchanged.

A sidecar collision discovered after publication is an explicit failure. The
new main file and colliding artifacts remain for investigation; they must not be
promoted based only on local integrity checks. Retry at a genuinely unused path.
As with service cutover, operators must keep the destination under exclusive
control through completion: these checks do not lock out unrelated processes
that open or modify the destination. Main-file nonreplacement remains atomic;
no multi-file filesystem transaction or live-service replacement is claimed.
