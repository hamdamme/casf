# CASF completion tracker

Updated 10 November 2026. Target confirmed by the maintainer: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 53 is merged into main at `7af8d93e182868e96f76ab7cef72a23143e0f1d7`. Release-evidence preparation starts from that revision and targets main directly. The original audit remains a record of its earlier baseline.

**Current position:** Phases 1–4 and Sessions 1–11 complete. Phase 5, Session 12 is awaiting review of advisories, licensing, release notes and the approval proposal. Additional Linux/cloud evaluation is deferred by the maintainer; Ubuntu CI continues.

**Progress:** 22/28 tasks complete; 6 remaining. 11/14 sessions complete; 3 remaining. 4/6 phases complete; 2 remaining, including the current phase.

These counts describe this completion plan, not the proportion of all historical project work. A session is a reviewable work package, not a fixed time estimate. Historical Phase 3 closeout is a separate record. Partial implementation and work awaiting review remain in the remaining totals.

## Tasks

| Phase | Session | Task | Work | Status |
|---:|---:|---|---|---|
| 1 | 1 — Current project review | F01 | Review current code, checks, and PR 29 | Complete |
| 1 | 1 — Current project review | F02 | Establish current inventory, baseline, and completion tracker | Complete |
| 1 | 2 — Final requirements | F03 | Define exact experimental release version, platform and support scope | Complete |
| 1 | 2 — Final requirements | F04 | Map each gap to a fix/design decision and acceptance check | Complete |
| 2 | 3 — Startup and trust | F05 | Complete agreed startup and manifest trust checks; address A02 | Complete |
| 2 | 3 — Startup and trust | F06 | Add corruption, wrong-key and inconsistent-state regressions | Complete |
| 2 | 4 — Restore and recovery | F07 | Authenticate restore evidence and preserve final seal, checkpoints and receipts; address A01 | Complete |
| 2 | 4 — Restore and recovery | F08 | Verify old backup, missing evidence and interrupted recovery behavior | Complete |
| 2 | 5 — Checkpoint operation | F09 | Complete agreed checkpoint scheduling and retry behavior | Complete |
| 2 | 5 — Checkpoint operation | F10 | Verify outages, restarts, duplicate submissions and pending/witnessed reporting | Complete |
| 2 | 6 — Storage and public interfaces | F11 | Resolve database integrity and migration requirements | Complete |
| 2 | 6 — Storage and public interfaces | F12 | Resolve agreed API, export and verification-report conformance gaps | Complete |
| 3 | 7 — Adversarial inputs | F13 | Implement generated-input/property tests with actual coverage | Complete |
| 3 | 7 — Adversarial inputs | F14 | Implement bounded fuzz testing and preserve failures as regressions | Complete |
| 3 | 8 — Crashes and full validation | F15 | Exercise process crashes, concurrency, interrupted submissions and recovery | Complete |
| 3 | 8 — Crashes and full validation | F16 | Run supported validation matrix and update requirement evidence | Complete |
| 4 | 9 — Research evidence | F17 | Rerun only experiments affected by source changes in new output locations | Complete |
| 4 | 9 — Research evidence | F18 | Reconcile outcomes, limitations and historical/current evidence; preserve originals | Complete |
| 4 | 10 — Documentation and review | F19 | Verify user workflows/demo; retire obsolete runner and clarify historical material after review | Complete |
| 4 | 10 — Documentation and review | F20 | Review critical changes and resolve release-blocking findings | Complete |
| 5 | 11 — Build and install | F21 | Build exact packages from identified final source; verify developer import source | Complete |
| 5 | 11 — Build and install | F22 | Clean-install exact packages and exercise documented flows | Complete |
| 5 | 12 — Release evidence | F23 | Refresh advisories, license review and package contents | Awaiting review |
| 5 | 12 — Release evidence | F24 | Prepare release notes, hashes, support details and final checklist | Awaiting review |
| 6 | 13 — Publication | F25 | Present exact release for user approval; publish only after explicit approval | Pending |
| 6 | 13 — Publication | F26 | Verify public downloads and installation | Pending |
| 6 | 14 — Final handoff | F27 | Deliver operating guide, demonstration, maintenance checklist and limits | Pending |
| 6 | 14 — Final handoff | F28 | Verify source/release consistency and close tracker with evidence | Pending |

