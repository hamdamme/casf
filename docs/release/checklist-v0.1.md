# Current experimental candidate checklist

Updated 9 November 2026 for the startup/restore fix branch, based on merged
PR 29 at `0f2df3de8dbee0da92c45d66167aac2813327a69`. Package metadata
remains `0.1.0rc1`. This page records release gates; the
[completion tracker](completion-tracker.md) records phases, sessions and tasks.
Dated session records describe evidence available at their own revisions.

## Current disposition

| Area | Status | Evidence and completion boundary |
| --- | --- | --- |
| Historical merged source validation | PASS for the PR 28 source | [Actions run 118](https://github.com/hamdamme/casf/actions/runs/41265472713) passed all six locked and minimum dependency jobs for Python 3.12, 3.13 and 3.14 at `a3bfa110810e88e5736b451f8e25b3f968c609dd`, merged as `93ba4325675c948b108a0281c2b0d97c713decdc`. These checks do not validate later source changes. |
| Startup/restore fix batch | Local evidence recorded; hosted checks tracked on the fix PR | The reviewed local batch passed 455 tests, including 47 new cases, plus lint and typing. The previous PR head passed all six hosted jobs and build/install checks. Follow [PR #30](https://github.com/hamdamme/casf/pull/30) for exact-head hosted results and review status. [Recovery guide](../writer-recovery.md) states the implemented checks and remaining trust boundaries. This is not final artifact approval. |
| Requirements traceability | Mapped with explicit limits | [Evidence map](../../tests/requirement_evidence.json), [traceability checks](../../tests/unit/test_traceability.py), and [current evidence guide](requirement-evidence.md). A mapped assertion is not proof of full specification conformance. |
| Specification conformance | Not fully established | [Current implementation reference](../current-reference.md#operational-limits-and-specification-differences) records startup, restore, API and storage differences. These require implementation evidence or an explicit specification decision before claiming full conformance. |
| Assessed security findings | Corrected or documented within assessed scope | [Phase 3 dispositions](phase3-closeout-2026-10-28.md#reviewer-findings-and-disposition), [October 31 source changes](notes-review-candidate-2026-10-31.md), and PR 28 header regressions. This does not assert that no unknown defects exist. |
| Historical research evidence | Accepted with scope limits | Maintainer acceptance is recorded in [Phase 3 closeout](phase3-closeout-2026-10-28.md#research-evidence-boundary). Original results do not measure the current candidate. [Research guide](../../research/README.md) states the current interpretation. |
| External review | Limited review accepted | [Scope](phase3-closeout-2026-10-28.md#review-coverage) records examined and unexamined areas. No additional reviewer is required by this cleanup. |
| Platforms and native components | Evidence available for recorded environments | macOS arm64 was checked manually; Ubuntu hosted CI runs Python 3.12 through 3.14. The workflow uses ubuntu-latest. Exact earlier runtime inventories are in [closeout](phase3-closeout-2026-10-28.md#validated-platform-and-component-scope). No macOS CI or Windows validation is claimed. |
| Licensing and reporting channel | Recorded checks complete within scope | [License inventory](dependency-review.md) and [closeout](phase3-closeout-2026-10-28.md). The original candidate carried Apache 2.0 notices and no vendored dependencies; a real private report established channel delivery. Final artifact contents must still be inspected. |
| Final candidate artifacts | BLOCKED for current source | The October 28 approved files and October 31 review files predate later source changes. Select a final source revision, build into a new directory, verify clean installs and documented flows, inspect contents, and record exact hashes. Preserve prior artifacts unchanged. |
| Dependency advisory freshness | Due with final artifact preparation | Queries are dated evidence. Refresh exact resolved versions when preparing the final candidate; do not report old advisory results as current. |
| Exact artifact acceptance | Not recorded for current source | The October 28 approval applies only to its recorded hashes and notes. A later build requires its own hash confirmation and decision. |

## Historical records

[Phase 3 closed on 28 October](phase3-closeout-2026-10-28.md) for the exact
candidate recorded there. That completed milestone is preserved. Subsequent
source fixes do not inherit that artifact approval, and later documentation
cleanup does not reopen completed experiments or external review.

The [October 28 notes](notes-v0.1.md), [October 31 review notes](notes-review-candidate-2026-10-31.md),
[installation rehearsal](install-rehearsal-2026-10-27.md),
[Session 3 validation](session3-validation.md), and
[streaming validation](streaming-validation.md) are dated evidence.
The previous combined checklist is preserved in
[Git history at 93ba432](https://github.com/hamdamme/casf/blob/93ba4325675c948b108a0281c2b0d97c713decdc/docs/release/checklist-v0.1.md).
It must not be used as the current gate table.
