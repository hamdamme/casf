# Checkpoint worker and retry scheduling

This decision records its implementation-time context. Statements about separate
work refer to that stage; use the [current reference](../current-reference.md)
and [completion tracker](../release/completion-tracker.md) for present behavior
and acceptance status.

The foreground `CheckpointWorker` operates on an already verified signing
`Writer`. `tick()` performs at most one submission; `run(stop)` polls until
stopped or the final checkpoint is accepted. `casf witness work` exposes the
same behavior, with `--once` for one tick. It requires verified startup and has
no local-only mode. Append does not start a thread or submit network requests.

The default triggers are 128 unwitnessed records or 60 seconds after the worker
last accepted a checkpoint. An idle interval produces a heartbeat. Once a
backlog starts draining, remaining records are scheduled immediately in batches
of at most 128. A final pending checkpoint is retried; a final accepted log
stops the worker. A missing timer or a checkpoint accepted outside this worker
is conservatively due immediately, rather than trusting a remote timestamp.

An additive `checkpoint_schedule` table stores the accepted checkpoint hash and
the next local deadline. Existing `outbox.attempts` and `next_attempt_at` store
submission attempts and retry deadlines. Scheduling metadata is operational,
not authenticated evidence; it never authorizes a record or changes signed
formats. Unversioned stores originally acquired the table through normal initialization.
[ADR-010](ADR-010-storage-migrations.md) supersedes that behavior with explicit
copy migration and versioned schemas.

Transport failures and HTTP 429/503 are retryable. Retry delays double from one
second to a maximum of 60 seconds by default. The deadline is committed before
network submission; an interrupted attempt retains the same pending bytes and
schedule. Every submission increments its durable attempt count. Invalid
evidence, trust failures, other HTTP errors and local storage failures stop the
worker instead of entering an automatic retry loop. No receipt is accepted
without the existing signature, chain and external-state persistence checks.

Worker ticks take the retained-state lock before the existing recovery lock,
matching verified startup's lock order. This serializes verified workers and
reconciliation. No SQLite transaction spans a witness request. Each tick checks
the current hold and retained authority status before acting. Separate
connections are required for separate executing threads.

Deadlines use local Unix time to survive restarts; in-process elapsed waiting
uses the stop event's wait operation. Clock changes affect operating timing,
not trust. Future deadlines are clamped to the configured interval or retry
maximum so a backward clock adjustment cannot impose a larger wait. Durations
must be between one millisecond and one day. These are scheduling targets,
not a maximum unwitnessed exposure guarantee. Fresh startup still requires a
reachable witness; an offline restart cannot bypass it to run the worker.
