# Fresh wheel verification rehearsal

Date: 2026-10-27. Source revision: `070ea05a62c82ce12f76e63af63b22464ef526a6`.
This is a focused rehearsal, not release approval.

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

The optional witness extra was not installed into the fresh environment, and
the complete locked dependency installation and final artifact hashes remain
open. The reproducible install gate therefore remains blocked.
