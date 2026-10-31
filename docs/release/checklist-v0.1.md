# Release checklist, 0.1.0rc1 experimental candidate

Section 26 gates with evidence. Each row is pass or explicitly
marked blocked; blocked rows name the remaining action. Publication is
a separate deliberate maintainer action (SPEC §25).

Status reviewed on 2026-10-28. Benchmark completion below refers to the
recorded configurations and original experiment commits. It does not imply
that every proposed experiment or release requirement is complete.

| Gate (SPEC §26) | Status | Evidence |
| --- | --- | --- |
| Original source disposition complete | pass | docs/adr/; CHANGELOG.md session history |
| All requirements linked to evidence | pass | The [traceability check](requirement-evidence.md) passed after updating the T12 witness identity test. The maintainer accepts historical benchmarks as research evidence only; they are not measurements of this candidate. See the [Phase 3 closeout record](phase3-closeout-2026-10-28.md). |
| No unresolved blocking security findings | pass | Disposition of all assessed reviewer findings is in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md). No actionable security fix remains identified; system limits and limited review coverage remain explicit. |
| Reproducible install | pass | The exact rebuilt `0.1.0rc1` wheel installed in a clean Python 3.12.11 environment and passed dependency checks, CLI help, witness smoke, and synthetic public evidence verification. Full integrity, anchored, and online CLI rehearsal passed on unchanged candidate application code. Exact artifact hashes are in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md). |
| Offline verification without secrets | pass | rehearsal verify ran integrity mode with public keys only; tests/unit/test_verifier.py (R03) |
| Witness recovery and fork tests | pass | tests/unit/test_witness.py and test_witness_http.py (T08, T09, T22) |
| Key rotation drill | pass | tests/unit/test_lifecycle.py (T14) |
| Undetectable cases documented | pass | research/limitations.md; benchmarks/results/detection-v1/report.md |
| Locked Python package advisory review | pass | The [2026-10-28 refresh](dependency-review-2026-10-28.json) queried all 24 locked external packages and uv 0.13.5 at exact versions. OSV and PyPI reported no listed advisories. Refresh again before publication. |
| Platform and bundled component review | pass | macOS candidate components and Ubuntu runtime values for CPython 3.12, 3.13, and 3.14 are recorded in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md). The locked test jobs and runtime inventory passed within the stated scope. |
| Minimum dependency compatibility | pass | All six [PR 21 GitHub jobs](https://github.com/hamdamme/casf/actions/runs/40740660886) passed across Python 3.12, 3.13, and 3.14, covering locked and minimum dependencies for the current candidate. Historical checks are recorded in [Session 3](session3-validation.md). |
| License and contact checks | pass | Both candidate artifacts declare Apache-2.0 and contain the exact repository LICENSE. The wheel contains no bundled third party dependencies; the [dependency review](dependency-review.md) records declared licenses and license files for runtime packages. A real private report established channel delivery. No specific unresolved license or contact issue was found. |
| Research results separated from guarantees | pass | research/protocol.md and research/limitations.md; notes-v0.1.md "not claimed" section |
| Package contents free of keys and data | pass | Candidate wheel and source archive were inspected. Neither contains backup or research paths, RQ2 files, databases, key files, or private key blocks. Both contain the project license. See the [Phase 3 closeout record](phase3-closeout-2026-10-28.md). |
| Recorded Linux benchmark matrix with network delay injection | pass | [Report](../../benchmarks/results/linux-matrix-v2/report.md) and 40 raw run files cover the four configurations in [manifest.v2.json](../../benchmarks/manifest.v2.json), including the 25 ms delay case. |
| Recorded wide area benchmark matrix | pass | [Report](../../benchmarks/results/wide-area-v3/report.md) and 20 raw run files cover two batch sizes on one network path; writer geography is not recorded. |
| Disclosure channel delivery | pass | A real private report was received and inspected. Its findings and dispositions are listed in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md). |
| External review of protocol and design | pass | The maintainer accepts the limited review for the first experimental release. The [Phase 3 closeout record](phase3-closeout-2026-10-28.md) lists what was examined and what was not. No more reviews are expected. |
| Maintainer approval of artifact hashes and notes | pass | On 2026-10-28, the maintainer approved the exact candidate and notes after confirming that both artifact files match the recorded SHA 256 values in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md). Approval to publish remains separate and has not been given. |

The detailed current status of the six Phase 3 gates is in the
[Phase 3 closeout record](phase3-closeout-2026-10-28.md). Historical entries
below are retained as dated evidence; they do not override the current table.
The review candidate's coverage status and outstanding limits are tracked in
the [test coverage record](test-coverage-status.md).

## Candidate status update, 2026-10-31

The 0.1.0rc1 artifact hashes approved on 2026-10-28 identify the exact
artifacts in that approval record. Subsequent repository changes under review
modify parser behavior, network transport, packaging metadata, CLI behavior,
and documentation. The old artifacts remain preserved as historical
evidence, but they do not represent this source tree. A candidate containing
these changes has now been built for review and checked locally. Exact wheel
and source archive hashes, package contents, install checks, lint, typing,
focused and full test outcomes, dependency advisory query, and H3 follow up
are recorded in the [review candidate notes](notes-review-candidate-2026-10-31.md)
and [H3 supplement](../../research/h3-witness-outage-review-2026-10-31.md).
The wheel and source archive passed clean environment installation checks.
The lock check passed with the pinned uv version. All 402 tests passed on the
local macOS Python 3.12 environment; the hosted Python matrix has not yet run
for this branch.

