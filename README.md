# CASF

**Cryptographic Audit and Signing Framework**

[![CI](https://github.com/hamdamme/casf/actions/workflows/ci.yml/badge.svg)](https://github.com/hamdamme/casf/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

CASF is an experimental Python framework for creating cryptographically verifiable audit records. It combines Ed25519 signatures, SHA-256 hash chaining, canonical JSON based on RFC 8785, and an independent witness that retains authenticated checkpoints.

The goal is to help applications produce evidence of record integrity and detect certain changes or rollbacks when a verifier has independently retained witness state. **CASF does not guarantee that every event was recorded or that the events described in a signed record are true.**

## Project status

**Development version:** `0.1.0.dev0` · **Protocol:** proposed `casf-v1` profile · **Stage:** research and release candidate review

The repository includes an implemented Python library, command line interface, SQLite writer, reference HTTP witness, evidence export and verification, automated tests, and research experiments. CI checks Python 3.12, 3.13, and 3.14.

The protocol specification remains a design review document. The project has not undergone an independent security audit or a public release, and it should not be treated as production ready security infrastructure.

## Capabilities

- **Signed records:** Bind each record to its log, sequence, predecessor, and signing key using Ed25519 and SHA-256.
- **Durable writer:** Store records and append state transactionally in SQLite, with idempotent retries.
- **Independent witness:** Accept validated chain extensions and retain signed checkpoint receipts in separate state.
- **Evidence export:** Export verifiable evidence bundles for examination without the writer's private key.
- **Verification results:** Report `PASS`, `FAIL`, or `INCONCLUSIVE` with separate integrity, anchored, and online modes.
- **Key lifecycle:** Support sealed logs, linked rotation epochs, and revocation status checks.
- **Research tooling:** Run repeatable benchmark workloads and a documented adversarial detection matrix.

## Developer quick start

Requires Python 3.12 or newer and Git.

```bash
git clone https://github.com/hamdamme/casf.git
cd casf
python3 -m venv .venv-tools
.venv-tools/bin/python -m pip install "uv==0.13.5"
.venv-tools/bin/uv sync --locked --extra witness --extra dev --group build --python python3
.venv/bin/casf --help
.venv/bin/python -m pytest tests/
```

This checks out the development source and runs its tests. It is **not** a production deployment guide. For current protocol and verification rules, see the [project specification](docs/specification/CASF_SPEC_001.md). The earlier operation and verification manuals are preserved as historical design context; their examples describe the superseded prototype.

The committed `uv.lock` records exact dependency versions for development and
new experiments. See the [dependency guide](docs/dependencies.md) for checks,
package builds, and deliberate dependency updates. Existing research results
retain the environments recorded when they were produced. The optional
witness server uses Uvicorn; see the [server guide](docs/witness-server.md)
for installation, resource limits, and deployment requirements.

## How verification works

1. The writer receives an event and creates a signed, sequential record.
2. A checkpoint summarizes an authenticated prefix of the log.
3. A separately operated witness validates the extension and retains a signed receipt.
4. A verifier examines an evidence bundle and, depending on its mode, trusted checkpoint state or a fresh witness response.

These are different assurances. A valid local signature chain alone cannot prove that an older valid snapshot is current.

## Documentation

| Resource | Purpose |
| --- | --- |
| [Project specification](docs/specification/CASF_SPEC_001.md) | Threat model, protocol rules, trust assumptions, and requirements |
| [Architecture decisions](docs/adr/ADR-001-through-004-baseline-decisions.md) | Design choices and their rationale |
| [Development guide](DEVELOPMENT.md) | Working rules for implementation and review |
| [Verification manual](docs/05-verification-manual.md) | Historical design background; consult the specification for current rules |
| [Research protocol](research/protocol.md) | Research questions, methods, and reproducibility |
| [Research limitations](research/limitations.md) | Detection boundaries and limits of the experiments |
| [Release checklist](docs/release/checklist-v0.1.md) | Candidate review gates and pending maintainer actions |
| [Contributing](CONTRIBUTING.md) | Contribution expectations |
| [Security policy](SECURITY.md) | Private vulnerability reporting and support scope |

## Repository organization

| Path | Purpose |
| --- | --- |
| `src/casf/` | Current package implementation |
| `tests/` | Unit and conformance tests and other validation |
| `vectors/v1/` | Canonical encoding and cryptographic test vectors |
| `benchmarks/` | Experiment runners, manifests, results, and reports |
| `research/` | Research protocol and documented limitations |
| `docs/specification/` | Governing specification draft |
| `docs/adr/` | Recorded architectural decisions |
| `docs/01-*.md` through `docs/05-*.md` | Earlier design documents, not the governing protocol |

The active implementation is under `src/casf/`. The earlier prototype remains accessible in the repository's Git history.

## Evaluation evidence

The repository includes [an adversarial detection report](benchmarks/results/detection-v1/report.md), [local benchmark reports](benchmarks/results/local-subset-v1/report.md), [Linux benchmark results](benchmarks/results/linux-matrix-v2/report.md), and [wide area experiment results](benchmarks/results/wide-area-v3/report.md). Their recorded configurations, hardware, and assumptions matter; individual observations are not performance guarantees.

See [research limitations](research/limitations.md) for cases that verification cannot detect and for limits on generalizing the results.

## Security boundaries

CASF produces integrity evidence, not proof of event completeness or confidentiality. A compromised authorized writer can sign false events. An unwitnessed suffix remains exposed to loss, and rollback detection depends on retained trusted state, connectivity, and the assumptions defined in the specification.

Do not describe CASF as tamper proof, formally verified, independently audited, or compliant with a regulatory framework without separate evidence. Report suspected vulnerabilities using the [security policy](SECURITY.md), not a public issue containing sensitive details.

## License

Licensed under the [Apache License 2.0](LICENSE).
