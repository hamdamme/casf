"""Validate explicit evidence links, not claims of complete requirement coverage."""

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "tests" / "requirement_evidence.json"


def _target(nodeid, root=ROOT):
    """Resolve a concrete test function without counting comments or this audit."""
    relative, name = nodeid.split("::")
    path = root / relative
    assert path.resolve().is_relative_to((root / "tests").resolve()), nodeid
    assert path.name != "test_traceability.py", "audit cannot be its own evidence"
    assert path.name.startswith("test_") and path.suffix == ".py", nodeid
    assert name.startswith("test_"), nodeid
    tree = ast.parse(path.read_text())
    matches = [node for node in tree.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    assert len(matches) == 1, f"missing or ambiguous test: {nodeid}"
    return matches[0]


def test_requirement_mapping_matches_specification():
    data = json.loads(EVIDENCE.read_text())
    spec = (ROOT / "docs/specification/CASF_SPEC_001.md").read_text()
    expected = {}
    for row in spec.splitlines():
        cells = [cell.strip() for cell in row.split("|")]
        if len(cells) > 3 and re.fullmatch(r"R\d{2}", cells[1]):
            expected[cells[1]] = re.findall(r"\bT\d{2}\b", cells[3])
    assert set(expected) == {f"R{i:02d}" for i in range(1, 13)}
    assert data["requirements"] == expected
    assert set(data["spec_tests"]) == {f"T{i:02d}" for i in range(1, 23)}
    for identifiers in expected.values():
        assert set(identifiers) <= data["spec_tests"].keys()


def test_evidence_targets_exist_and_have_checks():
    data = json.loads(EVIDENCE.read_text())
    for identifier, entry in data["spec_tests"].items():
        assert entry["assertion_scope"].strip(), identifier
        assert isinstance(entry["remaining_review"], str), identifier
        assert entry["nodeids"], identifier
        assert len(set(entry["nodeids"])) == len(entry["nodeids"]), identifier
        for nodeid in entry["nodeids"]:
            target = _target(nodeid)
            checks = [node for node in ast.walk(target)
                      if isinstance(node, ast.Assert) or (
                          isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                          and isinstance(node.func.value, ast.Name)
                          and node.func.value.id == "pytest" and node.func.attr == "raises")]
            assert checks, f"no assertion or expected exception: {nodeid}"


def test_evidence_rejects_audit_self_reference():
    with pytest.raises(AssertionError, match="own evidence"):
        _target("tests/unit/test_traceability.py::test_requirement_mapping_matches_specification")


def test_evidence_rejects_comment_only_reference(tmp_path):
    path = tmp_path / "tests/test_sample.py"
    path.parent.mkdir()
    path.write_text("# T01 test_missing\n")
    with pytest.raises(AssertionError, match="missing or ambiguous"):
        _target("tests/test_sample.py::test_missing", tmp_path)


def test_evidence_rejects_renamed_test(tmp_path):
    path = tmp_path / "tests/test_sample.py"
    path.parent.mkdir()
    path.write_text("def test_new_name():\n    assert 1 == 1\n")
    with pytest.raises(AssertionError, match="missing or ambiguous"):
        _target("tests/test_sample.py::test_old_name", tmp_path)


def test_evidence_rejects_path_outside_tests(tmp_path):
    with pytest.raises(AssertionError):
        _target("outside.py::test_example", tmp_path)
