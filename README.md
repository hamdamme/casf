# CASF

**Cryptographic Audit and Signing Framework**

[![CI](https://github.com/hamdamme/casf/actions/workflows/ci.yml/badge.svg)](https://github.com/hamdamme/casf/actions/workflows/ci.yml)
rc3 archive: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24321232.svg)](https://doi.org/10.5281/zenodo.24321232)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

CASF is an experimental Python framework for creating cryptographically verifiable audit records. It combines Ed25519 signatures, SHA-256 hash chaining, canonical JSON based on RFC 8785, and an independent witness that retains authenticated checkpoints. The goal is to help applications produce evidence of record integrity and detect certain changes or rollbacks when a verifier has independently retained witness state.

**CASF does not guarantee that every event was recorded or that the events described in a signed record are true.**

## Project status

- **Latest published release:** [0.1.0rc4 experimental prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc4).
- **Release evidence:** [Public downloads and fresh installation checks](docs/release/0.1.0rc4/publication-0.1.0rc4.md).
- **Maturity:** Experimental; not independently audited or production ready. [Detailed status](docs/release/README.md#project-status-and-release-history).

rc4 includes the security, key-file and package corrections described in the
[release notes](docs/release/0.1.0rc4/notes-0.1.0rc4.md).

## Where to go next

| Reader | Start here |
| --- | --- |
| Evaluate the design | [Specification](docs/specification/CASF_SPEC_001.md), [ADRs](docs/adr/), [limitations](research/limitations.md), [research evidence](research/README.md) |
| Use CASF | [Installation](docs/guide/installation.md), [synthetic demo](docs/guide/demo.md), [verification](docs/guide/verification.md) |
| Operate CASF | [Administration](docs/operations/administration.md), [witness server](docs/operations/witness-server.md), [recovery](docs/operations/writer-recovery.md) |
| Contribute | [Development](DEVELOPMENT.md), [contribution guide](CONTRIBUTING.md) |

See the [documentation index](docs/README.md) for API references and testing guides,
and the [release records](docs/release/README.md) for revision-specific evidence.

## Capabilities

- **Signed records:** Bind each record to its log, sequence, predecessor, and signing key using Ed25519 and SHA-256.
- **Durable writer:** Verify trust, retained authority status and fresh witness history before signing; store records transactionally with idempotent retries.
- **Independent witness:** Accept validated chain extensions and retain signed checkpoint receipts in separate state.
- **Checkpoint worker:** Schedule bounded checkpoints and durable retries through a [verified foreground worker](docs/reference/checkpoint-worker.md).
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
.venv-tools/bin/uv sync --locked --no-editable --extra witness --extra dev --group build --python python3
PYTHONPATH=src .venv/bin/casf --help
PYTHONPATH=src .venv/bin/python -m pytest tests/
```

This checks out the development source and runs its tests. It is **not** a production deployment guide. For implemented behavior and specification differences, start with the [current implementation reference](docs/reference/current-reference.md). The [project specification](docs/specification/CASF_SPEC_001.md) defines the intended protocol requirements. The [historical archive](docs/historical/README.md) preserves the original Word document and prototype manuals; their examples are not current instructions.

For user installation and verification instructions, see the [installation and usage guide](docs/guide/installation.md). CASF is not published to a package index; use the GitHub release artifacts.

For a complete local walkthrough, run the [verified synthetic demo](docs/guide/demo.md).
It provisions temporary keys and a loopback witness, verifies exported evidence,
rejects tampering, and exercises backup, restore and sealing. It needs no cloud
server and keeps only public synthetic output.

The committed `uv.lock` records exact dependency versions for development and
new experiments. See the [dependency guide](docs/reference/dependencies.md) for checks,
package builds, and deliberate dependency updates. Existing research results
retain the environments recorded when they were produced. The optional
witness server uses Uvicorn; see the [server guide](docs/operations/witness-server.md)
for installation, resource limits, and deployment requirements.

## How verification works

1. The writer receives an event and creates a signed, sequential record.
2. A checkpoint summarizes an authenticated prefix of the log.
3. A separately operated witness validates the extension and retains a signed receipt.
4. A verifier examines an evidence bundle and, depending on its mode, trusted checkpoint state or a fresh witness response.

These are different assurances. A valid local signature chain alone cannot prove that an older valid snapshot is current.

## Repository organization

| Path | Purpose |
| --- | --- |
| `src/casf/` | Current package implementation |
| `examples/` | Runnable synthetic workflows using the current public interfaces |
| `tests/` | Unit and conformance tests and other validation |
| `vectors/v1/` | Canonical encoding and cryptographic test vectors |
| `benchmarks/` | Experiment runners, manifests, results, and reports |
| `research/` | Current research guide, historical protocol, study methods and preprint |
| `docs/specification/` | Governing specification draft |
| `docs/adr/` | Recorded architectural decisions |
| `docs/historical/` | Archived original Word document and prototype index |
| `docs/historical/01-*.md` through `docs/historical/05-*.md` | Earlier design documents, not the governing protocol |

The active implementation is under `src/casf/`. The earlier prototype remains accessible in the repository's Git history.

## Evaluation evidence

The [current local follow-up](research/current-evidence-2026-11-10.md) identifies its measurement revision and limits. Earlier [detection](benchmarks/results/detection-v1/report.md), [local](benchmarks/results/local-subset-v1/report.md), [Linux](benchmarks/results/linux-matrix-v2/report.md), and [wide area](benchmarks/results/wide-area-v3/report.md) results remain historical. Their recorded configurations, hardware, and assumptions matter; individual observations are not performance guarantees.

See [research limitations](research/limitations.md) for cases that verification cannot detect and for limits on generalizing the results.

## Security boundaries

CASF produces integrity evidence, not proof of event completeness or confidentiality. A compromised authorized writer can sign false events. An unwitnessed suffix remains exposed to loss, and rollback detection depends on retained trusted state, connectivity, and the assumptions defined in the specification.

Do not describe CASF as tamper proof, formally verified, independently audited, or compliant with a regulatory framework without separate evidence. Report suspected vulnerabilities using the [security policy](SECURITY.md), not a public issue containing sensitive details.

## License

The software is licensed under the [Apache License 2.0](LICENSE). The
[research manuscript](research/preprint/README.md) has a separate publication
license decision pending; no manuscript deposit or DOI is claimed.

## Citation

If you use CASF in research, cite the software version you used:

> Aynazarov, H. (2026). CASF: Cryptographic Audit and Signing Framework (0.1.0rc4)
> (Version 0.1.0rc4) [Computer software]. GitHub.
> [Published release](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc4).

Machine-readable citation metadata is available in [CITATION.cff](CITATION.cff).
The rc4 Zenodo archive and DOI are **Pending**. The historical
[rc3 software DOI](https://doi.org/10.5281/zenodo.24321232) identifies rc3 only,
not rc4, the separate research manuscript or later changes on `main`.
