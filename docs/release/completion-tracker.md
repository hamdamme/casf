# CASF completion tracker

Updated 10 November 2026. Target confirmed by the maintainer: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 30 merged as `65a0252ace032e5a5dae0a85d3d959b4c1b1e399`. The Desktop main checkout was fast-forwarded to that commit. The next implementation branch is `fix/writer-trust-pins`; the original audit remains a record of its earlier baseline.

**Current position:** Phase 1 complete. Phase 2, Session 3 in progress; the first implementation batch also addresses part of Session 4.

**Progress:** 5/28 tasks complete; 23 remaining. 2/14 sessions complete; 12 remaining. 1/6 phases complete; 5 remaining, including the current phase.

These counts describe this completion plan, not the proportion of all historical project work. A session is a reviewable work package, not a fixed time estimate. Historical Phase 3 closeout is a separate record. Partial implementation and work awaiting review remain in the remaining totals.

## Tasks

| Phase | Session | Task | Work | Status |
|---:|---:|---|---|---|
| 1 | 1 — Current project review | F01 | Review current code, checks, and PR 29 | Complete |
| 1 | 1 — Current project review | F02 | Establish current inventory, baseline, and completion tracker | Complete |
| 1 | 2 — Final requirements | F03 | Define exact experimental release version, platform and support scope | Complete |
| 1 | 2 — Final requirements | F04 | Map each gap to a fix/design decision and acceptance check | Complete |
| 2 | 3 — Startup and trust | F05 | Complete agreed startup and manifest trust checks; address A02 | In progress |
| 2 | 3 — Startup and trust | F06 | Add corruption, wrong-key and inconsistent-state regressions | Complete |
| 2 | 4 — Restore and recovery | F07 | Authenticate restore evidence and preserve final seal, checkpoints and receipts; address A01 | In progress |
| 2 | 4 — Restore and recovery | F08 | Verify old backup, missing evidence and interrupted recovery behavior | In progress |
| 2 | 5 — Checkpoint operation | F09 | Complete agreed checkpoint scheduling and retry behavior | Pending |
| 2 | 5 — Checkpoint operation | F10 | Verify outages, restarts, duplicate submissions and pending/witnessed reporting | Pending |
| 2 | 6 — Storage and public interfaces | F11 | Resolve database integrity and migration requirements | Pending |
| 2 | 6 — Storage and public interfaces | F12 | Resolve agreed API, export and verification-report conformance gaps | Pending |
| 3 | 7 — Adversarial inputs | F13 | Implement generated-input/property tests with actual coverage | Pending |
| 3 | 7 — Adversarial inputs | F14 | Implement bounded fuzz testing and preserve failures as regressions | Pending |
| 3 | 8 — Crashes and full validation | F15 | Exercise process crashes, concurrency, interrupted submissions and recovery | Pending |
| 3 | 8 — Crashes and full validation | F16 | Run supported validation matrix and update requirement evidence | Pending |
| 4 | 9 — Research evidence | F17 | Rerun only experiments affected by source changes in new output locations | Pending |
| 4 | 9 — Research evidence | F18 | Reconcile outcomes, limitations and historical/current evidence; preserve originals | Pending |
| 4 | 10 — Documentation and review | F19 | Verify user workflows/demo; retire obsolete runner and clarify historical material after review | In progress |
| 4 | 10 — Documentation and review | F20 | Review critical changes and resolve release-blocking findings | Pending |
| 5 | 11 — Build and install | F21 | Build exact packages from identified final source; verify developer import source | Pending |
| 5 | 11 — Build and install | F22 | Clean-install exact packages and exercise documented flows | Pending |
| 5 | 12 — Release evidence | F23 | Refresh advisories, license review and package contents | Pending |
| 5 | 12 — Release evidence | F24 | Prepare release notes, hashes, support details and final checklist | Pending |
| 6 | 13 — Publication | F25 | Present exact release for user approval; publish only after explicit approval | Pending |
| 6 | 13 — Publication | F26 | Verify public downloads and installation | Pending |
| 6 | 14 — Final handoff | F27 | Deliver operating guide, demonstration, maintenance checklist and limits | Pending |
| 6 | 14 — Final handoff | F28 | Verify source/release consistency and close tracker with evidence | Pending |

## Acceptance and reporting

A task is complete when its stated acceptance check has passed and supporting evidence is recorded. Work awaiting required review is marked Awaiting review. Added tasks change the total explicitly; missing requirements are not silently dropped. Existing research and accepted review scope remain credited.

After every completed task, report: task ID and changes; checks actually run and results; current phase/session; completed and remaining task/session/phase counts; blockers; the user action required or “Nothing needed”; and the next task.

## Latest session summary

- Completed F03: recorded the experimental release boundary, planned next review candidate 0.1.0rc2, supported validation targets, support limits and final release gates. The package version stays unchanged until final candidate preparation.
- Completed F04: mapped all eight audit findings to completion tasks and acceptance evidence.
- F05/F06: full local record/index/journal verification and wrong-signing-key protection merged in PR 30; F06 is complete. The next batch adds explicitly supplied authority, log, manifest and witness pins during creation, startup and restore, plus CLI `--trust` support. These changes await review. Compatibility calls without pins remain local-only; status, default-policy completion and fresh external-state reconciliation remain open under F05.
- F07/F08: restore now preserves verified checkpoint/receipt chains, checkpoint indices, final seals and supplied pending tails. Added malformed-evidence, anchor, backup, continuation and process-interruption checks. Restore commits manifest, records and journal atomically. External anchor authentication/currentness and broader failure coverage remain open.
- F19: removed the unused alternate test runner and three empty test-directory marker files. Updated coverage and recovery guidance. Incorporated merged PR 29 and reconciled the current reference with the startup/restore changes. Broader executable-documentation validation remains open.
- Review follow-up: rejected incoming receipts that name the wrong manifest or previous receipt before committing them. Four regressions first reproduced the mismatch between receipt acceptance and startup verification; they now pass, including restart and recovery with the valid receipt. Added coverage for a restored nonfinal pending checkpoint with later unwitnessed records.
- Verification: PR 30 passed 455 tests locally and in all six hosted jobs before merge. The trust-pin batch adds 28 cases; all 483 tests pass locally, and Ruff and mypy pass. Hosted results must identify the final PR head; prior results do not certify later changes. These are review-build checks, not completion of final-candidate F21/F22.
- Preservation: the trust-pin batch leaves specification bytes, frozen vectors, research and historical experiment results unchanged from merged PR 30. No experiments were rerun or releases published.
- Remaining: 23 tasks, 12 sessions, 5 phases.
- User action: review the trust-pin changes and their checks before merge.
- Next task: complete status and default trust policy, fresh witness reconciliation and authenticated external anchors under F05/F07. Full specification conformance is not yet claimed.

## Evidence

- [Release scope and audit-to-acceptance mapping](completion-scope-v0.1.md)
- [Startup and recovery behavior and limitations](../writer-recovery.md)
- [New integrity and recovery regressions](../../tests/unit/test_writer_integrity_recovery.py)
- [Writer trust regressions](../../tests/unit/test_writer_trust.py) and [CLI trust regressions](../../tests/unit/test_cli_writer_trust.py)
- [Requirement-to-test evidence](../../tests/requirement_evidence.json)
- [Coverage status](test-coverage-status.md)

The dated repository audit and full file inventory were delivered in the maintainer's review workspace. They describe the baseline, not the post-fix branch.
