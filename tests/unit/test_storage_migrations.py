"""R04/R08/R09: constrained stores and byte-preserving copy migration."""

import sqlite3
from pathlib import Path

import pytest

from casf.errors import CasfError
from casf.storage import Database
from casf.witness import SCHEMA as WITNESS_SCHEMA
from casf.witness import Witness
from casf.writer import Writer
from tests.unit.test_writer import LOG, LOG_ID, WIT, _append, _writer

FIXTURES = Path(__file__).parents[1] / "fixtures" / "storage-v0"


def legacy(path, kind):
    with sqlite3.connect(path) as con:
        con.executescript((FIXTURES / f"{kind}.sql").read_text())
    return path


def rows(path):
    with sqlite3.connect(path) as con:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {name: con.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
                for name in names}


@pytest.mark.parametrize("kind, schema, identity", [
    ("writer", None, 0x43415346), ("witness", WITNESS_SCHEMA, 0x43415357),
], ids=["writer", "witness"])
def test_new_store_has_identity_version_and_relationships(tmp_path, kind, schema, identity):
    db = Database(tmp_path / f"{kind}.db", **({"schema": schema} if schema else {}))
    try:
        con = db.connection
        assert con.execute("PRAGMA user_version").fetchone() == (1,)
        assert con.execute("PRAGMA application_id").fetchone() == (identity,)
        table = "records" if kind == "writer" else "w_state"
        assert con.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    finally:
        db.close()


def test_unversioned_store_requires_explicit_migration(tmp_path):
    source = legacy(tmp_path / "old.db", "writer")
    before = source.read_bytes()
    with pytest.raises(CasfError, match="migration"):
        Database(source)
    assert source.read_bytes() == before


@pytest.mark.parametrize("kind", ["writer", "witness"])
def test_migration_preserves_every_row_and_authenticated_byte(tmp_path, kind):
    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", kind)
    before = source.read_bytes()
    original = rows(source)
    dest = tmp_path / "new.db"
    migrate_database(source, dest, kind=kind)
    assert source.read_bytes() == before
    assert rows(dest) == original
    assert dest.stat().st_mode & 0o777 == 0o600
    if kind == "writer":
        writer = Writer(dest, LOG, local_only=True)
        try:
            assert len(list(writer.records(LOG_ID))) == 2
            assert writer.pending_checkpoint(LOG_ID)[0]["body"]["final"] is True
            assert writer._db.connection.execute("SELECT attempts FROM outbox").fetchone() == (3,)
        finally:
            writer.close()
    else:
        witness = Witness(dest, WIT)
        try:
            assert witness._db.connection.execute("SELECT sealed FROM w_state").fetchone() == (1,)
        finally:
            witness.close()


def test_constraints_reject_orphans_and_invalid_values(tmp_path):
    writer = _writer(tmp_path / "writer.db")
    try:
        con = writer._db.connection
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO receipts VALUES (?, ?)", ("ab" * 32, b"{}"))
        for sql in ("UPDATE heads SET count=-1", "UPDATE heads SET count=1.5",
                    "UPDATE heads SET sealed=4", "UPDATE heads SET head_hash='ab'",
                    "UPDATE heads SET head_hash='AB' || substr(head_hash,3)"):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(sql)
            con.rollback()
        _append(writer)
    finally:
        writer.close()


@pytest.mark.parametrize("change, message", [
    ("PRAGMA user_version=2", "version"),
    ("PRAGMA application_id=1128354647", "identity"),
    ("DROP TRIGGER records_no_delete", "schema"),
    ("CREATE TABLE sqliteXextra(value)", "schema"),
])
def test_open_refuses_changed_schema_without_modifying_it(tmp_path, change, message):
    path = tmp_path / "writer.db"
    _writer(path).close()
    with sqlite3.connect(path) as con:
        con.execute(change)
    before = path.read_bytes()
    with pytest.raises(CasfError, match=message):
        Database(path)
    assert path.read_bytes() == before


