# Phase 3 release gate evidence

Review date: 2026-10-28. This record updates the release evidence after PR 20.
The maintainer accepts the historical benchmark scope and the limited
external review for the first experimental release. This does not authorize
publication.

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

Maintainer decision: accepted for the first experimental release. The areas
not examined and system limits above remain explicit release limitations. No
additional review is expected.

## Research evidence boundary

The recorded Linux and wide area benchmark results remain attached to their
original code revisions, machines, workloads, and network path. They are
historical research evidence only. They do not measure the final release
candidate. No historical benchmark was rerun for this closeout.

Maintainer decision: accepted. Keep those results as historical research
evidence and make no performance claim about the release candidate.

## Candidate specific evidence

Candidate version: `0.1.0rc1`, rebuilt from source commit
`9189cb2627aeb9f2436e751fe320b73a3ba91079` with Build 1.6.1 and Setuptools
84.2.1. The application source and project version metadata are unchanged
from candidate source `21619f0`; this final rebuild packages the corrected
public README version. Its package metadata and installed `casf.__version__`
match.

| Check | Result and evidence |
| --- | --- |
| Build | Wheel and source archive built from the committed source above on macOS 15.6.1 arm64, CPython 3.12.11, with Build 1.6.1 and Setuptools 84.2.1. |
| Clean install | The exact wheel was installed in a new CPython 3.12.11 environment with the `witness` extra. `pip check` found no broken requirements; installed `casf.__version__` is `0.1.0rc1`. |
| Exact artifact CLI smoke | The exact installed wheel's `casf --help` and `casf verify --help` passed; help shows mandatory `--state`, first use `--initialize-state`, and integrity, anchored, and online modes. The exact installed witness extra passed a loopback request and clean shutdown. A separate temporary synthetic public bundle passed installed package verification through record 2. This is software smoke evidence, not research data or the separate real file demonstration. |
| Full CLI mode rehearsal | The complete synthetic integrity, anchored, and online command line rehearsal passed on the earlier `21619f0` candidate. Application source and `pyproject.toml` have not changed since that source revision. Each mode passed first with `--initialize-state` and again with the same `--state` file without initialization. The exact rebuilt artifact received the clean install and smoke checks above. |
| Package and license inspection | Wheel has 29 files; source archive has 34. Both declare Apache-2.0 and include LICENSE bytes matching the repository. Neither contains backup, research, RQ2, database, or key paths, nor private key blocks. The wheel bundles no third party dependencies. Installed cryptography, cffi, pycparser, Uvicorn, Click, and h11 distributions each include license files; cryptography includes Apache and BSD license files. |
| Dependency advisories | The exact version query for 24 locked packages plus uv 0.13.5 completed on 2026-10-28. OSV and PyPI returned no listed advisories. See [the saved query result](dependency-review-2026-10-28.json). Refresh immediately before publication. |
| PR 20 validation | PR 20 merged as `26cbb0c`. Its [CI run](https://github.com/hamdamme/casf/actions/runs/40724739683) completed successfully: three locked dependency jobs and three minimum dependency jobs for Python 3.12, 3.13, and 3.14. |

Artifact SHA 256 values:

| Artifact | SHA 256 |
| --- | --- |
| `casf-0.1.0rc1-py3-none-any.whl` | `bf129d37ddaeec6ec8c5cd543566f60570b016a050663b90e3c26bd59e7e3132` |
| `casf-0.1.0rc1.tar.gz` | `22bb94b2137c497565c30d5b992bc71e6dc2d089f3ef4eb91490bdfc44d83cc6` |

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

The [PR 21 CI run](https://github.com/hamdamme/casf/actions/runs/40740660886)
passed all six locked and minimum dependency jobs. It ran on Ubuntu 24.04.5
x86_64 and reported the same component
versions on CPython 3.12.15, 3.13.17, and 3.14.9: SQLite 3.45.1, Python TLS
OpenSSL 3.0.13, cryptography 50.0.2 with bundled OpenSSL 4.0.3, and cffi
2.1.1. The runner image inventory also reports OpenSSL
3.0.13-0ubuntu3.16 ([runner inventory](https://github.com/actions/runner-images/blob/ubuntu24/20261012.334/images/ubuntu/Ubuntu2404-Readme.md)).
The runtime inventory passed on all three versions. The package wheel is pure
Python; cryptography and cffi supply the native components externally and are
not bundled in the CASF wheel.

The platform assessment covers the stated macOS arm64 and Ubuntu 24.04 x86_64
validation scope with CPython 3.12 through 3.14. It does not certify other
Linux images, Windows, or other processor types.

## Current decisions for the six remaining gates

| Gate | Status | Evidence and remaining maintainer decision |
| --- | --- | --- |
| Requirements evidence and historical scope | PASS | T01 through T22 have mapped assertions; the focused traceability check passed, including PR 20 under T12. The maintainer accepts the historical Linux and wide area results as research evidence only, not candidate measurements. |
| Security findings | PASS | All assessed findings have a code, test, or documented limit disposition above. No actionable security fix is currently identified. CASF does not claim a formal security audit. |
| Platform and native component review | PASS | macOS candidate components and the Ubuntu runtime versions from PR 21 are recorded above. The locked tests and runtime inventory passed for CPython 3.12, 3.13, and 3.14. No component issue was identified within the stated validation scope. |
| License and reporting channel | PASS | Candidate license metadata and bytes match Apache-2.0; external runtime package license files were present; no third party dependencies are bundled. A real private report established delivery. No specific unresolved license or contact issue was found. |
| External protocol review | PASS | The maintainer accepts the recorded limited review for the first experimental release. The areas not examined and system limits remain explicit above. No further external review is expected. |
| Artifact and notes approval | BLOCKED | The version, notes, artifacts, and hashes are recorded above. Maintainer approval is needed for this exact candidate. Publishing requires a separate explicit approval and has not occurred. |

Phase 3 remains open only for final candidate artifact and notes approval.
The historical benchmark scope and limited external review are accepted as
stated above. Publishing remains a separate action and has not occurred.
