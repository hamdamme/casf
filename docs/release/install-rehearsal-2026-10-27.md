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

This did not exercise the full key generation, init, append, and export CLI
workflow, the complete locked dependency installation, or the final release
artifact hashes. The reproducible install gate therefore remains blocked.
