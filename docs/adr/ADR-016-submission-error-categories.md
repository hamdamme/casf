# Submission errors and transport configuration

CASF-02 exposed a CLI catch that labeled permanent rejection and invalid receipts
as temporary unavailability. This decision refines application error categories
under SPEC §19; it does not change signed bytes, trust predicates, failure
precedence, receipt acceptance, or the protocol.

| Submission outcome | Python exception | CLI exit |
| --- | --- | --- |
| HTTP 200/201 with valid receipt committed | None | 0 |
| HTTP 400 | SchemaError | 2 |
| HTTP 401/403 | TrustError | 3 |
| HTTP 409 | EvidenceError | 1 |
| HTTP 429/503 | InconclusiveError | 4 |
| Timeout, unreachable peer, interrupted/bounded transport response | InconclusiveError | 4 |
| Other HTTP status, including 500/502/504 and redirects | CasfError | 5 |
| Malformed successful JSON or receipt schema/digest/encoding | SchemaError | 2 |
| Invalid receipt signature or binding/chain conflict | EvidenceError | 1 |
| Independent trust failure | TrustError | 3 |
| Invalid request configuration | SchemaError | 2 |
| Local persistence failure | Existing local error | 5 |

401/403 use the trust category because the peer refused authentication or
authorization. This is not evidence of record tampering. A 409 indicates a
conflict, not necessarily proof of rollback. Unexpected 5xx statuses require
operator diagnosis; only the explicitly documented 429/503 signal temporary
server unavailability. No status is inferred from untrusted response text.
Schema and trust exceptions retain their specific classes through the CLI.

Failure retains the identical pending checkpoint and range. Retry or receipt
recovery may resolve an uncertain submission without inventing a new checkpoint.
Diagnostics contain fixed messages/status numbers, never peer payloads or tokens.
The existing transaction and retained-state protections still apply.

CASF-H01: base URLs allow HTTP(S) origins and an optional lone `/`; reject other
paths, query delimiters and fragments (even empty ones) before connection.
Prefix routing is unsupported. HTTPS certificate authentication, loopback-only
plain HTTP and redirect refusal are unchanged.

CASF-H02: transport timeouts must be non-Boolean int/float values, finite and
positive. Invalid configuration raises ValueError at transport and SchemaError
at submission/receipt-recovery boundaries. The online wrapper retains CasfError
for wrong types/nonfinite values and InconclusiveError for exhausted numeric
budgets. Reconciliation retains its SchemaError validation. Total monotonic
network deadlines and socket cleanup are unchanged.

## Bearer configuration exception redaction

The shared transport rejects non-string bearer credentials, ASCII control
characters (including CR/LF and DEL), and characters outside the HTTP header's
Latin-1 encoding before connecting. It does not trim or otherwise change a
credential. A defensive boundary also replaces header-construction ValueError
exceptions with a fixed message.

Submission and receipt recovery retain SchemaError for invalid configuration;
direct transport and online fetch retain ValueError for this transport error.
Sanitized exceptions are raised after leaving the unsafe handler, with
`from None`, so neither an explicit cause nor implicit context retains that
exception. Using `from None` inside the handler alone would only hide the
context when rendered. Network/TLS failure categories and socket cleanup remain
unchanged. Pending canonical bytes survive and a corrected credential can retry.
The regression checks ordinary complete traceback rendering and exception-chain
attributes; applications must also avoid logging credentials or capturing locals.
