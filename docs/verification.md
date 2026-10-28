# Verification status and resource budgets

Verification requires an authority signed status statement for the expected
manifest with a serial at least as large as the provisioned minimum. Supply
statements as `status_envelopes` to the Python verifier or as `status.jsonl`
in a bundle. Provision the initial active statement using the authority
workflow. Exporting writer records does not authorize the writer to create
an authority statement.

A missing or unrelated statement reports `STATUS_MISSING`, UNKNOWN trust,
and FAIL. The CLI returns exit code 3. Invalid signatures, issuer mismatches,
stale serials, and revocation also fail. A verified revoked statement cannot
be undone by an active statement later in the supplied list. Malformed status
input fails verification even if another valid active statement is present;
valid statements for a different manifest are ignored. This strict handling
prevents malformed evidence from being silently accepted.

A signed active statement proves its signed content, not that no later
revocation exists. `STATUS_CURRENTNESS_UNCONFIRMED` records this limitation.
An online witness response does not establish current authority status.
Previously accepted bundles without status evidence must obtain an authentic
statement; do not disable trust checks to recover an overall PASS.

## Remembered verifier state

Every CLI verification requires `--state PATH`. Use a private directory owned
by the current user, with mode 700, outside the bundle and witness backups.
State and lock files use mode 600. The reference implementation supports local
macOS and Linux filesystems; network filesystem locking is not established.

Create the directory once. Explicitly initialize the first accepted observation:

```bash
mkdir -m 700 verifier-state
casf verify bundle --trust trust.json --state verifier-state/state.json --initialize-state --mode online
```

For later verifications, omit `--initialize-state` and use the same state path:

```bash
casf verify bundle --trust trust.json --state verifier-state/state.json --mode online
```

The version 1 state file maps each manifest hash to the greatest authority
status serial accepted during a successful verification, plus a checkpoint
index and hash when anchored or online verification established one. First
use reports `VERIFIER_STATE_INITIALIZED`; the first checkpoint observation
also reports `CHECKPOINT_FIRST_OBSERVATION`. These indicate a new baseline,
not proof that no history was lost before that observation.

The verifier checks the supplied checkpoint chain against the saved checkpoint,
including when the new checkpoint has a higher index. Online mode also checks
the fresh signed witness view. All modes enforce the greater of the provisioned
and saved status serial minimums. Integrity mode does not check witness history
or advance the saved checkpoint; it preserves any existing checkpoint.

One persistent sidecar lock covers reading state, verification, and saving.
Concurrent processes wait for that lock and read the latest saved state before
verifying. A successful result is reported only after a temporary file has
been flushed, atomically replaced, and its directory flushed. Failed or
inconclusive verification does not update the observations. The sidecar lock
may be created even when verification fails; do not remove it while verifiers
are running. State input is limited to 1 MiB and rejects duplicate or unknown
fields, unsafe permissions, symbolic links, and hard links.

Missing, malformed, unreadable, or unwritable state produces a local error
(exit code 5), without a PASS. Restore a trusted copy after loss or damage.
`--initialize-state` refuses existing observations for the same manifest and
cannot overwrite malformed state. It can add an explicitly provisioned new
manifest to an existing valid file. Never use initialization as an automatic
recovery step: deleting state and initializing again discards continuity.
A save error after replacement may leave a valid newer file; inspect and
retry normally instead of deleting it. Historical CLI examples predate this
required option; use the commands above for the current implementation.

These are local retained observations, not independently current revocation
information. Rejected status statements, including revocations that cause a
FAIL, are not persisted by this successful verification store. Administrators
must maintain trusted revocation provisioning. If the witness and verifier
state are both restored, or an attacker controls the verifier state, rollback
protection can be lost. Protect and back up this file separately from the
witness and evidence. Do not store it in a public repository.

