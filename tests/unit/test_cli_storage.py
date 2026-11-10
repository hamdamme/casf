"""CLI contract for explicit storage migration."""

import pytest

from tests.unit.test_storage_migrations import legacy, rows


@pytest.mark.parametrize("kind", ["writer", "witness"])
def test_cli_migration_and_repeat_refusal(tmp_path, capsys, kind):
    import json

    from casf.cli import main

    source = legacy(tmp_path / "old.db", kind)
    dest = tmp_path / "new.db"
    command = ["storage", "migrate", "--source", str(source), "--destination", str(dest),
               "--kind", kind, "--json"]
    assert main(command) == 0
    assert json.loads(capsys.readouterr().out) == {
        "migrated": True, "kind": kind, "schema_version": 1, "destination": str(dest)}
    assert main(command) == 5
    assert "already exists" in capsys.readouterr().err
    assert rows(dest) == rows(source)
