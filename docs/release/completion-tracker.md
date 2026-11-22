# CASF completion tracker

Updated 22 November 2026. Target: experimental v0.1 for research and evaluation.

Audit baseline: `93ba4325675c948b108a0281c2b0d97c713decdc`. PR 54 was accepted at
`ecc47630c1340ac118dc50f2989cc51c37171080`. Explicit publication approval followed;
[0.1.0rc2 is published](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc2).
The original audit and release-preparation records remain historical.

**Current position:** PR 57 was merged at
`e59fd64feed2d7136c0ee4ae543455ba90d3e572`, accepting the scoped tracked-file
review and corrections. The original 28 tasks, 14 sessions and six phases are
accepted. This is historical scope acceptance, not proof that no defects remain.

PR 58 merged at `cb3febff53a7cf8274a4b871f5be1382ebaedd33`, accepting
A01–A05. The experimental plan has **33/33 tasks, 15/15 sessions and 7/7 phases
accepted**. This does not close the production gates.

The internal-deployment extension adds **eight tasks across Sessions 16–21** in
Phase 8; see [acceptance plan](internal-deployment-acceptance.md). Current position:
**Phase 8, Session 21 — research-demo publication complete**. Overall:
**37/41 tasks accepted; P08 publication and public-download verification are complete.**
See the [rc3 publication record](publication-0.1.0rc3.md). Four production tasks remain incomplete.
P05/P06 remain partial production gates, outside this research-demo closeout.
**P03: Whole-machine power-loss testing — Pending future validation.**
**P04: Independent security review — Pending independent evaluation.**
Both tasks remain explicitly incomplete and relevant to future production-readiness
evaluation. Neither blocks publication of the experimental research release;
artifact review, publication approval and download validation remain required.
Neither is counted as complete. P02 was accepted in PR 69; the scoped USB result
was accepted in PR 70 at `95ec5b9a6b7bb465c3790b8ddb6d62930f9934e4` without closing P03.
[Permissions, backup roundtrip and daily policy evidence](backup-custody-2026-11-16.md)
were accepted in PR 71. The [synthetic transaction CLI](../synthetic-transactions.md)
was accepted in PR 72 and its post-merge CI passed; this does not establish a
production event source. The [adopted operating rules](research-demo-closeout.md)
and rc3 publication close P08, but not P05/P06. P05/P06 remain partial: operational keys, trust provisioning and
real-use acceptance are not established by synthetic tests. Future releases require separate approval.

These counts describe this completion plan, not the proportion of all historical project work. A session is a reviewable work package, not a fixed time estimate. Historical Phase 3 closeout is a separate record. Partial implementation and work awaiting review remain in the remaining totals.

## Next experimental release

PR 82 merged at `3333d0025388e97a3e54b7ae29974b7369545f81`, accepting the
SQLite permissions and canonical JSONL corrections and regressions. The earlier
PR 78 and C03/D01–D03 corrections remain included. Post-merge CI 238 passed all
ten jobs on this exact source.

The [replacement rc4 candidate](candidate-0.1.0rc4-3333d00.md) is built from
`3333d00`. Six fresh installations passed 76 commands across native macOS and
emulated Ubuntu, including four 21-check workflows. The previous `d4721c4`
artifacts remain historical and must not be published as the corrected rc4.
Preparation is complete; exact-file review, final advisory disposition and
separate publication approval remain pending. No new researcher signoff is claimed.

Remaining release work is review and a final dependency-query refresh, approved
GitHub publication and download verification, then a new Zenodo version and
citation verification. Estimated remaining release effort is 1–2 development
sessions after approval; external review timing is unknown. Preparation does not
authorize publication.

These are maintenance steps after the accepted rc3 closeout, not changes to the
37/41 historical plan count. Production tasks remain incomplete as stated above.

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
| 7 | 15 | A01 | CASF-01: strict Boolean verifier policy and wrappers | Accepted in PR 58 |
| 7 | 15 | A02 | CASF-02: submission error categories, pending bytes and redaction | Accepted in PR 58 |
| 7 | 15 | A03 | CASF-H01: reject unsupported base-URL components | Accepted in PR 58 |
| 7 | 15 | A04 | CASF-H02: strict transport timeout boundaries | Accepted in PR 58 |
| 7 | 15 | A05 | CASF-H03: targeted adversarial coverage, validation and production-gate handoff | Accepted in PR 58 |

