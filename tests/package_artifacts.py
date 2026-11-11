"""Inspect locally built distributions without extracting or importing them."""

import argparse
import ast
import configparser
import hashlib
import json
import subprocess
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

from packaging.requirements import Requirement


def check_members(actual, expected, generated):
    if set(actual) != set(expected) | generated:
        raise ValueError("package member inventory differs from the expected files")
    for name, data in expected.items():
        if actual[name] != data:
            raise ValueError(f"packaged file differs from source: {name}")


def check_metadata(data, project):
    metadata = BytesParser().parsebytes(data)
    for field, value in {"Name": project["name"], "Version": project["version"],
                         "Requires-Python": project["requires-python"],
                         "License-Expression": project["license"]}.items():
        if metadata.get_all(field) != [value]:
            raise ValueError(f"package metadata mismatch: {field}")
    urls = {f"{name}, {url}" for name, url in project.get("urls", {}).items()}
    if set(metadata.get_all("Project-URL", [])) != urls:
        raise ValueError("package project URLs mismatch")
    if metadata.get_all("License-File") != ["LICENSE"]:
        raise ValueError("package license declaration mismatch")
    if set(metadata.get_all("Provides-Extra", [])) != set(project["optional-dependencies"]):
        raise ValueError("package extras mismatch")
    requirements = [Requirement(value) for value in project["dependencies"]]
    for extra, dependencies in project["optional-dependencies"].items():
        requirements.extend(Requirement(f'{value}; extra == "{extra}"') for value in dependencies)
    actual = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
    if len(actual) != len(requirements) or set(actual) != set(requirements):
        raise ValueError("package dependency declarations mismatch")


def check_entry_points(data, project):
    config = configparser.ConfigParser()
    config.read_string(data.decode())
    if config.sections() != ["console_scripts"] or dict(config["console_scripts"]) != project["scripts"]:
        raise ValueError("package entry points mismatch")


def inspect(root, directory):
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    version = project["version"]
    assignments = ast.parse((root / "src/casf/__init__.py").read_text()).body
    runtime_version = [ast.literal_eval(node.value) for node in assignments
                       if isinstance(node, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "__version__"
                               for t in node.targets)]
    if runtime_version != [version]:
        raise ValueError("runtime and project versions differ")
    package = {p.relative_to(root / "src").as_posix(): p.read_bytes()
               for p in sorted((root / "src/casf").rglob("*"))
               if p.is_file() and (p.suffix == ".py" or p.name == "py.typed")}
    wheel = directory / f"casf-{version}-py3-none-any.whl"
    sdist = directory / f"casf-{version}.tar.gz"
    info = f"casf-{version}.dist-info/"
    with zipfile.ZipFile(wheel) as archive:
        members = archive.infolist()
        if len({m.filename for m in members}) != len(members):
            raise ValueError("duplicate wheel member")
        wheel_files = {m.filename: archive.read(m) for m in members}
    check_members(wheel_files, {**package, info + "licenses/LICENSE":
                                (root / "LICENSE").read_bytes()},
                  {info + name for name in ("METADATA", "WHEEL", "entry_points.txt",
                                            "top_level.txt", "RECORD")})
    check_metadata(wheel_files[info + "METADATA"], project)
    check_entry_points(wheel_files[info + "entry_points.txt"], project)
    source_files = {}
    prefix = f"casf-{version}/"
    with tarfile.open(sdist) as archive:
        seen = set()
        for member in archive.getmembers():
            if member.name in seen:
                raise ValueError("duplicate source archive member")
            seen.add(member.name)
            if member.isdir():
                continue
            if not member.isfile() or not member.name.startswith(prefix):
                raise ValueError("unexpected source archive member type or prefix")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("unreadable source archive member")
            source_files[member.name[len(prefix):]] = stream.read()
    expected = {"src/" + name: data for name, data in package.items()}
    for name in ("LICENSE", "README.md", "pyproject.toml", "MANIFEST.in", "uv.lock",
                 "examples/__init__.py", "examples/verified_workflow.py"):
        expected[name] = (root / name).read_bytes()
    generated = {"PKG-INFO", "setup.cfg"} | {"src/casf.egg-info/" + name for name in (
        "PKG-INFO", "SOURCES.txt", "dependency_links.txt", "entry_points.txt",
        "requires.txt", "top_level.txt")}
    check_members(source_files, expected, generated)
    for name in ("PKG-INFO", "src/casf.egg-info/PKG-INFO"):
        check_metadata(source_files[name], project)
    check_entry_points(source_files["src/casf.egg-info/entry_points.txt"], project)
    return {"version": version, "runtime_files": len(package), "artifacts": {
        path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "size": path.stat().st_size,
                    "members_sha256": {name: hashlib.sha256(data).hexdigest()
                                       for name, data in sorted(files.items())}}
        for path, files in ((wheel, wheel_files), (sdist, source_files))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = inspect(root, args.directory)
    result["source_commit"] = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    result["worktree_clean"] = not subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain"], text=True).strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"Checked {result['version']}: {result['runtime_files']} runtime files in both artifacts")


if __name__ == "__main__":
    main()
