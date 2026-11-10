"""Fail-closed schema recognition and transactional initialization."""

import sqlite3
from functools import lru_cache

from casf.errors import CasfError
from casf.storage import legacy
from casf.storage.schema import VERSION, WITNESS, WITNESS_ID, WRITER, WRITER_ID

SchemaObjects = tuple[tuple[str, str, str], ...]


def identity(schema: str) -> int:
    if schema == WRITER:
        return WRITER_ID
    if schema == WITNESS:
        return WITNESS_ID
    raise CasfError("unsupported storage schema")


def objects(con: sqlite3.Connection) -> SchemaObjects:
    return tuple((str(kind), str(name), str(sql))
                 for kind, name, sql in con.execute(
                     "SELECT type, name, sql FROM sqlite_master "
                     "WHERE name NOT GLOB 'sqlite_*' ORDER BY type, name"))


@lru_cache(maxsize=4)
def expected(schema: str) -> SchemaObjects:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(schema)
        return objects(con)
    finally:
        con.close()


def check_integrity(con: sqlite3.Connection) -> None:
    if con.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise CasfError("storage integrity check failed")
    if con.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise CasfError("storage foreign-key violation")


def validate_schema(con: sqlite3.Connection, schema: str, *, allow_empty: bool = False) -> bool:
    """Return true only for a new, empty store; otherwise validate version 1."""
    app_id = identity(schema)
    version = con.execute("PRAGMA user_version").fetchone()[0]
    stored_id = con.execute("PRAGMA application_id").fetchone()[0]
    actual = objects(con)
    if version == 0 and stored_id == 0:
        if not actual and allow_empty:
            return True
        raise CasfError("unversioned storage requires explicit migration to a new destination")
    if version != VERSION:
        raise CasfError(f"unsupported storage schema version: {version}")
    if stored_id != app_id:
        raise CasfError("storage application identity does not match the requested store")
    if actual != expected(schema):
        raise CasfError("storage schema does not match its declared version")
    check_integrity(con)
    return False


def initialize(con: sqlite3.Connection, schema: str) -> None:
    """Create tables and version markers in one transaction, including on retry."""
    con.execute("BEGIN IMMEDIATE")
    try:
        if validate_schema(con, schema, allow_empty=True):
            # executescript commits an existing transaction; execute complete
            # statements individually so DDL and version markers are atomic.
            statement = ""
            for line in schema.splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    con.execute(statement)
                    statement = ""
            con.execute(f"PRAGMA application_id={identity(schema)}")
            con.execute(f"PRAGMA user_version={VERSION}")
        con.commit()
    except BaseException:
        con.rollback()
        raise


def legacy_tables(con: sqlite3.Connection, schema: str) -> tuple[str, ...]:
    """Recognize only the published unversioned layouts, without executing them."""
    identity(schema)
    if con.execute("PRAGMA user_version").fetchone()[0] != 0:
        raise CasfError("migration requires unversioned storage; use backup for versioned stores")
    if con.execute("PRAGMA application_id").fetchone()[0] != 0:
        raise CasfError("unsupported legacy storage identity")
    baseline = expected(legacy.WRITER if schema == WRITER else legacy.WITNESS)
    optional = "checkpoint_schedule" if schema == WRITER else "w_status"
    earlier = tuple(entry for entry in baseline if entry[1] != optional)
    actual = objects(con)
    if actual not in (baseline, earlier):
        raise CasfError("unrecognized legacy storage schema")
    check_integrity(con)
    # Parent tables precede their dependents. Names are constants, not input SQL.
    order = (("manifests", "heads", "records", "checkpoints", "receipts", "outbox",
              "checkpoint_schedule") if schema == WRITER else
             ("manifests", "w_state", "w_status", "w_checkpoints", "w_receipts",
              "w_record_digests"))
    names = {entry[1] for entry in actual if entry[0] == "table"}
    return tuple(name for name in order if name in names)
