# Dependency and distribution review for 0.1.0rc2

Reviewed 10 November 2026 after PR 53 merged at
`7af8d93e182868e96f76ab7cef72a23143e0f1d7`. Queries were recorded on
11 November UTC. The [saved results](dependency-review-0.1.0rc2.json) bind the
lockfile hash, exact versions, query times, source URLs and response hashes.
The [candidate record](candidate-0.1.0rc2.md) identifies the unchanged files
actually inspected; historical reviews remain preserved.

## Package advisories

All 24 external packages in `uv.lock`, including conditional Colorama, plus
uv 0.13.5 were queried at exact versions. All 50 OSV/PyPI requests completed;
no listed advisories, pagination remainder or yanked release files were returned.
No dependency versions changed. These are dated database responses, not proof
that a component is free of vulnerabilities. They do not assess Python's native
libraries or every library embedded in a development tool. Refresh before
publication and on dependency changes.

Sources: [OSV version query API](https://google.github.io/osv.dev/post-v1-query/)
and [PyPI version JSON API](https://docs.pypi.org/api/json/).

## License and redistribution inventory

| Distribution | Version | Declared or supplied license |
| --- | --- | --- |
| ast-serialize | 0.13.1 | MIT |
| build | 1.6.1 | MIT |
| cffi | 2.1.1 | MIT-0 |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | BSD-3-Clause |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| h11 | 0.16.0 | MIT |
| hypothesis | 6.170.9 | MPL-2.0 |
| iniconfig | 2.3.1 | MIT |
| librt | 0.16.0 | MIT |
| mypy | 2.4.0 | MIT |
| mypy-extensions | 1.1.0 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pathspec | 1.1.1 | MPL-2.0 |
| pluggy | 1.7.0 | MIT |
| pycparser | 3.12 | BSD-3-Clause |
| pygments | 2.21.0 | BSD-2-Clause |
| pyproject-hooks | 1.3.3 | MIT |
| pytest | 9.1.1 | MIT |
| ruff | 0.17.2 | MIT |
| setuptools | 84.2.1 | MIT |
| sortedcontainers | 2.4.0 | Apache-2.0 |
| typing-extensions | 4.16.0 | PSF-2.0 |
| uvicorn | 0.54.0 | BSD-3-Clause |
| uv | 0.13.5 | MIT OR Apache-2.0 |

Installed license/notice files were inventoried and hashed for 23 locked external
packages and uv. The conditional Colorama wheel was downloaded, checked against
both PyPI and the lockfile hash, and inspected without installation or execution.
Supplied texts resolve incomplete metadata for h11, mypy-extensions, pathspec,
pluggy, sortedcontainers and Colorama. The record also retains additional notice
files found in tool distributions; the table is not an exhaustive list of every
embedded native or vendored component's license.

The exact CASF wheel contains 45 files; its source archive contains 54 regular
files. Both retain the original Apache-2.0 LICENSE bytes and metadata. Their
hashes still match the candidate record. Inspection found no native libraries,
third-party implementation packages, key/database files or PEM private-key
blocks. The archive contains the locked dependency recipe and synthetic example,
not the dependency distributions themselves. The dependency license conditions
therefore remain attached to their separately installed distributions. No
specific missing notice was identified for this CASF wheel/source distribution
path. A bundled executable, container or copied environment needs a separate
inventory and notice review; none is prepared here.

Python and its native components are external to the CASF wheel. Their upstream
license references are [Python](https://docs.python.org/3.12/license.html),
[SQLite](https://sqlite.org/copyright.html) and
[OpenSSL](https://openssl-library.org/source/license/). No platform binaries are
included in the proposed release assets.

## Native component findings and disposition

The original local check used Python 3.12.11, Python TLS OpenSSL 3.6.0,
SQLite 3.54.0 and cryptography's OpenSSL 4.0.3. That historical test result is
retained, but its TLS environment is not recommended for new operation.
[Python 3.12.16](https://www.python.org/downloads/release/python-31216/) includes
later security fixes, including an emergency certificate distrust update.
The [September OpenSSL advisory](https://openssl-library.org/news/secadv/20260929.txt)
includes certificate-processing fixes relevant to TLS clients. Upstream now
lists 3.6 as unsupported in its [November advisory](https://openssl-library.org/news/secadv/20261110.txt).

A checksum-verified Astral Python 3.12.16 build was installed only in a new
temporary directory. Its Python TLS uses OpenSSL 3.5.9; its SQLite is 3.53.1.
The exact existing candidate wheel, with the unchanged locked dependencies,
passed **1199 tests**, witness startup/shutdown and the **21-check demo** there.
All 39 imported runtime files matched source. The [runtime record](runtime-review-0.1.0rc2.json)
identifies the interpreter download, actual components and test revision.
System Python was not changed. CI now checks the setup-python catalog for the
latest available interpreter within each supported minor, rather than relying
only on its cache. Catalog availability varies by platform and can lag upstream
security releases. The [first review run](https://github.com/hamdamme/casf/actions/runs/42951661939)
selected 3.12.16, 3.13.18 and 3.14.10 on Ubuntu, but 3.12.10, 3.13.17 and 3.14.10
on macOS. Those hosted jobs are compatibility evidence, not a patched-runtime
recommendation. The separate local 3.12.16 check above covers the unchanged
candidate on a newer macOS interpreter.

| Finding | CASF assessment and limit |
| --- | --- |
| OpenSSL November 10 advisories: CVE-2026-88822, CVE-2026-95691 (QUIC); CVE-2026-88823, CVE-2026-95692 (AES-GCM-SIV); CVE-2026-107496 (CMS encryption) | The inspected CASF paths use TCP HTTPS, Ed25519 and PKCS8; no QUIC, AES-GCM-SIV or CMS operations were found. A synthetic PKCS8 probe identified AES-256-CBC. This is a code-path applicability assessment, not blanket clearance of the installed OpenSSL libraries. The advisory schedules releases with fixes for December 1; do not claim 4.0.4/3.5.10 was installed here. |
| SQLite CVE-2026-11822 / CVE-2026-11824, fixed in 3.53.2 | The updated interpreter's 3.53.1 is below that fix. Upstream describes arbitrary SQL with FTS5 and defensive mode disabled. CASF exposes no arbitrary-SQL or FTS interface and rejects unknown schema objects before its integrity check. This does not certify the native parser against every malicious database. Use maintained, patched SQLite for deployment; this test environment is compatibility evidence. |
| SQLite 3.54.1 correction to a 32-bit heap-buffer overflow | Local validation is 64-bit arm64; the stated 32-bit condition does not match it. This is not evidence for 32-bit support. |

Sources for these assessments: [OpenSSL November advisory](https://openssl-library.org/news/secadv/20261110.txt),
[cryptography wheel build notes](https://cryptography.io/en/latest/changelog/#v50-0-2),
[SQLite CVE table](https://sqlite.org/cves.html), and
[SQLite release history](https://sqlite.org/changes.html). Inspected source:
`src/casf/crypto/__init__.py`, `keys.py`, `transport.py`, `witness/server.py`,
`storage/schema.py` and `storage/versioning.py`. No exploit test or independent
native-code audit is claimed. Minimum-dependency CI is compatibility testing,
not a deployment recommendation. Final operating environments need their own
vendor-patch and configuration review; version strings alone cannot establish
whether a distributor backported fixes.

## Acceptance boundary

No package-level advisory or missing CASF distribution notice was identified
by the checks above. Native findings have the explicit scoped dispositions
above; they are not erased by green tests. Review that scope with the
[release notes](notes-0.1.0rc2.md) and [approval checklist](approval-0.1.0rc2.md).
Additional Linux/cloud deployment evaluation remains deferred. No release,
tag, private vulnerability report or external review request was sent.
