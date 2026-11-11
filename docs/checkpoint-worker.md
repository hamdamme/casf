# Checkpoint scheduling and retries

The checkpoint worker runs in the foreground on a verified writer. Run one
process per store under the process supervisor used for the application. It
does not create an implicit thread during append. Stop it with Ctrl-C, or use
the library stop event. Reopen with verified startup after a crash or trust
configuration change.

```sh
casf witness work --db writer.db --key log.pem \
  --trust trust.json --status-file active-status.json \
  --state /protected/casf/state.json --json
```

The passphrase and witness token use the same named environment variables as
other writer commands. The witness URL comes from independent trust
configuration. Supply `--initialize-state` only for an explicitly unobserved
manifest; never delete retained state to make startup pass. This command has
no local-only override. Startup must establish fresh witness continuity before
the worker can run, including after an offline restart.

## Scheduling

- Create a checkpoint at 128 unwitnessed records or after 60 seconds, whichever
  occurs first while polling. An idle interval produces a heartbeat.
- Drain a triggered backlog in consecutive batches of at most 128 records.
- Preserve the sole pending checkpoint and its bytes until its receipt is
  validated and saved. Retry an existing final checkpoint; stop after its
  receipt is accepted.
- Retry transport failures and HTTP 429/503 with delays of 1, 2, 4, 8 seconds,
  up to 60 seconds. Invalid evidence, other HTTP errors, trust failures and
  local persistence failures stop the process for investigation.

`--interval`, `--retry-initial`, `--retry-max` and `--poll-interval` configure
these durations in seconds, from 0.001 through 86400. Initial retry delay must
not exceed the maximum. Polling defaults to one second; these are operating
targets, not guarantees of maximum unwitnessed exposure.

Deadlines and pending attempt counts survive restart in SQLite. A timer absent
from an older store, or a receipt accepted outside the worker, triggers an
immediate checkpoint to establish a local schedule. Remote timestamps are not
used as scheduling authority. The `checkpoint_schedule` table is part of schema
version 1. Unversioned stores require explicit copy [migration](storage-migrations.md);
opening a versioned store does not repair a missing table. This metadata is not part of
an evidence bundle or an authenticated trust anchor.

Local Unix time makes deadlines portable across restarts. A backward clock
change clamps a future wait to the configured interval or retry maximum; a
forward change may trigger work earlier. Keep the host clock maintained.

## Reports and one-shot use

Add `--once` to perform one scheduling tick and at most one submission. Exit 4
means work remains pending or retry is delayed; exit 0 means the tick has no
outstanding backlog. Permanent failures use the existing CLI error exits.
Continuous mode prints changed reports and stops on accepted final seals.
The JSON stream contains one object per line:

| Field | Meaning |
|---|---|
| `state` | `idle`, `waiting`, `retry`, `witnessed` or `sealed` |
| `committed` | Locally committed record count |
| `witnessed` | Prefix covered by a validated, locally saved receipt |
| `backlog` | Committed minus witnessed records |
| `pending_checkpoint_hash` | Exact checkpoint awaiting acceptance, or null |
| `attempts` | Attempts for the current pending checkpoint; zero when none remains |
| `next_action_at_ms` | Local scheduling deadline as Unix milliseconds, or null after sealing |
| `startup_verified` | True for this CLI command |

A retry report does not undo a local append or establish witness acceptance.
The witness may already have accepted a request whose reply was lost. The next
attempt reuses the exact checkpoint; startup can also recover its stored
receipt. A failed external-state save stops the worker and holds the writer
until verified reopening succeeds.

## Python integration

```python
from threading import Event
from casf.writer.worker import CheckpointWorker

# writer was opened with Writer.open_verified and remains owned by this thread.
worker = CheckpointWorker(writer, log_id)
report = worker.tick()  # at most one submission
stop = Event()         # another thread may call stop.set()
worker.run(stop, on_result=lambda result: print(result.as_json()))
```

Use separate writer connections for separate executing threads. Verified
workers share the retained-state and recovery locks, preventing competing
checkpoint creation. SQLite transactions finish before network requests.
Local-only writers bypass verified authorization and must not be mixed into
the deployed worker workflow. Supplied status is still subject to the
administrative distribution assumptions in the [recovery guide](writer-recovery.md).

See [ADR-009](adr/ADR-009-checkpoint-worker.md),
[worker tests](../tests/unit/test_checkpoint_worker.py),
[CLI tests](../tests/unit/test_cli_checkpoint_worker.py), and
[HTTP retry tests](../tests/unit/test_submission_retry.py).
