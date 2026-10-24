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
| All requirements linked to evidence | pass | tests/unit/test_traceability.py enforces R01 to R12 and T01 to T22 in CI |
| No unresolved blocking security findings | blocked | Review and accept the Uvicorn replacement recorded under [D05](../adr/ADR-001-through-004-baseline-decisions.md) and complete the current dependency review before release approval. |
| Reproducible install | pass | wheel and sdist built from commit; fresh venv install; CLI roundtrip ends in verify PASS (rehearsal log in this file) |
| Offline verification without secrets | pass | rehearsal verify ran integrity mode with public keys only; tests/unit/test_verifier.py (R03) |
| Witness recovery and fork tests | pass | tests/unit/test_witness.py and test_witness_http.py (T08, T09, T22) |
| Key rotation drill | pass | tests/unit/test_lifecycle.py (T14) |
| Undetectable cases documented | pass | research/limitations.md; benchmarks/results/detection-v1/report.md |
| Dependency advisory review | blocked | The earlier candidate recorded a runtime advisory check. Review the current versions in [uv.lock](../../uv.lock); the earlier result does not establish their current advisory status. |
| License and contact checks | pass | LICENSE Apache 2.0; SECURITY.md; GitHub private vulnerability reporting enabled on the repository |
| Research results separated from guarantees | pass | research/protocol.md and research/limitations.md; notes-v0.1.md "not claimed" section |
| Package contents free of keys and data | pass | wheel and sdist inspected: casf package, license, and metadata only |
| Recorded Linux benchmark matrix with network delay injection | pass | [Report](../../benchmarks/results/linux-matrix-v2/report.md) and 40 raw run files cover the four configurations in [manifest.v2.json](../../benchmarks/manifest.v2.json), including the 25 ms delay case. |
| Recorded wide area benchmark matrix | pass | [Report](../../benchmarks/results/wide-area-v3/report.md) and 20 raw run files cover two batch sizes on one network path; writer geography is not recorded. |
| Disclosure channel test submission | blocked | channel enabled; the test report itself is a maintainer action to avoid fabricated evidence |
| External review of protocol and design | blocked | sought, not yet received; not claimed anywhere |
| Maintainer approval of artifact hashes and notes | blocked | final maintainer action at actual release time |

## Current validation evidence

The dependency update in commit `b96fa4a` passed 213 tests on each of Python
3.12, 3.13, and 3.14 on macOS. [PR 4 CI](https://github.com/hamdamme/casf/actions/runs/40066783179)
also passed all three versions on Linux, including lint, typing, tests,
package builds, and installation of the built wheel in a fresh environment.
The wheel checks covered package import and CLI startup. The full CLI
rehearsal below is the separate historical record from 2026-10-12.

These checks support the reviewed code state. Final release artifacts and
hashes still require approval. The build reports a license metadata
deprecation warning that remains to be addressed.

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
