# Streaming verification API decision

Date: 2026-10-27. Scope: SPEC Sections 5, 15, 19, and 20.

## Compatibility

Keep `read_bundle` and `Bundle.records` as the existing eager list API.
Callers can still index, iterate repeatedly, and use `len`. Restore continues
using this compatibility API. It intentionally uses memory proportional to
record count and is not the streaming verification entry point.

Add `open_bundle` as a context manager returning `StreamingBundle`. Its
`records` generator reads from an owned regular file descriptor once and
closes at context exit, including early failure. Manifest, export metadata,
checkpoints, receipts, and status statements retain their bounded representation.
No signed formats or protocol interpretation change.

The CLI and installed public verification check use `open_bundle`. Record
schema, line, count, and byte errors can now occur during consumption.
`BundleReadError` is a `CasfError`; resource violations retain `LimitError`.
Callers must exhaust records before accepting a report. The CLI drains any
remaining records after an early verdict, then saves state only after a
successful report and validated EOF. Malformed input returns exit 2; local
read errors return exit 5. Neither path prints PASS or advances saved state.

`verify` still accepts any record iterable and returns the same report type.
It consumes records once and retains only the current chain head, count,
and checkpoint boundary digests. For anchored and online modes it consumes
up to `max_chain_steps + 1` checkpoints before records, using the extra item
only as a budget sentinel. Checkpoint iterators must be independent of record
consumption. Exceptions from caller iterators propagate. For valid iterables,
record failures retain priority over checkpoint validation failures. Integrity
mode does not consume checkpoints.

## Memory bounds and limits

For record count N, maximum decoded record footprint R, bounded decoded
protocol evidence E, and configured checkpoint traversal limit C, the streaming
path uses O(R + E + C) retained memory, not O(N * R) or O(N) record digests.
Only counts requested by the first C checkpoint envelopes are retained, with
at most C digests. Invalid checkpoint counts are never used to allocate a
record sized array; all checkpoint schemas, signatures, linkage, count rules,
and head comparisons still run before acceptance.

E is bounded by per file evidence counts, protocol envelope size, and total
bundle bytes. Status, checkpoint, and receipt verification have traversal
budgets. Actual memory can rise as more protocol evidence is supplied within
these fixed budgets; raising budgets raises the memory ceiling. A log with
one checkpoint per record can therefore increase protocol memory up to the
configured ceiling. This is a bounded protocol state design, not a claim of
identical memory for arbitrary evidence counts or unlimited histories.

The reader uses bounded reads before parsing and preserves symlink and
nonregular file rejection. Total input accounting includes every required
member and optional status statements. Metadata record counts are checked
against observed EOF, not trusted as authenticated claims. Concurrent editing
of a bundle is unsupported; opened record descriptors avoid path replacement
redirecting an ongoing read, but do not provide a filesystem snapshot.

## Evidence

See the [streaming validation record](../release/streaming-validation.md) for
measurements and checks. Historical experiments and authenticated fixtures
remain unchanged. This decision does not close unrelated release gates.
