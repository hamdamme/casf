# Current CASF implementation reference

The experimental 0.1.0rc2 GitHub prerelease is published. The
[publication record](release/publication-0.1.0rc2.md) distinguishes the build commit,
accepted review revision, Linux validation and public-installation evidence.
Start with the [operating handoff](operating-handoff.md). The separate
[research follow-up](../research/current-evidence-2026-11-10.md) identifies its
measurement revision and preserves the historical results.
The [completion tracker](release/completion-tracker.md) distinguishes completed
work from remaining validation, research and release gates. Package metadata is
`0.1.0rc2`; the proposed wire profile is `casf-v1`. These identify different
things. Validation records must name the exact source or artifact bytes.

## Which document to use

| Purpose | Current reference |
| --- | --- |
| Install and verify | [Installation](installation.md) and [verification](verification.md) |
| Run a complete synthetic example | [Verified workflow demo](demo.md) |
| Provision keys, manifests, trust and status | [Administration](administration.md) |
| Operate the reference service | [Witness server](witness-server.md) |
| Protocol requirements and threat model | [CASF SPEC 001 revision 0.10](specification/CASF_SPEC_001.md) |
| Research questions, outcomes and source records | [Research guide](../research/README.md) |
| Exact candidate files and installation checks | [Candidate record](release/candidate-0.1.0rc2.md) and [build procedure](release/candidate-build.md) |
| Release preparation and advisory scope | [Release notes](release/notes-0.1.0rc2.md), [dependency review](release/dependency-review-0.1.0rc2.md) and [approval proposal](release/approval-0.1.0rc2.md) |
| Candidate state and validation | [Release checklist](release/checklist-v0.1.md) |
| Current workflow and scoped code review | [Review record](release/workflow-review-2026-11-10.md) |
| Completion phases and current task status | [Completion tracker](release/completion-tracker.md) |
| Local startup checks, backup and restore | [Writer recovery](writer-recovery.md) |
| Recovery failure cases and operating steps | [Recovery drills](recovery-drills.md) |
| Typed log, checkpoint, witness and export operations | [Log API](log-api.md) |
| Immutable append requests and results | [Append API](append-api.md) |
| Prefix exports and machine diagnostics | [Export and reports](export-and-reports.md) |
| SQLite schema checks and upgrades | [Storage migration](storage-migrations.md) |
| Automatic checkpoint scheduling and retries | [Checkpoint worker](checkpoint-worker.md) |
| Generated inputs and parser fuzzing | [Adversarial testing](adversarial-testing.md) |
| Test evidence and its limits | [Requirement evidence](release/requirement-evidence.md) and [coverage](release/test-coverage-status.md) |
| Supported platform checks and retained results | [Validation matrix](release/validation-matrix.md) |

The [repository review](release/repository-review.md) accounts for tracked files
and records retained historical material, corrections and verification limits.
The [line-review continuation](release/line-review-2026-11-11.md) records additional
source fixes and the methods used for all tracked files. Those fixes are unreleased and are
not included in the published `0.1.0rc2` downloads.

The specification states intended requirements, not proof of complete
implementation. The source and tests establish implemented behavior. The
numbered documents `01` through `05` and the [original technical Word document](historical/README.md)
describe the earlier prototype. Their HMAC, encryption and `auditfw` examples
are historical, not installation or API instructions for the current package.
Dated release records describe only their recorded revisions and artifacts.

## Implemented workflow

1. Obtain the authority public key through an independent trusted channel.
   Create or verify a signed manifest, provision trust pins, and obtain an
   authority signed status statement. Public key possession alone does not
   establish the operator's identity.
2. Initialize with `Writer.initialize_verified` and reopen with
   `Writer.open_verified`, passing independent pins and `StartupPolicy`.
   CLI writing commands require trust, signed status and retained state by
   default. Startup checks full local history, active status, a fresh witness
   view and external persistence before permitting new signed records.
3. Explicitly create a checkpoint and submit it to the registered witness.
   The witness validates the extension and stores a signed receipt. Append
   does not wait for a receipt or automatically schedule submission.
4. Export a bundle. Export includes records and accepted checkpoint and
   receipt evidence; add authentic authority status separately as
   `status.jsonl`. Export needs no private key. A pending final checkpoint
   must obtain its receipt before export; use a database backup when pending
   state must be preserved.
5. Verify with provisioned trust and separately retained verifier state.
   Every CLI verification requires `--state`; initialize each manifest's
   first observation explicitly and retain that state for subsequent checks.

A PDF demonstration records an application supplied fingerprint. CASF verifies
that signed event; a separate hash computation compares the PDF bytes.
CASF does not automatically open, hash, or authenticate the document's origin.

## API and verification behavior

The implemented writer API is `casf.writer.Writer`. Use `StartupPolicy` with
`initialize_verified` or `open_verified` before `append` and checkpoint
operations. A direct signing constructor requires explicit `local_only=True`;
keyless readers remain available. Offline `restore_from_bundle` returns a
keyless reader by default and must be promoted through verified startup.

Independent pins authenticate the authority, expected log, manifest and
witness. Supplied signed status is checked against both provisioned and retained
serial minima; observed revocation is terminal across runs. A fresh witness
query reconciles missing journal evidence before the external checkpoint is
saved and writing resumes. Already open verified writers check retained status
before further signing. Status distribution remains administrative, so an
active statement does not prove there is no undistributed revocation.