## Acceptance and reporting

A task is complete when its stated acceptance check has passed and supporting evidence is recorded. Work awaiting required review is marked Awaiting review. Added tasks change the total explicitly; missing requirements are not silently dropped. Existing research and accepted review scope remain credited.

After every completed task, report: task ID and changes; checks actually run and results; current phase/session; completed and remaining task/session/phase counts; blockers; the user action required or “Nothing needed”; and the next task.

## Latest session summary

- PR 53 is merged. Candidate build and clean-install evidence are accepted, completing F21–F22 and Session 11.
- F23: all 25 exact external package/tool versions were queried through OSV and PyPI; no listed advisories or yanked files were returned. License/notice files and both exact candidate archives were inspected. Native findings are assessed separately with explicit applicability and deployment limits; green tests do not certify host libraries.
- F24: prepared release notes, support guidance, exact asset hashes, a checksum file and a concrete GitHub prerelease proposal. The proposed tag identifies the original build commit; later review commits are not misrepresented as the artifact source. No PyPI publication is proposed.
- Validation: the unchanged installed wheel passed 1199 tests and the 21-check demo on an isolated Python 3.12.16 runtime. All 39 imports matched source. Lint, typing and the unchanged dependency lock passed. CI now checks setup-python's latest available versions across all twelve configurations; its macOS catalog still trails upstream for some minors. Hosted compatibility checks do not certify a patched runtime.
- Evidence: [dependency/native review](dependency-review-0.1.0rc2.md), [release notes](notes-0.1.0rc2.md), [exact proposal](approval-0.1.0rc2.md), [manifest](release-manifest-0.1.0rc2.json), and [checksums](SHA256SUMS-0.1.0rc2.txt). Reporting is enabled; no new private report was sent.
- Remaining acceptance: review F23–F24 and final CI, including the scoped native-library dispositions. Publication needs a fresh preflight and separate explicit approval of the exact files, notes, tag target and destination. Additional Linux/cloud deployment evaluation remains deferred.
- Remaining: 6 tasks, 3 sessions and 2 phases, including F23–F24 awaiting review. Accepting this batch completes Session 12 and Phase 5, leaving 4 tasks, 2 sessions and 1 phase.
- User action: review the release-evidence draft PR and its checks. Merging it does not authorize publication.
- Next task after acceptance: Phase 6, Session 13 — confirm the exact publication proposal, obtain explicit approval, publish only if approved, then verify public downloads and installation (F25–F26).

## Evidence

- [Release scope and audit-to-acceptance mapping](completion-scope-v0.1.md)
- [Startup and recovery behavior and limitations](../writer-recovery.md)
- [Recovery drill matrix and operating procedure](../recovery-drills.md)
- [Generated inputs and parser fuzzing](../adversarial-testing.md)
- [Process crash and concurrency matrix](../process-crash-testing.md)
- [Supported validation matrix and evidence](validation-matrix.md)
- [Current research measurements and reconciliation](../../research/current-evidence-2026-11-10.md)
- [Runnable workflow](../demo.md) and [critical-change review](workflow-review-2026-11-10.md)
- [Bundle and incremental verification](../verifier-api.md)
- [Typed log operations and result boundaries](../log-api.md)
- [Typed append requests and results](../append-api.md)
- [Prefix export and complete diagnostics](../export-and-reports.md)
- [Storage integrity and migration](../storage-migrations.md)
- [Checkpoint worker behavior and reports](../checkpoint-worker.md)
- [New integrity and recovery regressions](../../tests/unit/test_writer_integrity_recovery.py)
- [Writer trust regressions](../../tests/unit/test_writer_trust.py) and [CLI trust regressions](../../tests/unit/test_cli_writer_trust.py)
- [Requirement-to-test evidence](../../tests/requirement_evidence.json)
- [Coverage status](test-coverage-status.md)

The dated repository audit and full file inventory were delivered in the maintainer's review workspace. They describe the baseline, not the post-fix branch.
