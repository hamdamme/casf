# Locked dependency review

Review date: 2026-10-24. Scope: all 24 external Python packages recorded in
uv.lock, including conditional packages, plus uv 0.13.5 used for installation
and builds. CASF itself is excluded from the external package count.

The lockfile SHA 256 is `91c0ca22aaab17b660ca15faf326d38313349eaa78ba866fcf81c9199dd6de0b`.
The [query record](dependency-review-2026-10-24.json) retains the exact versions,
query time, PyPI license metadata, and OSV results.

## Advisory result

Exact version queries returned no listed advisories in the OSV responses or
PyPI vulnerability fields for any of the 25 queried packages. This is a dated
query outcome, not proof of absence of vulnerabilities. No package versions
were upgraded by this review.

Sources were the [OSV query API](https://google.github.io/osv.dev/api/) and
PyPI version JSON endpoints, using the package name and exact locked version.
For example, [cryptography 50.0.2 metadata](https://pypi.org/pypi/cryptography/50.0.2/json).
Repeat the queries before publishing or changing dependencies.

## License inventory

| Package | Version | Used by | Declared license |
|---|---|---|---|
| `ast-serialize` | 0.13.1 | development | `MIT` |
| `build` | 1.6.1 | build | `MIT` |
| `cffi` | 2.1.1 | base | `MIT-0` |
| `click` | 8.5.0 | witness | `BSD-3-Clause` |
| `colorama` | 0.4.6 | development, build | `BSD-3-Clause` |
| `cryptography` | 50.0.2 | base | `Apache-2.0 OR BSD-3-Clause` |
| `h11` | 0.16.0 | witness | `MIT` |
| `hypothesis` | 6.170.9 | development | `MPL-2.0` |
| `iniconfig` | 2.3.1 | development | `MIT` |
| `librt` | 0.16.0 | development | `MIT` |
| `mypy` | 2.4.0 | development | `MIT` |
| `mypy-extensions` | 1.1.0 | development | `MIT` |
| `packaging` | 26.3 | development, build | `Apache-2.0 OR BSD-2-Clause` |
| `pathspec` | 1.1.1 | development | `MPL-2.0` |
| `pluggy` | 1.7.0 | development | `MIT` |
| `pycparser` | 3.12 | base | `BSD-3-Clause` |
| `pygments` | 2.21.0 | development | `BSD-2-Clause` |
| `pyproject-hooks` | 1.3.3 | build | `MIT` |
| `pytest` | 9.1.1 | development | `MIT` |
| `ruff` | 0.17.2 | development | `MIT` |
| `setuptools` | 84.2.1 | build | `MIT` |
| `sortedcontainers` | 2.4.0 | development | `Apache-2.0` |
| `typing-extensions` | 4.16.0 | development | `PSF-2.0` |
| `uvicorn` | 0.54.0 | witness | `BSD-3-Clause` |
| `uv` | 0.13.5 | tooling | `MIT OR Apache-2.0` |

The table records package declarations, not a blanket license clearance.
License files supplied with the installed distributions were consulted where
metadata needed clarification. In particular, mypy extensions ships an MIT
license, pathspec supplies MPL 2.0, and the Colorama wheel supplies the BSD
3 Clause conditions. The Colorama wheel hash was checked before reading its
license; it was not installed or executed on macOS.

Hypothesis and pathspec are development dependencies with MPL 2.0 declarations.
They are not included in the CASF wheel. Dependency packages retain their own
licenses and notices. The package inventory does not replace checking bundled
native components or final redistribution notices for a release.

## Packaging correction and checks

CASF keeps its existing Apache 2.0 license. Its package metadata now uses the
SPDX expression and explicitly includes LICENSE. The declared build backend
minimum is Setuptools 77.0.3, following the
[packaging guidance](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).
The locked backend remains 84.2.1. This is a metadata correction, not a change
to the license text or application behavior.

With the locked backend, both the wheel and source archive built successfully
without the previous Setuptools license deprecation warning. Both contain
`License-Expression: Apache-2.0`, a LICENSE declaration, and the original
license bytes. Archive checks found no local backups, research result files,
databases, private key files, or PEM private key blocks. The wheel contains
CASF modules and package metadata; the source archive contains source,
configuration, README, license, and package metadata.

Fresh base and witness wheel installations passed on macOS Python 3.12.11,
3.13.17, and 3.14.9. Checks covered installed license metadata, imports, CLI
startup, the missing optional dependency message, a witness request, and
shutdown. Runtime dependencies were installed from exports with hashes.
These are package checks; the complete application suite was not rerun for
this metadata and documentation change.

## Remaining acceptance

- Review the target platform Python, SQLite, TLS, and bundled native components
  before release. These are not fully represented by Python package metadata.
- Complete final redistribution notice and license review for the actual release
  artifacts. This inventory does not certify legal compliance.
- Add and run the minimum dependency compatibility job required by the spec.
  The new minimum build backend version was not separately exercised; builds
  here used the locked backend.
- Review requirement to assertion mappings. The current traceability test
  checks identifier presence, not adequacy of each requirement's tests.
- Test the private reporting channel, obtain the external review required by
  the checklist, and approve final artifacts and release notes.

No security report was sent, no reviewer was contacted, and no release was
published as part of these checks. Original evidence and local backups remain
unchanged. D05 remains open pending completion and acceptance of its remaining
review conditions.
