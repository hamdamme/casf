# Prefix exports and verification reports

`Writer.export_bundle` exports one log and returns the destination `Path`.
The optional `through` argument selects a contiguous prefix beginning at
record 1. Omitting it exports the snapshot's entire committed head. Zero
exports an empty history; negative values, booleans, fractions and values
beyond the snapshot head are rejected.

```python
bundle_path = writer.export_bundle(log_id, "evidence-prefix", through=128)
```

The CLI exposes the same range selection:

```bash
casf export --db writer.db --out evidence-prefix --through 128 --json
```

The destination must not already exist. Export needs no private key.
`through` and `record_count` in `export.json` both equal the selected count.
A prefix deliberately omits later records and cannot establish currentness.
Use independently retained anchors or online verification to assess it.

## Evidence and publication

Records, manifest and accepted checkpoint/receipt envelopes retain their exact
stored bytes, with LF delimiters. Only checkpoints within the selected prefix
and their receipts are included. A prefix ending before the first accepted
checkpoint has no anchor evidence. Every included accepted checkpoint must
have its receipt. Pending nonfinal checkpoints are excluded; a pending final
seal blocks every export, including a shorter prefix. Use a database backup
to preserve pending operational state. Supply authentic authority status
separately as `status.jsonl`; export cannot create it.

Export holds one SQLite read snapshot while streaming files. It does not build
a Python list of the record history. Concurrent appends can continue, but the
WAL may grow until the export releases its snapshot. `read_bundle` and restore
remain eager operations. The allocation regression measures Python allocations,
not an upper bound on SQLite caches or total process memory.

Files are created privately in a sibling staging directory. Files and the
bundle directory are flushed before an exclusive rename; the parent directory
is flushed afterward. Publication refuses files, empty or populated
directories, and dangling symlinks, including paths created during export.
Linux uses [RENAME_NOREPLACE](https://man7.org/linux/man-pages/man2/rename.2.html);
macOS uses [RENAME_EXCL](https://developer.apple.com/documentation/foundation/urlresourcekey/volumesupportsexclusiverenamingkey).
Unsupported rename capabilities fail without an ordinary-rename fallback.
These operations rely on the host filesystem and hardware durability model.

An error before publication leaves no destination. A parent-directory flush
error after publication may leave a complete bundle: inspect it before
retrying to a new path. A killed process can leave a private `.casf-export-*`
directory; remove it only after confirming no export is using it. Unrelated
old temporary directories are never reused or deleted.

## Complete machine diagnostics

`Report.to_dict()` and `casf verify --json` share diagnostic JSON version 1.
This serialization version is separate from the `casf-v1` cryptographic profile
and the SQLite schema version. Existing CLI fields remain present; additional
fields expose the full report and policy. Each call returns independent lists
and objects, so changing the returned dictionary does not change the report.

| Fields | Meaning |
| --- | --- |
| `report_version`, `mode`, `result` | Diagnostic format version, requested verification mode, and overall verdict. |
| `protocol_status`, `signature_status`, `chain_status` | Separate dimensions using the existing `OK`, `FAIL`, `NOT_CHECKED` enum. |
| `trust_status`, `anchor_status`, `freshness_status` | Existing trust, anchor and freshness enums; see the [verification guide](verification.md). |
| `verified_from`, `verified_through` | Successfully examined record range. An empty range is 0 through 0. |
| `witnessed_through`, `unwitnessed_count` | Established witness coverage and the unanchored suffix. |
| `checkpoint_index`, `checkpoint_hash` | Established checkpoint identity, or null. A non-PASS report never authorizes advancing retained checkpoint state. |
| `first_failure_seq`, `diagnostic_codes` | Exact first failed record when applicable and stable diagnostic identifiers. |
| `observed_status_serial` | Authenticated authority status serial observed, independently of the overall verdict. |
| `assumptions` | Caller-provisioned authority trust, supplied-status currentness limit, witness honesty requirement, unwitnessed-tail policy, retained-state inputs and configured work limits. |

A FAIL or INCONCLUSIVE verification still emits this report with its existing
nonzero exit category. Usage, malformed-bundle and local I/O failures remain
errors rather than partial verification reports. The CLI consumes records to
EOF before publishing a report or advancing an accepted checkpoint. It retains
authenticated status/revocation observations independently, as documented in
the [state guide](verification.md#remembered-verifier-state).

The current enum labels and missing-trust verdicts still differ from the
normative SPEC §15 contract. Aligning those semantics, immutable typed public
requests/results and incremental verification remain open interface work.
A breaking diagnostic-format change requires a new serialization version;
this batch does not claim full interface conformance.

See [ADR-011](adr/ADR-011-export-and-report-interfaces.md),
[export regressions](../tests/unit/test_export_contract.py), and
[report regressions](../tests/unit/test_report_contract.py).