def test_open_detects_foreign_key_violation_written_outside_adapter(tmp_path):
    path = tmp_path / "writer.db"
    _writer(path).close()
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO receipts VALUES (?, ?)", ("ab" * 32, b"{}"))
    with pytest.raises(CasfError, match="foreign-key"):
        Database(path)


def test_open_detects_disabled_check_constraints(tmp_path):
    path = tmp_path / "writer.db"
    _writer(path).close()
    with sqlite3.connect(path) as con:
        con.execute("PRAGMA ignore_check_constraints=ON")
        con.execute("UPDATE heads SET count=-1")
    with pytest.raises(CasfError, match="integrity"):
        Database(path)


@pytest.mark.parametrize("kind, optional", [
    ("writer", "checkpoint_schedule"), ("witness", "w_status"),
])
def test_migration_supports_earlier_layout_without_inventing_state(tmp_path, kind, optional):
    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", kind)
    with sqlite3.connect(source) as con:
        con.execute(f"DROP TABLE {optional}")
    expected = rows(source)
    dest = tmp_path / "new.db"
    migrate_database(source, dest, kind=kind)
    assert rows(dest) == {**expected, optional: []}


@pytest.mark.parametrize("change, kind", [
    ("INSERT INTO receipts VALUES ('" + "ab" * 32 + "', X'7B7D')", "writer"),
    ("UPDATE heads SET count=-1", "writer"),
    ("UPDATE outbox SET attempts=-1", "writer"),
    ("UPDATE outbox SET next_attempt_at=1e999", "writer"),
    ("UPDATE outbox SET from_seq=10", "writer"),
    ("UPDATE w_state SET sealed=9", "witness"),
    ("UPDATE w_state SET head_hash='short'", "witness"),
    ("INSERT INTO w_receipts VALUES ('" + "ab" * 32 + "', X'7B7D')", "witness"),
])
def test_failed_migration_retains_source_and_publishes_nothing(tmp_path, change, kind):
    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", kind)
    with sqlite3.connect(source) as con:
        con.execute(change)
    before = source.read_bytes()
    dest = tmp_path / "new.db"
    with pytest.raises(sqlite3.IntegrityError):
        migrate_database(source, dest, kind=kind)
    assert source.read_bytes() == before
    assert not dest.exists()
    assert not list(tmp_path.glob(".casf-*-*"))


@pytest.mark.parametrize("change, kind", [
    ("CREATE TABLE extra(secret BLOB)", "writer"),
    ("PRAGMA user_version=99", "writer"),
    ("PRAGMA application_id=1", "writer"),
    ("DROP TRIGGER records_no_update", "writer"),
    ("", "witness"),
    ("", "invalid"),
])
def test_migration_refuses_unknown_versions_layouts_and_kinds(tmp_path, change, kind):
    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", "writer")
    with sqlite3.connect(source) as con:
        if change:
            con.execute(change)
    before = source.read_bytes()
    dest = tmp_path / "new.db"
    with pytest.raises(CasfError):
        migrate_database(source, dest, kind=kind)
    assert source.read_bytes() == before
    assert not dest.exists()


def test_versioned_store_uses_backup_instead_of_migration(tmp_path):
    from casf.storage import migrate_database

    path = tmp_path / "writer.db"
    _writer(path).close()
    with pytest.raises(CasfError, match="use backup"):
        migrate_database(path, tmp_path / "new.db", kind="writer")


def test_migration_includes_committed_wal_content(tmp_path):
    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", "writer")
    con = sqlite3.connect(source)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA wal_autocheckpoint=0")
        con.execute("UPDATE outbox SET attempts=7")
        con.commit()
        assert Path(str(source) + "-wal").stat().st_size > 0
        dest = tmp_path / "new.db"
        migrate_database(source, dest, kind="writer")
        assert rows(dest) == rows(source)
    finally:
        con.close()


