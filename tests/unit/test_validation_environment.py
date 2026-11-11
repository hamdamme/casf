"""Validation evidence must identify the code actually imported by the job."""

import shutil

import pytest

from tests.validation_environment import check_import, collect


@pytest.fixture
def packages(tmp_path):
    source = tmp_path / "src" / "casf"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("VERSION = 1\n")
    (source / "py.typed").touch()
    prefix = tmp_path / "venv"
    installed = prefix / "site-packages" / "casf"
    shutil.copytree(source, installed)
    return tmp_path, source, prefix, installed


def test_inventory_distinguishes_source_and_matching_wheel(packages):
    root, source, prefix, installed = packages
    first = check_import(root, source, prefix, "source")
    second = check_import(root, installed, prefix, "wheel")
    assert first["path"] != second["path"]
    assert first["files_sha256"] == second["files_sha256"]


@pytest.mark.parametrize("mode", ["source", "wheel"])
def test_inventory_rejects_wrong_import_location(packages, mode):
    root, source, prefix, installed = packages
    with pytest.raises(RuntimeError, match="validation must import"):
        check_import(root, installed if mode == "source" else source, prefix, mode)


@pytest.mark.parametrize("change", ["modified", "missing", "extra"])
def test_inventory_rejects_stale_or_incomplete_wheel(packages, change):
    root, _, prefix, installed = packages
    if change == "modified":
        (installed / "__init__.py").write_text("VERSION = 0\n")
    elif change == "missing":
        (installed / "py.typed").unlink()
    else:
        (installed / "obsolete.py").write_text("pass\n")
    with pytest.raises(RuntimeError, match="differ"):
        check_import(root, installed, prefix, "wheel")


def test_inventory_rejects_wheel_outside_selected_environment(packages, tmp_path):
    root, _, _, installed = packages
    with pytest.raises(RuntimeError, match="selected environment"):
        check_import(root, installed, tmp_path / "another-venv", "wheel")


def test_inventory_records_runtime_without_unrelated_environment(monkeypatch):
    from pathlib import Path

    import casf

    root = Path(__file__).resolve().parents[2]
    mode = "source" if Path(casf.__file__).resolve().is_relative_to(root / "src") else "wheel"
    monkeypatch.setenv("CASF_TEST_SECRET", "synthetic-private-marker")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    data = collect(mode)
    assert data["context"]["GITHUB_RUN_ID"] == "123"
    assert "CASF_TEST_SECRET" not in data["context"]
    assert "synthetic-private-marker" not in str(data)
    assert len(data["source_commit"]) == 40
    assert type(data["worktree_clean"]) is bool
    assert data["sqlite"] and data["cryptography_openssl"] and data["python_tls"]
    assert data["packages"]["casf"] == casf.__version__
