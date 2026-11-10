# CASF completion tracker

Updated 10 November 2026. Target confirmed by the maintainer: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 39 is merged into main at `9227f6a765f9311c6d218dbdbfc0195b74844f88`. The recovery-drill batch starts from that revision and targets main directly. The original audit remains a record of its earlier baseline.

**Current position:** Phase 1 and Session 3 complete. Phase 2, Session 4 awaiting review; checkpoint operation in Session 5 is next.

**Progress:** 7/28 tasks complete; 21 remaining. 3/14 sessions complete; 11 remaining. 1/6 phases complete; 5 remaining, including the current phase.

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
| 2 | 4 — Restore and recovery | F08 | Verify old backup, missing evidence and interrupted recovery behavior | Awaiting review |
| 2 | 5 — Checkpoint operation | F09 | Complete agreed checkpoint scheduling and retry behavior | Pending |
| 2 | 5 — Checkpoint operation | F10 | Verify outages, restarts, duplicate submissions and pending/witnessed reporting | In progress |
| 2 | 6 — Storage and public interfaces | F11 | Resolve database integrity and migration requirements | Pending |
| 2 | 6 — Storage and public interfaces | F12 | Resolve agreed API, export and verification-report conformance gaps | In progress |
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

- PR 39 is merged. F05 and F07 are complete: verified startup, durable authority status and checkpoint retention, and authenticated offline restore followed by verified promotion have been accepted. Session 3 is complete.
- F08 awaiting review: deterministic drills now cover storage exhaustion, corrupt backups, lost signing keys, writer and witness rollback, unavailable witnesses and interrupted backup/recovery. The matrix links each failure to assertions and an operating procedure.
- Fixed three storage error paths: SQLite exhaustion remains distinguishable from lock contention, failed database initialization closes its connection, and CLI database errors return local error 5 without a traceback.
- Backup publication uses a complete private temporary copy, file synchronization, atomic publication without replacement, and directory synchronization. Tests cover dangling symlinks, concurrent destination creation, copy/sync failure and process exit; source evidence and retry behavior are checked.
- Validation: exact local and hosted results belong to the draft PR. The new drills use actual SQLite page-limit exhaustion, injected filesystem failures and selected process exits. They do not claim physical disk or power-loss validation.
- Preservation: authenticated formats, frozen vectors and historical research outputs are unchanged. No release was published; review builds do not close final candidate F21/F22.
- Remaining: 21 tasks, including F08 awaiting review; 11 sessions; 5 phases. After F08 acceptance, 20 tasks and 10 sessions remain, and Session 4 can close.
- User action: review the recovery-drill draft PR and its checks. Nothing is merged or released by this work.
- Next task: implement and test the agreed checkpoint/retry worker in Session 5. Broader process crashes, property/fuzz coverage, release validation and publication approval remain separate gates.

## Evidence

- [Release scope and audit-to-acceptance mapping](completion-scope-v0.1.md)
- [Startup and recovery behavior and limitations](../writer-recovery.md)
- [Recovery drill matrix and operating procedure](../recovery-drills.md)
- [New integrity and recovery regressions](../../tests/unit/test_writer_integrity_recovery.py)
- [Writer trust regressions](../../tests/unit/test_writer_trust.py) and [CLI trust regressions](../../tests/unit/test_cli_writer_trust.py)
- [Requirement-to-test evidence](../../tests/requirement_evidence.json)
- [Coverage status](test-coverage-status.md)

The dated repository audit and full file inventory were delivered in the maintainer's review workspace. They describe the baseline, not the post-fix branch.
