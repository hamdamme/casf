"""Regressions for repository checks that must reject inconsistent evidence."""

import hashlib
import subprocess

import pytest

from tests.repository_check import inspect, links


def test_markdown_links_check_headings_and_reference_links(tmp_path):
    (tmp_path / "guide.md").write_text("# Read this\n## Repeated\n## Repeated\n")
    page = tmp_path / "README.md"
    page.write_text("[first](guide.md#read-this)\n[again][ref]\n[ref]: guide.md#repeated-1\n")
    assert links(tmp_path, page) == 2
    page.write_text("[stale](guide.md#no-such-heading)")
    with pytest.raises(ValueError, match="missing heading"):
        links(tmp_path, page)


@pytest.mark.parametrize("target", ["absent.md", "../outside.md"])
def test_markdown_links_reject_missing_or_outside_targets(tmp_path, target):
    page = tmp_path / "README.md"
    page.write_text(f"[bad]({target})")
    with pytest.raises(ValueError, match="missing or outside"):
        links(tmp_path, page)


def test_inventory_reads_tracked_files_and_rejects_changed_evidence(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Test",
                    "-c", "user.email=test@example.invalid", "commit", "--allow-empty",
                    "-qm", "Fixture"], check=True)
    data = b'{"synthetic": true}\n'
    (tmp_path / "record.json").write_bytes(data)
    (tmp_path / "SHA256SUMS.txt").write_text(
        hashlib.sha256(data).hexdigest() + "  record.json\n")
    (tmp_path / "fixture.sql").write_text("CREATE TABLE events (id INTEGER PRIMARY KEY);")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    result = inspect(tmp_path)
    assert not result["errors"]
    assert len(result["files"]) == 3
    (tmp_path / "record.json").write_text('{"synthetic": false}')
    assert any("checksum mismatch" in e["error"] for e in inspect(tmp_path)["errors"])
    (tmp_path / "record.json").write_text('{invalid')
    assert any(e["path"] == "record.json" for e in inspect(tmp_path)["errors"])