@pytest.mark.parametrize("destination", ["source", "file", "symlink", "directory"])
def test_migration_never_overwrites_a_destination(tmp_path, destination):
    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", "writer")
    dest = tmp_path / "new.db"
    if destination == "source":
        dest = source
    elif destination == "file":
        dest.write_bytes(b"retained")
    elif destination == "symlink":
        dest.symlink_to(tmp_path / "missing.db")
    else:
        dest.mkdir()
    before = source.read_bytes()
    with pytest.raises(CasfError, match="destination already exists"):
        migrate_database(source, dest, kind="writer")
    assert source.read_bytes() == before
    if destination == "file":
        assert dest.read_bytes() == b"retained"
    if destination == "symlink":
        assert dest.is_symlink()


def test_failed_publication_retains_source(tmp_path, monkeypatch):
    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", "writer")
    before = source.read_bytes()
    dest = tmp_path / "new.db"

    def fail(*args):
        raise OSError("injected publication failure")

    monkeypatch.setattr("casf.storage.os.link", fail)
    with pytest.raises(OSError, match="injected"):
        migrate_database(source, dest, kind="writer")
    assert source.read_bytes() == before
    assert not dest.exists()
    assert not list(tmp_path.glob(".casf-*-*"))


def _interrupted_migration(source, dest, stage):
    import os

    from casf.storage import migrate_database, versioning

    if stage == "before_commit":
        original = versioning.check_integrity

        def interrupt(con):
            if con.execute("PRAGMA user_version").fetchone() == (1,):
                assert con.in_transaction
                assert con.execute("SELECT count(*) FROM records").fetchone() == (2,)
                os._exit(77)
            original(con)

        versioning.check_integrity = interrupt
    else:
        def stop(self, destination):
            os._exit(77)

        Database.backup = stop
    migrate_database(source, dest, kind="writer")


@pytest.mark.parametrize("stage", ["before_commit", "before_publication"])
def test_process_exit_keeps_legacy_source_and_allows_retry(tmp_path, stage):
    from casf.storage import migrate_database
    from tests.unit.test_writer import MP

    source = legacy(tmp_path / "old.db", "writer")
    before = source.read_bytes()
    dest = tmp_path / "new.db"
    process = MP.Process(target=_interrupted_migration, args=(source, dest, stage))
    process.start()
    process.join(30)
    if process.is_alive():
        process.terminate()
        process.join(5)
        pytest.fail("migration child did not exit")
    assert process.exitcode == 77
    assert source.read_bytes() == before
    assert not dest.exists()
    migrate_database(source, dest, kind="writer")
    assert rows(dest) == rows(source)


def test_initialization_rolls_back_schema_and_markers_together(tmp_path):
    from casf.storage.schema import WRITER
    from casf.storage.versioning import initialize

    class FailingConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql.startswith("PRAGMA user_version="):
                raise sqlite3.OperationalError("injected version write failure")
            return super().execute(sql, parameters)

    path = tmp_path / "new.db"
    con = sqlite3.connect(path, factory=FailingConnection)
    try:
        with pytest.raises(sqlite3.OperationalError, match="injected"):
            initialize(con, WRITER)
        assert con.execute("SELECT name FROM sqlite_master").fetchall() == []
        assert con.execute("PRAGMA application_id").fetchone() == (0,)
        assert not con.in_transaction
    finally:
        con.close()
    Database(path).close()


@pytest.mark.parametrize("table", ["outbox", "checkpoint_schedule"])
def test_checkpoint_references_cannot_cross_logs(tmp_path, table):
    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", "writer")
    dest = tmp_path / "new.db"
    migrate_database(source, dest, kind="writer")
    db = Database(dest)
    try:
        con = db.connection
        other = "123e4567-e89b-42d3-a456-426600000099"
        con.execute("INSERT INTO manifests VALUES (?, ?, ?)", (other, "ab" * 32, b"{}"))
        con.commit()
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            con.execute(f"UPDATE {table} SET log_id=?", (other,))
        con.rollback()
    finally:
        db.close()


