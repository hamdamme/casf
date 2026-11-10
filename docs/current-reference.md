# Current CASF implementation reference

This guide describes the implementation at source revision
`93ba4325675c948b108a0281c2b0d97c713decdc` after PR 28. Package metadata is
`0.1.0rc1`; the proposed wire profile is `casf-v1`. These identify different
things. A package version alone does not identify the source or artifact bytes.

## Which document to use

| Purpose | Current reference |
| --- | --- |
| Install and verify | [Installation](installation.md) and [verification](verification.md) |
| Provision keys, manifests, trust and status | [Administration](administration.md) |
| Operate the reference service | [Witness server](witness-server.md) |
| Protocol requirements and threat model | [CASF SPEC 001 revision 0.10](specification/CASF_SPEC_001.md) |
| Research questions, outcomes and source records | [Research guide](../research/README.md) |
| Candidate state and validation | [Release checklist](release/checklist-v0.1.md) |
| Test evidence and its limits | [Requirement evidence](release/requirement-evidence.md) and [coverage](release/test-coverage-status.md) |

The specification states intended requirements, not proof of complete
implementation. The source and tests establish implemented behavior. The
numbered documents `01` through `05` and the original technical Word document
describe the earlier prototype. Their HMAC, encryption and `auditfw` examples
are historical, not installation or API instructions for the current package.
Dated release records describe only their recorded revisions and artifacts.

## Implemented workflow

1. Obtain the authority public key through an independent trusted channel.
   Create or verify a signed manifest, provision trust pins, and obtain an
   authority signed status statement. Public key possession alone does not
   establish the operator's identity.
2. Append events using `Writer` or `casf append`. The writer signs records and
   commits them with the sequence and local head in a SQLite transaction.
3. Explicitly create a checkpoint and submit it to the registered witness.
   The witness validates the extension and stores a signed receipt. Append
   does not wait for a receipt or automatically schedule submission.
4. Export a bundle. Export includes records and accepted checkpoint and
   receipt evidence; add authentic authority status separately as
   `status.jsonl`. Export needs no private key.
5. Verify with provisioned trust and separately retained verifier state.
   Every CLI verification requires `--state`; initialize each manifest's
   first observation explicitly and retain that state for subsequent checks.

A PDF demonstration records an application supplied fingerprint. CASF verifies
that signed event; a separate hash computation compares the PDF bytes.
CASF does not automatically open, hash, or authenticate the document's origin.

## API and verification behavior

The implemented writer API is `casf.writer.Writer`, with methods such as
`create_log`, `append`, `export_bundle`, `backup`, and `restore_from_bundle`.
The conceptual free functions and `AppendResult` in SPEC section 19 are not
the current Python interface. Consult the method signatures in
[`writer/__init__.py`](../src/casf/writer/__init__.py) before integrating.
`create_log` checks the schema, manifest digest and writer key binding; it
does not authenticate the authority signature. Establish that trust before
initializing the writer, for example through `casf admin trust` with an
independently obtained authority public key.

The verifier is `casf.verifier.verify`. Its `Report` uses overall `PASS`,
`FAIL` and `INCONCLUSIVE`; verification dimensions use `OK`, `FAIL` and
`NOT_CHECKED`. Trust and anchor fields have their own enums. The CLI exposes
a subset of these fields, not the entire Python report. See the definitions
in [`verifier/__init__.py`](../src/casf/verifier/__init__.py) and the output
construction in [`cli/__init__.py`](../src/casf/cli/__init__.py).

Verification starts from record 1. Retained checkpoints support continuity
checks, but the public API does not implement a general incremental verifier
starting from an arbitrary trusted suffix. A valid signature chain does not
prove that it is the latest history. `WITNESS_AHEAD` can be inconclusive when
intervening evidence is unavailable; a conflicting authenticated retained
checkpoint produces `WITNESS_STATE_CONFLICT`. The H1 research guide records
that distinction rather than treating both as the same observed outcome.

`open_bundle` and the CLI stream records. The verifier retains record digests
only at checkpoint boundaries, subject to bounded protocol evidence and input
budgets. `read_bundle`, writer export and restore remain eager and can use
memory proportional to record count. Streaming verification is not a claim
of constant memory for every operation.

## Operational limits and specification differences

| Area | Implemented behavior and consequence | Source or evidence |
| --- | --- | --- |
| Startup | `_check_heads` compares local counts and stored head hashes in one snapshot. It does not perform the full cryptographic and external evidence startup verification intended by SPEC section 17. Do not treat opening a database as verification after restore or suspected corruption. | [Writer](../src/casf/writer/__init__.py) |
| Restore | Records are verified and rebuilt. A supplied anchor count ahead of the restored history seals the store. The caller must authenticate that anchor; restore does not query the witness or rebuild the accepted checkpoint and receipt journal. | [Writer](../src/casf/writer/__init__.py), [restore tests](../tests/unit/test_bundle.py) |
| Scheduling and recovery | Checkpoint creation, submission and recovery are explicit calls. There is no automatic background checkpoint or retry worker. A checkpoint batch limit is not a hard bound on the pending backlog during an outage. | [Checkpoint code](../src/casf/writer/__init__.py), [H3 method](../research/h3-witness-outage.md) |
| SQLite | WAL, FULL synchronization and foreign key enforcement are configured. The current DDL does not declare foreign key relationships. Enabling the pragma is not evidence that the proposed relationships in SPEC section 17 exist. | [Storage](../src/casf/storage/__init__.py) |
| Export and status | Export excludes pending checkpoints and does not create authority status. Keep status provisioning and verifier trust separate from writer output. | [Writer](../src/casf/writer/__init__.py), [verification](verification.md) |
| Network | The client bounds total request time, response bytes, individual status and header lines, and header count. The reference service still needs operational TLS and access controls. | [Transport](../src/casf/transport.py), [server guide](witness-server.md) |
| Validation | Deterministic regressions and selected integration and crash scenarios exist. A maintained fuzzing job, exercised property generators and a complete process crash matrix are not established. | [Coverage status](release/test-coverage-status.md) |

These differences remain explicit implementation limits. This guide does not
amend the normative specification or mark full conformance achieved. Changes
to trust, recovery or authenticated formats require a separate design decision
and targeted implementation evidence.

## Evidence boundaries

Hosted CI runs on Ubuntu for Python 3.12, 3.13 and 3.14. macOS evidence comes
from manual local validation; there is no macOS CI job. Historical platform
inventories identify the exact systems tested and do not certify all systems
with the same operating system name.

Research results remain tied to their original manifests, environments and
source digests. Current code tests, historical measurements, limited external
review and an exact package artifact approval are separate evidence. Use the
[release checklist](release/checklist-v0.1.md) for their current disposition.
