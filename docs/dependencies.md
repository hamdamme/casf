# Dependency management

This workflow supports requirement R12 by recording exact dependencies for
new development environments and experiments. It does not establish that a
new environment reproduces historical measurements.

## Setup

Use Python 3.12, 3.13, or 3.14. From the repository root:

```bash
python3 -m venv .venv-tools
.venv-tools/bin/python -m pip install "uv==0.13.5"
.venv-tools/bin/uv sync --locked --extra witness --extra dev --group build --python python3
```

The tool environment is separate from the project environment in `.venv`.
Both directories are ignored by Git. The package metadata retains its
supported dependency ranges; `uv.lock` records the exact resolved versions
and package hashes. The `dev` extra installs the test and analysis tools. The `witness` extra
installs the optional Uvicorn service; the base library does not require it.
The `build` group installs the build frontend and fixed Setuptools backend.
The same backend constraint applies to isolated builds performed by uv.

A locked installation fails if project metadata requires a lockfile update.
It does not silently select newer versions. Use the same uv version locally
and in CI. A lockfile covering several Python versions does not replace
executing the checks on each supported version.

## Checks and builds

```bash
.venv-tools/bin/uv lock --check
.venv/bin/ruff check src tests
.venv/bin/mypy src
.venv/bin/python -m pytest tests/
.venv-tools/bin/uv build --python .venv/bin/python --no-build-isolation --out-dir dist
```

The build command uses the installed build group from the locked environment.
CI also installs the resulting wheel in a fresh environment with runtime
dependencies exported from the lockfile and verifies package import and CLI
startup. It checks that the base installation reports a clear error when
the optional witness dependencies are absent, then installs the witness
dependencies and exercises a real request and shutdown. Runtime dependencies are installed with hash verification; the
locally built wheel is then installed without resolving dependencies again.

`requirements.txt` describes a minimum runtime dependency and is not a
lockfile. Ordinary pip installation remains available to library consumers;
it does not promise the exact development environment recorded here.

## Dependency updates

```bash
.venv-tools/bin/uv lock --upgrade
.venv-tools/bin/uv sync --locked --extra witness --extra dev --group build --python python3
```

Review the resolved versions, licenses, dependency advisories, and lockfile
diff before accepting an update. When changing the build backend version,
update both the build group and the uv build constraint in `pyproject.toml`.
Repeat lint, typing, tests, package build, and wheel installation checks.
CI exercises Python 3.12, 3.13, and 3.14 on Linux. Record any environment that
was not tested and retain the lockfile with the source commit for each new
experiment. Historical result files and their recorded environments remain
unchanged.

The witness implementation uses Uvicorn with h11 and the standard asyncio
loop. See the [server guide](witness-server.md) for resource limits and
[dependency review](release/http-dependency-review.md) for the exact added
packages. D05 remains open until implementation review and validation are
accepted. Dependency locking alone does not close the decision.
