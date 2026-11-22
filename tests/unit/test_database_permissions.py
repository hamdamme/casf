"""SQLite stores stay private without disrupting SQLite's own file locks."""

import os
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from casf.errors import CasfError
from casf.storage import Database
from casf.witness import Witness
from casf.writer import Writer
from tests.unit.test_file_permissions import DARWIN, add_acl
from tests.unit.test_writer import LOG, WIT


def modes(path):
    return [stat.S_IMODE(Path(str(path) + s).stat().st_mode) for s in ("", "-wal", "-shm")]


@pytest.mark.parametrize("mask", [0o022, 0o077])
@pytest.mark.parametrize("kind", ["database", "writer", "witness"])
def test_new_store_and_recreated_sidecars_are_private(tmp_path, mask, kind):
    tmp_path.chmod(0o755)
    path = tmp_path / "store.db"
    previous = os.umask(mask)
    try:
        if kind == "writer":
            store = Writer(path, LOG, local_only=True)
        elif kind == "witness":
            store = Witness(path, WIT)
        else:
            store = Database(path)
        try:
            assert modes(path) == [0o600] * 3
        finally:
            store.close()
        # SQLite removes the sidecars at close; reopening must recreate them safely.
        store = Witness(path, WIT) if kind == "witness" else Database(path)
        try:
            assert modes(path) == [0o600] * 3
        finally:
            store.close()
        assert os.umask(mask) == mask  # The library must not alter process-wide umask.
    finally:
        os.umask(previous)


def test_existing_readable_store_requires_private_directory(tmp_path, monkeypatch):
    path = tmp_path / "store.db"
    Database(path).close()
    path.chmod(0o644)
    store = Database(path)
    try:
        assert modes(path) == [0o644] * 3
    finally:
        store.close()
    before = path.read_bytes()
    tmp_path.chmod(0o755)
    monkeypatch.setattr(
        sqlite3, "connect", lambda *a, **kw: pytest.fail("SQLite opened unsafe file")
    )
    with pytest.raises(CasfError, match="database permissions"):
        Database(path)
    assert path.read_bytes() == before
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal"])
def test_unsafe_existing_file_rejected_before_sqlite(tmp_path, monkeypatch, suffix):
    path = tmp_path / "store.db"
    store = Database(path)
    selected = Path(str(path) + suffix)
    if not selected.exists():
        selected.touch(mode=0o600)
    selected.chmod(0o666)
    try:
        monkeypatch.setattr(
            sqlite3, "connect", lambda *a, **kw: pytest.fail("SQLite opened unsafe file")
        )
        with pytest.raises(CasfError, match="database permissions"):
            Database(path)
        assert stat.S_IMODE(selected.stat().st_mode) == 0o666
    finally:
        store.close()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_orphan_sidecar_refused_without_creating_main(tmp_path, suffix):
    path = tmp_path / "store.db"
    sidecar = Path(str(path) + suffix)
    sidecar.write_bytes(b"synthetic existing evidence")
    with pytest.raises(CasfError, match="sidecar"):
        Database(path)
    assert not path.exists()
    assert sidecar.read_bytes() == b"synthetic existing evidence"


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "directory"])
def test_nonregular_or_linked_database_is_refused(tmp_path, kind):
    path = tmp_path / "store.db"
    target = tmp_path / "target"
    if kind in ("symlink", "hardlink"):
        target.write_bytes(b"synthetic evidence")
        if kind == "symlink":
            path.symlink_to(target)
        else:
            os.link(target, path)
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.mkdir()
    with pytest.raises(CasfError, match="regular"):
        Database(path)
    if target.exists():
        assert target.read_bytes() == b"synthetic evidence"


def test_writable_parent_refused_before_creation(tmp_path):
    tmp_path.chmod(0o777)
    path = tmp_path / "store.db"
    with pytest.raises(CasfError, match="database directory"):
        Database(path)
    assert not path.exists()


def test_acl_inspection_error_prevents_database_open(tmp_path, monkeypatch):
    from casf import storage

    path = tmp_path / "store.db"
    Database(path).close()

    def failed(path):
        raise CasfError("extended ACL could not be read")

    monkeypatch.setattr(storage, "reject_extended_acl_path", failed)
    monkeypatch.setattr(
        sqlite3, "connect", lambda *a, **kw: pytest.fail("SQLite opened unchecked file")
    )
    with pytest.raises(CasfError, match="ACL"):
        Database(path)


def test_cli_permission_failure_is_local_error(tmp_path, capsys):
    from casf.cli import main

    path = tmp_path / "store.db"
    Database(path).close()
    path.chmod(0o644)
    tmp_path.chmod(0o755)
    assert main(["status", "--db", str(path), "--json"]) == 5
    output = capsys.readouterr()
    assert "database permissions" in output.err
    assert not output.out


def test_permission_checks_do_not_drop_existing_sqlite_locks(tmp_path):
    path = tmp_path / "store.db"
    first = Database(path)
    try:
        first.connection.execute("BEGIN IMMEDIATE")
        second = Database(path)
        second.close()
        child = """import sqlite3,sys
con = sqlite3.connect(sys.argv[1], timeout=0)
try:
    con.execute('BEGIN IMMEDIATE')
except sqlite3.OperationalError as exc:
    print(exc.sqlite_errorname)
else:
    print('LOCK LOST')
finally:
    con.close()
"""
        result = subprocess.run(
            [sys.executable, "-c", child, str(path)], capture_output=True, text=True, check=True
        )
        assert result.stdout.strip() == "SQLITE_BUSY"
    finally:
        first.close()


@DARWIN
@pytest.mark.parametrize("target", ["directory", "main", "-wal", "-shm"])
def test_database_acl_is_rejected_before_sqlite(tmp_path, monkeypatch, target):
    path = tmp_path / "store.db"
    store = Database(path)
    selected = (
        tmp_path
        if target == "directory"
        else Path(str(path) + ("" if target == "main" else target))
    )
    add_acl(selected, "read")
    try:
        monkeypatch.setattr(
            sqlite3, "connect", lambda *a, **kw: pytest.fail("SQLite opened ACL file")
        )
        with pytest.raises(CasfError, match="ACL"):
            Database(path)
    finally:
        store.close()


@DARWIN
def test_inherited_acl_refused_before_database_creation(tmp_path):
    add_acl(tmp_path, "read,file_inherit,directory_inherit")
    with pytest.raises(CasfError, match="ACL"):
        Database(tmp_path / "store.db")
    assert not (tmp_path / "store.db").exists()


@DARWIN
def test_new_database_acl_checked_before_sqlite_bytes(tmp_path, monkeypatch):
    path = tmp_path / "store.db"
    original = os.open

    def with_acl(name, flags, mode=0o777, **kwargs):
        fd = original(name, flags, mode, **kwargs)
        if Path(name) == path and flags & os.O_CREAT:
            add_acl(path, "read")
        return fd

    monkeypatch.setattr(os, "open", with_acl)
    with pytest.raises(CasfError, match="ACL"):
        Database(path)
    assert path.read_bytes() == b""
