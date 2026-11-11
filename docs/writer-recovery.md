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
from casf.writer import StartupPolicy, Writer

# Obtain these pins and signed status through independent provisioning.
# Keep retained state in an owner-only directory outside the database backup.
startup = StartupPolicy(
    state_path="/protected/casf/state.json",
    status_envelopes=(signed_status,),
    witness_url="https://witness.example",
    token=witness_token,
)
writer = Writer.open_verified(
    "writer.db", log_private_key, trust_pins=provisioned_pins, startup=startup,
)
try:
    writer.append(log_id, event_id=event_id, actor="example",
                  event_type="demonstration", payload={"message": "synthetic event"},
                  attributes={})
finally:
    writer.close()
```

For a new log, use `Writer.initialize_verified(path, key, manifest,
trust_pins=..., startup=...)`. Provision and register the manifest with the
witness first. Set `initialize_state=True` only for an explicitly unobserved
manifest; existing state cannot be reset. Initialization submits an empty
checkpoint and checks a fresh witness response before authorizing records.
If interrupted, reopen with the same policy and retry the exact pending
bootstrap checkpoint. Omit initialization once the state entry exists.

Both entry points verify independent authority, manifest, log and witness pins,
all local history, supplied active status at the retained serial minimum, and
fresh witness continuity. They save the checkpoint externally before clearing
the database hold. Failed state persistence leaves writing blocked; retry can
reconcile an external checkpoint that persisted before a database failure.

Authenticated revocation is retained permanently, including when its serial
is below the retained minimum. A later active statement cannot clear it.
Newly authenticated status serials persist even if witness recovery fails.
Each later accepted receipt updates the external checkpoint before submission
returns success. A failed save preserves the pending checkpoint, retains a
write hold and requires verified reopening.
An already open verified writer rechecks retained status under the state lock
before append, checkpoint creation or submission. A newly observed higher
serial requires reopening with appropriate signed status. Use the same
protected state file consistently for a manifest's writer and verification
observations; retain it outside the database's rollback domain.

Pins and status inputs are copied at open. Supplied signed active status does
not prove that no newer revocation was withheld. This is the existing
administrative status-distribution assumption, not automatic revocation
lookup. Writer startup always reconciles fresh witness state; the trust file's
verification mode and unwitnessed-tail policy still apply separately to bundle
verification. Locally committed records may remain unwitnessed after append.

`Writer(path)` opens a keyless reader for inspection. `Writer(path, key)` now
fails closed; explicit `local_only=True` selects the compatibility writer.
That mode still checks local integrity and any supplied manifest pins, but
bypasses verified startup and retained authority status. Research harnesses and
component tests select it explicitly to preserve their original experimental
procedures. CLI writing commands use verified startup by default and expose
`--local-only` as an explicit alternative. Their JSON output includes
`startup_verified`. See [administration](administration.md#use-pins-with-writer-commands)
and [ADR-008](adr/ADR-008-verified-writer-startup.md).

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

`Writer.restore_from_bundle` requires a new destination and returns a keyless
reader by default. Reopen through `Writer.open_verified` before signing. An
explicit `local_only=True` retains the compatibility return behavior. It validates records
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
that the witness has no newer checkpoint. Use explicit fresh reconciliation
before promoting a restored store; restore does not invoke it automatically.

### Authority status during restore

Set `require_active_status=True` with independent `trust_pins` to check the
bundle's signed status statements before creating the destination. This uses
the public verifier's status and integrity rules: missing, forged, unrelated,
revoked or below-minimum status fails. A later active statement cannot override
a supplied revocation. The provisioned `minimum_status_serial` is enforced;
pass the maximum independently retained minimum when recovering a known log.

This option is false for compatibility with the local-only restore API.
It checks supplied evidence, does not discover newer revocations, and does not
persist or update external status high-water state. Writer startup and append
do not inherit continuous status enforcement from a successful restore.
Verified startup applies retained status and fresh witness checks before the
restored database can sign. Offline restore does not perform promotion.

## Recover a pending receipt

After a restart, `Writer.recover_pending_receipt(log_id, base_url, token)`
looks up the existing pending checkpoint digest. It requires independently
supplied trust pins and can use a keyless writer. The returned checkpoint must
match the pending bytes; both signatures, identity bindings and the preceding
receipt link are checked before the outbox clears atomically.

```sh
casf witness recover --db writer.db --trust trust.json \
  --url https://witness.example --json
```

No checkpoint is resubmitted or regenerated. Missing receipts, transport
failures and rejected evidence leave the pending checkpoint intact. The CLI
returns 4 when the receipt is unavailable, and 1 for invalid signed evidence.
Success reports `recovered: true`, its count and `freshness_checked: false`.
This retrieves historical acceptance; it does not query a fresh witness view,
recover a longer missing journal, or run an automatic retry worker.

## Reconcile a fresh witness journal

`Writer.reconcile_witness` queries a fresh nonce-bound witness view, authenticates
the checkpoint and receipt under independent pins, and retrieves any missing
accepted journal. It verifies every recovered pair and its record head before
committing the journal. This API needs no signing key and is separate from the
historical `casf witness recover` command.

```python
from casf.writer import Writer

