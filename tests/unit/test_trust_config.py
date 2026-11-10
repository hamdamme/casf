"""R07/R10: malformed configuration cannot relax verification policy."""

import json

import pytest

from casf.cli import _load_trust, main
from casf.errors import SchemaError
from tests.unit.test_cli import _trust
from tests.unit.test_writer import LOG_ID, _manifest_envelope


@pytest.mark.parametrize("section,field,value", [
    ("policy", "allow_unwitnessed", "false"),
    ("policy", "allow_unwitnessed", 1),
    ("policy", "allow_unwitnessed", None),
    ("policy", "mode", "unknown"),
    ("policy", "mode", []),
    ("policy", "max_chain_steps", True),
    ("policy", "max_chain_steps", "10"),
    ("policy", "max_chain_steps", 0),
    ("log", "minimum_status_serial", True),
    ("log", "minimum_status_serial", "1"),
    ("log", "minimum_status_serial", 0),
    ("log", "manifest_hash", "AB" * 32),
    ("log", "manifest_hash", None),
    ("log", "witness_id", "wrong"),
    ("log", "witness_url", []),
])
def test_trust_loader_rejects_invalid_policy_values(tmp_path, section, field, value):
    path = _trust(tmp_path, _manifest_envelope())
    data = json.loads(path.read_text())
    entry = data["policy"] if section == "policy" else data["logs"][LOG_ID]
    entry[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(SchemaError):
        _load_trust(str(path), LOG_ID)


@pytest.mark.parametrize("allow", [False, True])
def test_trust_loader_preserves_explicit_boolean_policy(tmp_path, allow):
    path = _trust(tmp_path, _manifest_envelope())
    data = json.loads(path.read_text())
    data["policy"]["allow_unwitnessed"] = allow
    path.write_text(json.dumps(data))
    assert _load_trust(str(path), LOG_ID)[2]["allow_unwitnessed"] is allow


def test_invalid_policy_cannot_initialize_verifier_state(tmp_path, capsys):
    from casf.writer import Writer
    from tests.status import active_status
    from tests.unit.test_writer import AUTH, LOG

    manifest = _manifest_envelope()
    writer = Writer(tmp_path / "writer.db", LOG, local_only=True)
    try:
        writer.create_log(manifest)
        bundle = writer.export_bundle(LOG_ID, tmp_path / "bundle")
    finally:
        writer.close()
    (bundle / "status.jsonl").write_text(json.dumps(active_status(
        AUTH, manifest["manifest_hash"])) + "\n")
    path = _trust(tmp_path, manifest)
    data = json.loads(path.read_text())
    data["policy"]["allow_unwitnessed"] = "false"
    path.write_text(json.dumps(data))
    state = tmp_path / "state.json"
    assert main(["verify", str(bundle), "--trust", str(path), "--state", str(state),
                 "--initialize-state"]) == 2
    output = capsys.readouterr()
    assert "PASS" not in output.out
    assert not state.exists()
