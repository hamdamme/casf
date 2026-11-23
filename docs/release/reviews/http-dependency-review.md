# HTTP dependency review

Original review date: 2026-10-24. Scope: packages added for the optional witness service.
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

## Distribution license scope

The source archive and wheel package CASF code and do not vendor third party
Python implementations. The project declares `cryptography` as a runtime
dependency and `uvicorn` plus `h11` for the optional witness extra. Their
locked transitive runtime packages and PyPI metadata checked for this
distribution path are:

| Package | Locked version | Dependency scope | PyPI license expression or classifier | License file listed |
|---|---:|---|---|---|
| cryptography | 50.0.2 | Runtime | Apache-2.0 OR BSD-3-Clause | LICENSE, LICENSE.APACHE, LICENSE.BSD |
| cffi | 2.1.1 | cryptography transitive runtime | MIT-0 | LICENSE |
| pycparser | 3.12 | cffi transitive runtime | BSD-3-Clause | LICENSE |
| uvicorn | 0.54.0 | Optional witness extra | BSD-3-Clause | LICENSE.md |
| click | 8.5.0 | Uvicorn dependency | BSD-3-Clause | LICENSE.txt |
| h11 | 0.16.0 | Optional witness extra | MIT | LICENSE.txt |
| colorama | 0.4.6 | Windows only build and test dependency | BSD License | PyPI metadata did not list a license file |

The optional and transitive packages remain separate distributions installed
by the package manager; the candidate CASF artifacts contain the CASF Apache
2.0 license file and do not copy their implementation files. PyPI metadata
for the exact package versions was checked on 2026-10-31. This is a metadata
inventory, not a full review of every dependency's license text or of
redistribution as a combined product. Do not create a bundled application
without reviewing the full notices for the exact selected dependency set.

## Uvicorn pin review, 2026-10-31

The project retains the exact `uvicorn==0.54.0` pin and the checked lock entry.
The current pin is the published 0.54.0 release, and its upstream release
notes describe changes to the opt in experimental HTTP/2 implementation; CASF
uses asyncio with ASGI 3 and h11, without enabling that experimental mode.
The upstream security page showed no published Uvicorn advisories when checked
on this date. No evidence found in this review justifies changing the pin.
The lock remains necessary for repeatable candidate builds.

Sources checked on 2026-10-31: [Uvicorn 0.54.0 release notes](https://github.com/Kludex/uvicorn/blob/main/docs/release-notes.md), [Uvicorn security page](https://github.com/Kludex/uvicorn/security), and [PyPI release metadata](https://pypi.org/project/uvicorn/0.54.0/).

Remaining review includes platform SQLite and TLS components, a complete
license and redistribution notice inventory, and maintainer acceptance of the
implementation. Historical experiment environments remain as recorded and are
not upgraded by this review.

## Locked package advisory refresh, 2026-10-31

`pip-audit` 2.10.1 queried the OSV vulnerability service for all 24 exact
package versions in `uv.lock`, without dependency resolution. It reported no
known vulnerabilities for those versions on this date. This result applies to
the lockfile package list and the advisory data returned by OSV; it is not a
guarantee of safety and does not assess the macOS or Ubuntu system libraries,
SQLite, TLS implementation, licenses, or redistribution notices. Repeat the
advisory query before publication. Source: [OSV query API](https://osv.dev/).
