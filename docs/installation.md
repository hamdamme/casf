# Install and use CASF

CASF `0.1.0rc1` was an experimental candidate and has not been published to a
package index. Its previously approved artifacts predate the current source
changes and are no longer a candidate for these changes. A new wheel and
source archive must be built, checked, and separately approved before any
publication. Do not use `pip install casf` until a release is announced.

## Install from a checked candidate wheel

The [validation matrix](release/validation-matrix.md) targets CPython 3.12,
3.13 and 3.14 on GitHub hosted Ubuntu x86_64 and macOS arm64 runners, with
locked and minimum direct dependencies. Runner images can change; each job
records its actual components. Consult the exact revision's results before
treating it as validated. Local macOS checks and historical results are
recorded separately. Other operating systems and processor types are outside
this matrix; the checks are not a broad compatibility guarantee.

Download the wheel supplied with the approved release, then create a separate
environment and install that file. Replace the example filename with the
downloaded file name.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ./casf-0.1.0rc1-py3-none-any.whl
.venv/bin/casf --help
source .venv/bin/activate
```

The wheel includes the witness server code, but does not install its optional
HTTP server dependencies unless the `witness` extra is selected. For a checked
local wheel, install `"./casf-0.1.0rc1-py3-none-any.whl[witness]"` using the
environment's pip. The filename is illustrative until new artifacts are
approved. For
development from a source checkout, the repository's locked setup installs
the witness and development tools:

```bash
git clone https://github.com/hamdamme/casf.git
cd casf
python3 -m venv .venv-tools
.venv-tools/bin/python -m pip install "uv==0.13.5"
.venv-tools/bin/uv sync --locked --no-editable --extra witness --extra dev --group build --python python3
PYTHONPATH=src .venv/bin/casf --help
```

The remaining examples use `casf` from the activated candidate environment.
When checking development source instead, run them from the repository root
with `PYTHONPATH=src .venv/bin/casf` in place of `casf`. This distinction avoids
testing a stale installed package. The [synthetic demo](demo.md) supplies a
complete temporary workflow without requiring existing keys or evidence.

## Existing SQLite stores

Current source uses schema version 1. Earlier unversioned writer and witness
stores require an explicit copy migration before opening. Stop services, retain
the source and external state, and follow the [migration guide](storage-migrations.md).
Evidence bundles and authenticated `casf-v1` bytes are unchanged.

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
