# Current experimental candidate checklist

Updated 11 November 2026. The explicitly approved experimental 0.1.0rc2
[GitHub prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc2) is published.
The [publication record](publication-0.1.0rc2.md) supersedes preparation-time status;
its exact hashes and tested revisions remain distinct from subsequent documentation.
The [operating handoff](../operating-handoff.md) and [completion tracker](completion-tracker.md)
record the handoff accepted by the maintainer's merge of [PR 55](https://github.com/hamdamme/casf/pull/55).
Repository reconciliation corrected premature completion counts; see the
[file review](repository-review.md). No PyPI upload was performed.

## Current disposition

| Area | Status | Evidence and completion boundary |
| --- | --- | --- |
| Startup, trust and recovery implementation | Accepted through the merged implementation PRs | Verified opening checks independent pins, supplied status, full local history, fresh witness continuity and durable retained state. Restore preserves signed evidence and seals. [Recovery guide](../writer-recovery.md) and [assertion map](../../tests/requirement_evidence.json). |
| Scheduling, storage and public interfaces | Accepted through PR 47 | Durable checkpoint retries, versioned schemas/migration, typed operations, complete bundle reads and trusted suffix verification have regression coverage. See the [current reference](../current-reference.md). |
| Generated, fuzz and process testing | Accepted through PRs 48–49 | Twelve generated properties, a 25-case parser corpus, seeded mutation campaigns and 27 parent-controlled crash cases. Their [coverage limits](test-coverage-status.md) remain explicit. |
| Supported validation matrix | Final PR 54 run passed all twelve jobs | [Recorded run](https://github.com/hamdamme/casf/actions/runs/42952534486) tested head `823948e`: 1199 tests and the 21-check demonstration per job. This is release evidence, not a claim about later documentation-PR checks. |
| Requirements traceability | Mapped with explicit limits | [Evidence map](../../tests/requirement_evidence.json), structural [traceability checks](../../tests/unit/test_traceability.py), and [evidence guide](requirement-evidence.md). Named assertions are not proof of every specification rule. |
| Specification and operational boundaries | Explicit; full conformance not claimed | [Current implementation limits](../current-reference.md#operational-limits-and-specification-differences) include administrative trust/status distribution, witness recovery assumptions, bounded generated coverage and hardware durability. |
| Research evidence | Local refresh accepted in PR 51 | The [current follow-up](../../research/current-evidence-2026-11-10.md) records new detection, H1, local batching, H3 and RQ4 evidence. H1's primary expectation remains unmet; WAN/Linux performance and preprint values remain historical. [October 28 acceptance](phase3-closeout-2026-10-28.md#research-evidence-boundary) still applies to its original records. |
| Documentation and critical-change review | Accepted in PR 52 | The [21-check demo](../demo.md) and [scoped review](workflow-review-2026-11-10.md) record executed workflows, corrected guidance and the remote benchmark URL fix. Existing limited external review is preserved in [its scope record](phase3-closeout-2026-10-28.md#review-coverage). |
| Linux laptop and future deployment | Laptop validation complete; persistent deployment separate | [Publication evidence](publication-0.1.0rc2.md) records actual Ubuntu laptop checks. Independently operated witnesses, cloud deployment and new WAN measurements remain future work. |
| Candidate build and installation | Published exact files verified | Original [candidate evidence](candidate-0.1.0rc2.md) is retained; [post-publication checks](publication-0.1.0rc2.md) verify downloaded bytes and fresh installations. CI builds are separate artifacts. |
| Dependency advisories and licensing | Accepted in PR 54; preflight refreshed | All 25 exact queries completed without listed package advisories before publication. [Native findings](dependency-review-0.1.0rc2.md) retain their scoped dispositions; this is not host-library clearance. |
| Security reporting | Setting confirmed enabled | The direct reporting route and best-effort policy are in [SECURITY.md](../../SECURITY.md). The [October 28 delivery record](phase3-closeout-2026-10-28.md) remains historical; no new report was sent. |
| Release notes and acceptance | Explicit publication approval received | [Published notes](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc2), exact retained assets and original build target were approved. Preparation records remain historical. |
| Publication and handoff | Publication verified; handoff accepted in PR 55 | [Public-installation evidence](publication-0.1.0rc2.md), [operating handoff](../operating-handoff.md) and [tracker](completion-tracker.md). PR 55 merged as `710fbe346598c05ab4989a3656c907eb0aa2c853`; its final head passed all twelve CI configurations. |

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
