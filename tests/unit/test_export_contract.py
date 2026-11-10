"""R03/R09: prefix exports and atomic publication without replacement."""

import os

import pytest

from casf.bundle import read_bundle
from casf.errors import CasfError, SchemaError
from casf.writer import Writer
from tests.unit.test_writer import LOG_ID, _append, _writer


def test_publication_preserves_destination_created_after_file_writes(tmp_path, monkeypatch):
    writer = _writer(tmp_path / "writer.db")
    dest = tmp_path / "bundle"
    original = writer._write_member
    inode = []

    def competing(path, data):
        original(path, data)
        if path.name == "export.json":
            dest.mkdir()
            inode.append(dest.stat().st_ino)

    monkeypatch.setattr(writer, "_write_member", competing)
    try:
        with pytest.raises(CasfError, match="already exists"):
            writer.export_bundle(LOG_ID, dest)
        assert dest.stat().st_ino == inode[0]
        assert list(dest.iterdir()) == []
    finally:
        writer.close()


@pytest.mark.parametrize("through", [0, 1, 3])
def test_export_selects_exact_prefix(tmp_path, through):
    writer = _writer(tmp_path / "writer.db")
    try:
        for n in range(1, 4):
            _append(writer, n)
        dest = writer.export_bundle(LOG_ID, tmp_path / "bundle", through=through)
        bundle = read_bundle(dest)
        assert [r["body"]["seq"] for r in bundle.records] == list(range(1, through + 1))
        assert bundle.metadata["through"] == bundle.metadata["record_count"] == through
        assert len(list(writer.records(LOG_ID))) == 3
    finally:
        writer.close()


@pytest.mark.parametrize("through", [-1, True, 1.5, "1", 9007199254740992, 2])
def test_invalid_prefix_never_publishes_a_bundle(tmp_path, through):
    writer = _writer(tmp_path / "writer.db")
    try:
        _append(writer)
        dest = tmp_path / "bundle"
        with pytest.raises(SchemaError):
            writer.export_bundle(LOG_ID, dest, through=through)
        assert not dest.exists()
        assert not writer._db.connection.in_transaction
    finally:
        writer.close()


