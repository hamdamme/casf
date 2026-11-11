# Current experimental candidate checklist

Updated 10 November 2026 after PR 52 merged at
`79fce315a3b0ec06f2293643f01ea66a62b79136`. Package metadata is now
`0.1.0rc2`; exact local review files and their build revision are recorded in the
[candidate record](candidate-0.1.0rc2.md). No existing artifact approval covers
these source changes or authorizes publication.
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
| Research evidence | Local refresh accepted in PR 51 | The [current follow-up](../../research/current-evidence-2026-11-10.md) records new detection, H1, local batching, H3 and RQ4 evidence. H1's primary expectation remains unmet; WAN/Linux performance and preprint values remain historical. [October 28 acceptance](phase3-closeout-2026-10-28.md#research-evidence-boundary) still applies to its original records. |
| Documentation and critical-change review | Accepted in PR 52 | The [21-check demo](../demo.md) and [scoped review](workflow-review-2026-11-10.md) record executed workflows, corrected guidance and the remote benchmark URL fix. Existing limited external review is preserved in [its scope record](phase3-closeout-2026-10-28.md#review-coverage). |
| Separate Linux/cloud evaluation | Deferred by the maintainer | Ubuntu CI continues. Additional machine deployment, independently administered witness operation and new WAN measurements have not been performed. The [remote plan](../../benchmarks/wide-area.md) records prerequisites for that later work. |
| Candidate build and installation | Prepared; review pending | The [identified 0.1.0rc2 files](candidate-0.1.0rc2.md) passed content inspection and 32 fresh-install checks, including two complete synthetic workflows. Final content/license acceptance and publication approval remain open. CI builds are separate validation artifacts. |
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
