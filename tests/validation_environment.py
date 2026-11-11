"""Record validation provenance and reject imports from the wrong CASF build."""

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import ssl
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

from cryptography.hazmat.bindings.openssl.binding import Binding

import casf

CONTEXT_KEYS = (
    "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_EVENT_NAME",
    "CASF_PR_HEAD_SHA", "RUNNER_OS", "RUNNER_ARCH", "ImageOS", "ImageVersion",
)


def package_hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*"))
            if path.is_file() and (path.suffix == ".py" or path.name == "py.typed")}


def check_import(root, package, prefix, mode):
    source = (root / "src" / "casf").resolve()
    package = package.resolve()
    if mode == "source":
        if package != source:
            raise RuntimeError("source validation must import the checked-out src/casf")
    elif mode == "wheel":
        if package == source or not package.is_relative_to(prefix.resolve()):
            raise RuntimeError("wheel validation must import CASF from the selected environment")
    else:
        raise ValueError("unknown import mode")
    expected, actual = package_hashes(source), package_hashes(package)
    if not expected or actual != expected:
        raise RuntimeError("imported CASF files differ from the checked-out source")
    return {"mode": mode, "path": str(package), "files_sha256": actual}


def collect(mode):
    root = Path(__file__).resolve().parents[1]

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    binding = Binding()
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(UTC).isoformat(),
        "source_commit": git("rev-parse", "HEAD"),
        "worktree_clean": not git("status", "--porcelain"),
        "context": {key: os.environ[key] for key in CONTEXT_KEYS if key in os.environ},
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python": sys.version,
        "python_executable": sys.executable,
        "sqlite": sqlite3.sqlite_version,
        "python_tls": ssl.OPENSSL_VERSION,
        "cryptography_openssl": binding.ffi.string(binding.lib.OpenSSL_version(0)).decode(),
        "packages": dict(sorted((dist.metadata["Name"], dist.version)
                                for dist in metadata.distributions())),
        "casf": check_import(root, Path(casf.__file__).parent, Path(sys.prefix), mode),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-mode", choices=("source", "wheel"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = collect(args.import_mode)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(data, sort_keys=True))


if __name__ == "__main__":
    main()
