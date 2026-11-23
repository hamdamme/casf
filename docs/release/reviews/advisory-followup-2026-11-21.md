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
| Validation | Focused regressions, supported CI matrix, lint, typing and package checks. | Complete; public merge CI #234 passed all ten jobs |
| Review | Maintainer and follow-up review of the exact correction revision. | Maintainer merge accepted; final follow-up disposition pending |
| Candidate | Build and approve new artifacts from accepted source before publication. | Replacement artifacts built and validated; approval pending |

The acceptance policy is recorded in [ADR-017](../../adr/ADR-017-audit-input-boundaries.md#follow-up-decisions-before-rc4).
Regression files: `test_advisory_followup.py`, `test_file_permissions.py` and the
updated read-category expectations in `test_advisory_c01_c06.py`.

## Current post-merge status

The maintainer merged the corrections as
`d4721c43b23ec93a14819390a1d7606f0c74e259`, whose tree matches reviewed
`0fac103594823a0def2dc92a863dd9563f070359`.
[CI #234](https://github.com/hamdamme/casf/actions/runs/44989456952) passed all ten
hosted configurations: 1747 tests plus 14 Darwin-only skips in each Ubuntu job,
1761 tests without skips in each macOS job, and 72,900 total parser cases.
This supersedes the platform-validation gaps in the historical sections below.

The [replacement candidate](../0.1.0rc4/candidate-0.1.0rc4-d4721c4.md) identifies new files
built from that exact merge. All 40 packaged/runtime files match; 35 installation
commands on native macOS and 35 on locally emulated Ubuntu passed, including
four 21-check synthetic workflows. Historical candidate files remain preserved.

Tracked acceptance is **5/7 tasks (71%)**: four corrections and validation are
complete. Maintainer source acceptance is established by merge; final follow-up
disposition and approval of the exact candidate remain open. No new independent
researcher signoff is claimed. Tagging, publication and disclosure are separate.

## Initial validation record

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

At that revision, tracked completion was **4/7 tasks (57%)**. Subsequent pre-merge
validation reopened D02 for hostname syntax; the follow-up below records that work.

A clean committed-source build at that revision passed package inspection. Its
member hashes match the wheel and source archive used for local validation.
These are private review artifacts, not approved publication assets:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc4-py3-none-any.whl` | 111912 | `7a1eb8c08c2430b18910117aaeec36fc36a08df1ecf5e91bbb5d22228fff406e` |
| `casf-0.1.0rc4.tar.gz` | 149823 | `06087a89cb709976b6f8a97abedc97c02902fce72d7dd504a63d431c0cabbb90` |

Native ACL tests use disposable synthetic files; HTTP response regressions stub
transport. Existing integration tests use local loopback services.

## D02 hostname validation follow-up

Independent pre-merge validation found that `https://bad host` passed origin
validation, reached secret/transport callbacks and state creation, and exited 4.
The shared validator now rejects whitespace and controls before URL parsing and
checks DNS hostname syntax and lengths after IDNA conversion. IP literals retain
their existing handling. Valid HTTPS names, internationalized names, trailing
DNS dots, explicit ports and loopback HTTP origins remain supported.

Regressions cover transport, verification and both stored/overridden writer
startup origins. Invalid origins must fail before secrets, network callbacks,
writer initialization or retained-state creation. Only the three Python files
introduced by the original follow-up receive whole-file formatting.

Validation below applies to the implementation and tests accompanying this record.
The correction adds 101 cases for malformed origins and valid-host compatibility.

| Platform | Python | SQLite | Complete suite |
| --- | --- | --- | --- |
| macOS arm64 | 3.12.0 | 3.43.1 | 1,761 passed |
| macOS arm64 | 3.12.14 | 3.53.1 | 1,761 passed |
| macOS arm64 | 3.13.17 | 3.53.1 | 1,761 passed |
| macOS arm64 | 3.14.9 | 3.53.1 | 1,761 passed |
| Linux arm64 | 3.12.16 | 3.42.0 | 1,747 passed; 14 Darwin-only skips |
| Linux arm64 | 3.12.16 | 3.46.1 | 1,747 passed; 14 Darwin-only skips |

Each macOS environment also passed 282 focused transport/security regressions and
the independent D02 acceptance test that previously returned exit 4. All native
ACL cases passed. Linux runs used offline containers and read-only source mounts;
the 3.42.0 run loaded the compiled SQLite 3.42.0 amalgamation explicitly.

Lint, strict typing, lock/dependency checks, repository consistency and package
inspection passed. The wheel and source distribution contain the expected 40
runtime files. Python 3.12.14, 3.13.17 and 3.14.9 each passed base/witness wheel
smoke checks, public synthetic verification, the 21-check example and 8,100 bounded
parser fuzz cases. The three newly added files pass formatting. The whole-tree
formatter still reports 142 pre-existing files; those files were not reformatted.
AST comparisons confirmed formatting preserved the ACL implementation/tests and
the existing follow-up test functions. Full-diff review found no unintended code,
credentials or operational private keys.

D02 was complete again within this scope. At that point completion was **4/7 (57%)**:
Linux x86_64, Linux Python 3.13/3.14 and the separate minimum-dependency matrix were
not rerun. Hosted Actions cannot run on the temporary advisory fork. Remaining
platform validation, maintainer/follow-up review and an accepted candidate remain
open; local success does not claim those gates or publication are complete.

## Limitations and next milestone

Darwin ACL policy rejects even restrictive entries; callers must explicitly
provision compatible paths. Ancestor-directory administration, compromised
accounts/root and broader filesystem races remain outside this scoped guarantee.
A read failure does not advance checkpoint state; independently authenticated
status observations may still advance under existing policy. No evidence of
production readiness or absence of other defects is claimed.

The current milestone is final review and approval of the replacement candidate.
Publication and advisory disclosure require separate approval. Estimated remaining
effort is 1–2 development sessions for approved publication, download/installation
verification and Zenodo closeout; external review timing is unknown.
