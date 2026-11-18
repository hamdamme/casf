"""Regressions for the November 14 C01-C06 findings; synthetic material only."""

import argparse
import json
import sqlite3
import time

import pytest
from cryptography.hazmat.primitives import serialization

from casf import crypto
from casf.cli import _cmd_admin_trust, _load_trust
from casf.errors import (
    CasfError,
    EvidenceError,
    InconclusiveError,
    SchemaError,
    TrustError,
    WitnessResponseError,
)
from casf.model.schema import _check_timestamp
from casf.online import fetch_latest
from casf.storage.versioning import check_integrity
from casf.writer import Writer
from casf.writer.recovery import _lookup
from tests.unit.test_cli import _trust
from tests.unit.test_receipt_recovery import pending_store
from tests.unit.test_writer import AUTH, AUTH_PUB, LOG_ID, _manifest_envelope
from tests.unit.test_writer_trust import _pins


@pytest.mark.parametrize("field", ["created_at", "recorded_at", "issued_at",
                                  "accepted_at", "responded_at", "generated_at"])
@pytest.mark.parametrize("year", ["٢٠٢٦", "２０２６"])
def test_timestamp_requires_ascii(field, year):
    with pytest.raises(SchemaError):
        _check_timestamp(f"{year}-01-01T00:00:00.000000Z", field)
    _check_timestamp("2026-01-01T00:00:00.000000Z", field)


@pytest.mark.parametrize("table,column", [("outbox", "next_attempt_at"),
                                          ("checkpoint_schedule", "next_checkpoint_at")])
@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
def test_integrity_checks_finite_times_without_sql_constraints(table, column, value):
    # Legacy tables and old SQLite CHECK evaluation cannot establish finiteness.
    with sqlite3.connect(":memory:") as con:
        con.execute(f"CREATE TABLE {table}({column} REAL)")
        con.execute(f"INSERT INTO {table} VALUES (?)", (value,))
        assert con.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        with pytest.raises(CasfError, match="finite"):
            check_integrity(con)


@pytest.mark.parametrize("status,error", [(400, SchemaError), (401, TrustError),
    (403, TrustError), (409, EvidenceError), (429, InconclusiveError),
    (503, InconclusiveError), (500, WitnessResponseError)])
@pytest.mark.parametrize("operation", ["latest", "lookup", "receipt"])
def test_read_http_categories(tmp_path, monkeypatch, status, error, operation):
    def response(*args, **kwargs):
        return status, b'synthetic-private-response'
    if operation == "latest":
        monkeypatch.setattr("casf.online.http_request", response)
        call = lambda: fetch_latest("http://127.0.0.1:1", LOG_ID, "synthetic-token")
    elif operation == "lookup":
        monkeypatch.setattr("casf.writer.recovery.http_request", response)
        call = lambda: _lookup("http://127.0.0.1:1", LOG_ID, "synthetic-token",
                               "00" * 32, time.monotonic() + 10)
    else:
        pending_store(tmp_path)
        writer = Writer(tmp_path / "writer.db", trust_pins={LOG_ID: _pins()})
        before = writer.pending_checkpoint(LOG_ID)
        monkeypatch.setattr("casf.writer.http_request", response)
        call = lambda: writer.recover_pending_receipt(
            LOG_ID, "http://127.0.0.1:1", "synthetic-token")
    try:
        with pytest.raises(error) as caught:
            call()
        assert type(caught.value) is error
        assert "synthetic" not in str(caught.value)
        if operation == "receipt":
            assert writer.pending_checkpoint(LOG_ID) == before
    finally:
        if operation == "receipt":
            writer.close()


@pytest.mark.parametrize("key", [b"abc", bytes(32)])
def test_trust_authority_keys_match_identity(tmp_path, key):
    path = _trust(tmp_path, _manifest_envelope())
    data = json.loads(path.read_text())
    data["authorities"] = {crypto.key_id(AUTH_PUB): crypto.b64url_encode(key)}
    path.write_text(json.dumps(data))
    with pytest.raises(SchemaError):
        _load_trust(str(path), LOG_ID)


