# Build and check a local candidate

This procedure prepares review files. It does not tag, publish or approve a
release. Use a clean checkout and the locked tooling in [dependencies](../dependencies.md).
Record the source revision, interpreter, dependency inventory and exact file hashes.
Keep old candidate files; use a new output directory for each attempt.

## Build from committed source

From the clean repository root, with uv 0.13.5 installed in `.venv-tools`:

```bash
test -z "$(git status --porcelain)" || exit 1
CASF_CHECKOUT="$PWD"
CASF_CANDIDATE_REVISION="$(git rev-parse HEAD)"
CASF_CANDIDATE_ROOT="$(mktemp -d)"
mkdir "$CASF_CANDIDATE_ROOT/source"
git archive --format=tar --output="$CASF_CANDIDATE_ROOT/source.tar" "$CASF_CANDIDATE_REVISION"
tar -xf "$CASF_CANDIDATE_ROOT/source.tar" -C "$CASF_CANDIDATE_ROOT/source"
.venv-tools/bin/uv sync --project "$CASF_CANDIDATE_ROOT/source" --locked --no-editable --all-extras --all-groups --python python3.12
SOURCE_DATE_EPOCH="$(git show -s --format=%ct "$CASF_CANDIDATE_REVISION")" \
  "$CASF_CANDIDATE_ROOT/source/.venv/bin/python" -m build --no-isolation \
  "$CASF_CANDIDATE_ROOT/source" --outdir "$CASF_CANDIDATE_ROOT/dist"
"$CASF_CANDIDATE_ROOT/source/.venv/bin/python" tests/package_artifacts.py \
  "$CASF_CANDIDATE_ROOT/dist" --output "$CASF_CANDIDATE_ROOT/artifacts.json"
```

The inspector compares all runtime files with the checkout, checks version,
dependencies, license and entry-point metadata, and rejects unexpected files.
The source archive also contains `uv.lock` and the synthetic example. It is a
package source archive, not a full repository export: tests, documentation and
research remain in the identified checkout. Do not change that checkout between
building and comparing it. Setting `SOURCE_DATE_EPOCH` records a controlled build
input; this procedure alone does not prove reproducibility across machines.

## Install the exact files

Export hashed requirements for the base installation and a separate witness
installation. Neither includes CASF itself:

```bash
.venv-tools/bin/uv export --locked --no-default-groups --no-emit-project --output-file "$CASF_CANDIDATE_ROOT/base.txt"
.venv-tools/bin/uv export --locked --extra witness --no-default-groups --no-emit-project --output-file "$CASF_CANDIDATE_ROOT/witness.txt"
.venv-tools/bin/uv venv --python python3.12 "$CASF_CANDIDATE_ROOT/base"
.venv-tools/bin/uv pip install --python "$CASF_CANDIDATE_ROOT/base/bin/python" --require-hashes -r "$CASF_CANDIDATE_ROOT/base.txt"
.venv-tools/bin/uv pip install --python "$CASF_CANDIDATE_ROOT/base/bin/python" --no-deps "$CASF_CANDIDATE_ROOT/dist/casf-0.1.0rc2-py3-none-any.whl"
.venv-tools/bin/uv pip check --python "$CASF_CANDIDATE_ROOT/base/bin/python"
mkdir "$CASF_CANDIDATE_ROOT/outside-checkout"
cd "$CASF_CANDIDATE_ROOT/outside-checkout"
unset PYTHONPATH PYTHONHOME
"$CASF_CANDIDATE_ROOT/base/bin/casf" --help
"$CASF_CANDIDATE_ROOT/base/bin/python" -I "$CASF_CHECKOUT/tests/validation_environment.py" --import-mode wheel --output "$CASF_CANDIDATE_ROOT/base-environment.json"
"$CASF_CANDIDATE_ROOT/base/bin/python" -I "$CASF_CHECKOUT/tests/wheel_smoke.py"
```

Repeat in a new environment using `witness.txt` and the same wheel. Use absolute tool and test-script paths through `CASF_CHECKOUT` from this
directory. Run
`tests/wheel_smoke.py --witness` and `examples/verified_workflow.py NEW_DIRECTORY`
with that environment's `python -I`. The workflow must report 21 checks and the
expected tamper/unavailable-witness outcomes. Run `tests/public_fixture.py` and
`tests/public_verify.py` as separate isolated processes to check public-only
verification without importing writer or witness modules in the verifier.

Finally, use a third fresh environment with `witness.txt` to install the exact
`.tar.gz`, with `--no-deps --build-constraint BUILD_CONSTRAINTS.txt`; for this
candidate the constraint file contains `setuptools==84.2.1`. The installer uses
an isolated build environment. Repeat the import, entry-point, public verification
and witness workflow checks. The example can be run from the checked source
archive after extraction; `python -I` keeps its source package off the import path.

Run installed checks outside the checkout, without `PYTHONPATH` or `PYTHONHOME`.
Retain logs, import inventories and public synthetic outputs. Compare installation
origin paths and all 39 runtime file hashes with the inspected artifacts; rehash
the artifacts after installation. Temporary private demo keys and databases are
not release evidence. Full tests and all supported CI jobs remain separate gates.

The [candidate record](candidate-0.1.0rc2.md) identifies the executed checks.
Advisory/license review, final notes, a reviewed release tag and explicit
publication approval remain necessary before these files can be distributed.
