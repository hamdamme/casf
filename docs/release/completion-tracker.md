# CASF completion tracker

Updated 11 November 2026. Target: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 54 was accepted at
`ecc47630c1340ac118dc50f2989cc51c37171080`. Explicit publication approval followed;
[0.1.0rc2 is published](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc2).
The original audit and release-preparation records remain historical.

**Current position:** PR 57 was merged at
`e59fd64feed2d7136c0ee4ae543455ba90d3e572`, accepting the scoped tracked-file
review and corrections. The original 28 tasks, 14 sessions and six phases are
accepted. This is historical scope acceptance, not proof that no defects remain.

The subsequent Team A audit opens five remediation tasks below, with a separate
[remediation record](team-a-remediation.md) and [production gates](production-readiness-gates.md).
Current work is **Phase 7, Session 15 — audit remediation**. Progress is
**28/33 tasks accepted, 14/15 sessions and 6/7 phases closed**; five remediation
tasks await validation and maintainer review. No new release is authorized.

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
| 4 | 10 — Documentation and review | F19 | Finish manual file review; preserve workflow and historical-document corrections already verified | Complete |
| 4 | 10 — Documentation and review | F20 | Validate and review newly reproduced runtime defects and regression fixes | Complete |
| 5 | 11 — Build and install | F21 | Build exact packages from identified final source; verify developer import source | Complete |
| 5 | 11 — Build and install | F22 | Clean-install exact packages and exercise documented flows | Complete |
| 5 | 12 — Release evidence | F23 | Refresh advisories, license review and package contents | Complete |
| 5 | 12 — Release evidence | F24 | Prepare release notes, hashes, support details and final checklist | Complete |
| 6 | 13 — Publication | F25 | Present exact release for user approval; publish only after explicit approval | Complete |
| 6 | 13 — Publication | F26 | Verify public downloads and installation | Complete |
| 6 | 14 — Final handoff | F27 | Deliver operating guide, demonstration, maintenance checklist and limits | Complete |
| 6 | 14 — Final handoff | F28 | Reconcile source/release distinctions and close only the verified scope | Complete |

## Team A remediation extension

| Phase | Session | Task | Work | Status |
| --- | --- | --- | --- | --- |
| 7 | 15 | A01 | CASF-01: strict Boolean verifier policy and wrappers | Awaiting review |
| 7 | 15 | A02 | CASF-02: submission error categories, pending bytes and redaction | Awaiting review |
| 7 | 15 | A03 | CASF-H01: reject unsupported base-URL components | Awaiting review |
| 7 | 15 | A04 | CASF-H02: strict transport timeout boundaries | Awaiting review |
| 7 | 15 | A05 | CASF-H03: targeted adversarial coverage, validation and production-gate handoff | Awaiting review |

## Acceptance and reporting

A task is complete when its stated acceptance check has passed and supporting evidence is recorded. Work awaiting required review is marked Awaiting review. Added tasks change the total explicitly; missing requirements are not silently dropped. Existing research and accepted review scope remain credited.

After every completed task, report: task ID and changes; checks actually run and results; current phase/session; completed and remaining task/session/phase counts; blockers; the user action required or “Nothing needed”; and the next task.

## Latest session summary

- PR 57 continuation: all 512 tracked paths have a recorded review method;
  266 manually read text files, 243 structured-data reviews and three document
  text/visual reviews. Runtime and benchmark fixes, corrected crash assertions,
  1,258 passing local tests and retained-data reconciliation are recorded in the
  [review report](line-review-2026-11-11.md). F19/F20/F28 were accepted by the PR 57 merge.
- Team A remediation: five additional tasks await review; see the remediation
  record for exact checks and limitations. Production gates remain separate.


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
- F02/F19 reconciliation: the tracked-file inventory, original audit dispositions,
  historical archive, status corrections and package links are delivered in the
  [repository review](repository-review.md). PR 55's merge accepts these corrections
  and F27/F28. The earlier premature closeout remains documented in that review.
- PR 55 validation: [CI run 43067257585](https://github.com/hamdamme/casf/actions/runs/43067257585)
  passed all twelve configurations at `42909d756285cd8cfb13ef49671dfeea8783f290`:
  1203 tests and the 21-check demo per configuration. Six locked jobs also checked
  all 506 tracked files and 522 local links. Two macOS jobs were retried after
  runner-capacity cancellations; the successful retry used the same source.
  These results belong to that reviewed head, not to later bookkeeping edits.
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

The original 9 November audit and inventory describe the baseline. The [repository review](repository-review.md) reuses their findings and records every tracked path, corrections, retained evidence and verification limits for this revision.
