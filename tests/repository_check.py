"""Check every tracked file's structure, local Markdown links and retained hashes.

This is a repository consistency check, not a semantic or security proof.
External links, PDF layout and historical measurements need separate evidence.
"""

import argparse
import ast
import hashlib
import json
import re
import sqlite3
import subprocess
import tomllib
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit


def tracked(root):
    return subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "-z"], text=True).rstrip("\0").split("\0")


def headings(text):
    counts = Counter()
    result = set()
    for line in re.sub(r"```.*?```", "", text, flags=re.DOTALL).splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*$", line)
        if match:
            slug = re.sub(r"[^\w\- ]", "", match[1].lower()).replace(" ", "-")
            n = counts[slug]
            counts[slug] += 1
            result.add(slug + (f"-{n}" if n else ""))
    return result


def links(root, path):
    text = re.sub(r"```.*?```", "", path.read_text(), flags=re.DOTALL)
    targets = re.findall(r"\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", text)
    targets += re.findall(r"(?m)^\s*\[[^\]]+\]:\s*(\S+)", text)
    count = 0
    for raw in targets:
        url = urlsplit(raw.strip("<>"))
        if url.scheme or url.netloc:
            continue
        target = (path.parent / unquote(url.path)).resolve() if url.path else path
        if not target.is_relative_to(root) or not target.exists():
            raise ValueError(f"missing or outside local link: {raw}")
        if (url.fragment and target.suffix == ".md"
                and unquote(url.fragment) not in headings(target.read_text())):
            raise ValueError(f"missing heading: {raw}")
        count += 1
    return count


def category(name):
    if name.startswith(("docs/historical/", "docs/0")):
        return "historical prototype"
    if name.startswith(("benchmarks/results/", "research/preprint/")):
        return "retained research evidence"
    if name.startswith("research/"):
        return "research methods and interpretation"
    if name.startswith("docs/release/"):
        return "release evidence and review"
    if name.startswith("docs/adr/"):
        return "design decision record"
    if name.startswith("docs/"):
        return "specification or user guide"
    if name.startswith("src/"):
        return "runtime implementation or package marker"
    if name.startswith(("tests/", "vectors/")):
        return "validation code or fixture"
    if name.startswith(("benchmarks/", "examples/")):
        return "research harness or runnable example"
    return "project policy or build configuration"


def inspect(root):
    root = root.resolve()
    rows, errors = [], []
    for name in tracked(root):
        path = root / name
        row = {"path": name, "category": category(name), "checks": []}
        try:
            if path.is_symlink():
                raise ValueError("tracked symbolic link requires explicit review")
            data = path.read_bytes()
            row.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            suffix = path.suffix
            if suffix == ".docx":
                with zipfile.ZipFile(path) as archive:
                    if archive.testzip() is not None:
                        raise ValueError("corrupt DOCX archive")
                    for part in archive.namelist():
                        if part.endswith((".xml", ".rels")):
                            ET.fromstring(archive.read(part))
                row["checks"].append("DOCX archive and all XML parts parsed")
            elif suffix == ".pdf":
                if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-1024:]:
                    raise ValueError("invalid PDF envelope")
                row["checks"].append("PDF envelope; reading copy protected by manuscript hashes")
            else:
                text = data.decode("utf-8")
                row["checks"].append("UTF-8 read")
                if suffix == ".py":
                    tree = ast.parse(text)
                    stubs = []
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            body = [n for n in node.body if not (
                                isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                                and isinstance(n.value.value, str))]
                            if not body or all(isinstance(n, ast.Pass) or (
                                    isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                                    and n.value.value is Ellipsis) for n in body):
                                stubs.append({"line": node.lineno, "name": node.name})
                    row["checks"].append("Python AST parsed")
                    if stubs:
                        row["no_op_functions"] = stubs
                elif suffix == ".json":
                    json.loads(text)
                    row["checks"].append("JSON parsed")
                elif suffix in (".toml", ".lock"):
                    tomllib.loads(text)
                    row["checks"].append("TOML parsed")
                elif suffix == ".svg":
                    ET.fromstring(text)
                    row["checks"].append("SVG XML parsed")
                elif suffix == ".sql":
                    connection = sqlite3.connect(":memory:")
                    try:
                        connection.executescript(text)
                        if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                            raise ValueError("invalid SQL fixture")
                    finally:
                        connection.close()
                    row["checks"].append("SQL restored and integrity checked in memory")
                elif suffix == ".md":
                    row["local_links"] = links(root, path)
                    row["checks"].append("local Markdown files and heading targets checked")
                if path.name == "SHA256SUMS.txt":
                    checked = 0
                    for line in text.splitlines():
                        digest, relative = line.split(maxsplit=1)
                        target = (path.parent / relative.lstrip(" *")).resolve()
                        if not target.is_relative_to(root):
                            raise ValueError("checksum target outside repository")
                        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                            raise ValueError(f"checksum mismatch: {relative}")
                        checked += 1
                    row["checks"].append(f"{checked} retained checksums matched")
            # Tests use literal redaction markers; actual PEM blocks are forbidden.
            if re.search(rb"-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----\r?\n"
                         rb"[A-Za-z0-9+/=]{40}", data):
                raise ValueError("private key block requires removal")
        except (ValueError, OSError, SyntaxError, ET.ParseError, zipfile.BadZipFile,
                sqlite3.Error) as exc:
            errors.append({"path": name, "error": str(exc)})
        rows.append(row)
    return {"source_commit": subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "files": rows, "errors": errors,
        "counts": dict(Counter(row["category"] for row in rows)),
        "local_links": sum(row.get("local_links", 0) for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(Path(__file__).resolve().parents[1])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Checked {len(result['files'])} tracked files and {result['local_links']} local links")
    for error in result["errors"]:
        print(f"{error['path']}: {error['error']}")
    return bool(result["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
