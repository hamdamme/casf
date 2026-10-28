# Release checklist, 0.1.0.dev0 candidate

Section 26 gates with evidence. Each row is pass or explicitly
marked blocked; blocked rows name the remaining action. Publication is
a separate deliberate maintainer action (SPEC §25).

Status reviewed on 2026-10-27. Benchmark completion below refers to the
recorded configurations and original experiment commits. It does not imply
that every proposed experiment or release requirement is complete.

| Gate (SPEC §26) | Status | Evidence |
| --- | --- | --- |
| Original source disposition complete | pass | docs/adr/; CHANGELOG.md session history |
| All requirements linked to evidence | blocked | The [Session 3 review](session3-validation.md) adds scenario tests and package rehearsals. Streaming memory evidence is recorded in the [validation record](streaming-validation.md). Historical benchmark scope, external review, and final evidence acceptance remain open; structural mapping checks do not establish complete coverage. |
| No unresolved blocking security findings | blocked | Recent verification fixes are recorded below. The reporting reviewer confirmed the three reported issues fixed at `fb9643c`. Assessment of other findings remains open. Complete the platform, dependency, and release reviews under [D05](../adr/ADR-001-through-004-baseline-decisions.md); passing tests alone do not close this gate. |
| Reproducible install | blocked | Earlier package rehearsals passed and current CI includes package installation checks. The [fresh wheel rehearsal](install-rehearsal-2026-10-27.md) records successful integrity, anchored, and online CLI verification on Python 3.13.17, including key generation, log initialization, append, checkpoint, witness submission, and export. The optional witness extra was not installed in the fresh environment; complete locked dependency installation and final artifact hashes remain open. The historical log below is preserved. |
| Offline verification without secrets | pass | rehearsal verify ran integrity mode with public keys only; tests/unit/test_verifier.py (R03) |
| Witness recovery and fork tests | pass | tests/unit/test_witness.py and test_witness_http.py (T08, T09, T22) |
| Key rotation drill | pass | tests/unit/test_lifecycle.py (T14) |
| Undetectable cases documented | pass | research/limitations.md; benchmarks/results/detection-v1/report.md |
| Locked Python package advisory review | pass | [Review](dependency-review.md) covers all 24 external locked packages and uv 0.13.5. OSV and PyPI returned no listed advisories for these exact versions on 2026-10-24; repeat before publication. |
| Platform and bundled component review | blocked | Review the release platform Python, SQLite, TLS, and bundled native components; Python package queries do not cover the complete deployment. The separate Python 3.12 refresh is pending as recorded below. |
| Minimum dependency compatibility | pass | PR 10 was merged. All six [GitHub validation jobs](https://github.com/hamdamme/casf/actions/runs/40230741913) passed across Python 3.12, 3.13, and 3.14, covering locked and minimum direct dependencies. This completes the pending Session 3 compatibility checks; see [Session 3](session3-validation.md). |
| License and contact checks | blocked | Apache 2.0 metadata is corrected and the [license inventory](dependency-review.md) is recorded. License files were inspected for the six installed runtime packages. Final redistribution review remains open. A real private report was received; this establishes reporting channel delivery, not resolution of its findings. |
| Research results separated from guarantees | pass | research/protocol.md and research/limitations.md; notes-v0.1.md "not claimed" section |
| Package contents free of keys and data | pass | Fresh wheel and source archive inspected after the metadata correction; no backups, research results, databases, private key files, or PEM private key blocks found. See the [review](dependency-review.md). |
| Recorded Linux benchmark matrix with network delay injection | pass | [Report](../../benchmarks/results/linux-matrix-v2/report.md) and 40 raw run files cover the four configurations in [manifest.v2.json](../../benchmarks/manifest.v2.json), including the 25 ms delay case. |
| Recorded wide area benchmark matrix | pass | [Report](../../benchmarks/results/wide-area-v3/report.md) and 20 raw run files cover two batch sizes on one network path; writer geography is not recorded. |
| Disclosure channel delivery | pass | A real private report was received and inspected. Delivery is established by that report rather than a fabricated test submission; the reporting reviewer confirmed the three reported issues fixed at `fb9643c`; other findings remain subject to assessment. |
| External review of protocol and design | blocked | Review submissions are complete according to the maintainer; no further feedback is expected. The reporting reviewer confirmed all three reported issues fixed at `fb9643c` and reported 354 passing tests. Assess the remaining findings and review coverage, resolve blocking issues, and record areas not reviewed before closing this gate. |
| Maintainer approval of artifact hashes and notes | blocked | final maintainer action at actual release time |

## Session 4 review status

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
