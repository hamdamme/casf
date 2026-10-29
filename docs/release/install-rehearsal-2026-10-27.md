# Fresh wheel verification rehearsal

Date: 2026-10-27. Source revision: `070ea05a62c82ce12f76e63af63b22464ef526a6`.
This is a focused rehearsal, not release approval.

This historical record describes the earlier `0.1.0.dev0` build and its
recorded hashes. It is superseded for release approval by the `0.1.0rc1`
artifacts and hashes in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md).

## Setup and results

- Built the wheel and source archive with uv 0.13.5 from a temporary copy of
  the source tree. The repository checkout was not modified by the build.
- Installed the wheel in a fresh Python 3.13.17 virtual environment. The base
  wheel and its runtime dependencies installed successfully.
- Generated a two record synthetic bundle with test signing keys held in
  memory. No key files or real audit data were used.
- Ran the installed CLI in integrity mode: PASS, two records verified.
- Ran the installed CLI in anchored mode against a signed checkpoint and
  receipt from a local witness: PASS, two records witnessed.
- Ran the installed CLI in online mode against the local witness: PASS,
  `FRESH_WITNESS_VIEW`.
- Supplied a deliberately mismatched provisioned witness ID: the installed
  CLI rejected it with exit code 3 and `WITNESS_ID_MISMATCH`.

The witness service for anchored and online checks ran from the existing
locked development environment. Installing the optional witness extra into
the fresh environment could not be completed because package index name
resolution failed. The client CLI and package under rehearsal were from the
fresh wheel; the witness service itself was not launched from that wheel.

## Full CLI workflow extension

The installed wheel was then used for the complete writer command path. Its
application source was built from `070ea05`; comparison with current main
`315efdb` confirms no changes to `src/`, `pyproject.toml`, or `uv.lock`
between those revisions.

- Generated authority, log, and witness keys through `casf key generate`.
- Initialized the log through `casf init` and appended two synthetic records
  through `casf append`.
- Created a checkpoint, submitted it to the loopback witness, and exported
  the bundle through the CLI.
- Verified the export through the installed CLI in integrity, anchored, and
  online modes. All three returned PASS; anchored mode reported two witnessed
  records and online mode reported `FRESH_WITNESS_VIEW`.

The manifest and active status statement were created with helper scripts
using the installed Python API because the CLI has no commands for those
provisioning steps. The local witness service ran from the existing locked
development environment. Keys, database, bundle, and state stayed in a
temporary directory; the key files used only a synthetic passphrase.

At the time of this focused rehearsal, the optional witness extra had not been
installed in the fresh environment and final artifact hashes were open. The
follow up below records the later complete locked installation and artifact
hashes.

## Full locked install and artifact hashes

Date: 2026-10-27. Source commit: `9556a62c7bdf677233e95e2222bdd1557067b774`.
GitHub comparison confirmed the merged commit `2b7e3d3` has the same file tree.
The check ran on macOS arm64 with Python 3.13.17 and uv 0.13.5.

- Exported the committed source to a temporary directory; the repository
  checkout was not changed.
- Ran `uv sync --locked --all-extras --all-groups --no-editable`: PASS. The
  lock resolved 25 packages and installed 24, including the witness, dev, and
  build dependencies.
- Built the wheel and source archive with the locked build tools using
  `python -m build --no-isolation`.
- Installed the exact wheel into the fresh environment. `uv pip check` passed
  for all 24 installed packages, and `casf --help` exited successfully.
- Confirmed imports and versions: CASF 0.1.0.dev0, cryptography 50.0.2,
  Uvicorn 0.54.0, and h11 0.16.0.

SHA 256 hashes for the built artifacts:

| Artifact | SHA 256 |
| --- | --- |
| `casf-0.1.0.dev0-py3-none-any.whl` | `46c34bc6a5283a65be108b94c3fd7018ef8259448c606844d494b43a8354a784` |
| `casf-0.1.0.dev0.tar.gz` | `004222fc88867b69a9ebfd2a0c261cdba15efe4420d68855b4d4012884b592fa` |

No tests were run as part of this installation check. It verifies one macOS
arm64 and Python version using local development artifacts; it does not approve
publication or replace the separate platform, redistribution, and maintainer
reviews. Future release artifacts may have different hashes.
