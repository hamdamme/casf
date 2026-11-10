"""R05/R09/R11: the real CLI distinguishes committed, pending and witnessed work."""

import json
import sqlite3

from casf.cli import main
from tests.unit import test_cli_verified_startup as startup
from tests.unit.test_cli import _event

environment = startup.setup


def test_cli_worker_once_reports_pending_then_witnessed(environment, tmp_path, capsys):
    common, _, _, _, _, _ = environment
    assert startup.initialize(environment) == 0
    capsys.readouterr()
    args = ["witness", "work", *common, "--once"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "witnessed"
    assert main(["append", *common, "--event", str(_event(tmp_path))]) == 0
    capsys.readouterr()
    assert main(args) == 4
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == "idle" and result["startup_verified"] is True
    assert result["committed"] == 1 and result["witnessed"] == 0 and result["backlog"] == 1
    with sqlite3.connect(tmp_path / "writer.db") as con:
        con.execute("UPDATE checkpoint_schedule SET next_checkpoint_at=0")
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == "witnessed"
    assert result["committed"] == result["witnessed"] == 1 and result["backlog"] == 0


def test_cli_worker_retry_wait_survives_restart(environment, tmp_path, capsys, monkeypatch):
    common, _, _, _, _, _ = environment
    assert startup.initialize(environment) == 0
    capsys.readouterr()
    requests = []

    def unavailable(*args, **kwargs):
        requests.append(args)
        return 503, b"unavailable"

    monkeypatch.setattr("casf.writer.http_request", unavailable)
    args = ["witness", "work", *common, "--once", "--retry-initial", "30"]
    assert main(args) == 4
    first = json.loads(capsys.readouterr().out)
    assert first["state"] == "retry" and first["attempts"] == 1
    assert main(args) == 4
    second = json.loads(capsys.readouterr().out)
    assert second["state"] == "waiting"
    assert second["pending_checkpoint_hash"] == first["pending_checkpoint_hash"]
    assert second["next_action_at_ms"] == first["next_action_at_ms"]
    assert len(requests) == 1


def test_cli_worker_stops_after_pending_final_receipt(environment, capsys):
    common, _, _, _, _, _ = environment
    assert startup.initialize(environment) == 0
    assert main(["seal", *common]) == 0
    capsys.readouterr()
    assert main(["witness", "work", *common]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == "sealed" and result["pending_checkpoint_hash"] is None


def test_cli_worker_has_no_local_only_override(capsys):
    assert main(["witness", "work", "--local-only"]) == 2
    assert not capsys.readouterr().out
