"""SQLite adapter: transactions, constraints, settings (SPEC §17).

Stores manifests, records, heads, checkpoints, receipts and the pending
submission outbox, with versioned schemas and relationship constraints.

Envelopes are stored as canonical UTF-8 BLOBs; table indexes are
derived lookup data, never authenticated facts.
"""

import os
import sqlite3
import tempfile
from pathlib import Path

from casf.errors import CasfError
from casf.storage.schema import WRITER as SCHEMA
from casf.storage.versioning import initialize, validate_schema

__all__ = ["Database"]


class Database:
    """One SQLite connection with the SPEC §17 settings verified."""

    def __init__(self, path: str | Path, busy_timeout_ms: int = 5000,
                 schema: str = SCHEMA, check_same_thread: bool = True) -> None:
        self.path = str(path)
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
        except BaseException:
            con.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def backup(self, destination: str | Path) -> None:
        """Publish a complete, flushed backup without replacing an existing path."""
        dest = Path(destination).absolute()
        if os.path.lexists(dest):
            raise CasfError("backup destination already exists")
        directory = os.open(dest.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with tempfile.TemporaryDirectory(prefix=".casf-backup-", dir=dest.parent) as staging:
                temporary = Path(staging) / "backup.db"
                fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
                try:
                    target = sqlite3.connect(temporary)
                    try:
                        self.connection.backup(target)
                    finally:
                        target.close()
                    os.fsync(fd)
                finally:
                    os.close(fd)
                try:
                    # A hard link publishes atomically and refuses every existing
                    # destination, including one created while the copy was running.
                    os.link(temporary, dest)
                except FileExistsError as exc:
                    raise CasfError("backup destination already exists") from exc
            os.fsync(directory)
        finally:
            os.close(directory)
