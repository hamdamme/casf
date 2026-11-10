# Prefix export and complete diagnostic serialization

SPEC §§19–20 require bounded prefix exports and atomic publication without
overwriting an existing destination. The previous check followed by ordinary
`rename` can replace an empty directory created between those operations.
This decision changes publication, not authenticated bytes or trust rules.

`Writer.export_bundle(log_id, destination, *, through=None)` retains its Path
return value. `through` selects the contiguous prefix from record 1 through a
nonnegative safe integer, no greater than the snapshot's head. Omitting it
selects the whole head. Accepted checkpoints and receipts are included only
when their counts fit that prefix. Pending checkpoints remain excluded, and a
pending final seal still blocks export. A prefix is historical evidence, not
a claim that the source or witness had no later records.

Export streams stored envelope BLOBs from one SQLite read transaction into a
private sibling directory, preserving their exact bytes. Files and the bundle
directory are flushed before publication. Linux uses `renameat2` with
`RENAME_NOREPLACE`; macOS uses `renamex_np` with `RENAME_EXCL`. Unsupported
platforms or filesystems fail closed rather than using a racy fallback. The
destination parent is flushed after publication. A late flush error can leave
a complete destination; no retry overwrites it. A hard process exit can leave
private staging files. Host filesystem and hardware assumptions still apply.

`Report.to_dict()` supplies the complete diagnostic representation shared by
Python callers and CLI verification. It includes all existing report fields,
checkpoint index/hash, requested policy and explicit trust assumptions. Lists
and objects in the returned representation are independent copies. Existing
CLI field names, enum values and exit categories remain compatible. Empty
verified ranges use 0 through 0. A nonzero verification result retains its
full report; a late malformed bundle still prevents report publication and
checkpoint advancement.

This is an incremental interface change. The typed append/result API,
normalization of report enum names and missing-trust verdicts against SPEC
§15, and the incremental verifier contract still require separate decisions
and regression coverage. This decision does not waive those acceptance gates
or mark interface conformance complete. Candidate schema version 1 and
cryptographic profile casf-v1 are unaffected.

Affected requirements: R03, R09, R10. Tests cover publication races and
failures, interrupted exports, snapshot consistency, prefix boundaries, exact
BLOB preservation and full success/failure/inconclusive diagnostics. Historical
research outputs remain tied to their original revisions.
