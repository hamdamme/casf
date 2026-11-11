# CASF completion tracker

Updated 10 November 2026. Target confirmed by the maintainer: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 52 is merged into main at `79fce315a3b0ec06f2293643f01ea66a62b79136`. Candidate preparation starts from that revision and targets main directly. The original audit remains a record of its earlier baseline.

**Current position:** Phases 1–4 and Sessions 1–10 complete. Phase 5, Session 11 is awaiting review of the candidate builds and clean-install verification. Additional Linux/cloud evaluation is deferred by the maintainer; Ubuntu CI continues.

**Progress:** 20/28 tasks complete; 8 remaining. 10/14 sessions complete; 4 remaining. 4/6 phases complete; 2 remaining, including the current phase.

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
| 5 | 11 — Build and install | F21 | Build exact packages from identified final source; verify developer import source | Awaiting review |
| 5 | 11 — Build and install | F22 | Clean-install exact packages and exercise documented flows | Awaiting review |
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

- PR 52 is merged. The workflow and scoped implementation review are accepted, completing F19–F20, Session 10 and Phase 4.
- F21: prepared version 0.1.0rc2, built an exact wheel and source archive from clean commit `e92194fe0fa6eb37c2ff9016c381b8e734008880`, inspected their contents and metadata, and recorded their hashes. Both source-selected and installed developer imports matched all 39 runtime files.
- F22: passed 32 checks across fresh base-wheel, witness-wheel and source-archive environments. Both witness-capable installations ran the 21-check synthetic workflow. Public-only verification, CLI entry points, optional dependency behavior and installed import identities passed.
- Local validation: 1199 tests, lint, strict typing and lock consistency passed. Six damaged package copies were rejected. CI now checks package contents and the installed demo in all twelve configurations; those jobs must pass for the proposed PR revision.
- Evidence: [candidate record](candidate-0.1.0rc2.md), [file hashes and installation results](candidate-0.1.0rc2.json), and [build procedure](candidate-build.md). CI validation files are distinct from the retained local candidate files.
- Remaining acceptance: review F21–F22 and CI. Final advisories, licensing, package acceptance, notes, support details and publication approval remain open. Additional Linux/cloud deployment evaluation is deferred.
- Remaining: 8 tasks, 4 sessions and 2 phases, including F21–F22 awaiting review. Accepting this batch completes Session 11, leaving 6 tasks, 3 sessions and 2 phases.
- User action: review the candidate preparation draft PR and its checks. No release tag or publication was created.
- Next task after acceptance: Phase 5, Session 12 — refresh advisory/license evidence and prepare final release notes, hashes, support details and checklist (F23–F24).

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
