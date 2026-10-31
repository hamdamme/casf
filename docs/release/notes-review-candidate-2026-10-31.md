# CASF 0.1.0rc1 review candidate notes

These notes describe source changes prepared after the previously approved
0.1.0rc1 wheel and source archive. They are not approval or publication
instructions. The earlier artifacts and their recorded hashes remain
preserved as historical evidence and do not contain these changes.

## Changes under review

- Reject duplicate JSON properties and prohibited numeric forms in CLI,
  witness, writer response, and retained status state inputs.
- Apply a total deadline and response size limit to online verification and
  writer witness submission.
- Require the reference witness to hold a verified active status before it
  accepts checkpoints, and stop new acceptance after a verified revocation.
- Add local commands for signed manifests, verifier trust pins, signed status,
  witness registration, and linked epoch manifests.
- Include the `py.typed` package marker in built distributions.
- Permit export without a private key; append and checkpoint signing still
  require the log key.

The commands and bounds require full regression, lock, build, clean install,
and installed wheel checks before a new candidate can be approved.

## Artifact contents

The wheel contains the installable `casf` package, command entry point,
package metadata, license, and typing marker. The source archive contains the
package source and build metadata, README, license, and typing marker. The
source archive excludes tests, benchmarks, docs, and research. Neither
artifact contains the repository research tree, raw benchmark results, RQ2
experiment files, reviewer material, local databases, or private keys.

## Verification workflow

Every CLI verification command requires `--state PATH`; first use also needs
`--initialize-state`. The exact examples are in
[installation and usage](../installation.md). Manifest, trust, status,
registration, and epoch setup are described in the
[administration guide](../administration.md).

The historical research measurements remain tied to their original code and
environment. The source changes listed here do not retroactively update those
measurements. The bounded network transport changes affect H3 timing; a new
H3 run is recorded separately in
[`research/h3-witness-outage-review-2026-10-31.md`](../../research/h3-witness-outage-review-2026-10-31.md).

## Status

Built for review on macOS 15.6.1 arm64 with Python 3.12.11, setuptools
84.2.1, and the pinned build frontend 1.6.1 from source commit
`0d0d34411f36e088e453c79d5a8bfd19333bbf7c`
(`docs: record H3 review run and release checks`). The exact `uv 0.13.5` lock
check passed. The wheel installed in a clean environment and passed the base
wheel smoke check, CLI administration help, required `--state` help check, and
`py.typed` check. The source archive installed in a clean environment and
passed import, administration command, typing marker, and required state
option checks. The full suite passed 402 tests; the focused security and H3
tests passed 179 tests; Ruff and mypy passed. The OSV advisory check returned
no known vulnerabilities for all 24 exact locked package versions.

| Artifact | SHA 256 | Size |
|---|---|---:|
| `casf-0.1.0rc1-py3-none-any.whl` | `d403d3f5bd58bdca074b31be1d47d08993260e32bf88658a98a31f4ae165b9a2` | 68531 bytes |
| `casf-0.1.0rc1.tar.gz` | `b253a7d6523d3b15b1bbd31a53d35afa4d1a0509450976fd651f2a6afe7f8f64` | 62777 bytes |

These are review candidate artifacts, not the maintainer approved artifacts
from 2026-10-28. The checked runtime and optional witness dependency metadata
shows no actual security or license issue; CASF does not vendor their code.
No release has been published. Release remains blocked on hosted Python
matrix checks for this branch and separate maintainer approval of these exact
hashes and notes.
