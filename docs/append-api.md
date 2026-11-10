# Typed append requests and results

Use `Writer.append_event(log_id, request)` with an `EventRequest` to receive an
immutable `AppendResult`. The writer must already have completed
[verified startup](writer-recovery.md); explicit local-only operation keeps its
existing, reduced assurance. The Python append operation never submits a
network request. A CLI command can still perform fresh startup checks before
it calls append.

```python
from casf.writer import EventRequest

request = EventRequest(
    event_id="123e4567-e89b-42d3-a456-426614174099",
    actor="example-service",
    event_type="document-read",
    payload={"document": "synthetic-example"},
    attributes={},
)
result = writer.append_event(log_id, request)
assert result.committed is True
record = result.record
state = result.witness_state
```

`EventRequest.from_dict(value)` accepts exactly the same five fields; there are
no parser-supplied defaults. UUIDs, field types, string sizes, Unicode, nesting
and numeric restrictions are checked before the append write transaction.
Requests retain canonical immutable bytes. Changing the original dictionaries,
`request.payload`, `request.attributes`, or `request.to_dict()` cannot alter
that snapshot. Request size is bounded by the record-body budget, and the
complete generated body must also fit 64 KiB before signing. A request near
the limit can fail after the generated metadata is added. UUID fields reject
trailing characters, including a trailing newline.

## What a successful result means

The record is committed before a result is returned. Its witness state is
observed inside that same append or idempotent-lookup transaction:

| `WitnessState` | Meaning for this record |
| --- | --- |
| `COMMITTED_LOCAL` | Neither accepted receipt nor durable pending checkpoint covers it. |
| `PENDING_WITNESS` | A durable pending checkpoint covers it; its receipt has not been stored. |
| `WITNESSED` | An accepted local receipt covers it. |

A checkpoint for an older prefix does not label later appends as pending
submission. The observation can become stale as a worker progresses. Retrying
the identical event returns the same record and timestamp with the then-current
witness observation. A previously returned result remains unchanged.

`result.record` and `result.to_dict()` return detached dictionaries. Mutating
those dictionaries cannot modify the result or the stored record. The result
contains no private key. It is a local API observation, not independently
signed proof of a commit, authority trust or fresh witness state. Verify public
evidence with independently provisioned trust when those assurances matter.

## Errors, retries and compatibility

Input, signing, trust, storage and conflict failures never return a successful
result. `SchemaError` and `LimitError` identify input/profile failures;
`EventIdConflictError` identifies an event ID reused with different content;
`BusyError` identifies exhausted lock retries. Existing seal and verified
startup errors are unchanged. SQLite and filesystem failures remain visible.

An exception or process interruption after commit can leave the outcome
uncertain to the caller. Retry the **same event ID and identical request**.
Do not infer rollback from an error or allocate a new event ID automatically.
Conflicts and retries do not consume a sequence.

`Writer.append(log_id, **fields)` remains available and returns its existing
record dictionary. It now uses the same immutable request snapshot and shared
transaction code. No authenticated format, request digest domain, checkpoint
policy or startup authorization rule changes.

CLI append retains `seq`, `event_id` and its existing `startup_verified` flag,
and adds `committed` and `witness_state`. It does not print payloads or
attributes. Input/profile limits return usage exit code 2; no failure prints a
committed result. The startup flag remains separate from journal coverage.

[ADR-012](adr/ADR-012-typed-append-results.md) records this method-based API
decision. Other result types, report enum/verdict alignment and incremental
verification remain open interface work. These examples do not claim the
whole experimental release is complete.
