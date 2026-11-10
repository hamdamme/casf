"""R04/R09/R10: immutable request snapshots and explicit append results."""

import pytest

from casf.writer import Writer
from tests.unit.test_event_models import EVENT_ID, event
from tests.unit.test_writer import LOG, LOG_ID, _writer


def test_append_copies_nested_input_before_digest_and_lock(tmp_path, monkeypatch):
    path = tmp_path / "writer.db"
    writer = _writer(path)
    values = event()
    original = writer._append_once

    def mutate(log_id, request, digest):
        values["payload"]["items"][0]["value"] = "changed"
        values["attributes"]["labels"].append("changed")
        return original(log_id, request, digest)

    monkeypatch.setattr(writer, "_append_once", mutate)
    try:
        record = writer.append(LOG_ID, **values)
        assert record["body"]["payload"] == event()["payload"]
        assert record["body"]["attributes"] == event()["attributes"]
    finally:
        writer.close()
    reopened = Writer(path, LOG, local_only=True)
    try:
        assert reopened.append(LOG_ID, **event()) == record
    finally:
        reopened.close()


def test_typed_append_reports_a_committed_local_record(tmp_path):
    from casf.writer import AppendResult, EventRequest, WitnessState

    writer = _writer(tmp_path / "writer.db")
    try:
        result = writer.append_event(LOG_ID, EventRequest(**event()))
        assert isinstance(result, AppendResult)
        assert result.committed is True
        assert result.witness_state is WitnessState.COMMITTED_LOCAL
        assert result.record["body"]["seq"] == 1
        assert writer.append(LOG_ID, **event()) == result.record
    finally:
        writer.close()


@pytest.mark.parametrize("change", [
    {"event_id": EVENT_ID + "\n"}, {"event_id": "not-a-uuid"},
    {"event_id": EVENT_ID.upper()}, {"actor": None}, {"actor": "é" * 129},
    {"event_type": "x" * 257}, {"payload": []}, {"attributes": None},
    {"payload": {"bad": 1.5}}, {"payload": {"bad": 9007199254740992}},
    {"payload": {"bad": "\ud800"}}, {"payload": {"bad": b"bytes"}},
    {"payload": {"large": "x" * 32769}},
])
def test_invalid_requests_fail_before_a_write_transaction(tmp_path, change):
    from casf.errors import CasfError
    from casf.writer import EventRequest

    values = event(**change)
    with pytest.raises(CasfError):
        EventRequest(**values)
    writer = _writer(tmp_path / "writer.db")
    statements = []
    writer._db.connection.set_trace_callback(statements.append)
    try:
        with pytest.raises(CasfError):
            writer.append(LOG_ID, **values)
        assert not any(sql.startswith("BEGIN") for sql in statements)
        assert list(writer.records(LOG_ID)) == []
    finally:
        writer.close()


def test_result_owns_record_bytes_and_is_immutable(tmp_path):
    from dataclasses import FrozenInstanceError

    from casf.writer import EventRequest, WitnessState

    writer = _writer(tmp_path / "writer.db")
    try:
        result = writer.append_event(LOG_ID, EventRequest(**event()))
        record = result.record
        serialized = result.to_dict()
        record["body"]["payload"]["items"].clear()
        serialized["record"]["body"]["attributes"].clear()
        assert result.record["body"]["payload"] == event()["payload"]
        assert result.record["body"]["attributes"] == event()["attributes"]
        assert result.to_dict()["committed"] is True
        with pytest.raises(FrozenInstanceError):
            result.witness_state = WitnessState.WITNESSED
        assert "original" not in repr(result)
    finally:
        writer.close()


