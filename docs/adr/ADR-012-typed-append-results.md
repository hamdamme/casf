# Immutable append requests and explicit results

SPEC §§11, 17 and 19 require copying caller input before locking and returning
an explicit committed record and witness state. The existing `Writer.append`
retains references to payload and attribute dictionaries after calculating the
request digest. Caller mutation can therefore produce a record whose stored
request digest disagrees with its content. This decision fixes that boundary
without changing authenticated formats, startup authorization or retries.

The typed entry point is `Writer.append_event(log_id, EventRequest) ->
AppendResult`. This is the method-based equivalent of the conceptual append
interface in SPEC §19. `EventRequest` validates the exact five event fields and
retains canonical immutable bytes. Its accessors return detached dictionaries.
`AppendResult` is immutable, contains the record, `committed=True`, and a
`WitnessState`. Accessing or serializing its record cannot mutate the result.
Neither value is independent cryptographic evidence of a commit or receipt.

Witness state is observed in the same transaction as append or idempotent
lookup. `WITNESSED` means an accepted local receipt covers the record;
`PENDING_WITNESS` means the durable pending checkpoint covers it;
`COMMITTED_LOCAL` means neither does. A pending checkpoint covering an older
prefix does not label newer records as pending submission. The observation
can become stale as a worker progresses. It does not claim fresh witness
state beyond the existing startup contract.

Both append interfaces share authorization, signing, idempotency and the same
transaction implementation. A result is returned only after commit. A timeout,
storage failure, conflict, trust failure or interrupted uncertain outcome
never returns a successful result. Retry the same event ID and identical
request to resolve uncertainty. Neither interface submits network requests.
Request and generated record-body byte budgets are checked before signing;
profile-limit errors use CLI usage
exit code 2. UUID validation rejects all trailing characters.

`Writer.append(...keyword fields...)` retains its existing envelope-dictionary
return value and now uses the same immutable request snapshot. CLI append uses
the typed operation and adds `committed` and `witness_state` to its existing
sequence/event output without exposing payloads or secrets.

Other public result types, report enum/verdict alignment and incremental
verification remain separate interface acceptance work. This decision does
not claim that all SPEC §19 conceptual functions have been implemented.

Affected requirements: R04, R09, R10. Regression coverage includes nested input
mutation, malformed requests, transaction outcomes, same-event retries,
pending/accepted coverage, verified authorization, concurrency and interruption.
Research outputs remain historical; performance reruns use new output paths.