@pytest.mark.parametrize("sql, values", [
    ("INSERT INTO manifests VALUES (?, ?, ?)", (None, "ab" * 32, b"{}")),
    ("INSERT INTO manifests VALUES (?, ?, ?)", (LOG_ID, "ab", b"{}")),
    ("INSERT INTO manifests VALUES (?, ?, ?)", (LOG_ID, "AB" * 32, b"{}")),
    ("INSERT INTO manifests VALUES (?, ?, ?)", (LOG_ID, "ab" * 32, "{}")),
    ("INSERT INTO manifests VALUES (?, ?, ?)", (LOG_ID, "ab" * 32, b"")),
    ("INSERT INTO w_state VALUES (?, 0, ?, -1, ?, ?, 0)",
     (LOG_ID, "ab" * 32, "00" * 32, "00" * 32)),
    ("INSERT INTO w_status VALUES (?, 1, 'active')", ("ab" * 32,)),
    ("INSERT INTO w_checkpoints VALUES (?, 0, ?, ?)", (LOG_ID, "ab" * 32, b"{}")),
    ("INSERT INTO w_receipts VALUES (?, ?)", ("ab" * 32, b"{}")),
    ("INSERT INTO w_record_digests VALUES (?, 1, ?)", (LOG_ID, "ab" * 32)),
])
def test_witness_rejects_invalid_keys_blobs_and_orphans(tmp_path, sql, values):
    db = Database(tmp_path / "witness.db", schema=WITNESS_SCHEMA)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            db.connection.execute(sql, values)
        db.connection.rollback()
    finally:
        db.close()


def test_migrated_pair_replays_pending_final_receipt_without_resigning(tmp_path):
    import json

    from casf.storage import migrate_database
    from casf.writer import SealedError

    for kind in ("writer", "witness"):
        migrate_database(legacy(tmp_path / f"old-{kind}.db", kind),
                         tmp_path / f"{kind}.db", kind=kind)
    writer = Writer(tmp_path / "writer.db", LOG, local_only=True)
    witness = Witness(tmp_path / "witness.db", WIT)
    try:
        checkpoint, start, stop = writer.pending_checkpoint(LOG_ID)
        stored = witness._db.connection.execute(
            "SELECT envelope FROM w_receipts WHERE checkpoint_hash=?",
            (checkpoint["checkpoint_hash"],)).fetchone()[0]
        receipt = witness.submit(LOG_ID, checkpoint,
                                 list(writer.records(LOG_ID))[start - 1:stop])
        assert receipt == json.loads(stored)
        writer.record_receipt(LOG_ID, receipt)
        assert writer.pending_checkpoint(LOG_ID) is None
        with pytest.raises(SealedError):
            _append(writer, 3)
    finally:
        writer.close()
        witness.close()


def test_destination_created_during_migration_is_retained(tmp_path, monkeypatch):
    import os

    from casf.storage import migrate_database

    source = legacy(tmp_path / "old.db", "writer")
    dest = tmp_path / "new.db"
    before = source.read_bytes()
    original = os.link

    def race(src, dst):
        dest.write_bytes(b"concurrent destination")
        original(src, dst)

    monkeypatch.setattr("casf.storage.os.link", race)
    with pytest.raises(CasfError, match="already exists"):
        migrate_database(source, dest, kind="writer")
    assert source.read_bytes() == before
    assert dest.read_bytes() == b"concurrent destination"


def test_missing_source_is_not_created(tmp_path):
    from casf.storage import migrate_database

    source, dest = tmp_path / "missing.db", tmp_path / "new.db"
    with pytest.raises(sqlite3.OperationalError):
        migrate_database(source, dest, kind="writer")
    assert not source.exists()
    assert not dest.exists()
