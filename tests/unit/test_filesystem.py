"""Exclusive directory publication on supported platforms, with no fallback."""

import ctypes
import errno
from pathlib import Path

import pytest

from casf.filesystem import rename_directory_exclusive


def test_native_exclusive_rename_preserves_existing_directory(tmp_path):
    source, dest = tmp_path / "staged", tmp_path / "destination"
    source.mkdir()
    (source / "data").write_bytes(b"complete")
    dest.mkdir()
    original = dest.stat().st_ino
    with pytest.raises(FileExistsError):
        rename_directory_exclusive(source, dest)
    assert dest.stat().st_ino == original
    assert (source / "data").read_bytes() == b"complete"
    assert not list(dest.iterdir())
    dest.rmdir()
    rename_directory_exclusive(source, dest)
    assert (dest / "data").read_bytes() == b"complete"
    assert not source.exists()


@pytest.mark.parametrize("platform", ["darwin", "linux"])
@pytest.mark.parametrize("failure", [errno.ENOTSUP, errno.EIO, errno.EEXIST])
def test_native_error_propagates_without_ordinary_rename(monkeypatch, platform, failure):
    from types import SimpleNamespace

    calls = []

    def denied(*args):
        calls.append(args)
        ctypes.set_errno(failure)
        return -1

    monkeypatch.setattr("casf.filesystem.sys.platform", platform)
    monkeypatch.setattr("casf.filesystem.ctypes.CDLL",
                        lambda *a, **kw: SimpleNamespace(renamex_np=denied, renameat2=denied))
    with pytest.raises(OSError) as error:
        rename_directory_exclusive(Path("staged"), Path("destination"))
    assert error.value.errno == failure
    assert calls == ([(b"staged", b"destination", 4)] if platform == "darwin" else
                     [(-100, b"staged", -100, b"destination", 1)])


@pytest.mark.parametrize("platform", ["unsupported", "darwin", "linux"])
def test_missing_native_support_fails_closed(monkeypatch, platform):
    monkeypatch.setattr("casf.filesystem.sys.platform", platform)
    monkeypatch.setattr("casf.filesystem.ctypes.CDLL", lambda *a, **kw: object())
    with pytest.raises(OSError) as error:
        rename_directory_exclusive(Path("staged"), Path("destination"))
    assert error.value.errno == errno.ENOTSUP


def test_native_paths_reject_embedded_null(tmp_path):
    with pytest.raises(ValueError, match="null byte"):
        rename_directory_exclusive(tmp_path / "staged", tmp_path / "destination\0suffix")
