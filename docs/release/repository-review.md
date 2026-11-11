# Repository reconciliation

Reviewed 11 November 2026 against handoff head
`981c107d5abc63459b336a5f7631e8f421673892`, building on accepted main
`ecc47630c1340ac118dc50f2989cc51c37171080`. This closes remaining work from the
original request to check every repository file. It does not replace the release
or its exact-byte evidence. The maintainer accepted the corrections and final
handoff by merging [PR 55](https://github.com/hamdamme/casf/pull/55) as
`710fbe346598c05ab4989a3656c907eb0aa2c853`. The review findings below preserve
their original scope; the acceptance update does not rerun the research.

## Coverage and reuse

The original 9 November inventory covered 321 paths at
`93ba4325675c948b108a0281c2b0d97c713decdc`. Comparing its file hashes with the
501-file handoff baseline found 244 unchanged files, 74 changed files and 183
added files; three obsolete files had already been removed. Existing startup,
restore, API, research, package, CI and Linux evidence was reused, with its
revision boundaries preserved. Historical performance experiments were not rerun.

The [file register](repository-files.json) gives every tracked path a role,
disposition and verification method. It covers source, tests, fixtures, vectors,
examples, benchmark code and results, research and binary reading copies,
documentation, policies, workflow, metadata and lockfile. It also records the
archive move and earlier removals. It is a dated review snapshot, not a promise
that future commits automatically inherit this review.

The executable [repository check](../../tests/repository_check.py) reads every
tracked file and checks applicable formats: Python AST, JSON, TOML, DOCX archive
and XML, SVG XML, PDF envelope, SQLite fixture restoration and integrity, local
Markdown file/heading links, and all retained SHA256SUMS lists. CI retains its
per-file checks and hashes. PDF text was additionally extracted from all eleven
pages, and the Word reading copy was inspected as text. Existing preprint source,
Word, PDF and SVG checksums match. No binary document was rewritten or rerendered.

The review also checked current Python documentation snippets for syntax and
imported API names, inspected no-op functions and duplicate-file groups, compared
current guidance with the implemented APIs and prior workflow review, and
reconciled the original findings below. The file check is not itself a semantic
proof, an external-link availability audit or a visual document-layout review.

## Original findings and closure

| Finding | Disposition and evidence |
| --- | --- |
| A01 Restore drops final seals and signed journals | Fixed in earlier implementation work; [recovery guide](../writer-recovery.md), mapped restore regressions and full suite retained. No duplicate rewrite. |
| A02 Startup only checks metadata | Fixed with full local verification, independent trust/status and fresh witness reconciliation; [startup decision](../adr/ADR-008-verified-writer-startup.md) and regressions retained. |
| A03 Scheduling, storage and API gaps | Worker, migration, typed operations, complete bundle and incremental verification implemented in earlier PRs; [current reference](../current-reference.md) links each contract and its tests. |
| A04 Empty testing scaffolds | Removed empty integration/adversarial trees; property, parser mutation and process-crash suites now execute. Corrected coverage text that incorrectly grouped the populated property suite with removed scaffolds. |
| A05 Broken alternate test runner | Already removed; confirmed absent. Pytest is the maintained runner. |
| A06 Historical/current guidance mixed | Moved original Word file unchanged behind an explicit archive index; retained warning-labeled Markdown copies; corrected changelog, specification status, preparation records, decision context, Linux and outage guidance. Expanded the original backlog disposition and replaced a nonexistent prototype-tag reference with a verified source commit. |
| A07 Stale installed source | Existing source/import guards retained; local checks explicitly selected checked-out src. Distribution inspection compared the new local validation build with this source, not with the published artifact. |
| A08 Presentation and handoff | Existing runnable demo and operating guide retained; added missing package repository/documentation/issues URLs and checks for those fields. Added this durable file register and CI consistency check. |

The earlier tracker closed A06/A08 and final review too soon. F02/F19 and F27/F28
were marked Awaiting review until PR 55 merged. They are now accepted in the
[tracker](completion-tracker.md). The corrections closed unfinished original work;
they did not create a new release milestone.

## Kept intentionally

- Original Word bytes are unchanged; the [archive index](../historical/README.md)
  records their digest and directs readers to current instructions.
- The two runtime `_debug_hook` methods are intentional crash-test injection
  points. Logging overrides and the test send callback intentionally do nothing.
  No unimplemented public runtime function was found by the AST/stub review.
  Package markers, exception classes and `py.typed` have concrete import/type roles.
- Eight duplicate-content groups are retained: frozen experiment manifests,
  repeated deterministic run orders, equal detection reports from distinct runs,
  and three Python package markers. Byte equality does not make their roles redundant.
- Raw measurements, frozen vectors, SQL migration fixtures, preprint formats and
  sanitized publication copies retain provenance. No research result or frozen
  protocol vector was changed. The four preprint hashes were verified.
- `requirements.txt` remains the documented minimum-runtime convenience file;
  `pyproject.toml` defines package requirements and `uv.lock` pins development.
- Historical approval JSON remains false where it was false at preparation time;
  the publication record supplies the later decision. No historical approval is fabricated.

## Validation and limits

Local macOS validation: 1203 tests passed, including four repository-check
regressions; Ruff across source/tests/benchmarks/examples/vectors and strict mypy
passed. The lock check passed unchanged. Both local validation distributions
passed exact member/source/metadata inspection, including the new project URLs.
The runtime edits change docstrings only, verified by comparing ASTs with
module/class/function docstrings removed. These edits still change source bytes;
the published release hashes are not reused as hashes for this checkout.

[CI run 43067257585](https://github.com/hamdamme/casf/actions/runs/43067257585)
passed all twelve configurations at PR head `42909d756285cd8cfb13ef49671dfeea8783f290`:
1203 tests and the 21-check demo per configuration. All six locked jobs passed
the 506-file, 522-link repository check. Two macOS jobs needed a retry because
hosted runners were unavailable, not because tests failed. The retry passed on
the same source. Prior 1199-test CI and Linux evidence remains tied to its
recorded revisions. Later acceptance-text edits do not inherit those exact-head runs.

No remaining unexplained tracked artifact, public function stub, broken local
Markdown target or unresolved original audit finding was identified after these
corrections. This is a bounded repository engineering review, not proof of every
possible program behavior or independent cryptographic/security certification.
PR 55's merge completes acceptance of this review. Production operation,
independent witness administration, physical power-loss tests, broader research
and manuscript licensing/deposit remain explicitly separate decisions.