@pytest.fixture
def witnessed(tmp_path):
    from casf import crypto
    from casf.witness import Witness
    from tests.status import register_active
    from tests.unit.test_writer import AUTH, AUTH_PUB, WIT, _manifest_envelope

    writer = _writer(tmp_path / "writer.db")
    witness = Witness(tmp_path / "witness.db", WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(witness, _manifest_envelope(), AUTH)
    try:
        for n in range(1, 4):
            record = _append(writer, n)
            cp = writer.create_checkpoint(LOG_ID, final=n == 3)
            writer.record_receipt(LOG_ID, witness.submit(LOG_ID, cp, [record]))
        yield writer
    finally:
        writer.close()
        witness.close()


@pytest.mark.parametrize("through", [0, 1, 2, 3, None])
def test_prefix_limits_journal_and_preserves_exact_blobs(witnessed, tmp_path, through):
    writer = witnessed
    count = 3 if through is None else through
    dest = writer.export_bundle(LOG_ID, tmp_path / "bundle", through=through)
    con = writer._db.connection
    expected = {
        "manifest.json": con.execute("SELECT envelope FROM manifests").fetchone()[0] + b"\n",
        "records.jsonl": b"".join(row[0] + b"\n" for row in con.execute(
            "SELECT envelope FROM records WHERE seq<=? ORDER BY seq", (count,))),
        "checkpoints.jsonl": b"".join(row[0] + b"\n" for row in con.execute(
            "SELECT envelope FROM checkpoints WHERE count<=? ORDER BY idx", (count,))),
        "receipts.jsonl": b"".join(row[0] + b"\n" for row in con.execute(
            "SELECT r.envelope FROM receipts r JOIN checkpoints c "
            "ON r.checkpoint_hash=c.checkpoint_hash WHERE c.count<=? ORDER BY c.idx", (count,))),
    }
    assert {name: (dest / name).read_bytes() for name in expected} == expected
    bundle = read_bundle(dest)
    assert all(cp["body"]["count"] <= count for cp in bundle.checkpoints)
    assert bool(bundle.checkpoints and bundle.checkpoints[-1]["body"]["final"]) == (count == 3)
    if count:
        from casf.verifier import Mode, Result, verify
        from tests.status import active_status
        from tests.unit.test_bundle import _pins
        from tests.unit.test_writer import AUTH

        report = verify(bundle.manifest, bundle.records, _pins(bundle.manifest_hash),
                        mode=Mode.ANCHORED, checkpoint_envelopes=bundle.checkpoints,
                        receipt_envelopes=bundle.receipts,
                        status_envelopes=[active_status(AUTH, bundle.manifest_hash)])
        assert report.result is Result.PASS
        assert report.verified_through == report.witnessed_through == count


@pytest.mark.parametrize("through", [0, None])
def test_pending_final_seal_blocks_every_export_prefix(tmp_path, through):
    writer = _writer(tmp_path / "writer.db")
    try:
        _append(writer)
        writer.seal_log(LOG_ID)
        with pytest.raises(CasfError, match="final checkpoint receipt is pending"):
            writer.export_bundle(LOG_ID, tmp_path / "bundle", through=through)
        assert not (tmp_path / "bundle").exists()
    finally:
        writer.close()


@pytest.mark.parametrize("destination", ["file", "empty_directory", "directory", "symlink"])
def test_export_preserves_every_existing_destination(tmp_path, destination):
    writer = _writer(tmp_path / "writer.db")
    dest = tmp_path / "bundle"
    if destination == "file":
        dest.write_bytes(b"retained")
    elif destination == "symlink":
        dest.symlink_to(tmp_path / "missing")
    else:
        dest.mkdir()
        if destination == "directory":
            (dest / "retained").write_bytes(b"retained")
    inode = dest.lstat().st_ino
    try:
        with pytest.raises(CasfError, match="already exists"):
            writer.export_bundle(LOG_ID, dest)
        assert dest.lstat().st_ino == inode
    finally:
        writer.close()


@pytest.mark.parametrize("stage", ["write", "directory_flush", "rename", "parent_flush"])
def test_export_failure_never_leaves_a_partial_destination(tmp_path, monkeypatch, stage):
    from casf.filesystem import sync_directory

    writer = _writer(tmp_path / "writer.db")
    _append(writer)
    dest = tmp_path / "bundle"

    def fail(*args):
        raise OSError("injected publication failure")

    def flush(path):
        if (stage == "directory_flush" and path.name == "bundle") or (
                stage == "parent_flush" and path == dest.parent):
            fail()
        sync_directory(path)

    if stage == "write":
        monkeypatch.setattr(writer, "_write_member", fail)
    elif stage == "rename":
        monkeypatch.setattr("casf.writer.rename_directory_exclusive", fail)
    else:
        monkeypatch.setattr("casf.writer.sync_directory", flush)
    try:
        with pytest.raises(OSError, match="injected"):
            writer.export_bundle(LOG_ID, dest)
        assert not writer._db.connection.in_transaction
        assert len(list(writer.records(LOG_ID))) == 1
        assert not list(tmp_path.glob(".casf-export-*"))
        if stage == "parent_flush":
            assert len(read_bundle(dest).records) == 1
            with pytest.raises(CasfError, match="already exists"):
                writer.export_bundle(LOG_ID, dest)
        else:
            assert not dest.exists()
    finally:
        writer.close()


def test_failed_export_keeps_unrelated_old_temporary_directory(tmp_path):
    writer = _writer(tmp_path / "writer.db")
    stale = tmp_path / f"bundle.tmp-{os.getpid()}"
    stale.mkdir()
    (stale / "owner-data").write_bytes(b"retained")
    try:
        writer.export_bundle(LOG_ID, tmp_path / "bundle")
        assert (stale / "owner-data").read_bytes() == b"retained"
    finally:
        writer.close()


def test_export_checks_every_accepted_receipt(witnessed, tmp_path):
    con = witnessed._db.connection
    con.execute("DELETE FROM receipts")
    con.commit()
    dest = tmp_path / "bundle"
    with pytest.raises(CasfError, match="missing its receipt"):
        witnessed.export_bundle(LOG_ID, dest)
    assert not dest.exists()


def _crash_export(db, dest, stage):
    import casf.writer as module

    writer = Writer(db)
    if stage == "files":
        original = writer._write_member

        def write(path, data):
            original(path, data)
            if path.name == "records.jsonl":
                os._exit(78)

        writer._write_member = write
    elif stage == "publication":
        module.rename_directory_exclusive = lambda *args: os._exit(78)
    else:
        original = module.sync_directory

        def flush(path):
            if path == dest.parent:
                os._exit(78)
            original(path)

        module.sync_directory = flush
    writer.export_bundle(LOG_ID, dest)


@pytest.mark.parametrize("stage", ["files", "publication", "parent_flush"])
def test_process_exit_preserves_source_and_never_publishes_partial_bundle(tmp_path, stage):
    from tests.unit.test_writer import MP

    db, dest = tmp_path / "writer.db", tmp_path / "bundle"
    writer = _writer(db)
    _append(writer)
    writer.close()
    before = db.read_bytes()
    process = MP.Process(target=_crash_export, args=(db, dest, stage))
    process.start()
    process.join(30)
    if process.is_alive():
        process.terminate()
        process.join(5)
        pytest.fail("export child did not exit")
    assert process.exitcode == 78
    assert db.read_bytes() == before
    if stage == "parent_flush":
        assert len(read_bundle(dest).records) == 1
    else:
        assert not dest.exists()
        reader = Writer(db)
        try:
            reader.export_bundle(LOG_ID, dest)
            assert len(read_bundle(dest).records) == 1
        finally:
            reader.close()


def test_export_memory_does_not_materialize_record_history(tmp_path):
    import tracemalloc

    writer = _writer(tmp_path / "writer.db")
    try:
        for n in range(160):
            writer.append(LOG_ID, event_id=f"123e4567-e89b-42d3-a456-4266{n:08d}",
                          actor="test", event_type="export-memory", payload={"data": "x" * 8192},
                          attributes={})
        size = writer._db.connection.execute("SELECT SUM(length(envelope)) FROM records").fetchone()[0]
        tracemalloc.start()
        try:
            dest = writer.export_bundle(LOG_ID, tmp_path / "bundle")
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert peak < size // 2
        assert len(read_bundle(dest).records) == 160
    finally:
        writer.close()
