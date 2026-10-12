"""R12 / T18, T20, T21 (SPEC §23): attack harness detection matrix.

Every case predeclares the attacker controls, the verifier anchor,
connectivity, and the expected result before any run. The matrix
repeats one mutation at the beginning, the middle, the last
witnessed record, and the unwitnessed tail, and records whether the
observed result matches the expectation. Cases that correctly remain
undetectable (T18 tail loss, T20 false suffix, T21 isolated client)
must be reported as passing rather than hidden.
"""

import json

from benchmarks import attacks

REQUIRED_FIELDS = {"name", "spec", "mutation", "mode", "attacker",
                   "anchor", "connectivity", "expected"}


def test_matrix_cases_are_predeclared():
    assert len(attacks.CASES) >= 9
    for case in attacks.CASES:
        assert REQUIRED_FIELDS <= set(case), case["name"]
        assert case["expected"] in ("PASS", "FAIL")
        assert case["attacker"]  # who controls what is never blank


def _rows(tmp_path, names):
    out = []
    for name in names:
        case = next(c for c in attacks.CASES if c["name"] == name)
        out.append(attacks.run_case(case, tmp_path / name))
    return out


def test_tamper_detected_at_every_position(tmp_path):
    rows = _rows(tmp_path, ["tamper-beginning", "tamper-middle",
                            "tamper-last-witnessed", "tamper-tail"])
    for row in rows:
        assert row["observed"] == "FAIL", row["name"]
        assert row["match"] is True


def test_tail_loss_integrity_passes_and_is_documented(tmp_path):
    # T18: integrity may pass; no rollback protection is claimed
    row = _rows(tmp_path, ["truncate-tail-integrity"])[0]
    assert row["observed"] == "PASS"
    assert row["match"] is True
    assert "no rollback protection" in row["note"]


def test_t20_stolen_writer_key(tmp_path):
    detected, suffix = _rows(
        tmp_path, ["stolen-key-prefix-anchored", "stolen-key-suffix"])
    # prefix rewrite under a witnessed checkpoint is divergent
    assert detected["observed"] == "FAIL"
    assert "ANCHOR_DIVERGENT" in detected["codes"]
    # a false suffix after the last witnessed record remains possible
    assert suffix["observed"] == "PASS"
    assert suffix["match"] is True
    assert "false suffix" in suffix["note"]


def test_t21_witness_rollback_conditional(tmp_path):
    retained, isolated = _rows(
        tmp_path, ["witness-rollback-retained", "witness-rollback-isolated"])
    # a client holding the earlier pin sees the state conflict
    assert retained["observed"] == "FAIL"
    assert "WITNESS_STATE_CONFLICT" in retained["codes"]
    # an isolated client with no old pin cannot detect; no stronger claim
    assert isolated["observed"] == "PASS"
    assert isolated["match"] is True
    assert "conditional" in isolated["note"]


def test_matrix_artifact_records_every_row(tmp_path):
    rows = attacks.run_matrix(tmp_path / "out")
    artifact = json.loads(
        (tmp_path / "out" / "attacks.v1.json").read_text())
    assert len(artifact["rows"]) == len(attacks.CASES) == len(rows)
    for row in artifact["rows"]:
        assert REQUIRED_FIELDS <= set(row)
        assert row["observed"] in ("PASS", "FAIL", "INCONCLUSIVE")
        assert row["match"] is True, row["name"]