`Writer.append_event(log_id, EventRequest)` returns an immutable `AppendResult`
with the committed record and its transaction's witness observation. The
existing `Writer.append` keeps its dictionary return and now snapshots nested
input before calculating the request digest. See the [typed append guide](append-api.md).
`casf.api.open_log` binds an existing writer and exposes typed checkpoint,
witness-submission, export and seal operations. The existing Writer return
values remain available. See the [log API guide](log-api.md) for ownership,
commit boundaries and creation behavior. The [verifier API guide](verifier-api.md)
covers complete bundle reads and explicit trusted checkpoint starts.

The public verifier entry points are `casf.verifier.verify_bundle` and `verify`.
Their `Report` uses overall `PASS`,
`FAIL` and `INCONCLUSIVE`. Diagnostic JSON version 2 uses SPEC section 15 enum
labels, explicit NOT_CHECKED dimensions and inconclusive missing-trust verdicts.
`Report.to_dict()` and CLI JSON expose every diagnostic field, including the
verified range, failure position, checkpoint identity and requested policy.
`overall` is the canonical verdict; `result` remains a compatibility field.
See [export and report contracts](export-and-reports.md) for migration details.

Verification starts from record 1 by default. An explicit `VerificationAnchor`
authenticates a checkpoint and receipt against an independently retained hash
and provisioned keys, then verifies only the contiguous suffix. Reports identify
the trusted prefix and the bodies actually checked. Retained checkpoints still
constrain continuity; missing earlier history cannot authorize advancement.
A valid signature chain does not
prove that it is the latest history. `WITNESS_AHEAD` can be inconclusive when
intervening evidence is unavailable; a conflicting authenticated retained
checkpoint produces `WITNESS_STATE_CONFLICT`. The H1 research guide records
that distinction rather than treating both as the same observed outcome.

`verify_bundle`, `open_bundle`, writer export and the CLI stream records.
`verify_bundle` drains input through EOF and closes files before returning.
The verifier retains record digests
only at checkpoint boundaries, subject to bounded protocol evidence and input
budgets. `read_bundle` and restore remain eager and can use
memory proportional to record count. Streaming verification is not a claim
of constant memory for every operation.

## Operational limits and specification differences

| Area | Implemented behavior and consequence | Source or evidence |
| --- | --- | --- |
| Startup | Verified opening checks independent pins, supplied active status, full local history and fresh witness continuity, then saves external high-water state before allowing writes. Revocation persists across restarts. Explicit local-only mode bypasses this authorization. Work grows with history size. | [Recovery guide](writer-recovery.md), [startup tests](../tests/unit/test_verified_startup.py) |
| Restore | Verified records, checkpoints, receipts and seals are rebuilt atomically. Signed anchors require independent pins; bare anchors remain caller-authenticated. An anchor ahead of restored records seals the store. Offline restore returns a keyless reader; verified startup is required before signing. | [Recovery guide](writer-recovery.md), [anchor tests](../tests/unit/test_restore_anchors.py) |
| Scheduling and recovery | Verified startup reconciles fresh witness history. The foreground checkpoint worker schedules 128-record/60-second checkpoints and durable bounded retries, preserving pending bytes and final seals. A checkpoint batch limit is not a hard bound on the backlog during an outage. | [Worker guide](checkpoint-worker.md), [historical H3 method](../research/h3-witness-outage.md) |
| SQLite | Version 1 writer and witness schemas enforce relationships, exact lengths, types and ranges with WAL/FULL settings. Existing unversioned stores require explicit migration to a new path; envelope bytes and pending state are preserved. Structural checks do not establish freshness. | [Migration guide](storage-migrations.md), [storage tests](../tests/unit/test_storage_migrations.py) |
| Export and status | Export streams a selected prefix from one snapshot and publishes without replacing any destination. Accepted checkpoint evidence is limited to that prefix. A pending final seal blocks export; database backup preserves pending state. Export does not create authority status. | [Export guide](export-and-reports.md), [verification](verification.md) |
| Network | The client bounds total request time, response bytes, individual status and header lines, and header count. The reference service still needs operational TLS and access controls. | [Transport](../src/casf/transport.py), [server guide](witness-server.md) |
| Validation | Hypothesis properties, bounded parser mutation campaigns and 27 process-crash cases run with the full suite on Ubuntu and macOS. Named transaction and replacement boundaries are covered; complete generated state machines, coverage-guided fuzzing and physical power loss are not. | [Coverage status](release/test-coverage-status.md), [validation matrix](release/validation-matrix.md) |

These differences remain explicit implementation limits. This guide does not
amend the normative specification or mark full conformance achieved. Changes
to trust, recovery or authenticated formats require a separate design decision
and targeted implementation evidence.

## Evidence boundaries

Hosted CI targets Ubuntu x86_64 and macOS arm64 for Python 3.12, 3.13 and 3.14,
with locked and minimum direct dependencies. Each job retains source/import
identity, actual runtime components and test reports. Results apply to their
recorded revision. Historical manual platform inventories remain separate and
do not certify all systems with the same operating system name.

Research results remain tied to their original manifests, environments and
source digests. Current code tests, historical measurements, limited external
review and an exact package artifact approval are separate evidence. Use the
[release checklist](release/checklist-v0.1.md) for their current disposition.

The [Team A remediation](release/team-a-remediation.md) records subsequent API
and submission hardening. See the separate [production gates](release/production-readiness-gates.md)
for work that code tests cannot establish.
