# Typed log operations

`casf.api.open_log(writer, log_id)` binds one stored log to an existing Writer.
Complete [verified startup](writer-recovery.md) before using a signing writer.
The handle does not authorize the log, open a connection, contact a witness,
or take ownership of the writer's lifetime. Close the writer when finished.
Existing explicit local-only writers retain their reduced assurance.

```python
from casf.api import EventRequest, open_log

# writer has already completed the configured verified startup workflow.
log = open_log(writer, log_id)
request = EventRequest(
    event_id="123e4567-e89b-42d3-a456-426614174099",
    actor="example-service",
    event_type="document-read",
    payload={"document": "synthetic-example"},
    attributes={},
)
appended = log.append(request)
checkpoint = log.pending_checkpoint()
if checkpoint is None:
    checkpoint = log.create_checkpoint()
witnessed = log.submit_pending(witness_url, token)
exported = log.export_bundle("evidence")
```

The handle is frozen and owns its manifest snapshot. Each operation checks
that the stored manifest still matches, then delegates to the existing writer.
Mutating operations retain startup, retained-status and private-key checks.
An already-open handle cannot bypass a later observed revocation or newer
required status. Read-only writers can bind a handle and export public evidence;
they cannot sign. Use one connection per executing thread as with Writer.

## Results and commit boundaries

| Operation | Result and boundary |
| --- | --- |
| `log.append(EventRequest)` | Immutable `AppendResult` after local commit; see the [append guide](append-api.md). |
| `log.create_checkpoint(final=False)` | Immutable `Checkpoint` after the pending checkpoint and outbox commit. Existing pending work must be submitted first. |
| `log.pending_checkpoint()` | Immutable `Checkpoint` or None; read-only observation of the durable pending bytes. |
| `log.submit_pending(url, token, timeout=10.0)` | Immutable `WitnessResult` after receipt validation and local commit. `stored=True`, `witness_state=WITNESSED`, `count` and `checkpoint_hash` describe that receipt. |
| `log.export_bundle(destination, through=None)` | Immutable `ExportResult` after publication and synchronization. `metadata` is the exact snapshot metadata written to `export.json`; `destination`, `published=True` and `through` describe that export. |
| `log.seal_log()` | Immutable final `Checkpoint`; pending receipt acquisition remains a separate operation. |

A Checkpoint exposes `body`, `checkpoint_hash`, `index`, `count`, `final`,
`log_id` and `to_dict()`. A WitnessResult exposes a detached `receipt` and
serializes the receipt plus its observation fields with `to_dict()`.
ExportResult likewise returns detached `metadata` and JSON serialization.
Changes to caller dictionaries or returned nested values cannot alter the
owned result. A previously returned observation does not update as work proceeds.

Only `submit_pending` contacts the witness. Network unavailability, a rejection,
a signature failure or local commit error raises the existing exception; none
returns a successful WitnessResult. If the witness accepted a checkpoint but
the local receipt commit failed, retry the same pending checkpoint. Its bytes
remain unchanged. A final checkpoint stops new appends even before its receipt
arrives. `final` must be a boolean; truthy strings or integers are rejected.

Exports retain the existing [snapshot and publication rules](export-and-reports.md).
They never replace a destination. A synchronization failure after publication
can leave a complete directory without returning success; inspect it and use a
new destination on retry. ExportResult does not reread the database afterward,
so a concurrent append cannot inflate its published count.

These values are local API observations, not independent proof of durable
storage, authority trust or fresh witness state. Model construction checks
schema, digest consistency and signature encoding. It does not authenticate
a signature. Writer operations still validate signatures and trust as required.

## Creation and compatibility

`Manifest(envelope)` takes an owned immutable snapshot of a signed manifest.
The lower-level `create_log(manifest, writer)` helper delegates to the explicit
writer's existing creation policy and returns a LogHandle after commit. It
does not replace `Writer.initialize_verified`, provision trust or establish
fresh startup authorization. For the verified initialization workflow, create
the writer with `initialize_verified`, then select it with `open_log`.

All existing Writer APIs retain their return values: `create_log` returns the
manifest hash; checkpoint/seal/submit return envelope dictionaries; export
returns a Path. `Writer.export_bundle_result` is also available directly and
uses the same export implementation. Manifest creation and receipt recording
now snapshot dictionary inputs before validation and storage. Fixed digest and
base64url fields reject trailing characters, including a trailing newline.

[ADR-014](adr/ADR-014-typed-log-operations.md) records these method-based
contracts. The [verifier API guide](verifier-api.md) covers complete bundle
reads and incremental verification from explicit trusted checkpoints. This API
change does not complete the experimental
release or alter authenticated formats, storage schema or historical results.

Submission errors follow [ADR-016](adr/ADR-016-submission-error-categories.md).
`EvidenceError` identifies invalid receipt signatures/bindings or an HTTP 409
conflict; `SchemaError`, `TrustError` and `InconclusiveError` remain distinct.
These inherit `CasfError`, preserving broad exception handling. `submit_pending`
and the typed handle reject invalid timeout configuration with `SchemaError`.
Only finite, positive, non-Boolean int/float timeouts are accepted. Base URLs
must be origins with at most a lone trailing slash. These checks do not change
receipt authentication or pending-checkpoint identity.