The existing 0.1.0rc1 publication approval does not cover this changed source
or these new artifact hashes. Publication of this candidate is blocked pending
the hosted checks and the maintainer's separate approval of the exact new
hashes and notes. No release has been published.

All six Phase 3 closeout gates are PASS. Phase 3 is closed; publication is
still subject to separate maintainer approval.

## Session 4 review status

This is a dated historical note. The current platform and redistribution
review passed within the scope recorded in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md).

Platform review remains open. The previous local Python 3.12 environment uses
Python 3.12.11 and OpenSSL 3.6.0. A separate validation run with Python 3.12.16
was deferred by the maintainer. The earlier availability check is historical,
not a current claim that this version is unavailable. Confirm the selected
runtime and its bundled components during final platform review. Previous
environments and results are preserved.

License files were inspected for cryptography, CFFI, pycparser, Uvicorn,
Click, and h11. Final redistribution review remains open. The private
reporting channel received a real report. Delivery does not close the security review.

## Current validation evidence

Verification changes at `85067de` passed 322 local tests on macOS with
Python 3.13.17. All six [GitHub validation jobs](https://github.com/hamdamme/casf/actions/runs/40439587582)
passed for that commit across Python 3.12, 3.13, and 3.14 with locked and
minimum dependencies. [PR 12](https://github.com/hamdamme/casf/pull/12)
merged these changes as `1c7b7ee`. This is validation evidence, not release approval.

The changes verify HTTPS connections, report unsigned witness errors as
inconclusive, and retain verified history between command line runs.
Command line verification requires a state file and explicit initialization
for the first observation. See [verification usage](../verification.md).

An initial external technical review informed these fixes. On 2026-10-27,
the reporting reviewer confirmed all three reported issues fixed at `fb9643c`
and reported 354 passing tests. This is reviewer supplied confirmation, not
a new local test run. The maintainer confirmed that no further review
submissions are expected. Assessment of other findings and review coverage
remains open. No formal security audit or proof is claimed.

The confirmation is retained privately in the reporting channel. Its receipt
does not publish the advisory or approve a software release.

The earlier implementation retained records in memory. The streaming
implementation now processes records sequentially with bounded protocol state;
see the [validation record](streaming-validation.md) for measured memory use
and compatibility limits. The eager reader remains available for restore
and existing callers. Other requirements still need final acceptance.

Historical research results remain tied to their original code versions and
environments. They are not measurements of the final release candidate.

## Earlier transport validation

The Uvicorn implementation in commit `6d69563` passed 236 tests on each of
Python 3.12, 3.13, and 3.14 on macOS and local Linux ARM containers, as
recorded in the [transport validation](http-validation.md).
[PR 7 CI](https://github.com/hamdamme/casf/actions/runs/40123118085) was verified
as successful for all three Python jobs, including lint, typing, tests,
builds, and base and witness wheel installation checks. The maintainer merged
PR 7 as `0f48046`. A merge does not approve a public release.

The subsequent license metadata correction passed fresh package builds and
base and witness wheel checks on all three macOS Python versions. The prior
license deprecation warning is absent. The [dependency review](dependency-review.md)
records the scope and remaining limitations. Final artifact hashes and notes
still require approval at release time.

## Earlier dependency validation

The dependency update in commit `b96fa4a` passed 213 tests on each of Python
3.12, 3.13, and 3.14 on macOS. [PR 4 CI](https://github.com/hamdamme/casf/actions/runs/40066783179)
also passed all three versions on Linux, including lint, typing, tests,
package builds, and installation of the built wheel in a fresh environment.
The wheel checks covered package import and CLI startup. The full CLI
rehearsal below is the separate historical record from 2026-10-12.

Those checks support that earlier code state. Its license metadata warning
was subsequently addressed as recorded above. The historical CLI rehearsal
below remains unchanged and is not a new rehearsal of the current candidate.

## Clean install rehearsal log

The following command log is historical from 2026-10-12 and describes the
earlier `0.1.0.dev0` build. Its verification example predates required CLI
state retention. Use the current `--state` examples in the [installation and
usage guide](../installation.md) and the [verification guide](../verification.md).

Commands (run 2026-10-12, macOS, Python 3.12):

```
python -m build                       # wheel + sdist from this commit
python3 -m venv /tmp/casf-rehearsal   # fresh environment
pip install dist/casf-0.1.0.dev0-py3-none-any.whl
casf key generate --role authority --out auth.pem --passphrase-env ...
casf key generate --role log --out log.pem --passphrase-env ...
casf key generate --role witness --out wit.pem --passphrase-env ...
casf init --manifest manifest.json --db w.db --key log.pem ...
casf append --db w.db --key log.pem ... --event event.json
casf export --db w.db --key log.pem ... --out bundle
casf verify bundle --trust trust.json --mode integrity
```

Result: `mode: integrity  result: PASS`, exit code 0. The manifest
and trust files were built with the installed library API only.


## Streaming verification evidence

The [streaming validation record](streaming-validation.md) tracks the current
implementation and measurements for the memory requirement in Sections 5,
15, and 20. The CLI streams records, and the verifier retains only bounded
checkpoint boundary digests. Protocol evidence remains subject to explicit
budgets. The eager reader remains available for compatibility and restore.
Streaming evidence does not close external review, platform, redistribution,
or final release approval.
