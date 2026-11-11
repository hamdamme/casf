# Current experimental candidate checklist

Updated 10 November 2026 after PR 50 merged at
`b3cf12be89455f5515a8ad001295086c91527342`. Package metadata remains
`0.1.0rc1`; the next review candidate is planned as `0.1.0rc2` during final
artifact preparation. No existing artifact approval covers these source changes.
The [completion tracker](completion-tracker.md) records tasks and review status.

## Current disposition

| Area | Status | Evidence and completion boundary |
| --- | --- | --- |
| Startup, trust and recovery implementation | Accepted through the merged implementation PRs | Verified opening checks independent pins, supplied status, full local history, fresh witness continuity and durable retained state. Restore preserves signed evidence and seals. [Recovery guide](../writer-recovery.md) and [assertion map](../../tests/requirement_evidence.json). |
| Scheduling, storage and public interfaces | Accepted through PR 47 | Durable checkpoint retries, versioned schemas/migration, typed operations, complete bundle reads and trusted suffix verification have regression coverage. See the [current reference](../current-reference.md). |
| Generated, fuzz and process testing | Accepted through PRs 48–49 | Twelve generated properties, a 25-case parser corpus, seeded mutation campaigns and 27 parent-controlled crash cases. Their [coverage limits](test-coverage-status.md) remain explicit. |
| Supported validation matrix | Exact revision results required | [Twelve configurations](validation-matrix.md) cover Ubuntu x86_64 and macOS arm64, Python 3.12–3.14, locked/minimum direct dependencies, builds and installed-wheel checks. Review all jobs, runtime/import identities and retained results for the proposed revision. A badge alone does not close this gate. |
| Requirements traceability | Mapped with explicit limits | [Evidence map](../../tests/requirement_evidence.json), structural [traceability checks](../../tests/unit/test_traceability.py), and [evidence guide](requirement-evidence.md). Named assertions are not proof of every specification rule. |
| Specification and operational boundaries | Explicit; full conformance not claimed | [Current implementation limits](../current-reference.md#operational-limits-and-specification-differences) include administrative trust/status distribution, witness recovery assumptions, bounded generated coverage and hardware durability. |
| Research evidence | Local refresh awaiting review | The [current follow-up](../../research/current-evidence-2026-11-10.md) records new detection, H1, local batching, H3 and RQ4 evidence. H1's primary expectation remains unmet; WAN/Linux performance and preprint values remain historical. [October 28 acceptance](phase3-closeout-2026-10-28.md#research-evidence-boundary) still applies to its original records. |
| Documentation and critical-change review | Current workflow/release review remains | Validate the documented demo and operating flows, reconcile current versus historical instructions, and resolve release-blocking findings. Existing limited external review is preserved in [its scope record](phase3-closeout-2026-10-28.md#review-coverage). |
| Final candidate artifacts | Not prepared for final acceptance | Select the final source, update candidate metadata, build into a new directory, inspect wheel/source contents, clean-install exact files and record hashes. Ordinary PR builds are validation artifacts, not approved release files. |
| Dependency advisories and licensing | Refresh at final artifact preparation | [Earlier reviews](dependency-review.md) are dated. Inspect exact resolved packages, native components, notices and final contents; old advisory results are not current clearance. |
| Security reporting | Historical channel test retained | [October 28 record](phase3-closeout-2026-10-28.md) documents the tested private reporting channel and best-effort scope. No new report was sent during validation. |
| Release notes and acceptance | Pending final files and explicit approval | Prepare support details, limitations, hashes and notes for the exact candidate. Previous approval does not transfer to a new build. |
| Publication and handoff | Not authorized or performed | Publish only after explicit approval of the prepared release, then verify public installation and complete the operating/maintenance handoff. |

## Historical records

The [October 28 closeout](phase3-closeout-2026-10-28.md),
[October 28 notes](notes-v0.1.md), [October 31 review notes](notes-review-candidate-2026-10-31.md),
[installation rehearsal](install-rehearsal-2026-10-27.md),
[Session 3 validation](session3-validation.md), and
[streaming validation](streaming-validation.md) describe their own revisions.
Their original measurements, artifacts and acceptance decisions remain unchanged.

The [previous checklist at PR 49's merge](https://github.com/hamdamme/casf/blob/4d89e764050455d8d0fe289bd6bb27710ec3b3bb/docs/release/checklist-v0.1.md)
preserves the earlier gate table, including PR 28/30 validation. It is historical
evidence, not the current release decision.