@pytest.mark.parametrize("case", ["writable_file", "writable_directory", "symlink"])
def test_trust_rejects_unsafe_paths(tmp_path, case):
    path = _trust(tmp_path, _manifest_envelope())
    if case == "writable_file":
        path.chmod(0o666)
    elif case == "writable_directory":
        tmp_path.chmod(0o777)
    else:
        link = tmp_path / "link"
        link.symlink_to(path)
        path = link
    try:
        with pytest.raises(SchemaError):
            _load_trust(str(path), LOG_ID)
    finally:
        tmp_path.chmod(0o700)


def test_public_readable_trust_is_allowed(tmp_path):
    path = _trust(tmp_path, _manifest_envelope())
    path.chmod(0o644)
    assert _load_trust(str(path), LOG_ID)[0]


@pytest.mark.parametrize("url", ["http://example.com", "https://example.com/prefix",
                                 "https://example.com?secret=synthetic"])
def test_admin_rejects_invalid_url_before_publication(tmp_path, url, capsys):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest_envelope()))
    public = tmp_path / "authority.pem"
    public.write_bytes(AUTH.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    output = tmp_path / "trust.json"
    args = argparse.Namespace(manifest=str(manifest), authority_public_key=str(public),
        timeout=10, witness_url=url, mode="online", allow_unwitnessed=False,
        max_chain_steps=1000, out=str(output), json=False)
    with pytest.raises(SchemaError):
        _cmd_admin_trust(args)
    assert not output.exists()
    assert "created trust" not in capsys.readouterr().out


@pytest.mark.parametrize("value", [0.0, 1.5, float.fromhex("0x1.fffffffffffffp+1023")])
def test_finite_schedule_range_unchanged(value):
    with sqlite3.connect(":memory:") as con:
        con.execute("CREATE TABLE outbox(next_attempt_at REAL)")
        con.execute("INSERT INTO outbox VALUES (?)", (value,))
        check_integrity(con)


def test_migration_rejects_infinity_before_destination_creation(tmp_path):
    from casf.storage import migrate_database
    from tests.unit.test_storage_migrations import legacy

    source = legacy(tmp_path / "old.db", "writer")
    with sqlite3.connect(source) as con:
        con.execute("UPDATE outbox SET next_attempt_at=1e999")
    before = source.read_bytes()
    destination = tmp_path / "new.db"
    with pytest.raises(CasfError, match="finite"):
        migrate_database(source, destination, kind="writer")
    assert source.read_bytes() == before
    assert not destination.exists()
    assert not list(tmp_path.glob(".casf-*-*"))


@pytest.mark.parametrize("status,code", [(400, 2), (401, 3), (403, 3), (409, 1),
                                       (429, 4), (503, 4), (500, 5)])
def test_receipt_http_cli_exit_categories(tmp_path, monkeypatch, capsys, status, code):
    from casf.cli import main

    pending_store(tmp_path)
    trust = _trust(tmp_path, _manifest_envelope())
    monkeypatch.setenv("CASF_WITNESS_TOKEN", "synthetic-token")
    monkeypatch.setattr("casf.writer.http_request",
                        lambda *a, **k: (status, b'synthetic-private-response'))
    assert main(["witness", "recover", "--db", str(tmp_path / "writer.db"),
                 "--trust", str(trust), "--url", "http://127.0.0.1:1"]) == code
    captured = capsys.readouterr()
    assert "synthetic" not in captured.out + captured.err


@pytest.mark.parametrize("kind", ["fifo", "directory", "directory_symlink"])
def test_trust_refuses_nonregular_or_redirected_paths(tmp_path, kind):
    import os

    if kind == "fifo":
        path = tmp_path / "pipe"
        os.mkfifo(path, 0o600)
    elif kind == "directory":
        path = tmp_path
    else:
        actual = tmp_path / "actual"
        actual.mkdir()
        _trust(actual, _manifest_envelope())
        link = tmp_path / "redirect"
        link.symlink_to(actual, target_is_directory=True)
        path = link / "trust.json"
    with pytest.raises(SchemaError):
        _load_trust(str(path), LOG_ID)


@pytest.mark.parametrize("status,error", [(401, TrustError), (403, TrustError),
                                        (503, InconclusiveError)])
def test_error_body_cannot_override_status(monkeypatch, status, error):
    monkeypatch.setattr("casf.online.http_request",
                        lambda *a, **k: (status, b'{"code":"NO_CHECKPOINT"}'))
    with pytest.raises(error):
        fetch_latest("http://127.0.0.1:1", LOG_ID, "synthetic-token")