@pytest.fixture
def witness(tmp_path):
    from casf import crypto
    from casf.witness import Witness
    from tests.status import register_active
    from tests.unit.test_writer import AUTH, AUTH_PUB, WIT, _manifest_envelope

    instance = Witness(tmp_path / "witness.db", WIT,
                       authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(instance, _manifest_envelope(), AUTH)
    try:
        yield instance
    finally:
        instance.close()


@pytest.mark.parametrize("final", [False, True])
def test_idempotent_retry_refreshes_witness_observation_without_changing_record(tmp_path, witness, final):
    from casf.writer import EventRequest, WitnessState

    writer = _writer(tmp_path / "writer.db")
    request = EventRequest(**event())
    try:
        local = writer.append_event(LOG_ID, request)
        checkpoint = writer.create_checkpoint(LOG_ID, final=final)
        pending = writer.append_event(LOG_ID, request)
        assert pending.witness_state is WitnessState.PENDING_WITNESS
        writer.record_receipt(LOG_ID, witness.submit(LOG_ID, checkpoint, [local.record]))
        accepted = writer.append_event(LOG_ID, request)
        assert accepted.witness_state is WitnessState.WITNESSED
        assert local.record == pending.record == accepted.record
        assert local.witness_state is WitnessState.COMMITTED_LOCAL
        assert pending.witness_state is WitnessState.PENDING_WITNESS
        assert len(list(writer.records(LOG_ID))) == 1
    finally:
        writer.close()


def test_pending_checkpoint_does_not_cover_later_appends(tmp_path, witness):
    from casf.writer import EventRequest, WitnessState

    writer = _writer(tmp_path / "writer.db")
    first, second = EventRequest(**event()), EventRequest(**event(event_id=EVENT_ID[:-1] + "2"))
    try:
        one = writer.append_event(LOG_ID, first)
        checkpoint = writer.create_checkpoint(LOG_ID)
        two = writer.append_event(LOG_ID, second)
        assert two.witness_state is WitnessState.COMMITTED_LOCAL
        assert writer.append_event(LOG_ID, first).witness_state is WitnessState.PENDING_WITNESS
        writer.record_receipt(LOG_ID, witness.submit(LOG_ID, checkpoint, [one.record]))
        assert writer.append_event(LOG_ID, first).witness_state is WitnessState.WITNESSED
        assert writer.append_event(LOG_ID, second).witness_state is WitnessState.COMMITTED_LOCAL
    finally:
        writer.close()


def test_event_conflict_does_not_consume_a_sequence(tmp_path):
    from casf.writer import EventIdConflictError, EventRequest

    writer = _writer(tmp_path / "writer.db")
    try:
        writer.append_event(LOG_ID, EventRequest(**event()))
        with pytest.raises(EventIdConflictError):
            writer.append_event(LOG_ID, EventRequest(**event(payload={"changed": True})))
        second = writer.append_event(LOG_ID, EventRequest(**event(event_id=EVENT_ID[:-1] + "2")))
        assert second.record["body"]["seq"] == 2
    finally:
        writer.close()


def test_failed_commit_returns_no_success_and_can_retry(tmp_path):
    import sqlite3

    from casf.writer import EventRequest

    writer = _writer(tmp_path / "writer.db")
    con = writer._db.connection
    request = EventRequest(**event())

    def deny_commit(action, arg1, _arg2, _database, _source):
        return (sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION and arg1 == "COMMIT"
                else sqlite3.SQLITE_OK)

    con.set_authorizer(deny_commit)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            writer.append_event(LOG_ID, request)
        assert not con.in_transaction
        assert list(writer.records(LOG_ID)) == []
        con.set_authorizer(None)
        assert writer.append_event(LOG_ID, request).record["body"]["seq"] == 1
    finally:
        con.set_authorizer(None)
        writer.close()


def test_exception_after_commit_resolves_by_same_event_retry(tmp_path, monkeypatch):
    from casf.writer import EventRequest

    writer = _writer(tmp_path / "writer.db")
    request = EventRequest(**event())

    def uncertain(stage):
        if stage == "after_commit":
            raise OSError("injected uncertain response")

    monkeypatch.setattr(writer, "_debug_hook", uncertain)
    try:
        with pytest.raises(OSError, match="uncertain"):
            writer.append_event(LOG_ID, request)
        result = writer.append_event(LOG_ID, request)
        assert result.committed is True
        assert result.record["body"]["seq"] == 1
        assert len(list(writer.records(LOG_ID))) == 1
    finally:
        writer.close()


def test_typed_append_never_submits_network_requests(tmp_path, monkeypatch):
    from casf.writer import EventRequest

    def forbidden(*args, **kwargs):
        pytest.fail("append attempted network I/O")

    monkeypatch.setattr("casf.writer.http_request", forbidden)
    writer = _writer(tmp_path / "writer.db")
    try:
        assert writer.append_event(LOG_ID, EventRequest(**event())).committed is True
    finally:
        writer.close()


def test_typeless_request_and_keyless_writer_cannot_return_success(tmp_path):
    from casf.errors import CasfError, SchemaError
    from casf.writer import EventRequest

    writer = _writer(tmp_path / "writer.db")
    try:
        with pytest.raises(SchemaError, match="EventRequest"):
            writer.append_event(LOG_ID, event())
    finally:
        writer.close()
    reader = Writer(tmp_path / "writer.db")
    try:
        with pytest.raises(CasfError):
            reader.append_event(LOG_ID, EventRequest(**event()))
        assert list(reader.records(LOG_ID)) == []
    finally:
        reader.close()


def test_body_budget_includes_generated_record_fields_before_signing(tmp_path, monkeypatch):
    from casf.canonical.jcs import canonicalize
    from casf.canonical.limits import MAX_CANONICAL_BODY_BYTES
    from casf.errors import LimitError
    from casf.writer import EventRequest

    values = event(payload={"a": "", "b": ""}, attributes={})
    length = (MAX_CANONICAL_BODY_BYTES - len(canonicalize(values)) - 1) // 2
    values["payload"] = {"a": "x" * length, "b": "x" * length}
    request = EventRequest(**values)  # request fits; generated body fields do not
    writer = _writer(tmp_path / "writer.db")
    try:
        with monkeypatch.context() as patch:
            patch.setattr("casf.crypto.sign_record", lambda *a: pytest.fail("signed oversized body"))
            with pytest.raises(LimitError, match="record body"):
                writer.append_event(LOG_ID, request)
        assert list(writer.records(LOG_ID)) == []
        assert writer.append_event(LOG_ID, EventRequest(**event())).record["body"]["seq"] == 1
    finally:
        writer.close()


def test_busy_typed_append_does_not_report_a_commit(tmp_path):
    import sqlite3

    from casf.writer import BusyError, EventRequest

    path = tmp_path / "writer.db"
    writer = _writer(path, busy_timeout_ms=0, max_retries=1)
    blocker = sqlite3.connect(path)
    blocker.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(BusyError):
            writer.append_event(LOG_ID, EventRequest(**event()))
        assert list(writer.records(LOG_ID)) == []
    finally:
        blocker.rollback()
        blocker.close()
        writer.close()


def _typed_process(path, queue):
    from casf.writer import EventRequest

    writer = Writer(path, LOG, local_only=True)
    try:
        queue.put(writer.append_event(LOG_ID, EventRequest(**event())).to_dict())
    finally:
        writer.close()


def test_concurrent_typed_retries_return_one_identical_record(tmp_path):
    from tests.unit.test_writer import MP

    path = tmp_path / "writer.db"
    _writer(path).close()
    queue = MP.Queue()
    processes = [MP.Process(target=_typed_process, args=(path, queue)) for _ in range(2)]
    try:
        for process in processes:
            process.start()
        results = [queue.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(30)
            assert process.exitcode == 0
        assert results[0] == results[1]
        assert results[0]["committed"] is True
        assert results[0]["record"]["body"]["seq"] == 1
        reader = Writer(path)
        try:
            assert len(list(reader.records(LOG_ID))) == 1
        finally:
            reader.close()
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(5)
        queue.close()
        queue.join_thread()


@pytest.mark.parametrize("field, replacement", [
    ("record_hash", "ab"), ("record_hash", "AB" * 32), ("signature", ""),
    ("signature", "AA"), ("body", {}),
])
def test_result_rejects_malformed_envelope_fields(tmp_path, field, replacement):
    from casf.errors import SchemaError
    from casf.writer import AppendResult, EventRequest, WitnessState

    writer = _writer(tmp_path / "writer.db")
    try:
        record = writer.append_event(LOG_ID, EventRequest(**event())).record
        record[field] = replacement
        with pytest.raises(SchemaError):
            AppendResult(record, WitnessState.COMMITTED_LOCAL)
    finally:
        writer.close()
