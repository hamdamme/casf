# Candidate 0.1.0rc2 build and installation record

The previous workflow review was accepted in PR 52, merged as
`79fce315a3b0ec06f2293643f01ea66a62b79136`. The local candidate below was built
from clean committed source `e92194fe0fa6eb37c2ff9016c381b8e734008880`, exported
with `git archive`. Later review-document commits are not claimed as its build
input. These are unpublished review files, not an approved release. No release
tag or publication was created.

## Identified files

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc2-py3-none-any.whl` | 105223 | `c38dcfedfc7173db826177a96dc0d442e90f52bb04447c917395420e9233cec2` |
| `casf-0.1.0rc2.tar.gz` | 141119 | `62f9f829b43de8e4987aaed3393d7427bf4b137b197dc34fea4800c325dc16b1` |

The [machine-readable record](candidate-0.1.0rc2.json) includes every member
hash and the installation results. The wheel has 45 files and the source archive
has 54 regular files. All 39 runtime files match the build revision. The source
archive additionally supplies the dependency lockfile and runnable synthetic
example. Only the package version changed in runtime source; authenticated
protocol bytes, database schemas and dependency versions are unchanged.

## Executed validation

The build used macOS arm64, CPython 3.12.11, uv 0.13.5, build 1.6.1 and
Setuptools 84.2.1 in a fresh locked environment. `SOURCE_DATE_EPOCH` was set to
the build commit's timestamp, `1794364791`. This records the exact build inputs;
no cross-machine byte-for-byte reproducibility claim is made.

- Full source suite: **1199 passed**, no failures or skips. Lint, strict typing
  of 38 source files, lock consistency and whitespace checks passed.
- **32 installation checks** passed across three new environments: base wheel,
  witness wheel, and source archive with an isolated constrained build backend.
  Runtime dependencies were installed from hashed exports of the same lockfile.
- Actual installed versions, CLI entry points, dependency consistency and all
  39 imported runtime hashes matched. Imports resolved inside each new
  environment, with isolated Python and no source-path override. Installation
  origin URLs identify the exact local artifact paths; the installer did not
  record archive hashes in its origin metadata, so artifacts were hashed before
  and after the checks and runtime contents were compared independently.
- The base environment contains CASF, cryptography, cffi and pycparser; its
  missing-witness-extra error was checked. The witness and source environments
  additionally contain Uvicorn, h11 and click. Installed dependency versions and
  native component versions are recorded, without implying advisory clearance.
- Both witness-capable installations completed the **21-check synthetic CLI
  workflow**, using the example from the source archive. Integrity, anchored and
  online verification passed; tampering failed; unavailable-witness verification
  was inconclusive. Restore and final witnessed sealing passed. Public-only
  verification ran in separate processes without private material or writer/
  witness module imports.
- Both source-selected and regularly installed developer imports were checked
  in the fresh locked environment. This avoids relying on the older local
  editable-install state.
- The package inspector rejected six deliberately changed wheel copies:
  missing type marker, changed runtime code, unexpected synthetic key file,
  wrong version, wrong dependency declaration and wrong CLI entry point.

The first local setup attempt used the host's older `python3` for archive
extraction and stopped before building because that interpreter lacked the
requested extraction filter. The successful procedure explicitly used Python
3.12. An offline lock refresh also lacked cached resolver metadata; the only
required lock change was the project version, and the resulting unchanged
dependency graph passed `uv lock --check --offline` and fresh locked installation.

CI now inspects both distributions and runs the installed workflow in every
locked/minimum configuration. Those jobs build their own validation files;
they do not test the exact local bytes listed above. CI evidence must identify
the PR head and tested merge revision separately from this local build input.

## Remaining acceptance

Review these changes and the full CI matrix. Final advisory and license review,
package-content acceptance, release notes, support details and the final
checklist are the next work package. Publication requires explicit approval of
the exact files, release notes and tag. If packaged inputs change, rebuild into
a new directory and repeat installation checks; do not overwrite these files or
reuse their approval for different hashes.

Additional Linux/cloud deployment evaluation remains deferred. Routine Ubuntu
CI continues. This record does not establish independent witness administration,
public-service security or production readiness.

See the [build procedure](candidate-build.md) and [completion tracker](completion-tracker.md).
