# C01–C06 remediation review

Baseline: `dffd0ef79fda69235e1ef7f21766e261da133735` (latest main before this work).
The reviewed paths were unchanged from the report's `d9f5473` baseline. All six
findings required work. This record describes unreleased source changes, not
replacement rc3 artifacts or completion of independent production assessment.

| Finding | Remediation and evidence |
| --- | --- |
| C01 | ASCII-only full timestamp matching; both reported Unicode-year forms are rejected for the shared timestamp validator. Valid ASCII timestamps remain accepted. |
| C02 | Independent finite scheduling-value validation on open/migration; valid finite range and schema bytes unchanged. Migration rejects before publication and preserves its source. |
| C03 | Shared HTTP classification for submission, latest queries and both receipt lookup paths; CLI recovery preserves unexpected-status exit 5 rather than misreporting invalid evidence. Pending checkpoint contents remain unchanged. |
| C04 | Authority pin length and issuer/key-ID matching enforced before evidence verification. |
| C05 | Descriptor-based regular-file, ownership and write-permission checks for trust files and their immediate directory; no final-component symlinks, FIFOs or directory inputs. Public readability remains permitted. Ancestor directories require trusted administration. |
| C06 | Supplied witness origins validated before trust-file publication; online mode requires an origin. Offline empty URLs remain supported. |

The decisions and compatibility boundaries are in
[ADR-017](../../adr/ADR-017-audit-input-boundaries.md). Protocol schema structure,
signing/canonicalization algorithms, cryptographic domains, retained-state rules
and database schema bytes are unchanged. The timestamp correction rejects
nonconforming encodings previously accepted accidentally.

## Reproduction and regression evidence

The initial regression commit `4ac3c64` adds 46 cases before code fixes:
**39 failed, 7 passed** on the baseline implementation. After the initial fixes,
all 46 passed. Additional controls and boundary cases bring the focused suite to
63 passing cases. A further CLI regression first reproduced HTTP 500 mapping
to exit 1 (one failure, six passing HTTP controls); the corrected mapping passes.
See [regressions](../../../tests/unit/test_advisory_c01_c06.py) and the
[requirement mapping](../../../tests/requirement_evidence.json).

An isolated build of official SQLite amalgamation 3420000 reproduced:
`SELECT sqlite_version(), 1e999 <= 1.7976931348623157e308` → `3.42.0|1`.
The ordinary local Python runtime uses SQLite 3.53.1, which returns false.
The regression deliberately uses unconstrained legacy scheduling columns so
`PRAGMA integrity_check` reports ok while the Python finite-value check must
reject infinity independently. The actual migration regression verifies source
bytes, no destination and temporary-directory cleanup. A full Python suite
linked against SQLite 3.42.0 was not run; the native SQL reproduction and
independent Python validation are separate checks.

## Validation commands

Executed on macOS arm64, Python 3.12.14 / SQLite 3.53.1:

- `PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_advisory_c01_c06.py -q`: 63 passed.
- `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`: 1606 passed in 109.77 seconds.
- `.venv/bin/ruff check src tests benchmarks examples`: passed.
- `.venv/bin/mypy src`: passed, 38 source files.
- `uv lock --check` and `uv pip check --python .venv/bin/python` with uv 0.13.5: passed.
- `uv build --python .venv/bin/python --no-build-isolation`: wheel and source archive built locally.
- `tests/package_artifacts.py`: 39 runtime files checked in both packages.
- Fresh isolated wheel install from the lockfile, `tests/wheel_smoke.py --witness`,
  and `examples/verified_workflow.py`: passed, including 21 demo checks.
- `python -m tests.fuzz --guided --seed 20261112 --cases 2000`: 2025 cases passed.
- Repository file/link validation, traceability tests and `git diff --check`:
  562 tracked files, 673 local links and six traceability tests passed; diff checks passed.

GitHub CI supplies Linux and additional Python/macOS coverage through the
[current ten-job matrix](../validation-matrix.md). Hosted results must be read
against the final PR revision; local success does not substitute for those jobs.
No release, tag, asset, PyPI package, deployment or production key was changed.
No manual hardware test is needed for these input-validation fixes. The existing
P03–P06 production tasks remain open. Passing these checks is not a guarantee
that no other defects remain.
