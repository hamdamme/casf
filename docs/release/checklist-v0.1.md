# Current experimental release checklist

See the [release records index](README.md) for current work and historical evidence.

Updated 22 November 2026. **0.1.0rc3 is published and public downloads and
installations are verified.** See the [publication closeout](0.1.0rc3/publication-0.1.0rc3.md). The [candidate record](0.1.0rc3/candidate-0.1.0rc3-c38bf82.md) identifies exact build
revision and artifacts. Later documentation and CI revisions are distinct.
The [research-demo closeout](reviews/research-demo-closeout.md) is the current scope;
production deployment is not part of this release scope.

The published [0.1.0rc2 prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc2)
and its [publication evidence](0.1.0rc2/publication-0.1.0rc2.md) remain unchanged. No PyPI
upload was performed. Historical acceptance does not approve new artifact bytes.

## Next candidate

The [3333d00 candidate](0.1.0rc4/candidate-0.1.0rc4-3333d00.md) is superseded and
historical. It includes the PR 78/82 corrections but omits the Ed25519 fix.
Its artifacts and all earlier rc4 artifacts must not be published. The
[replacement candidate](0.1.0rc4/candidate-0.1.0rc4-492f330.md) is built from PR 84's
merge `492f330`. CI 242 passed all ten jobs on that source; the exact wheel and
sdist passed fresh installation checks. This documentation PR needs its own CI.

| rc4 gate | Current status |
| --- | --- |
| C03/D01–D03 correction source | Merged at `d4721c4`; same source tree as reviewed `0fac103` |
| SQLite permissions and canonical JSONL | Accepted in PR 82 at `3333d00`; historical regressions passed |
| Small-order Ed25519 keys and retained checkpoint arguments | Accepted in PR 84 at `492f330`; installed regressions passed |
| Hosted acceptance matrix | CI 242: 10/10 jobs passed on exact build `492f330` |
| Exact replacement artifacts | Built from `492f330`; all 40 runtime files verified; new checksums recorded |
| Exact-file installations | 38 commands each on native macOS and emulated Ubuntu; four 21-check workflows passed |
| Dependency query refresh | Fresh queries required before publication |
| Final review and artifact approval | Pending review of these exact files; no independent signoff claimed |
| Tag, GitHub release and advisory publication | Not performed; require separate approval |
| Public downloads and Zenodo version | Pending approved publication |

The table below retains the accepted rc3 disposition. It does not approve rc4
or establish rc4 public-download or Zenodo verification.

## Current disposition

| Area | Status | Evidence and completion boundary |
| --- | --- | --- |
| Scoped tracked-file review | Accepted in PR 57 at `e59fd64feed2d7136c0ee4ae543455ba90d3e572` | [Methods and findings](reviews/line-review-2026-11-11.md) apply to that inventory/revision, not every later change. |
| Merged hardening and demo | Included in rc3 build | [Notes](0.1.0rc3/notes-0.1.0rc3.md), [changelog](../../CHANGELOG.md), existing regressions. |
| PR 71 backup/custody evidence | Accepted by merge | [Permissions and Proton restore](reviews/backup-custody-2026-11-16.md); synthetic recovery is not production-key recovery. |
| PR 72 terminal transaction demo | Accepted; post-merge CI passed | Main `40382b1ed5355fef9b7716919a7c141037528455`, [all twelve jobs](https://github.com/hamdamme/casf/actions/runs/43994726679). Cross-host evidence retains its own implementation revision. |
| Operating decisions | Adopted for single-operator synthetic use | [Rules](reviews/research-demo-closeout.md): daily manual backups, retention, monthly restore checks and recovery targets. Ongoing execution is not claimed. |
| Local candidate validation | Passed on named environments | 1543 source tests; 8100 bounded parser inputs; 33 Mac and 20 Linux installation checks; four installed 21-check workflows. See [candidate evidence](0.1.0rc3/candidate-0.1.0rc3-c38bf82.md). |
| PR validation matrix | Release review and subsequent citation merge passed | [Publication record](0.1.0rc3/publication-0.1.0rc3.md) identifies the twelve-job release run and ten-job PR 76 post-merge run. [Current matrix](validation-matrix.md). |
| Package contents and installation | Exact candidate files identified | [Hashes and runtime inventories](0.1.0rc3/candidate-0.1.0rc3-c38bf82.json); source archive now includes both examples. Local bytes and CI builds remain distinct. |
| Advisories and licensing | Package queries refreshed; existing license evidence retained | [Current review](0.1.0rc3/dependency-review-0.1.0rc3.md): 50 successful queries, no listed package advisories; native/host patch assessment remains separate. The final pre-publication refresh is retained in [publication evidence](0.1.0rc3/publication-0.1.0rc3.json); future releases require fresh queries. |
| Requirements and research | Existing evidence retained | [Assertion map](../../tests/requirement_evidence.json), [coverage](test-coverage-status.md), [research follow-up](../../research/current-evidence-2026-11-10.md). H1's primary expectation remains unmet; historical measurements are not rerun by tests. |
| Production acceptance | P05/P06 partial, outside demo scope | [Internal acceptance](internal-deployment-acceptance.md); no production keys or real records provisioned. P03 is pending future validation; P04 is pending independent evaluation. Both are incomplete future production-readiness evaluations, not blockers to experimental research publication. |
| Publication | P08 complete | [Approved rc3 publication](0.1.0rc3/publication-0.1.0rc3.md), exact public-download hashes, fresh Mac/Linux installs and Zenodo DOI verified. Future releases and deployments require separate approval. |

## Historical records

The [October 28 closeout](reviews/phase3-closeout-2026-10-28.md),
[October 28 notes](reviews/notes-v0.1.md), [October 31 review notes](reviews/notes-review-candidate-2026-10-31.md),
[installation rehearsal](reviews/install-rehearsal-2026-10-27.md),
[Session 3 validation](reviews/session3-validation.md), and
[streaming validation](reviews/streaming-validation.md) describe their own revisions.
Their original measurements, artifacts and acceptance decisions remain unchanged.

The [previous checklist at PR 49's merge](https://github.com/hamdamme/casf/blob/4d89e764050455d8d0fe289bd6bb27710ec3b3bb/docs/release/checklist-v0.1.md)
preserves the earlier gate table, including PR 28/30 validation. It is historical
evidence, not the current release decision.
