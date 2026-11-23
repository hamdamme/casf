# CASF

**Cryptographic Audit and Signing Framework**

[![CI](https://github.com/hamdamme/casf/actions/workflows/ci.yml/badge.svg)](https://github.com/hamdamme/casf/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24321232.svg)](https://doi.org/10.5281/zenodo.24321232)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

CASF is an experimental Python framework for creating cryptographically verifiable audit records. It combines Ed25519 signatures, SHA-256 hash chaining, canonical JSON based on RFC 8785, and an independent witness that retains authenticated checkpoints.

The goal is to help applications produce evidence of record integrity and detect certain changes or rollbacks when a verifier has independently retained witness state. **CASF does not guarantee that every event was recorded or that the events described in a signed record are true.**

## Project status

**Latest published release:** [0.1.0rc3 experimental prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc3) · **Protocol:** proposed `casf-v1` profile

The repository includes an implemented Python library, command line interface, SQLite writer, reference HTTP witness, evidence export and verification, automated tests, and research experiments. CI checks Python 3.12, 3.13, and 3.14.

The protocol specification remains a design review document. The project has not undergone an independent security audit and should not be treated as production ready security infrastructure.

Start with the [operating and maintenance handoff](docs/operating-handoff.md). The
[rc2 publication record](docs/release/publication-0.1.0rc2.md) retains the earlier release
files and download evidence. The [rc3 release](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc3)
provides the current experimental artifacts with [publication and installation evidence](docs/release/publication-0.1.0rc3.md); its source distribution is also
[archived on Zenodo](https://doi.org/10.5281/zenodo.24321232). No PyPI release has been published.

The scoped [tracked-file review](docs/release/line-review-2026-11-11.md) and corrections
were accepted in PR 57 at `e59fd64`; that review does not cover every later change.
Subsequent fixes and the [synthetic transaction demo](docs/synthetic-transactions.md)
were accepted through PR 72 at `40382b1`, whose post-merge CI passed.
The [research-demo closeout](docs/release/research-demo-closeout.md) records the
accepted evidence and operating rules. Published rc2 downloads predate these fixes.
The rc3 experimental release includes these fixes and the synthetic demo.

P03 (whole-machine power-loss testing) is **Pending future validation**. P04
(independent security review) is **Pending independent evaluation**. Both remain
incomplete and relevant to future production-readiness evaluation. Neither blocks
publication of experimental research releases; future releases still require
separate publication approval and artifact validation.

The next candidate is **0.1.0rc4, unpublished**. It includes the corrections from
[PR 78](https://github.com/hamdamme/casf/pull/78) and
[PR 82](https://github.com/hamdamme/casf/pull/82), plus rejection of small-order
Ed25519 keys that permit signature bypasses. Published rc2/rc3 are affected.
The [replacement artifacts from `492f330`](docs/release/candidate-0.1.0rc4-492f330.md)
include PR 84 and passed fresh installation checks. The `3333d00` artifacts remain
superseded and must not be published. Exact-file review and separate publication
approval are pending. See the [rc4 notes](docs/release/notes-0.1.0rc4.md).

## Capabilities

- **Signed records:** Bind each record to its log, sequence, predecessor, and signing key using Ed25519 and SHA-256.
- **Durable writer:** Verify trust, retained authority status and fresh witness history before signing; store records transactionally with idempotent retries.
- **Independent witness:** Accept validated chain extensions and retain signed checkpoint receipts in separate state.
- **Checkpoint worker:** Schedule bounded checkpoints and durable retries through a [verified foreground worker](docs/checkpoint-worker.md).
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

This checks out the development source and runs its tests. It is **not** a production deployment guide. For implemented behavior and specification differences, start with the [current implementation reference](docs/current-reference.md). The [project specification](docs/specification/CASF_SPEC_001.md) defines the intended protocol requirements. The [historical archive](docs/historical/README.md) preserves the original Word document and prototype manuals; their examples are not current instructions.

For user installation and verification instructions, see the [installation and usage guide](docs/installation.md). CASF is not published to a package index; use the GitHub release artifacts.

For a complete local walkthrough, run the [verified synthetic demo](docs/demo.md).
It provisions temporary keys and a loopback witness, verifies exported evidence,
rejects tampering, and exercises backup, restore and sealing. It needs no cloud
server and keeps only public synthetic output.

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
| [Implementation reference](docs/current-reference.md) | Current behavior, API boundaries and differences from the specification |
| [Verification guide](docs/verification.md) | Trust, retained state, diagnostic outcomes and resource budgets |
| [Verifier API](docs/verifier-api.md) | Complete bundle reads and incremental checks from trusted checkpoints |
| [Adversarial testing](docs/adversarial-testing.md) | Generated properties, bounded parser fuzzing, and replaying failures |
| [Install and use CASF](docs/installation.md) | Candidate installation, verification modes, and retained verifier state |
| [Runnable demonstration](docs/demo.md) | Verified CLI workflow, synthetic file fingerprint and expected outcomes |
| [Research guide](research/README.md) | Canonical questions, evidence, outcomes and historical label crosswalk |
| [Research limitations](research/limitations.md) | Detection boundaries and limits of the experiments |
| [Release records index](docs/release/README.md) | Current release work and revision-specific historical evidence |
| [Release checklist](docs/release/checklist-v0.1.md) | Current source checks, artifact status and historical decisions |
| [Contributing](CONTRIBUTING.md) | Contribution expectations |
| [Security policy](SECURITY.md) | Private vulnerability reporting and support scope |

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
| `docs/01-*.md` through `docs/05-*.md` | Earlier design documents, not the governing protocol |

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

If you use CASF in research, cite the archived software version:

> Aynazarov, H. (2026). CASF: Cryptographic Audit and Signing Framework (0.1.0rc3)
> (Version 0.1.0rc3) [Computer software]. Zenodo.
> https://doi.org/10.5281/zenodo.24321232

Machine-readable citation metadata is available in [CITATION.cff](CITATION.cff).
This DOI identifies the rc3 software archive, not the separate research manuscript
or later changes on `main`.
