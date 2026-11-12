# Bundle and incremental verification

`casf.verifier.verify_bundle` returns a `Report` after consuming a standard
bundle through EOF and closing its files. It uses public evidence and
independently provisioned `TrustPins`; it does not load writer, storage or HTTP
code. Default verification begins at genesis.

```python
from casf.errors import CasfError
from casf.verifier import Mode, Result, verify_bundle

try:
    report = verify_bundle("bundle", pins, Mode.ANCHORED)
except (CasfError, OSError):
    raise  # No complete report is available.
if report.result is Result.PASS:
    print(report.to_dict())
```

The reader checks EOF even when verification stops early for unknown trust,
invalid evidence or a work budget. Late malformed input, count mismatches,
resource limits and I/O errors raise instead of returning a partial verdict.
The [verification guide](verification.md) explains modes, authority status,
report fields and durable retained state.

## Explicit trusted starts

An incremental check requires a checkpoint, its witness receipt, and a
checkpoint hash retained or provisioned independently of the input being
verified. Never choose the expected hash automatically from an untrusted
bundle. Construction owns the evidence and checks encoding, schemas, digests
and checkpoint/receipt binding. The verifier then authenticates both signatures
with the accepted manifest and pinned witness before consuming suffix records.

```python
from casf.verifier import VerificationAnchor

anchor = VerificationAnchor(
    retained_checkpoint_envelope,
    retained_receipt_envelope,
    expected_checkpoint_hash=independently_retained_hash,
)
report = verify_bundle("bundle", pins, Mode.ANCHORED, anchor=anchor)
```

The bundle remains a full version 1 prefix from sequence 1. Earlier records
are parsed and counted, but their signatures, hashes and chain are not checked
again. Earlier checkpoint/receipt objects must have valid schemas, digests and
ordering; their signatures are not rechecked. Supplied objects at the starting
index must exactly match the explicit anchor. A shorter bundle cannot pass.
This invocation's PASS authenticates the suffix relative to the trusted head,
not the skipped record bodies. Omit `anchor` to check the complete history.

For an already available suffix stream, use the lower-level API:

```python
from casf.verifier import verify

report = verify(
    manifest_envelope, suffix_records, pins, Mode.ANCHORED,
    anchor=anchor,
    checkpoint_envelopes=checkpoint_extensions,
    receipt_envelopes=receipt_extensions,
    status_envelopes=status_statements,
)
```

The first record must be at `anchor.checkpoint.count + 1` and link to its
head. Checkpoint and receipt extensions start at the next checkpoint index
and link to the respective anchor digests. Supply only extensions, excluding
the anchor itself. Iterators are consumed once; read exceptions propagate.
Callers using this lower-level function still own complete input consumption.

## Scope and limits

`verified_from` and `verified_through` cover only successfully checked suffix
bodies, using absolute sequence numbers. They are both zero when no suffix
body was checked. Incremental reports add these assumptions:

| Field | Meaning |
| --- | --- |
| `anchor_checkpoint_hash` | Explicit trusted starting checkpoint. |
| `trusted_prefix_through` | Record count accepted through that start. |
| `prefix_signatures_checked` | Always false for an incremental invocation. |

The starting receipt still needs an independent witness pin in integrity
mode. Authority status, serial minima and terminal revocation apply in every
mode. A historical anchor does not establish freshness. Online mode uses
`online_query`, a caller-supplied callback returning a validated fresh view,
such as a configured call to `casf.online.query_latest`. The verifier does not
fetch missing intermediate evidence or configure a network client itself.

Anchored and online modes check every supplied receipt against its checkpoint
index, count, head and digest. They reject checkpoint or record extensions
after a final checkpoint. Integrity mode with an anchor also rejects records
after that final start; it does not authenticate later checkpoint evidence.
Unwitnessed suffixes require explicit `allow_unwitnessed=True` as before.

Retained state at or after the starting index must match the verified chain;
an older retained checkpoint needs additional history and returns
`RETAINED_CHECKPOINT_UNAVAILABLE`/INCONCLUSIVE. Integrity mode can compare
retained state only to the starting checkpoint. Conflicting or newer retained
state cannot be replaced by an older start. Use full anchored verification
when the needed continuity history precedes the chosen start.

`verify` limits suffix records with `max_records` and checkpoint/receipt
extensions with `max_chain_steps`; status statements have their own chain
budget. The trusted start does not consume an extension slot. `verify_bundle`
additionally bounds the entire input, including the skipped prefix, using
`max_records`, `max_line_bytes`, `max_evidence_objects` and `max_total_bytes`.
Defaults and sentinel behavior are documented in the
[resource limits](verification.md#work-and-input-limits). Record memory remains
bounded; evidence memory depends on the configured object limits.

Neither function persists retained state. The CLI continues to perform full
verification and independently retain authenticated status observations even
when a later read fails. A library caller needing that observation-on-error
behavior must use the lower-level verifier and its own durable state workflow.
The convenience API deliberately returns no report after a read exception.

[ADR-015](adr/ADR-015-incremental-verification.md) records the API decision.
The [incremental tests](../tests/unit/test_incremental_verification.py) and
[bundle tests](../tests/unit/test_verify_bundle.py) cover these contracts.
Historical performance measurements remain tied to their original revisions;
this interface makes no new incremental performance claim.

### Strict policy arguments

`allow_unwitnessed` accepts only actual Python `True` or `False`. Direct `verify`
and `verify_bundle` calls reject strings, integers and `None` with `ValueError`;
values are never coerced. The core rejects the argument before consuming record
iterators. `False` preserves `UNWITNESSED_SUFFIX`; `True` explicitly permits a
valid unwitnessed suffix and discloses the partial anchor. Successful reports
retain a Boolean in `assumptions["allow_unwitnessed"]`.
