# rc4 follow-up remediation

Baseline: `75c81bea954a33275892d4b798bd5383cb74e094` (PR 79 merge).
This follow-up addresses the November 21 review by @adzguy. The earlier C01–C06
[record](advisory-remediation-2026-11-17.md) and candidate artifacts retain their
original scope and results. No release, public advisory or production change is
part of this remediation.

## Tracked scope

| Task | Acceptance | Status |
| --- | --- | --- |
| C03 | Unrecognized latest-view 404 bodies produce response errors through CLI exit 5; explicit NO_CHECKPOINT stays inconclusive. | Implemented; macOS full suite passed |
| D01 | Sensitive descriptors reject Darwin extended ACL entries and inspection failures; new sensitive bytes are checked before writing. | Implemented; macOS full suite passed |
| D02 | Loaded/effective origins reject invalid configuration with exit 2 before secrets, network or persistent changes. | Implemented; macOS full suite passed |
| D03 | Read 409 yields response error, not evidence conflict; submission compatibility and evidence verdicts retained. | Implemented; macOS full suite passed |
| Validation | Focused regressions, full supported-host checks, lint, typing and package checks. | In progress |
| Review | Maintainer and follow-up review of the exact correction revision. | Pending |
| Candidate | Build and approve new artifacts from accepted source before publication. | Pending |

The acceptance policy is recorded in [ADR-017](../adr/ADR-017-audit-input-boundaries.md#follow-up-decisions-before-rc4).
Regression files: `test_advisory_followup.py`, `test_file_permissions.py` and the
updated read-category expectations in `test_advisory_c01_c06.py`.

## Validation record

macOS arm64, Python 3.12.14 / SQLite 3.53.1: **1,660 tests passed** in
114.82 seconds, including all 54 new follow-up cases. The first full run exposed
stale installed package metadata; rebuilding/installing the rc4 wheel corrected
the environment before the clean full rerun. No failing assertion was removed.

Lint, strict typing (39 source files), dependency lock and installed dependency
checks passed. Six requirement-traceability tests passed. Package inspection
verified 40 runtime files in both wheel and source archive. The installed witness
smoke test and all 21 synthetic workflow checks passed. Repository checks passed
for 571 tracked files and 692 local links.

Linux validation is in progress. Hosted Actions endpoints on the private advisory
fork returned HTTP 404; no hosted CI success is claimed.
Native ACL tests use disposable synthetic files; HTTP response regressions stub
transport. Existing integration tests use local loopback services.

## Limitations and next milestone

Darwin ACL policy rejects even restrictive entries; callers must explicitly
provision compatible paths. Ancestor-directory administration, compromised
accounts/root and broader filesystem races remain outside this scoped guarantee.
A read failure does not advance checkpoint state; independently authenticated
status observations may still advance under existing policy. No evidence of
production readiness or absence of other defects is claimed.

The milestone is reviewed corrections followed by a separately identified,
validated candidate. Publication and advisory disclosure require separate approval.
Estimated remaining effort after local validation: 1–2 development sessions for
review responses and candidate preparation; external review timing is unknown.
