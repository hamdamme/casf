# Release checklist, 0.1.0.dev0 candidate

Section 26 gates with evidence. Each row is pass or explicitly
marked blocked; blocked rows name the remaining action. Publication is
a separate deliberate maintainer action (SPEC §25).

Status reviewed on 2026-10-24. Benchmark completion below refers to the
recorded configurations and original experiment commits. It does not imply
that every proposed experiment or release requirement is complete.

| Gate (SPEC §26) | Status | Evidence |
| --- | --- | --- |
| Original source disposition complete | pass | docs/adr/; CHANGELOG.md session history |
| All requirements linked to evidence | blocked | The [Session 3 review](session3-validation.md) adds scenario tests and package rehearsals. Historical benchmark scope, memory scaling, external review, and final evidence acceptance remain open; structural mapping checks do not establish complete coverage. |
| No unresolved blocking security findings | blocked | The Uvicorn replacement was merged in PR 7. Complete the remaining platform, dependency, and release reviews recorded under [D05](../adr/ADR-001-through-004-baseline-decisions.md); passing tests alone do not close this gate. |
| Reproducible install | pass | wheel and sdist built from commit; fresh venv install; CLI roundtrip ends in verify PASS (rehearsal log in this file) |
| Offline verification without secrets | pass | rehearsal verify ran integrity mode with public keys only; tests/unit/test_verifier.py (R03) |
| Witness recovery and fork tests | pass | tests/unit/test_witness.py and test_witness_http.py (T08, T09, T22) |
| Key rotation drill | pass | tests/unit/test_lifecycle.py (T14) |
| Undetectable cases documented | pass | research/limitations.md; benchmarks/results/detection-v1/report.md |
| Locked Python package advisory review | pass | [Review](dependency-review.md) covers all 24 external locked packages and uv 0.13.5. OSV and PyPI returned no listed advisories for these exact versions on 2026-10-24; repeat before publication. |
| Platform and bundled component review | blocked | Review the release platform Python, SQLite, TLS, and bundled native components; Python package queries do not cover the complete deployment. |
| Minimum dependency compatibility | blocked | A separate minimum dependency matrix is implemented for Python 3.12, 3.13, and 3.14. PR 9 GitHub CI passed the new matrix. Session 3 runtime changes still require their own GitHub validation; see [Session 3](session3-validation.md). |
| License and contact checks | blocked | Apache 2.0 metadata is corrected and the [license inventory](dependency-review.md) is recorded. Final redistribution notice review and a real private reporting channel test remain. |
| Research results separated from guarantees | pass | research/protocol.md and research/limitations.md; notes-v0.1.md "not claimed" section |
| Package contents free of keys and data | pass | Fresh wheel and source archive inspected after the metadata correction; no backups, research results, databases, private key files, or PEM private key blocks found. See the [review](dependency-review.md). |
| Recorded Linux benchmark matrix with network delay injection | pass | [Report](../../benchmarks/results/linux-matrix-v2/report.md) and 40 raw run files cover the four configurations in [manifest.v2.json](../../benchmarks/manifest.v2.json), including the 25 ms delay case. |
| Recorded wide area benchmark matrix | pass | [Report](../../benchmarks/results/wide-area-v3/report.md) and 20 raw run files cover two batch sizes on one network path; writer geography is not recorded. |
| Disclosure channel test submission | blocked | channel enabled; the test report itself is a maintainer action to avoid fabricated evidence |
| External review of protocol and design | blocked | sought, not yet received; not claimed anywhere |
| Maintainer approval of artifact hashes and notes | blocked | final maintainer action at actual release time |

## Current validation evidence

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
