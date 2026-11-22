"""SQLite adapter: transactions, constraints, settings (SPEC §17).

Stores manifests, records, heads, checkpoints, receipts and the pending
submission outbox, with versioned schemas and relationship constraints.

Envelopes are stored as canonical UTF-8 BLOBs; table indexes are
derived lookup data, never authenticated facts.
"""

import os
import sqlite3
import stat
import tempfile
import threading
from pathlib import Path

from casf.errors import CasfError
from casf.file_permissions import reject_extended_acl, reject_extended_acl_path
from casf.storage.schema import WRITER as SCHEMA
from casf.storage.versioning import initialize, validate_schema

__all__ = ["Database", "migrate_database"]

# Keep another CASF thread from opening a newly reserved file before its raw
# descriptor closes. Existing stores are inspected without raw file descriptors:
# closing one could discard locks held by another SQLite connection in this process.
_OPEN_LOCK = threading.Lock()


def _check_store_file(path: Path, private_directory: bool) -> None:
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_uid not in (os.geteuid(), 0)):
        raise CasfError("database files must be regular, trusted-owner files without links")
    if info.st_mode & 0o022 or (info.st_mode & 0o077 and not private_directory):
        raise CasfError("database permissions require owner-only files or a private directory; "
                        "stop services and review permissions before reopening")
    reject_extended_acl_path(path)


def _check_store_files(path: Path, private_directory: bool) -> None:
    _check_store_file(path, private_directory)
    for suffix in ("-wal", "-shm", "-journal"):
        try:
            _check_store_file(Path(str(path) + suffix), private_directory)
        except FileNotFoundError:
            # SQLite can remove sidecars when another connection closes.
            pass


def _prepare_database(path: Path) -> bool:
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(directory)
        if info.st_uid not in (os.geteuid(), 0) or info.st_mode & 0o022:
            raise CasfError("database directory must have a trusted owner and no group/other write access")
        reject_extended_acl(directory)
        private_directory = not bool(info.st_mode & 0o077)
        if not os.path.lexists(path):
            _refuse_destination_artifacts(path, "database creation", include_main=False)
            try:
                fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                pass  # Another process reserved it; validate before SQLite opens it.
            else:
                try:
                    if os.fstat(fd).st_mode & 0o077:
                        raise CasfError("new database requires owner-only permissions")
                    reject_extended_acl(fd)
                finally:
                    os.close(fd)
        _check_store_files(path, private_directory)
        return private_directory
    finally:
        os.close(directory)


def _refuse_destination_artifacts(dest: Path, operation: str, *,
                                  include_main: bool = True) -> None:
    if include_main and os.path.lexists(dest):
        raise CasfError(f"{operation} destination already exists")
    paths = [Path(str(dest) + suffix) for suffix in ("-wal", "-shm", "-journal")]
    if any(os.path.lexists(path) for path in paths):
        raise CasfError(f"{operation} destination SQLite sidecar already exists")


class Database:
    """One SQLite connection with the SPEC §17 settings verified."""

    def __init__(self, path: str | Path, busy_timeout_ms: int = 5000,
                 schema: str = SCHEMA, check_same_thread: bool = True) -> None:
        if str(path) in ("", ":memory:"):
            raise CasfError("database requires a persistent filesystem path")
        target = Path(path).absolute()
        self.path = str(target)
        with _OPEN_LOCK:
            private_directory = _prepare_database(target)
            self.connection = sqlite3.connect(
                self.path, timeout=busy_timeout_ms / 1000,
                check_same_thread=check_same_thread)
        con = self.connection
        try:
            con.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
            # Refuse unsupported stores before changing their journal settings.
            con.execute("BEGIN")
            try:
                empty = validate_schema(con, schema, allow_empty=True)
            finally:
                con.rollback()
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("PRAGMA foreign_keys=ON")
            # Verify the effective settings, not just the requests (SPEC §17).
            if con.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                raise CasfError("WAL mode is required and was not applied")
            if con.execute("PRAGMA synchronous").fetchone()[0] != 2:
                raise CasfError("synchronous=FULL is required and was not applied")
            if con.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise CasfError("foreign_keys=ON is required and was not applied")
            if empty:
                initialize(con, schema)
            _check_store_files(target, private_directory)
        except BaseException:
            con.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def backup(self, destination: str | Path) -> None:
        """Publish a complete, flushed backup without replacing an existing path."""
        dest = Path(destination).absolute()
        _refuse_destination_artifacts(dest, "backup")
        directory = os.open(dest.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with tempfile.TemporaryDirectory(prefix=".casf-backup-", dir=dest.parent) as staging:
                temporary = Path(staging) / "backup.db"
                _prepare_database(temporary)
                fd = os.open(temporary, os.O_RDWR | os.O_NOFOLLOW)
                try:
                    target = sqlite3.connect(temporary)
                    try:
                        self.connection.backup(target)
                    finally:
                        target.close()
                    os.fsync(fd)
                finally:
                    os.close(fd)
                _refuse_destination_artifacts(dest, "backup")
                try:
                    # A hard link publishes atomically and refuses every existing
                    # destination, including one created while the copy was running.
                    os.link(temporary, dest)
                except FileExistsError as exc:
                    raise CasfError("backup destination already exists") from exc
            os.fsync(directory)
            # A sidecar arriving during publication must not turn failure into
            # success. Leave all published artifacts intact for inspection.
            _refuse_destination_artifacts(dest, "backup", include_main=False)
        finally:
            os.close(directory)


def migrate_database(source: str | Path, destination: str | Path, *, kind: str) -> None:
    """Copy a recognized legacy store to version 1 without rewriting envelopes.

    Stop writers before migration and validate the result before service cutover.
    The source is retained; this operation does not establish evidence freshness.
    """
    from casf.storage.schema import WITNESS, WRITER
    from casf.storage.versioning import check_integrity, legacy_tables

    if kind not in ("writer", "witness"):
        raise CasfError("storage kind must be writer or witness")
    schema = WRITER if kind == "writer" else WITNESS
    dest = Path(destination).absolute()
    _refuse_destination_artifacts(dest, "migration")
    with tempfile.TemporaryDirectory(prefix=".casf-migrate-", dir=dest.parent) as staging:
        snapshot_path = Path(staging) / "snapshot.db"
        _prepare_database(snapshot_path)
        snapshot = sqlite3.connect(snapshot_path)
        try:
            original = sqlite3.connect(Path(source).resolve().as_uri() + "?mode=ro", uri=True)
            try:
                original.backup(snapshot)
            finally:
                original.close()
            tables = legacy_tables(snapshot, schema)
            candidate = Database(Path(staging) / "candidate.db", schema=schema)
            try:
                target = candidate.connection
                target.execute("BEGIN IMMEDIATE")
                try:
                    for table in tables:
                        cursor = snapshot.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
                        placeholders = ",".join("?" for _ in cursor.description)
                        target.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', cursor)
                    check_integrity(target)
                    target.commit()
                except BaseException:
                    target.rollback()
                    raise
                candidate.backup(dest)
            finally:
                candidate.close()
        finally:
            snapshot.close()
