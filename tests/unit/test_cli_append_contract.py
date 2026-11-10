"""CLI append exposes committed and witness state without event payloads."""

import json

from casf.canonical.jcs import canonicalize
from casf.cli import main
from tests.unit import test_cli_verified_startup as cli_tests
from tests.unit.test_append_contract import EVENT_ID, event
from tests.unit.test_cli_verified_startup import initialize
from tests.unit.test_verified_startup import statement

cli_setup = cli_tests.setup


def test_cli_append_reports_all_three_states_on_same_event(cli_setup, tmp_path, capsys):
    common, _, _, _, url, _ = cli_setup
    assert initialize(cli_setup) == 0
    capsys.readouterr()
    path = tmp_path / "event.json"
    path.write_bytes(canonicalize(event()))
    append = ["append", *common, "--event", str(path)]
    for state in ("COMMITTED_LOCAL", "PENDING_WITNESS", "WITNESSED"):
        assert main(append) == 0
        output = capsys.readouterr()
        assert json.loads(output.out) == {
            "seq": 1, "event_id": EVENT_ID, "committed": True, "witness_state": state,
            "startup_verified": True}
        assert "original" not in output.out
        if state == "COMMITTED_LOCAL":
            assert main(["checkpoint", *common]) == 0
            capsys.readouterr()
        elif state == "PENDING_WITNESS":
            assert main(["witness", "submit", *common, "--url", url]) == 0
            capsys.readouterr()


def test_cli_revoked_append_never_prints_committed_result(cli_setup, tmp_path, capsys):
    common, _, status, _, _, _ = cli_setup
    assert initialize(cli_setup) == 0
    capsys.readouterr()
    path = tmp_path / "event.json"
    path.write_bytes(canonicalize(event()))
    status.write_bytes(canonicalize(statement(2, "revoked")))
    assert main(["append", *common, "--event", str(path)]) == 3
    output = capsys.readouterr()
    assert not output.out
    assert "original" not in output.err


def test_cli_body_limit_is_usage_error_without_commit(cli_setup, tmp_path, capsys):
    from casf.canonical.limits import MAX_CANONICAL_BODY_BYTES
    from casf.writer import Writer
    from tests.unit.test_writer import LOG_ID

    common, _, _, _, _, _ = cli_setup
    assert initialize(cli_setup) == 0
    capsys.readouterr()
    values = event(payload={"a": "", "b": ""}, attributes={})
    length = (MAX_CANONICAL_BODY_BYTES - len(canonicalize(values)) - 1) // 2
    values["payload"] = {"a": "x" * length, "b": "x" * length}
    path = tmp_path / "event.json"
    path.write_bytes(canonicalize(values))
    assert main(["append", *common, "--event", str(path)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "record body" in output.err
    assert "xxxx" not in output.err
    reader = Writer(tmp_path / "writer.db")
    try:
        assert list(reader.records(LOG_ID)) == []
    finally:
        reader.close()
