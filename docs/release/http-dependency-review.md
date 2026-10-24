# HTTP dependency review

Review date: 2026-10-24. Scope: packages added for the optional witness service.
This inventory supports R10 and R12. It does not replace review of the complete
release dependency set or a security audit.

| Package | Locked version | Declared license | Declared Python minimum |
|---|---|---|---|
| Uvicorn | 0.54.0 | BSD 3 Clause | 3.10 |
| Click | 8.5.0 | BSD 3 Clause | 3.10 |
| h11 | 0.16.0 | MIT | 3.8 |

Sources: version metadata from [Uvicorn](https://pypi.org/pypi/uvicorn/0.54.0/json),
[Click](https://pypi.org/pypi/click/8.5.0/json), and
[h11](https://pypi.org/pypi/h11/0.16.0/json). These packages are separate
distributions; their copyright notices and license conditions remain applicable.
The server uses no Uvicorn standard extras, optional event loop, or WebSocket
implementation. The application explicitly selects asyncio, ASGI 3, and h11.

Exact version queries to the OSV API and the PyPI vulnerability fields returned
no advisories for these three versions on the review date. This records the
query outcome, not a guarantee that no vulnerability exists. Repeat the review
before release and when updating dependencies.

The witness extra explicitly requires h11 0.16.0 or newer so an existing older
installation cannot satisfy the HTTP parser requirement. Version 0.16.0 fixes
an HTTP framing issue described in the
[upstream advisory](https://github.com/python-hyper/h11/security/advisories/GHSA-vqfr-h8mv-ghfj).
The lockfile selects 0.16.0 for reproducible validation.

Remaining review includes the full runtime and development dependency set,
platform SQLite and TLS components, final redistribution notices, and maintainer
acceptance of the implementation. Historical experiment environments remain
as recorded and are not upgraded by this review.