## Acceptance and reporting

A task is complete when its stated acceptance check has passed and supporting evidence is recorded. Work awaiting required review is marked Awaiting review. Added tasks change the total explicitly; missing requirements are not silently dropped. Existing research and accepted review scope remain credited.

After every completed task, report: task ID and changes; checks actually run and results; current phase/session; completed and remaining task/session/phase counts; blockers; the user action required or “Nothing needed”; and the next task.

## Latest session summary

- PR 57 continuation: all 512 tracked paths have a recorded review method;
  266 manually read text files, 243 structured-data reviews and three document
  text/visual reviews. Runtime and benchmark fixes, corrected crash assertions,
  1,258 passing local tests and retained-data reconciliation are recorded in the
  [review report](line-review-2026-11-11.md). F19/F20/F28 were accepted by the PR 57 merge.
- Team A remediation: five tasks accepted in PR 58. Production gates remain
  separate; internal-deployment acceptance now has an explicit eight-task plan.


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

- PR 60 accepted the generated recovery sequences at
  `aadcc190897ddfe884e97bc21c6a3a2795fe9430`; all 12 CI jobs passed. At that revision, P07 remained
  open until guided-campaign review, and P02/P03 had not been scheduled. This is
  historical status; the current task dispositions above supersede it.

- PR 61 accepted P07 at `c263d6e0ca8ec29e2edd6cbc6c593ae087fe9021`.
  All 12 CI jobs passed. The independent review brief and internal operations
  worksheet prepare P04–P06; those tasks remain open pending actual review,
  assigned operators and deployment acceptance evidence.

## Historical candidate preparation before publication

The [rc3 record](candidate-0.1.0rc3.md), [notes](notes-0.1.0rc3.md),
[advisory refresh](dependency-review-0.1.0rc3.md) and
[operating rules](research-demo-closeout.md) document the research-demo closeout.
Build revision `a0ac1bfa61d3406c99b6bf758c62f6e840b633f3` passed 1543 local source
tests, 8100 parser inputs, 33 Mac installation checks and 20 Linux checks of the
same artifact bytes. Final PR CI is a separate revision-specific acceptance step.
P08 remains open for review, separate publication approval and downloaded-artifact
validation. P03 is pending future validation and P04 is pending independent
evaluation; both remain incomplete without blocking experimental publication. P05/P06 remain
partial production gates. No completed-task count is increased by preparation.

## Production evaluation status decision

The current decision keeps P03 **Pending future validation** and P04 **Pending
independent evaluation**. Both are incomplete future production-readiness
evaluations, not experimental research release publication blockers. This changes
status wording and release scope, not test results or completed-task counts.

Historically, the operator chose not to schedule whole-machine interruption tests
and postponed commissioning an independent review during the synthetic rehearsal.
The [pre-change records at PR 73's merge](https://github.com/hamdamme/casf/tree/d77daf31e3324ab75180bbfacc1457f49a1383cb/docs/release)
retain those earlier decisions. The current pending statuses supersede that
scheduling language. USB/reboot results, source revisions, artifact checksums and
all recorded validation outcomes remain unchanged.

## Historical candidate refresh after PR 74

PR 74 accepted the pending P03/P04 dispositions at
`c38bf821af013eaa4efa96a799577dab60250b48`. The [refreshed rc3 files](candidate-0.1.0rc3-c38bf82.md)
include that revision's README, new checksums and fresh installation/advisory
evidence. Prior candidate files and their recorded results remain preserved.
P08 stays open for artifact review, separate publication approval and downloaded
installation verification. No production gate or completed-task count changes.

Post-merge CI passed all twelve configurations on `c38bf82`, each with 1543 tests
and the 21-check demo. Refreshed exact-byte installation checks passed: 33 on Mac
and 20 on Linux. Release publication remains unapproved and incomplete.

## Publication closeout — 17 November 2026

The [rc3 publication and verification record](publication-0.1.0rc3.md) supersedes
the pre-publication P08 statuses in the historical preparation sections above.
P08 is accepted following approved publication, Mac/Linux public-download and
installation verification, and the Zenodo archive. PR 76 citation/CI changes
were merged and post-merge CI passed. P03–P06 remain incomplete; 37/41 tasks
are accepted. The agreed experimental research-release scope is finished.
