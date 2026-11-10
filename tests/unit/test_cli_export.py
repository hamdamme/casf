"""CLI prefix-export range and error contract."""

import json

from casf.bundle import read_bundle
from tests.unit.test_writer import _append, _writer


def test_cli_prefix_export_reports_and_validates_the_requested_range(tmp_path, capsys):
    from casf.cli import main

    writer = _writer(tmp_path / "writer.db")
    _append(writer)
    writer.close()
    dest = tmp_path / "bundle"
    command = ["export", "--db", str(tmp_path / "writer.db"), "--out", str(dest), "--json"]
    assert main([*command, "--through", "0"]) == 0
    assert json.loads(capsys.readouterr().out) == {"bundle": str(dest)}
    assert read_bundle(dest).records == []
    assert main([*command, "--through", "-1"]) == 2
    assert "nonnegative safe integer" in capsys.readouterr().err
