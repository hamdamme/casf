# CASF completion tracker

Updated 10 November 2026. Target confirmed by the maintainer: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 42 is merged into main at `08206bb577daf23d0e6c257a1f5c4ed09bc286fa`. The export/report batch starts from that revision and targets main directly. The original audit remains a record of its earlier baseline.

**Current position:** Phase 1 and Sessions 3–5 complete. Phase 2, Session 6 in progress; storage migration is complete, and public interface conformance is in progress.

**Progress:** 11/28 tasks complete; 17 remaining. 5/14 sessions complete; 9 remaining. 1/6 phases complete; 5 remaining, including the current phase.

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

- PR 42 is merged. F11 is complete: constrained versioned schemas and explicit writer/witness migrations have been accepted.
- F12 remains in progress. This review batch adds prefix exports, private streaming publication that cannot replace an existing destination, and complete diagnostic serialization shared by the Python verifier and CLI.
- Export tests cover exact envelope bytes, checkpoint/receipt boundaries, concurrent appends, bounded Python allocations, file/directory failures, destination races and process exits. Pending final seals remain protected; late publication errors never expose a partial bundle.
- Report tests cover full success/failure/inconclusive output, exact record ranges, checkpoint identity, policy assumptions, detached serialization and late malformed input. Existing enum values and exit categories are preserved.
- Remaining F12 acceptance: immutable typed requests/results, alignment of report enum names and missing-trust verdicts with SPEC section 15, and the incremental verification contract. These are required follow-up changes; this batch does not close Session 6 or Phase 2.
- Validation: exact local and hosted results belong to the draft PR. Selected crash tests do not close the broader process crash/concurrency matrix or final candidate package gates.
- Preservation: authenticated formats, cryptographic vectors, schema version 1 and historical research outputs are unchanged. No release was published.
- Remaining: 17 tasks, 9 sessions and 5 phases. F12 stays in the remaining total after this batch is accepted.
- User action: review the export/report draft PR and its checks. Nothing is merged or released by this work.
- Next task: continue F12 with the typed public API and report-semantics decisions. Property/fuzz coverage, broader crash tests, research/package validation and publication approval remain separate gates.

## Evidence

- [Release scope and audit-to-acceptance mapping](completion-scope-v0.1.md)
- [Startup and recovery behavior and limitations](../writer-recovery.md)
- [Recovery drill matrix and operating procedure](../recovery-drills.md)
- [Prefix export and complete diagnostics](../export-and-reports.md)
- [Storage integrity and migration](../storage-migrations.md)
- [Checkpoint worker behavior and reports](../checkpoint-worker.md)
- [New integrity and recovery regressions](../../tests/unit/test_writer_integrity_recovery.py)
- [Writer trust regressions](../../tests/unit/test_writer_trust.py) and [CLI trust regressions](../../tests/unit/test_cli_writer_trust.py)
- [Requirement-to-test evidence](../../tests/requirement_evidence.json)
- [Coverage status](test-coverage-status.md)

The dated repository audit and full file inventory were delivered in the maintainer's review workspace. They describe the baseline, not the post-fix branch.
