"""R07/R10: Darwin ACL checks use disposable files, never operational keys."""

import ctypes
import errno
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from casf.cli import _load_trust
from casf.errors import CasfError, SchemaError
from casf.file_permissions import reject_extended_acl
from casf.keys import generate_key, load_key
from casf.trust.state import locked_state
from tests.unit.test_cli import _trust
from tests.unit.test_writer import LOG_ID, _manifest_envelope

DARWIN = pytest.mark.skipif(sys.platform != "darwin", reason="native Darwin ACL semantics")
PASS = b"synthetic-passphrase"
MH = "ab" * 32


def add_acl(path, permissions):
    subprocess.run(["chmod", "+a", "everyone allow " + permissions, str(path)], check=True)


@DARWIN
@pytest.mark.parametrize("target", ["file", "directory"])
def test_trust_rejects_acl_write_access(tmp_path, target):
    path = _trust(tmp_path, _manifest_envelope())
    path.chmod(0o600)
    assert _load_trust(str(path), LOG_ID)
    add_acl(path if target == "file" else tmp_path,
            "write,append" if target == "file" else "add_file,delete_child")
    assert path.stat().st_mode & 0o022 == 0
    assert tmp_path.stat().st_mode & 0o022 == 0
    with pytest.raises(SchemaError, match="ACL"):
        _load_trust(str(path), LOG_ID)


@DARWIN
@pytest.mark.parametrize("target", ["key", "directory"])
def test_key_loading_rejects_extended_acl(tmp_path, target):
    path = tmp_path / "key.pem"
    generate_key("log", path, passphrase=PASS)
    add_acl(path if target == "key" else tmp_path, "read")
    with pytest.raises(CasfError, match="ACL"):
        load_key(path, passphrase=PASS)


@DARWIN
@pytest.mark.parametrize("target", ["state", "lock", "directory"])
def test_state_rejects_extended_acl(tmp_path, target):
    path = tmp_path / "state.json"
    with locked_state(str(path), MH, initialize=True) as state:
        state.save(1, None)
    before = path.read_bytes()
    selected = {"state": path, "lock": tmp_path / "state.json.lock", "directory": tmp_path}[target]
    add_acl(selected, "write")
    with pytest.raises(CasfError, match="ACL"), locked_state(str(path), MH):
        pytest.fail("ACL-writable state was accepted")
    assert path.read_bytes() == before


@DARWIN
@pytest.mark.parametrize("operation", ["key", "state"])
def test_inherited_acl_directory_rejected_before_publication(tmp_path, operation):
    add_acl(tmp_path, "read,write,file_inherit,directory_inherit")
    output = tmp_path / "new"
    with pytest.raises(CasfError, match="ACL"):
        if operation == "key":
            generate_key("log", output, passphrase=PASS)
        else:
            with locked_state(str(output), MH, initialize=True):
                pytest.fail("inheritable ACL accepted")
    assert not output.exists()


@DARWIN
def test_empty_acl_and_invalid_descriptor(tmp_path):
    path = tmp_path / "plain"
    path.write_bytes(b"synthetic")
    with path.open("rb") as stream:
        reject_extended_acl(stream.fileno())
    with pytest.raises(CasfError, match="could not be read"):
        reject_extended_acl(-1)


@pytest.mark.parametrize("failure", ["load", "read", "valid", "entries", "free"])
def test_acl_inspection_fails_closed(monkeypatch, failure):
    import casf.file_permissions as permissions

    freed = []

    def entry(*a):
        ctypes.set_errno(errno.EIO if failure == "entries" else errno.EINVAL)
        return -1

    def release(acl):
        freed.append(acl)
        return -1 if failure == "free" else 0

    def library():
        if failure == "load":
            raise OSError("synthetic")
        ctypes.set_errno(errno.EACCES)
        def read(*a):
            ctypes.set_errno(errno.EACCES)
            return None if failure == "read" else 123
        return SimpleNamespace(acl_get_fd_np=read,
                               acl_valid=lambda *a: -1 if failure == "valid" else 0,
                               acl_get_entry=entry, acl_free=release)

    monkeypatch.setattr(permissions.sys, "platform", "darwin")
    monkeypatch.setattr(permissions, "_darwin_acl", library)
    with pytest.raises(CasfError, match="ACL"):
        permissions.reject_extended_acl(4)
    assert freed == ([] if failure in {"load", "read"} else [123])


def test_non_darwin_does_not_load_darwin_library(monkeypatch):
    import casf.file_permissions as permissions

    monkeypatch.setattr(permissions.sys, "platform", "linux")
    monkeypatch.setattr(permissions, "_darwin_acl", lambda: pytest.fail("Darwin library loaded"))
    permissions.reject_extended_acl(4)


@DARWIN
@pytest.mark.parametrize("operation", ["key", "state", "status"])
def test_new_sensitive_file_checked_before_bytes_are_written(tmp_path, monkeypatch, operation):
    from casf.lifecycle import StatusBook
    from tests.unit.test_lifecycle import _status
    from tests.unit.test_writer import AUTH_PUB

    original_open = os.open
    created = []

    def open_with_acl(path, flags, mode=0o777, *, dir_fd=None):
        fd = original_open(path, flags, mode, dir_fd=dir_fd)
        if str(path).startswith((".casf-key-", ".casf-state-", ".casf-status-")):
            created.append(tmp_path / path)
            add_acl(created[-1], "read,write")
        return fd

    monkeypatch.setattr(os, "open", open_with_acl)
    output = tmp_path / "new"
    with pytest.raises(CasfError, match="ACL"):
        if operation == "key":
            generate_key("log", output, passphrase=PASS)
        elif operation == "state":
            with locked_state(str(output), MH, initialize=True) as state:
                state.save(1, None)
        else:
            StatusBook(output).observe(_status(1, mh=MH), AUTH_PUB)
    assert created
    assert not output.exists()
    assert all(not path.exists() for path in created)


@DARWIN
def test_explicit_empty_acl_is_allowed(tmp_path):
    from casf.file_permissions import _darwin_acl

    lib = _darwin_acl()
    lib.acl_init.argtypes = [ctypes.c_int]
    lib.acl_init.restype = ctypes.c_void_p
    lib.acl_set_fd_np.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
    lib.acl_set_fd_np.restype = ctypes.c_int
    path = tmp_path / "empty-acl"
    path.write_bytes(b"synthetic")
    acl = lib.acl_init(0)
    assert acl
    try:
        with path.open("rb") as stream:
            assert lib.acl_set_fd_np(stream.fileno(), acl, 0x100) == 0
            reject_extended_acl(stream.fileno())
    finally:
        assert lib.acl_free(acl) == 0
