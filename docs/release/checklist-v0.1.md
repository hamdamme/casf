# Release checklist, 0.1.0.dev0 candidate

Section 26 gates with evidence. Each row is pass or explicitly
marked blocked; blocked rows name the owner action. Publication is
a separate deliberate maintainer action (SPEC §25).

| Gate (SPEC §26) | Status | Evidence |
| --- | --- | --- |
| Original source disposition complete | pass | ROADMAP.md phase 0; docs/adr/ |
| All requirements linked to evidence | pass | tests/unit/test_traceability.py enforces R01 to R12 and T01 to T22 in CI |
| No unresolved blocking security findings | pass | detection matrix benchmarks/results/detection-v1/; advisory review row below |
| Reproducible install | pass | wheel and sdist built from commit; fresh venv install; CLI roundtrip ends in verify PASS (rehearsal log in this file) |
| Offline verification without secrets | pass | rehearsal verify ran integrity mode with public keys only; tests/unit/test_verifier.py (R03) |
| Witness recovery and fork tests | pass | tests/unit/test_witness.py and test_witness_http.py (T08, T09, T22) |
| Key rotation drill | pass | tests/unit/test_lifecycle.py (T14) |
| Undetectable cases documented | pass | research/limitations.md; benchmarks/results/detection-v1/report.md |
| Dependency advisory review | pass | pip-audit: runtime dependency cryptography clean; advisories found only for the pip tool itself inside the development venv, not shipped |
| License and contact checks | pass | LICENSE Apache 2.0; SECURITY.md; GitHub private vulnerability reporting enabled on the repository |
| Research results separated from guarantees | pass | research/protocol.md and research/limitations.md; notes-v0.1.md "not claimed" section |
| Package contents free of keys and data | pass | wheel and sdist inspected: casf package, license, and metadata only |
| Full benchmark matrix with network delay injection | blocked | planned on the Linux runner before M8 closes; local subset is the smoke reference |
| Disclosure channel test submission | blocked | channel enabled; the test report itself is a maintainer action to avoid fabricated evidence |
| External review of protocol and design | blocked | sought, not yet received; not claimed anywhere |
| Maintainer approval of artifact hashes and notes | blocked | final maintainer action at actual release time |

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
