# Phase 3 release gate evidence

Review date: 2026-10-28. This record updates the release evidence after PR 20.
It does not authorize publication. A proposed acceptance remains a maintainer
decision wherever stated below.

## Reviewer findings and disposition

| Finding | Evidence and disposition |
| --- | --- |
| A command line verifier could miss a rollback between runs. | Fixed by retaining verified checkpoint state. Tests cover state rollback, invalid state, and failure to advance state: `tests/unit/test_cli_state.py`. See [verification guidance](../verification.md#remembered-verifier-state). |
| An unsigned `NO_CHECKPOINT` response could be mistaken for proof of rollback. | Fixed: unsigned responses yield an inconclusive result and cannot advance state. Tests: `tests/unit/test_online_errors.py::test_unsigned_no_checkpoint_is_inconclusive_in_library_and_cli` and `tests/unit/test_cli_state.py::test_inconclusive_query_cannot_advance_state`. |
| HTTPS trust or redirect handling could expose a token or accept a downgraded connection. | Fixed: certificate and name checks are enforced, tokens are not sent to plain HTTP, and plain HTTP redirects are rejected. Tests: `tests/unit/test_online_transport.py::test_https_rejects_untrusted_certificate`, `test_https_rejects_hostname_mismatch`, `test_https_never_sends_token_to_plain_http`, and `test_https_does_not_follow_plain_http_redirect`. |
| Provisioned witness identity could differ from the identity in the signed manifest. | Fixed in PR 20. `tests/unit/test_cli.py::test_verify_mismatched_provisioned_witness_id_exit_3` checks the diagnostic, exit code, and absence of new verifier state. All six PR 20 checks passed. |
| A supplied checkpoint might not be trusted. | The verifier checks checkpoint signatures and pins the witness identity. Related assertions are in `tests/unit/test_verifier.py`; installed integrity, anchored, and online flows are recorded in the [fresh wheel rehearsal](install-rehearsal-2026-10-27.md). |
| A witness may sign conflicting views but retain only its current state. | The verifier reports `WITNESS_STATE_CONFLICT`; the witness does not retain both signed envelopes as a separate proof. The verifier test is `tests/unit/test_release_gaps.py::test_signed_witness_equivocation_retained_and_isolated_clients`. Operators who need third party proof must preserve submitted envelopes. This is a documented system limit, not a resolved ability to retain both views. |
| Missing or mismatched receipts and malformed witness status must not produce a pass. | Strict rejection and unknown trust behavior are documented in [verification guidance](../verification.md#unsigned-online-errors) and covered by verifier, online error, and release gap tests. |

Other stated limits remain: an unwitnessed tail may be lost; a stolen writer
key can sign a false suffix; and a verifier without a separately retained pin
cannot detect every witness rollback. These are documented protocol limits.
No formal security audit or proof is claimed. No actionable security fix is
currently identified from the findings assessed here.

## Review coverage

The received external review examined the witness and online tracks in depth
and examined part of the verifier. It did not review bundle resource limits,
all test assertions, canonical JSON and cryptographic vectors, schemas, server
hardening, lifecycle and sealing, benchmark methods, or the technical Word
document. No further review submission is expected. This is limited external
feedback, not a full audit.

Proposed maintainer decision: accept this limited review coverage for the first
experimental release, while retaining the unreviewed areas and system limits
above as explicit limitations. Gate status stays blocked until the maintainer
accepts or rejects this proposal.

## Research evidence boundary

The recorded Linux and wide area benchmark results remain attached to their
original code revisions, machines, workloads, and network path. They are
historical research evidence only. They do not measure the final release
candidate. No historical benchmark was rerun for this closeout.

Proposed maintainer decision: keep those results as historical research
evidence and make no performance claim about the release candidate. Gate
status stays blocked until the maintainer accepts or rejects this proposal.

## Candidate specific evidence

Candidate version: `0.1.0rc1`, built from source commit
`21619f0d115e29d758d458f5661598d9934c3f72`. Its metadata and installed
`casf.__version__` match. The first build was discarded after it exposed a
stale module version; the corrected build below was rebuilt from the commit
and installed into a fresh environment.

| Check | Result and evidence |
| --- | --- |
| Build | Wheel and source archive built with locked Setuptools 84.2.1 on macOS 15.6.1 arm64, CPython 3.12.11, using uv 0.13.5. |
| Clean install | The exact wheel was installed in a new CPython 3.12.11 environment with cryptography 50.0.2 and the witness dependencies. `uv pip check` reported all seven installed packages compatible. |
| CLI rehearsal | The installed wheel generated temporary keys, initialized a log, appended a synthetic record, created a checkpoint, submitted it to a loopback witness, exported a bundle, and verified integrity, anchored, and online modes. Each mode passed twice: once with `--initialize-state` and once using the same `--state` file without initialization. Evidence is explicitly synthetic smoke evidence, not research data. |
| Package and license inspection | Wheel has 29 files; source archive has 34. Both declare Apache-2.0 and include LICENSE bytes matching the repository. Neither contains backup, research, RQ2, database, or key paths, nor private key blocks. The wheel bundles no third party dependencies. Installed cryptography, cffi, pycparser, Uvicorn, Click, and h11 distributions each include license files; cryptography includes Apache and BSD license files. |
| Dependency advisories | The exact version query for 24 locked packages plus uv 0.13.5 completed on 2026-10-28. OSV and PyPI returned no listed advisories. See [the saved query result](dependency-review-2026-10-28.json). Refresh immediately before publication. |
| PR 20 validation | PR 20 merged as `26cbb0c`. Its [CI run](https://github.com/hamdamme/casf/actions/runs/40724739683) completed successfully: three locked dependency jobs and three minimum dependency jobs for Python 3.12, 3.13, and 3.14. |

Artifact SHA 256 values:

| Artifact | SHA 256 |
| --- | --- |
| `casf-0.1.0rc1-py3-none-any.whl` | `3152c009433ebdc3b2ee5c4477bb5e586e8d9100bc63f48b3480d49e4f0de2e1` |
| `casf-0.1.0rc1.tar.gz` | `b94211a6578b023054593a6714a11467247fd0b3ac442d2e9a7668387d8cd40e` |

## Validated platform and component scope

CASF's documented release validation scope is macOS arm64 and Ubuntu 24.04
x86_64, with CPython 3.12 through 3.14. Other systems and processor types
are not claimed as validated release targets.

The corrected candidate was installed and exercised on macOS 15.6.1 arm64
with CPython 3.12.11. Its active runtime reported SQLite 3.54.0 and Python
TLS OpenSSL 3.6.0. Cryptography 50.0.2 uses bundled OpenSSL 4.0.3 in its
native Rust extension; `otool` showed only macOS `libiconv` and `libSystem`
dependencies for that extension. The cffi native extension uses system
`libffi` and `libSystem`. Uvicorn, h11, and pycparser are Python code.

PR 20's successful CI ran on Ubuntu 24.04.5 x86_64 with CPython 3.12.15,
3.13.17, and 3.14.9. The pinned runner image inventory lists OpenSSL
3.0.13-0ubuntu3.16 and SQLite 3.45.1 ([runner inventory](https://github.com/actions/runner-images/blob/ubuntu24/20261012.334/images/ubuntu/Ubuntu2404-Readme.md)). CI built and installed the package and
ran the suite for each Python version, with locked and minimum dependency
jobs. The package wheel is pure Python. Cryptography and cffi are external
locked packages, not files bundled in the CASF wheel. This scopes the release
claim to environments with supported wheels and operating system libraries;
it does not certify other Linux images or architectures.

The original PR 20 logs did not print Python's loaded SQLite and TLS versions.
The current pull request adds a small CI inventory line for platform, Python,
SQLite, Python TLS, cryptography OpenSSL, and cffi versions. Until that line
has passed on Ubuntu and its output is reviewed, the platform gate remains
blocked. The macOS component review above is complete.

## Current decisions for the six remaining gates

| Gate | Status | Evidence and remaining maintainer decision |
| --- | --- | --- |
| Requirements evidence and historical scope | BLOCKED | T01 through T22 have mapped assertions; the focused traceability check passed, including PR 20 under T12. The historical Linux and wide area results are clearly labeled as historical and not candidate measurements. Maintainer approval is needed to accept that scope without rerunning the experiments. |
| Security findings | PASS | All assessed findings have a code, test, or documented limit disposition above. No actionable security fix is currently identified. CASF does not claim a formal security audit. |
| Platform and native component review | BLOCKED | macOS candidate components are recorded above. The current pull request must pass and report the Ubuntu runtime component inventory, then the values must be checked. No runtime component issue is currently identified. |
| License and reporting channel | PASS | Candidate license metadata and bytes match Apache-2.0; external runtime package license files were present; no third party dependencies are bundled. A real private report established delivery. No specific unresolved license or contact issue was found. |
| External protocol review | BLOCKED | The review scope and omitted areas are recorded above. Maintainer approval is needed to accept this limited review for the experimental release. No further external review is expected. |
| Artifact and notes approval | BLOCKED | The version, notes, artifacts, and hashes are recorded above. Maintainer approval is needed for this exact candidate. Publishing requires a separate explicit approval and has not occurred. |

Phase 3 is not ready to close until the Ubuntu runtime inventory is checked,
the maintainer decides whether to accept the historical benchmark scope and
limited external review, and approves or rejects the exact candidate artifacts
and notes. The release remains unpublished.