# Evaluate signed authority status and its retained serial before promotion.
# Load provisioned_pins, witness_url, token and retained_checkpoint independently.
writer = Writer("restored.db", trust_pins=provisioned_pins)
try:
    view = writer.reconcile_witness(
        log_id, witness_url, token,
        retained_checkpoint=retained_checkpoint,  # (index, digest), or None initially
        timeout=10.0, max_chain_steps=10_000,
    )
    # Persist the validated checkpoint in independently retained state.
    accepted = (view.body["checkpoint_index"], view.body["checkpoint_hash"])
finally:
    writer.close()
```

The optional retained checkpoint must occur in the verified journal. Missing,
lower or conflicting evidence fails without advancing accepted local state.
The method returns a `LatestView`; its count is the witnessed prefix, which can
be shorter than the locally committed history. Freshness means the witness
signed that view during this query under its honesty assumption. It does not
establish current authority status or discover withheld records.

Reconciliation commits a durable write hold before contacting the witness.
Timeouts, replay, invalid evidence, missing chain links and process interruption
leave the previous journal readable and block new appends and checkpoints,
including after restart. A successful retry atomically installs the recovered
journal and clears the hold. Exact pending bytes are preserved unless the
witness supplies their matching receipt. Accepted and pending final seals remain
sealed. Already committed duplicate appends may return their existing result.

A fresh authenticated checkpoint beyond the local record count raises
`RESTORE_BEHIND_WITNESS` and retains a terminal seal. A later lower witness view
cannot clear it. Recover missing records into a new verified store or create a
documented discontinuous epoch; receipt history cannot replace lost records.
`NO_CHECKPOINT` is not permission to resume a restored store.

Network requests share one monotonic timeout and missing checkpoint retrieval
has a step budget. A bounded advisory lock serializes recoveries. Network requests run outside
SQLite transactions while the committed hold blocks new writes. Local history
and concurrent receipt changes are rechecked in the final write transaction.
Local history validation and lock acquisition add to elapsed time. Configuration
and pin errors are rejected before starting the hold. See
[ADR-007](adr/ADR-007-witness-reconciliation.md) for storage compatibility and
transaction behavior.

The low-level reconciliation operation does not itself persist external state
or evaluate authority status. Verified startup combines these operations and
authorizes writing only after all succeed. The [checkpoint worker](checkpoint-worker.md)
provides automatic scheduling and durable retries after verified startup.
Bundle export does not carry the database's operational hold;
promoting a new restore still requires independent recovery checks.

## Pending final seals and backups

The current bundle exporter includes accepted checkpoints and receipts.
It now refuses to export a final checkpoint that has not yet received a
witness receipt: otherwise an export could omit the final seal and restore as
an open log. Obtain and persist the receipt first, or use `Writer.backup` to
preserve the complete database, including its pending checkpoint. The backup
API uses SQLite's consistent backup facility. Do not copy only a live main
database file and discard its WAL state.

Backup publication now uses a private temporary copy, flushes the complete
file and publishes it without replacing an existing destination. Interrupted
copies are not published. A directory-sync failure can leave a complete backup
while still reporting failure; verify it and retry to a new path. See the
[recovery drills and operating procedure](recovery-drills.md) for storage
exhaustion, corrupt backup, key loss, rollback and witness outage handling.

Nonfinal pending checkpoints remain outside the default accepted-only bundle
export. Use the complete database backup when pending state must be recovered.
[Prefix export and complete diagnostic output](export-and-reports.md) are
available. [Typed operation results](log-api.md) and the
[version 2 report contract](export-and-reports.md#complete-machine-diagnostics)
are implemented; earlier interface-work notes are historical.

## Remaining trust and recovery boundaries

Even with manifest pins, local checks cannot distinguish an internally valid
old snapshot from current history without independently retained or fresh
witness evidence. The explicit local-only path does not query the witness at startup. Verified
startup does query it, but cannot establish undistributed revocation knowledge.
Automatic scheduling requires running the checkpoint worker separately.
Authority keys inside a bundle never establish independent trust.
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

`tests/unit/test_latest_bindings.py` rejects conflicting signed latest fields.
`tests/unit/test_writer_reconciliation.py` covers fresh journal recovery,
retained-state conflicts, missing records, pending and final checkpoints,
shared deadlines, competing writes and a real process exit after journal
insertion. The restart verifies that only the hold survived the interrupted
transaction, then recovers against the same HTTP witness.

`tests/unit/test_verified_startup.py` and
`tests/unit/test_cli_verified_startup.py` cover default write authorization,
terminal revocation across runs, old open writers, failed external persistence,
keyless restore, bootstrap retries and the real CLI/witness workflow.
