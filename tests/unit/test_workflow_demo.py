"""Exercise the documented public workflow and its output preservation boundary."""

import json

import pytest

from examples.verified_workflow import run


def test_verified_workflow_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("CASF_PASSPHRASE", "preexisting-value")
    monkeypatch.setenv("CASF_WITNESS_TOKEN", "preexisting-token")
    output = tmp_path / "public"
    result = run(output)
    assert result["status"] == "complete"
    assert all(report["result"] == "PASS" for report in result["verification"].values())
    assert result["worker"]["committed"] == result["worker"]["witnessed"] == 1
    assert result["tamper_result"] == "FAIL"
    assert result["unavailable_witness_result"] == "INCONCLUSIVE"
    assert result["restored_final_state"] == "sealed"
    assert json.loads((output / "summary.json").read_text()) == result
    assert {p.name for p in output.iterdir()} == {
        "bundle", "trust.json", "synthetic-document.txt", "summary.json"}
    assert all(p.suffix not in {".db", ".pem", ".key"} for p in output.rglob("*"))
    import os
    assert os.environ["CASF_PASSPHRASE"] == "preexisting-value"
    assert os.environ["CASF_WITNESS_TOKEN"] == "preexisting-token"


def test_demo_preserves_existing_output(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_bytes(b"existing evidence\n")
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert evidence.read_bytes() == b"existing evidence\n"
    assert list(tmp_path.iterdir()) == [evidence]
