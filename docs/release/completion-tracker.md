# CASF completion tracker

Updated 11 November 2026. Target: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 54 was accepted at
`ecc47630c1340ac118dc50f2989cc51c37171080`. Explicit publication approval followed;
[0.1.0rc2 is published](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc2).
The original audit and release-preparation records remain historical.

**Current position:** All six phases and fourteen sessions are delivered for the
agreed experimental scope. Final handoff documentation is submitted through a PR;
merging that PR remains repository administration, not unperformed release validation.
No merge is performed as part of this closeout.

**Progress:** 28/28 tasks complete; 0 remaining. 14/14 sessions complete;
0 remaining. 6/6 phases complete; 0 remaining within this completion plan.

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
| 5 | 12 — Release evidence | F23 | Refresh advisories, license review and package contents | Complete |
| 5 | 12 — Release evidence | F24 | Prepare release notes, hashes, support details and final checklist | Complete |
| 6 | 13 — Publication | F25 | Present exact release for user approval; publish only after explicit approval | Complete |
| 6 | 13 — Publication | F26 | Verify public downloads and installation | Complete |
| 6 | 14 — Final handoff | F27 | Deliver operating guide, demonstration, maintenance checklist and limits | Complete |
| 6 | 14 — Final handoff | F28 | Verify source/release consistency and close tracker with evidence | Complete |

## Acceptance and reporting

A task is complete when its stated acceptance check has passed and supporting evidence is recorded. Work awaiting required review is marked Awaiting review. Added tasks change the total explicitly; missing requirements are not silently dropped. Existing research and accepted review scope remain credited.

After every completed task, report: task ID and changes; checks actually run and results; current phase/session; completed and remaining task/session/phase counts; blockers; the user action required or “Nothing needed”; and the next task.

## Latest session summary

- F23–F24: advisory, license, native-component and release-preparation review accepted in PR 54.
- F25–F26: the explicitly approved GitHub prerelease was published at the exact build
  commit with the retained wheel, source archive and checksum file. Public downloads
  on Mac and Linux matched all three hashes; fresh public wheel/source installations
  passed CLI, import, witness, public-verification and 21-check demonstrations. No PyPI upload.
- F27: [operating handoff](../operating-handoff.md) delivers installation/demo entry points,
  trust and state responsibilities, monitoring, backup/recovery, maintenance and support limits.
- F28: [publication evidence](publication-0.1.0rc2.md) and its machine-readable record
  identify the tag, assets, reviewed CI and Linux results. All 46 packaged source inputs
  match the build revision and accepted review checkout; all 39 imported runtime files match.
- Linux laptop validation is complete for the recorded Ubuntu/Python environment:
  1199 source tests and 1199 retained-wheel tests, zero failures/errors/skips,
  6075 parser cases and three 21-check demonstrations. This is separate from historical research.
- Remaining implementation/release tasks in this plan: none. Review and merge the final
  documentation PR to make this handoff the default-branch reference.
- Ongoing work: maintain dependencies and reporting, protect retained state and backups,
  and scope any persistent witness/HTTPS/cloud deployment separately. Production 1.0,
  independent audit and new WAN measurements are not claimed. H1 remains unmet.

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