Library callers remain responsible for durable state. The verifier report
exposes `observed_status_serial` and `checkpoint`; persist them only for PASS,
and supply them through the next call's `minimum_status_serial` trust pin
and `retained_checkpoint` argument while holding an appropriate lock.

## Unsigned online errors

An unsigned `NO_CHECKPOINT` response cannot prove that the witness lost
previously accepted history. Online verification therefore reports
`INCONCLUSIVE` with `FRESHNESS_INCONCLUSIVE`; the CLI returns exit code 4.
This applies even when valid checkpoint and receipt evidence is supplied.
It does not turn the error into a PASS or invalidate the supplied evidence.

In anchored mode, if checkpoints are supplied but none of the receipts
identifies the newest checkpoint, verification fails with
`RECEIPT_CHECKPOINT_MISMATCH`. If no receipts are supplied, the anchor is
incomplete and verification reports `RECEIPT_MISSING`. This strict behavior
can reject a bundle collected while receipt delivery is still pending; obtain
the matching receipt and verify again.

A validated signed witness view that conflicts with the supplied anchor or
retained checkpoint still reports `FAIL` with `WITNESS_STATE_CONFLICT`.
The witness rejects conflicting signed checkpoints but does not retain both
statements as a separate proof record. Operators who need third party
equivocation evidence must preserve the submitted checkpoint envelopes.
The online client continues to raise `NoCheckpointError` for the unsigned
response; the verifier treats that exception as unavailable freshness evidence.

## Work and input limits

The Python verifier accepts positive integer `max_chain_steps` and
`max_records` arguments. Defaults are 10000 and 1000000 respectively.
Checkpoint, receipt, and status streams each have the chain budget. One
additional item may be consumed to detect excess input, but it is not
validated cryptographically. Budget exhaustion is INCONCLUSIVE unless an
existing failure already prevents acceptance. The CLI honors the trust
policy's `max_chain_steps` and returns code 4 for an inconclusive result.

Bundle reads reject symbolic links and nonregular files, use bounded object
and line reads, and share a total byte budget across all bundle members,
including status.jsonl. Defaults are 128 KiB per record line, 32 KiB per
protocol envelope, 1000000 records, 100000 objects per evidence file, and
256 MiB total input. Limits are checked before parsing the excess input.
Invalid input returns CLI code 2. Each oversized item is rejected before
its cryptographic verification; earlier valid records may already have been checked.

Use `open_bundle` arguments `max_records`, `max_evidence_objects`, and
`max_total_bytes` to select smaller or larger budgets. The CLI exposes
`--max-records`, `--max-evidence-objects`, and `--max-bundle-bytes`.
The CLI streams records once and retains digests only at bounded checkpoint
boundaries. Protocol evidence lists remain bounded by the configured limits;
raising those limits raises the memory ceiling. Actual protocol memory can
increase with checkpoint and receipt counts within those limits.

```python
from casf.bundle import open_bundle
from casf.verifier import verify

with open_bundle(path) as bundle:
    report = verify(bundle.manifest, bundle.records, pins,
                    status_envelopes=bundle.statuses)
    for _ in bundle.records:
        pass  # Validate any unread tail before accepting the report.
```

Catch `CasfError` and `OSError` around the entire context. A read failure is
not a successful report. The CLI checks EOF before saving accepted state or
printing PASS. Its malformed input exit code is 2 and local I/O exit code is 5.
`read_bundle` retains the eager list API for compatibility and restore; callers
choosing it still allocate memory proportional to records. See the
[API decision](adr/ADR-006-streaming-verification.md) for iteration and memory bounds.

These changes do not alter signed bytes, key algorithms, or existing evidence.
The file reader was checked on macOS arm64 and Ubuntu 24.04 x86_64. The
current release validation scope is Python 3.12 through 3.14 on those systems.
Windows portability of its filesystem flags has not been established. See the
[Phase 3 closeout record](release/phase3-closeout-2026-10-28.md) for the exact
runtime inventory and evidence.
