# Explicit writer reconciliation

Date: 2026-11-10. Scope: SPEC Sections 14, 17, 18 and 19.

## API and trust boundary

Add `Writer.reconcile_witness(log_id, base_url, token, *, timeout=10.0,
max_chain_steps=10000, retained_checkpoint=None)`, returning `LatestView`.
Independent manifest, authority and witness pins are mandatory. The method
generates its own fresh nonce, authenticates the response and checkpoint,
retrieves missing accepted checkpoint/receipt pairs, and verifies them against
the local records before committing the recovered journal. It needs no signing
key. Optional independently retained `(index, hash)` evidence must occur in
the verified chain; a lower or conflicting witness view fails.

This operation establishes witness freshness, not authority status currency.
The caller must evaluate signed authority status and retain its serial and
checkpoint high-water state independently. Default startup policy, persistent
status enforcement and automatic recovery scheduling remain separate work.
No signed formats, cryptographic domains or historical fixtures change.

## Durable hold and serialization

Reserve local `heads.sealed=3` for reconciliation required and commit the hold
before network access. [ADR-008](ADR-008-verified-writer-startup.md) corrects the
initial implementation's network transaction: a bounded advisory recovery lock
serializes recovery while network requests run outside SQLite transactions.
Full local history and any concurrent receipt changes are rechecked in the
final write transaction. The hold blocks appends/checkpoints; WAL readers and
unrelated logs can continue. Network requests share one monotonic deadline and
chain traversal has a separate step limit. Local verification and lock
acquisition have their own costs; the network deadline does not bound the
entire operation.

Failure or interruption leaves the committed hold in place and preserves the
previous journal and pending bytes. Restart accepts the hold for inspection,
but append and checkpoint creation raise `ReconciliationRequiredError`. A
successful retry clears the hold atomically with the recovered journal and
restores any final seal. Older implementations reject this unknown seal value
at startup, so they cannot silently resume it.

A fresh authenticated checkpoint beyond the local record count marks the store
`sealed=1` and raises `RESTORE_BEHIND_WITNESS`; no recovered journal is committed.
This terminal state cannot be cleared by reconciliation, including a later
lower witness response. Recover missing records into a new verified store or
establish a documented discontinuous epoch. Other failures retain state 3.

Only exact matching pending checkpoints can acquire recovered receipts. An
unaccepted pending tail after the latest accepted checkpoint retains its bytes,
outbox range and final seal. Duplicate append requests can still return their
already committed result; no new record is written during a hold.

## Acceptance evidence

Regression tests cover response bindings, missing chains, pending and final
checkpoints, record loss, rollback, retained-state conflicts, replay, unavailable
evidence, bounded work, atomic failure and restart. These checks support R02,
R05, R06, R08 and R09; they do not establish full startup conformance.
