# rc4 follow-up remediation

Baseline: `75c81bea954a33275892d4b798bd5383cb74e094` (PR 79 merge).
This follow-up addresses the November 21 review by @adzguy. The earlier C01–C06
[record](advisory-remediation-2026-11-17.md) and candidate artifacts retain their
original scope and results. No release, public advisory or production change is
part of this remediation.

## Tracked scope

| Task | Acceptance | Status |
| --- | --- | --- |
| C03 | Unrecognized latest-view 404 bodies produce response errors through CLI exit 5; explicit NO_CHECKPOINT stays inconclusive. | Completed; local validation passed |
| D01 | Sensitive descriptors reject Darwin extended ACL entries and inspection failures; new sensitive bytes are checked before writing. | Completed; local validation passed |
| D02 | Loaded/effective origins reject invalid configuration with exit 2 before secrets, network or persistent changes. | Completed; local validation passed |
| D03 | Read 409 yields response error, not evidence conflict; submission compatibility and evidence verdicts retained. | Completed; local validation passed |
| Validation | Focused regressions, supported CI matrix, lint, typing and package checks. | Local checks complete; hosted matrix pending |
| Review | Maintainer and follow-up review of the exact correction revision. | Pending |
| Candidate | Build and approve new artifacts from accepted source before publication. | Pending |

The acceptance policy is recorded in [ADR-017](../adr/ADR-017-audit-input-boundaries.md#follow-up-decisions-before-rc4).
Regression files: `test_advisory_followup.py`, `test_file_permissions.py` and the
updated read-category expectations in `test_advisory_c01_c06.py`.

## Validation record

Correction revision: `1a3db0319d78c5c2073de7076cadc2efa7b42db7`. Subsequent
evidence-only commits do not change the runtime or regression source.

macOS arm64, Python 3.12.14 / SQLite 3.53.1: **1,660 tests passed** in
114.82 seconds, including all 54 new follow-up cases. The first full run exposed
stale installed package metadata; rebuilding/installing the rc4 wheel corrected
the environment before the clean full rerun. No failing assertion was removed.

Lint, strict typing (39 source files), dependency lock and installed dependency
checks passed. Six requirement-traceability tests passed. Package inspection
verified 40 runtime files in both wheel and source archive. The installed witness
smoke test and all 21 synthetic workflow checks passed. Repository checks passed
for 571 tracked files and 692 local links.

Linux aarch64 container, Python 3.12.16 / SQLite 3.46.1: **1,646 passed,
14 Darwin-only cases skipped** in 156.34 seconds. The full run had external
networking disabled and read-only source/Git mounts. Native worktree paths and
an isolated bytecode prefix prevent host pytest bytecode and Git environment
variables from interfering with disposable-repository and trace tests. Hypothesis
used an in-memory example database because the source mount was read-only;
this produced one warning, not a skipped property test.

Hosted Actions endpoints on the private advisory fork returned HTTP 404, and the
private PR has no check runs. No hosted CI success is claimed. Python 3.13/3.14,
Linux x86_64 and the hosted minimum-dependency matrix remain unverified for these
changes. Existing historical results do not cover this revision.

Tracked completion: **4/7 tasks (57%)**. Implementation is complete; matrix
validation, review and the accepted release candidate remain open.

A clean committed-source build at that revision passed package inspection. Its
member hashes match the wheel and source archive used for local validation.
These are private review artifacts, not approved publication assets:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc4-py3-none-any.whl` | 111912 | `7a1eb8c08c2430b18910117aaeec36fc36a08df1ecf5e91bbb5d22228fff406e` |
| `casf-0.1.0rc4.tar.gz` | 149823 | `06087a89cb709976b6f8a97abedc97c02902fce72d7dd504a63d431c0cabbb90` |

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
