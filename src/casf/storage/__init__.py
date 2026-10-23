"""SQLite adapter: transactions, constraints, settings (SPEC §17).

C05 scope: manifests, records and heads tables. Checkpoint, receipt
and outbox tables arrive with the witness tasks (C07/C08).

Envelopes are stored as canonical UTF-8 BLOBs; table indexes are
derived lookup data, never authenticated facts.
"""

import sqlite3
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
        con.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        con.execute("PRAGMA foreign_keys=ON")
        # verify the effective settings, not just the requests (SPEC §17)
        if con.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
            raise CasfError("WAL mode is required and was not applied")
        if con.execute("PRAGMA synchronous").fetchone()[0] != 2:
            raise CasfError("synchronous=FULL is required and was not applied")
        if con.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise CasfError("foreign_keys=ON is required and was not applied")
        con.executescript(schema)
        con.commit()

    def close(self) -> None:
        self.connection.close()
