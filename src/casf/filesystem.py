"""Publication helpers for the supported Linux and macOS filesystems."""

import ctypes
import errno
import os
import sys
from pathlib import Path


def rename_directory_exclusive(source: Path, destination: Path) -> None:
    """Atomically rename without replacing any existing destination.

    No check-then-rename fallback: unsupported kernels/filesystems must refuse
    publication. Both paths must be on the same filesystem.
    """
    old, new = os.fsencode(source), os.fsencode(destination)
    if b"\0" in old or b"\0" in new:
        raise ValueError("embedded null byte")
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename = getattr(libc, "renamex_np", None)
        if rename is None:
            raise OSError(errno.ENOTSUP, "exclusive directory rename is unavailable")
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(old, new, 0x00000004)  # RENAME_EXCL, sys/stdio.h
    elif sys.platform.startswith("linux"):
        rename = getattr(libc, "renameat2", None)
        if rename is None:
            raise OSError(errno.ENOTSUP, "exclusive directory rename is unavailable")
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                           ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(-100, old, -100, new, 1)  # AT_FDCWD, RENAME_NOREPLACE
    else:
        raise OSError(errno.ENOTSUP, "exclusive directory rename is unavailable")
    if result != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), str(destination))


def sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
