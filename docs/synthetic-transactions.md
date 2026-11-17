# Synthetic transaction entry

The source-checkout example `python -m examples.transactions` submits synthetic
transaction events through the existing verified CASF CLI. It does not implement
an accounting system, authenticate business events, or establish their completeness.
It is not installed as a new `casf` command and does not change the protocol.

## Setup

Use a fresh synthetic log with encrypted test keys, independently provisioned
public trust, signed active status and external retained writer state. Follow
[verified initialization](writer-recovery.md) and the [two-host rehearsal](release/two-host-rehearsal.md)
for provisioning. Do not reuse the revoked log left by the earlier rehearsal.
The writer can run on the Mac with the witness on Linux; the trust file selects
the witness URL. Existing HTTPS/private-CA or loopback-over-SSH configuration
must authenticate the endpoint. Never expose the plain HTTP backend on the LAN.

The example requires an initialized writer and existing retained state. It offers
neither `--local-only` nor `--initialize-state`. Supply credentials through the
existing `CASF_PASSPHRASE` and `CASF_WITNESS_TOKEN` environment mechanism, not
command-line values, committed files or shell-history commands containing secrets.
See [administration](administration.md) for credential handling.

## Enter an event

From the source checkout, replace these paths with the synthetic fixture paths:

```sh
PYTHONPATH=src .venv/bin/python -m examples.transactions \
  --synthetic --db /PRIVATE/writer.db --key /PRIVATE/log.pem \
  --trust /PRIVATE/trust.json --status-file /PRIVATE/status.json \
  --state /PRIVATE/retained.json \
  --transaction-id 123e4567-e89b-42d3-a456-426614174099 \
  --event-id 123e4567-e89b-42d3-a456-426614174001 \
  --event created --amount-minor 1250 --currency USD --json
```

Amounts are nonnegative integers in the currency's minor units, never floating
point. `1250` means USD 12.50; do not assume all currencies use two decimal places.
Currency syntax is three uppercase ASCII letters; the example does not validate
an ISO currency registry or perform conversion. IDs must be canonical UUIDs.
The event payload always includes `synthetic: true` and a fixed synthetic actor.

Repeat the identical command after an uncertain result. Reuse the event ID and
all event fields: the existing writer makes that append idempotent. Changing the
amount or other event fields under the same event ID is rejected. A repeat may
create an additional checkpoint but does not duplicate the transaction record.

For a refund or correction, use a new event ID, `--event refunded` or
`--event corrected`, and `--related-event-id ORIGINAL_EVENT_UUID`. This appends a
new signed event; it never edits earlier history. A reference must differ from
its own event ID. The example does not enforce existence of that referenced event,
accounting balances, refund limits, transaction ownership or business-state transitions.
A correction's amount is an explicitly recorded value, not an automatic balance update.

## Commit and recovery boundaries

The command performs verified append, creates or reuses a pending checkpoint,
and invokes one witness-worker submission attempt. JSON mode emits the existing
CLI result for each completed stage as a separate line. A local append message
is not confirmation of witness acceptance. Inspect the final exit code and worker
backlog; a retryable result can mean the event is committed locally but unwitnessed.
An older pending checkpoint may be submitted first, leaving newer events for a
later identical retry. Existing retry deadlines and pending bytes are preserved.

The adapter returns the first failing stage's exit category and does not continue
after that failure. It never rolls back a committed event because witnessing fails.
Existing trust, revocation, resource and network controls remain in the core CLI.
Signing proves the supplied event's integrity, not that a business transaction
occurred or that the application supplied every event.

This example supports synthetic integration acceptance only. Production source
selection, access control, durable source-to-CASF delivery, monitoring, operating
keys and backup automation remain separate decisions.
