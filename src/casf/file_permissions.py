"""Descriptor-based extended ACL policy for sensitive local files."""

import ctypes
import errno
import os
import sys
from functools import lru_cache

from casf.errors import CasfError


@lru_cache(maxsize=1)
def _darwin_acl() -> ctypes.CDLL:
    # Darwin sys/acl.h: ACL_TYPE_EXTENDED = 0x100, ACL_FIRST_ENTRY = 0.
    # Use the system library, never a library resolved from the current directory.
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    library.acl_get_fd_np.argtypes = [ctypes.c_int, ctypes.c_int]
    library.acl_get_fd_np.restype = ctypes.c_void_p
    library.acl_valid.argtypes = [ctypes.c_void_p]
    library.acl_valid.restype = ctypes.c_int
    library.acl_get_entry.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                     ctypes.POINTER(ctypes.c_void_p)]
    library.acl_get_entry.restype = ctypes.c_int
    library.acl_free.argtypes = [ctypes.c_void_p]
    library.acl_free.restype = ctypes.c_int
    return library


def reject_extended_acl(fd: int) -> None:
    """On macOS require an empty extended ACL; inspection errors fail closed.

    Linux POSIX access ACL masks are reflected in the existing mode checks.
    This policy does not interpret Darwin allow/deny entries or silently remove
    them. Even a restrictive ACL needs explicit administrator remediation.
    """
    if sys.platform != "darwin":
        return
    try:
        library = _darwin_acl()
    except (OSError, AttributeError):
        raise CasfError("extended ACL inspection is unavailable") from None
    ctypes.set_errno(0)
    acl = library.acl_get_fd_np(fd, 0x100)
    if not acl:
        # Darwin filesec_get_property reports an absent ACL as ENOENT.
        # Confirm the descriptor is still valid; all other errors fail closed.
        if ctypes.get_errno() == errno.ENOENT:
            os.fstat(fd)
            return
        raise CasfError("extended ACL could not be read")
    try:
        if library.acl_valid(acl) != 0:
            raise CasfError("extended ACL is invalid")
        entry = ctypes.c_void_p()
        ctypes.set_errno(0)
        result = library.acl_get_entry(acl, 0, ctypes.byref(entry))
        if result == 0:
            raise CasfError("extended ACLs are unsupported for sensitive files and directories")
        # Darwin returns -1/EINVAL when a valid ACL has no first entry.
        if result != -1 or ctypes.get_errno() != errno.EINVAL:
            raise CasfError("extended ACL entries could not be inspected")
    finally:
        if library.acl_free(acl) != 0:
            raise CasfError("extended ACL memory could not be released")
