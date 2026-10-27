# Reference witness HTTP server

The optional witness transport uses Uvicorn with h11 and asyncio. Core
verification and writer operations do not require the server dependency.
The transport preserves the existing witness state machine and signed bytes.
This change covers R05, R06, R10, and R12.

## Installation

For the locked development environment:

```bash
.venv-tools/bin/uv sync --locked --extra witness --extra dev --group build --python python3
```

For a wheel built from this source, install its `witness` extra. The package
metadata selects Uvicorn 0.54.0 and requires h11 0.16.0 or newer. The lockfile
records exact versions for new experiments. Importing CASF without this extra
remains supported; starting its server reports how to install the extra.

## Service lifecycle

Construct `WitnessService` with the database path, witness signing key,
bearer credential, and authority keys. Provision registered logs through the
existing witness API. Call `make_server(service, host, port)` and then
`serve_forever()`. Obtain credentials from a protected configuration source;
never place them in command line arguments or URLs.

For a background serving thread, call `shutdown()` from another thread,
join the serving thread, then call `server_close()` and `service.close()`.
For foreground service, use `server_close()` and `service.close()` in the
caller cleanup block after serving returns. Shutdown stops accepting work
and waits for active witness operations before closing the database. A lost
client connection does not cancel a witness commit. Retrying the identical
submission can recover its receipt.

## Resource controls

| Setting on WitnessService | Default | Behavior |
|---|---|---|
| max_request_bytes | 16 MiB | Reject a larger declared or received body with CASF JSON 413. |
| max_inflight | 64 | Bound admitted body readers and witness workers; reject extra CASF work with JSON 429. |
| request_timeout | 10 seconds | Total time to collect a body after complete request headers reach the application. |
| max_connections | 128 | Bound accepted sockets and Uvicorn tasks; an excess socket closes immediately, or a parsed request receives plain text 503. |
| header_timeout | 10 seconds | Close connections that do not complete request headers within the deadline. |

The body deadline returns JSON 400 and closes the connection. Authentication
is checked before reading a body. Early rejections close the connection so
unread data cannot become another request. POST requests require Content-Length;
chunked POST uploads without that header are rejected. The adapter also counts
received bytes and rejects duplicate authentication headers.

The h11 parser uses a 16 KiB incomplete event buffer limit. This is not a total
header size limit. A small Uvicorn protocol extension caps accepted sockets
and sets a total header deadline for the first and subsequent requests. It
uses the protocol class hook and must be revalidated when Uvicorn changes.
The server allows five seconds between requests on an idle persistent
connection. Operators must configure a reverse proxy with header size limits,
connection controls, and HTTPS before wider deployment. Proxy header trust and access logging are disabled
in this adapter. The application does not provide TLS itself.

These bounds do not guarantee availability under hostile traffic. Peers can
occupy the available connections until their deadlines expire. Shutdown waits for witness work already executing; Python cannot safely kill
a worker in the middle of a SQLite transaction. A stalled filesystem can
therefore delay shutdown. Process termination requires the existing recovery
and retry procedures and must not be described as a successful shutdown.

## Online client connections

Online verification uses HTTPS with certificate and hostname verification.
It uses the default Python trust store and never falls back to plain HTTP
or follows redirects. A failed TLS connection makes freshness inconclusive.
For local development, plain HTTP is accepted only with a literal loopback
address such as `127.0.0.1` or `[::1]`. Hostnames, including `localhost`,
require HTTPS. URLs must not contain credentials; supply the bearer token
through the existing protected configuration mechanism.

## Error contract

CASF application errors are JSON objects containing exactly `code`, `message`,
and `retryable`. Malformed HTTP and server connection limits can be rejected
before CASF runs, using minimal plain text 400 or 503 responses as approved
in ADR 004. Neither layer may expose secrets or request payloads. Internal
exceptions in CASF are converted to a generic retryable 503 response.

## Evidence and release status

New regression checks cover body deadlines, actual worker saturation,
disconnects, cancellation, malformed HTTP, connection limits, error sanitization,
and active shutdown. The wheel smoke check exercises installation both with
and without the optional server. Recorded research results retain their
original implementation and environment; this change does not replace them.
The [validation record](release/http-validation.md) lists the completed runs.
D05 remains open until the maintainer accepts implementation and validation
and completes the remaining release review.
