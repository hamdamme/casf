"""SQLite adapter: transactions, constraints, settings (SPEC §17).

Stores manifests, records, heads, checkpoints, receipts and the pending
submission outbox. Relationship constraints remain an explicit conformance
task; enabling foreign_keys does not create relationships in this schema.

Envelopes are stored as canonical UTF-8 BLOBs; table indexes are
derived lookup data, never authenticated facts.
"""

import os
import sqlite3
import tempfile
from pathlib import Path

from casf.errors import CasfError

__all__ = ["Database"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS manifests(
    log_id TEXT PRIMARY KEY,
    manifest_hash TEXT NOT NULL UNIQUE,
    envelope BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS records(
    log_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    envelope BLOB NOT NULL,
    UNIQUE(log_id, seq),
    UNIQUE(log_id, event_id)
);
CREATE TABLE IF NOT EXISTS heads(
    log_id TEXT PRIMARY KEY,
    count INTEGER NOT NULL,
    head_hash TEXT NOT NULL,
    sealed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS checkpoints(
    log_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    count INTEGER NOT NULL,
    checkpoint_hash TEXT NOT NULL,
    envelope BLOB NOT NULL,
    state TEXT NOT NULL,
    UNIQUE(log_id, idx),
    UNIQUE(log_id, checkpoint_hash)
);
CREATE TABLE IF NOT EXISTS receipts(
    checkpoint_hash TEXT PRIMARY KEY,
    envelope BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox(
    log_id TEXT PRIMARY KEY,
    checkpoint_hash TEXT NOT NULL,
    from_seq INTEGER NOT NULL,
    to_seq INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL DEFAULT 0
);
-- Append-only guards (SPEC §17). These deter accidental modification;
-- they are not protection against a file administrator.
CREATE TRIGGER IF NOT EXISTS records_no_update BEFORE UPDATE ON records
BEGIN SELECT RAISE(ABORT, 'records are append only'); END;
CREATE TRIGGER IF NOT EXISTS records_no_delete BEFORE DELETE ON records
BEGIN SELECT RAISE(ABORT, 'records are append only'); END;
CREATE TRIGGER IF NOT EXISTS manifests_no_update BEFORE UPDATE ON manifests
BEGIN SELECT RAISE(ABORT, 'manifests are immutable'); END;
CREATE TRIGGER IF NOT EXISTS manifests_no_delete BEFORE DELETE ON manifests
BEGIN SELECT RAISE(ABORT, 'manifests are immutable'); END;
"""


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
            con.executescript(schema)
            con.commit()
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
