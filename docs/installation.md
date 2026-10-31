# Install and use CASF

CASF `0.1.0rc1` was an experimental candidate and has not been published to a
package index. Its previously approved artifacts predate the current source
changes and are no longer a candidate for these changes. A new wheel and
source archive must be built, checked, and separately approved before any
publication. Do not use `pip install casf` until a release is announced.

## Install from a checked candidate wheel

The recorded checks cover CPython 3.12, 3.13, and 3.14 on macOS arm64 through
manual local validation, and those Python versions on GitHub hosted Ubuntu
x86_64 CI runners. The workflow uses `ubuntu-latest`, so it does not pin a
specific Ubuntu point release. macOS is not covered by GitHub Actions. Other
operating systems and processor types have not been validated for this
candidate. These checks describe evidence scope, not a broad compatibility
guarantee.

Download the wheel supplied with the approved release, then create a separate
environment and install that file. Replace the example filename with the
downloaded file name.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ./casf-0.1.0rc1-py3-none-any.whl
.venv/bin/casf --help
```

The wheel includes the witness server code, but does not install its optional
HTTP server dependencies unless the `witness` extra is selected. After the
package is published, install `casf[witness]` to add those dependencies. For
development from a source checkout, the repository's locked setup installs
the witness and development tools:

```bash
git clone https://github.com/hamdamme/casf.git
cd casf
python3 -m venv .venv-tools
.venv-tools/bin/python -m pip install "uv==0.13.5"
.venv-tools/bin/uv sync --locked --extra witness --extra dev --group build --python python3
.venv/bin/casf --help
```

## Verify an evidence bundle

Verification requires trusted public keys, an authority signed status
statement for the bundle's manifest, and a private state file retained by the
verifier. Keep this state separate from the evidence bundle and witness
backup. Never publish or discard it to reset rollback protection.

Create a private directory for state once:

```bash
mkdir -m 700 verifier-state
```

For the first observation of a manifest, initialize the state explicitly.
Choose the mode that matches the evidence and the trust material you have:

```bash
casf verify BUNDLE --trust trust.json --state verifier-state/state.json --initialize-state --mode integrity
```

For later checks, use the same state file and omit `--initialize-state`:

```bash
casf verify BUNDLE --trust trust.json --state verifier-state/state.json --mode integrity
```

Integrity mode checks the signed record chain. Anchored mode also needs a
trusted checkpoint and its witness receipt in the bundle. Online mode also
needs a witness URL configured in the trust file and a reachable witness.
Use the same state file for anchored and online checks when possible:

```bash
casf verify BUNDLE --trust trust.json --state verifier-state/state.json --mode anchored
casf verify BUNDLE --trust trust.json --state verifier-state/state.json --mode online
```

Do not initialize a new state file as an automatic recovery step. If state is
lost or damaged, restore a trusted copy before relying on rollback checks.
See the [verification guide](verification.md) for required status evidence,
error results, input limits, and recovery behavior. The CLI help lists all
commands; the [witness server guide](witness-server.md) describes the server
API and operating limits. The [local administration guide](administration.md)
explains manifest, trust, status, registration, and epoch commands.

The release rehearsal uses temporary synthetic evidence to check the
installed program. It is a software check, not a research result or the
separate real file demonstration.
