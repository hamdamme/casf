# Session 3 validation

Date: 2026-10-25. Base commit: `0afd209`.
This record describes the working changes for Phase 3 Session 3. The base
commit alone does not identify the changed source. The local rehearsal source
manifest and patch accompany the separate session outputs. GitHub validation
of the new branch remains pending.

## Corrections

- Missing or unrelated authority status produces UNKNOWN trust and FAIL.
  Signatures, issuer identity, minimum serial, and terminal revocation are
  checked. Valid active status records `STATUS_CURRENTNESS_UNCONFIRMED`.
- The Python verifier and CLI enforce chain and record work limits. Excess
  work is INCONCLUSIVE unless an existing failure already prevents acceptance.
- Bundle files use bounded reads before parsing, with byte and object budgets.
  Status files receive the same checks; symbolic links and nonregular files
  are rejected. CLI controls are documented in [verification](../verification.md).
- Existing synthetic tests and benchmark verification now supply signed active
  status evidence. Benchmarks stop if their final verification does not pass.
  Historical measurements and their environments remain unchanged.

Six initial regressions failed before the fixes: missing status, unrelated
status, absent chain budget support at the boundary and above it, unbounded
file reads, and ignored status symlinks. All six passed after implementation.

## Scenario evidence

The suite adds 35 cases, bringing the total from 240 to 275. They include
record duplication, reordering, wrong genesis, signed log splicing, authority
status rejection and currentness limits, budget boundaries and excess input,
CLI propagation, concurrent export, missing WAL recovery against an external
anchor, and two conflicting signed witness views. Retained state detects the
conflict; an isolated client without it can still accept its view.

The installed public verification rehearsal creates two synthetic records,
exports public evidence, and provisions public trust separately. A distinct
isolated process verifies the installed wheel with only that public input.
It checks that writer, storage, witness, CLI, and key management modules were
not imported. No private key file is exported. This rehearsal is now included
in both the locked and minimum package CI jobs.

## Local validation

All environments below were fresh macOS ARM installations of the built wheel.

| Python | Locked dependencies | Minimum direct dependencies |
| --- | --- | --- |
| 3.12.11 | 275 tests, witness check, public verification passed | 275 tests, witness check, public verification passed |
| 3.13.17 | 275 tests, witness check, public verification passed | 275 tests, witness check, public verification passed |
| 3.14.9 | 275 tests, witness check, public verification passed | 275 tests, witness check, public verification passed |

Wheel and source archive builds passed with the locked Setuptools 84.2.1
backend and with the minimum backend 77.0.3. The minimum environments used
cryptography 41.0.0, h11 0.16.0, and Uvicorn 0.54.0. This establishes the
recorded compatibility, not the security status of older dependencies.

Lint passed for source, tests, and benchmarks. Typing passed for 22 source
files. Workflow YAML parsing, lockfile validation, and Git whitespace checks
passed. Every application source file in the locked wheel matched the current
source bytes.

## Local benchmark rehearsal

The existing `benchmarks/manifest.v1.json` ran unchanged in a fresh locked
Python 3.12 environment. Both configurations completed all ten runs: 1000
records per run, 1 KiB target, and checkpoint batches of 128 and 16. All 20
raw results report PASS verification. Output was written outside the repository
so the original research results were not replaced.

This is a procedure rehearsal with changed verifier behavior, not a new claim
that historical performance numbers reproduce exactly. Its environment records
name the base commit; the accompanying source hashes and patch identify the
working changes. The historical Linux and wide area matrices were not rerun.
No external server was contacted. Final release scope for those historical
experiments remains a maintainer decision.

## Remaining acceptance

- GitHub must execute the updated Linux matrix before merge approval.
- Imported decoded records and verifier record digests remain in memory within
  configured budgets. Memory is not constant in record count. The stronger
  streaming requirement remains open rather than being claimed as satisfied.
- Final release acceptance must address the historical benchmark rerun scope,
  component and redistribution review, private reporting drill, and external
  review. This session does not close those gates.
- This change validates signed supplied status and a provisioned serial floor;
  it does not establish globally current revocation knowledge or add automatic
  distribution of status statements.

All 119 protected files matched the saved baseline or prior approved
corrections. Original commits, backups, research result files, frozen vectors,
package dependency metadata, uv.lock, and LICENSE remain preserved.
