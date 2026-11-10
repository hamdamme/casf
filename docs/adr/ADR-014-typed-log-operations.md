# Typed log operations and immutable results

SPEC §19 calls for a LogHandle and typed checkpoint, witness and export
results. The Writer API currently returns dictionaries, a manifest digest,
and a Path. ADR-012 added typed append without breaking those callers.
This decision completes the writer-side typed operation surface with a
bound handle, while preserving the existing entry points.

`casf.api.create_log(manifest: Manifest, writer: Writer) -> LogHandle` uses an
explicitly configured Writer as the signer/storage adapter. `open_log(writer,
log_id)` binds an existing log. The frozen handle owns an immutable manifest
snapshot and delegates append, create_checkpoint, submit_pending, export_bundle
and seal_log to that writer. Handles do not own the writer's lifetime, establish
startup authorization or bypass trust checks. Operations check the bound log
identity; callers close the writer. No implicit network operation is added.

`Manifest` and `Checkpoint` retain canonical immutable envelope bytes, validate
fixed schemas, digest consistency and signature encoding, and return detached
objects. Construction alone does not authenticate signatures or confer trust.
`WitnessResult` owns the receipt returned after verification and local receipt
commit. It reports WITNESSED and stored=true. A timeout, rejection or local
commit error remains an exception with pending evidence available for retry;
there is no successful result for a failed submission.

`ExportResult` contains destination, published=true and the exact export
metadata from the export's read snapshot. It is prepared before publication
and returned only after file/directory synchronization succeeds. Later appends
cannot change its count. The compatibility export method returns its existing
Path from the same implementation. A late publication error can still leave
a complete destination; existing no-overwrite and recovery rules apply.

Legacy manifest creation and receipt recording also snapshot caller dictionaries
before validation/use. Caller mutation must not separate validated evidence
from the bytes committed to SQLite. Checkpoint final flags reject non-booleans
before a transaction instead of interpreting truthy values as a final seal.
Fixed digest and base64url fields reject trailing characters.
Authenticated formats, digest domains, receipt checks and startup authorization
are unchanged. Existing raw dictionary/Path return values remain available.

This covers method-based equivalents of the writer operations in SPEC §19.
The streaming verify-bundle convenience interface and incremental verification
remain separate acceptance work. These types describe local API observations,
not independent evidence of durability, fresh witness state or release readiness.

Affected requirements: R04, R07, R09, R10. Regressions cover immutable ownership,
strict inputs, transaction failures, retry identity, snapshot metadata, final
seals and retained-state authorization. Historical research outputs are preserved.
