# Writer startup and recovery

The writer verifies local records and the checkpoint journal when opening a
database. Bundle restore preserves supplied, verified checkpoint and receipt
history and any final seal. Independently supplied trust pins also authenticate
the manifest authority and bind the expected log, manifest and witness.

## Independently pinned manifests

Pass `trust_pins` to `Writer` and `Writer.restore_from_bundle`. The mapping
uses expected log IDs as keys and `casf.verifier.TrustPins` values. Each value
must include an explicit `manifest_hash`, the authority public key under its
derived issuer ID, and the witness public key under its derived witness ID.
Obtain these pins through an authenticated channel independent of the database
or bundle. Do not build a trust policy from the evidence being checked.

```python
from casf.writer import Writer

# provisioned_pins is a separately loaded mapping of log IDs to TrustPins.
writer = Writer("writer.db", log_private_key, trust_pins=provisioned_pins)
try:
    writer.create_log(manifest)
finally:
    writer.close()

restored = Writer.restore_from_bundle(
    "restored.db", log_private_key, "bundle", trust_pins=provisioned_pins,
)
restored.close()
```

The writer checks the authority signature and exact pinned identities at
creation, startup and restore, and rechecks the manifest before appending or
creating a checkpoint. A supplied policy never falls back for an unprovisioned
log; an empty mapping authorizes no logs. The mapping and key dictionaries are
copied at open so later caller changes cannot alter an active writer's policy.
Pins can also be supplied to a keyless reader.

For compatibility, omitting `trust_pins` retains local-only validation and does
not authenticate the manifest authority. CLI writer commands accept `--trust
trust.json`; see [administration](administration.md#use-pins-with-writer-commands).
Supply it on every invocation. Pins are not persisted as trust inside the log
database. Writer pin checks do not evaluate authority status or
`minimum_status_serial`, apply the verifier's mode policy, or query fresh
witness state. Use the verifier for status and evidence evaluation. Full
startup and recovery conformance remains incomplete.

## Local startup checks

Opening `Writer` verifies manifest key bindings, every record's schema,
signature, sequence, predecessor and manifest binding, and the stored lookup
indexes and head. It then checks the signed checkpoint and receipt chains,
their correspondence with verified records, the pending outbox range, and the
final sealed state. Reads use one SQLite snapshot so a concurrent append does
not cause a false mismatch. Verification streams records; startup now performs
work proportional to the stored history and journal.

The writer refuses inconsistent local state and closes its connection on a
failed startup. Supplying the wrong signing key cannot append a record or
create a checkpoint for an existing log. A keyless writer can still read and
export a locally valid store.

Incoming receipts must match the manifest and immediately preceding accepted
receipt before the writer clears the pending checkpoint. A rejected receipt
leaves the outbox unchanged, including across restart, so a valid receipt can
still complete the pending submission.

## Bundle restore

`Writer.restore_from_bundle` requires a new destination. It validates records
and supplied checkpoint/receipt chains before committing restored history.
Accepted receipts retain their original signed contents and checkpoint
indices. Subsequent checkpoints continue the chain rather than restarting at
index zero. A final checkpoint retains its seal, including for an empty log.

A bundle may supply at most one signed pending tail after a complete accepted
prefix. Restore recreates that pending outbox entry with identical checkpoint
bytes, so the normal witness submission/receipt path can recover it. Receipts
are never invented. A validation failure removes the newly created partial
database. A valid restore behind a supplied external anchor is deliberately
retained sealed for inspection and raises `RESTORE_BEHIND_WITNESS`.

Manifest, records and journal are committed in one transaction. A process
interruption before commit can leave a newly created database schema, but no
partial log is committed and that empty store cannot append to the missing log.

An optional `anchor` must contain a safe integer `count` and a lowercase SHA-256
`head_hash`. If its count is covered by the restored history, its head must
match that exact prefix, even when it is older than the export. If log or
manifest identity fields are supplied, they must match. The caller remains
responsible for authenticating this anchor before passing it in.

For signed external evidence, supply both `anchor_checkpoint` and
`anchor_receipt` with independent `trust_pins`, and omit the bare `anchor`.
Restore authenticates the manifest, both signatures and all pair bindings
before creating the destination. An anchor within the restored record range
must match its checkpoint journal; missing or conflicting journal evidence
is rejected. A matching pending tail can obtain its original receipt from the
anchor pair. A newer anchor beyond the restored record count retains the
database sealed and raises `RESTORE_BEHIND_WITNESS`.

Signed anchors are historical evidence. Their authenticity does not prove
that the witness has no newer checkpoint. Fresh witness reconciliation and
authority status evaluation remain separate requirements.

## Pending final seals and backups

The current bundle exporter includes accepted checkpoints and receipts.
It now refuses to export a final checkpoint that has not yet received a
witness receipt: otherwise an export could omit the final seal and restore as
an open log. Obtain and persist the receipt first, or use `Writer.backup` to
preserve the complete database, including its pending checkpoint. The backup
API uses SQLite's consistent backup facility. Do not copy only a live main
database file and discard its WAL state.

Nonfinal pending checkpoints remain outside the default accepted-only bundle
export. Use the complete database backup when pending state must be recovered.
Broader pending export/report behavior remains a separate interface task.

## Remaining trust and recovery boundaries

Even with manifest pins, local checks cannot distinguish an internally valid
old snapshot from current history without independently retained or fresh
witness evidence. They do not query the witness at startup, establish current
revocation knowledge, or implement the planned automatic checkpoint/retry
worker. Authority keys inside a bundle never establish independent trust.
Reconcile external state before promoting
a restored or suspected-corrupt database. Full specification conformance is
not claimed by these fixes.

## Regression coverage

`tests/unit/test_writer_integrity_recovery.py` covers corrupted record bodies,
signatures and indexes; malformed checkpoint/receipt chains; lost seals;
pending outbox mismatch; accepted and pending final restore; continuation
against the original witness; bad external anchor inputs; failed restore
cleanup; an interrupted restore process; and wrong signing keys. Additional
coverage includes incoming receipt bindings and recovery of a nonfinal
pending checkpoint with an unwitnessed suffix. Requirement links include R02,
R04, R05, R08 and R09 with T03, T04, T08, T14 and T15. Existing concurrency and
process-crash tests continue to exercise snapshot behavior and transaction boundaries.

`tests/unit/test_writer_trust.py` covers supplied authority, witness, log and
manifest pins; forged signatures at creation, startup and restore; missing
provisioning; and caller policy mutation. `tests/unit/test_cli_writer_trust.py`
covers trusted command flows, rejection before writer operations, trust-file
versions and safe diagnostics. These checks support R02, R07, R09 and R10
through T03, T12, T15 and T17. They do not establish status or fresh witness
reconciliation coverage.
