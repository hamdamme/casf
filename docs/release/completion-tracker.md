# CASF completion tracker

Updated 10 November 2026. Target confirmed by the maintainer: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 50 is merged into main at `b3cf12be89455f5515a8ad001295086c91527342`. The research refresh starts from that revision and targets main directly. The original audit remains a record of its earlier baseline.

**Current position:** Phases 1–3 and Sessions 1–8 complete. Phase 4, Session 9 is awaiting review of the affected research reruns and evidence reconciliation.

**Progress:** 16/28 tasks complete; 12 remaining. 8/14 sessions complete; 6 remaining. 3/6 phases complete; 3 remaining, including the current phase.

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
| 4 | 9 — Research evidence | F17 | Rerun only experiments affected by source changes in new output locations | Awaiting review |
| 4 | 9 — Research evidence | F18 | Reconcile outcomes, limitations and historical/current evidence; preserve originals | Awaiting review |
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

- PR 50 is merged. Its twelve supported configurations and consolidated evidence have been accepted, completing F16, Session 8 and Phase 3.
- F17: recorded a plan before collection, protected existing benchmark outputs, and reran ten detection cases, ten H1 trials, twenty local performance runs, twenty H3 runs and RQ4 counts in new locations. Measurement source and import identity are pinned separately from result assembly.
- F18: added a dated reconciliation and reviewed public subset. H1 still returns INCONCLUSIVE without the retained newer pin; this remains an expectation mismatch. All 193 protected historical files are unchanged and 525 H3 raw checksums were verified. Historical WAN/Linux/preprint values remain historical.
- Local validation: 47 focused harness tests, the complete 1191-test suite, lint and typing passed. Hosted results belong to the proposed PR revision; all twelve jobs must pass before merge readiness is claimed.
- Remaining acceptance: review F17–F18 against the bounded rerun scope and explicit omissions. These studies do not measure independent witness administration, default verified startup, automatic worker performance or the full proposed workload matrix.
- Remaining: 12 tasks, 6 sessions and 3 phases, including F17–F18 awaiting review. Accepting this batch completes Session 9, leaving 10 tasks, 5 sessions and 3 phases.
- User action: review the research draft PR and its checks. Nothing is merged or released by this work.
- Next task after acceptance: Phase 4, Session 10 — validate documentation/demo workflows and review critical changes (F19–F20).

## Evidence

- [Release scope and audit-to-acceptance mapping](completion-scope-v0.1.md)
- [Startup and recovery behavior and limitations](../writer-recovery.md)
- [Recovery drill matrix and operating procedure](../recovery-drills.md)
- [Generated inputs and parser fuzzing](../adversarial-testing.md)
- [Process crash and concurrency matrix](../process-crash-testing.md)
- [Supported validation matrix and evidence](validation-matrix.md)
- [Current research measurements and reconciliation](../../research/current-evidence-2026-11-10.md)
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
