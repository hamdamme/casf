"""R03/R10: complete diagnostics shared by library and CLI callers."""

import pytest

from casf.verifier import verify
from tests.unit.test_verifier import _chain, _manifest_env, _pins, _status_env


@pytest.mark.parametrize("count", [0, 2])
def test_report_serialization_covers_all_diagnostic_fields(count):
    manifest = _manifest_env()
    report = verify(manifest, _chain(count), _pins(manifest["manifest_hash"]),
                    status_envelopes=[_status_env(manifest["manifest_hash"])])
    result = report.to_dict()
    assert result["mode"] == "integrity"
    assert result["result"] == "PASS"
    assert result["verified_from"] == (1 if count else 0)
    assert result["verified_through"] == count
    assert result["protocol_status"] == report.protocol_status.value
    assert result["signature_status"] == report.signature_status.value
    assert result["chain_status"] == report.chain_status.value
    assert result["first_failure_seq"] is None
    assert result["checkpoint_hash"] is None
    assert result["checkpoint_index"] is None
    assert result["observed_status_serial"] == 1
    assert result["assumptions"]["allow_unwitnessed"] is False


@pytest.mark.parametrize("failure_seq", [1, 2])
def test_report_keeps_exact_failure_and_verified_range(failure_seq):
    manifest = _manifest_env()
    records = _chain(2)
    records[failure_seq - 1]["signature"] = "A" * 86
    report = verify(manifest, records, _pins(manifest["manifest_hash"]),
                    status_envelopes=[_status_env(manifest["manifest_hash"])])
    output = report.to_dict()
    assert output["result"] == "FAIL"
    assert output["signature_status"] == "INVALID"
    assert output["first_failure_seq"] == failure_seq
    assert output["verified_from"] == (0 if failure_seq == 1 else 1)
    assert output["verified_through"] == failure_seq - 1
    assert "RECORD_SIGNATURE" in output["diagnostic_codes"]


def test_report_serialization_does_not_share_mutable_objects():
    manifest = _manifest_env()
    report = verify(manifest, _chain(1), _pins(manifest["manifest_hash"]),
                    status_envelopes=[_status_env(manifest["manifest_hash"])])
    serialized = report.to_dict()
    serialized["diagnostic_codes"].append("CALLER_CHANGED")
    serialized["assumptions"]["allow_unwitnessed"] = True
    assert "CALLER_CHANGED" not in report.diagnostic_codes
    assert report.assumptions["allow_unwitnessed"] is False
    report.diagnostic_codes.append("LATER_CHANGE")
    assert "LATER_CHANGE" not in serialized["diagnostic_codes"]


def test_report_records_requested_policy_and_budget_verdict():
    manifest = _manifest_env()
    report = verify(manifest, _chain(2), _pins(manifest["manifest_hash"]),
                    status_envelopes=[_status_env(manifest["manifest_hash"])],
                    allow_unwitnessed=True, max_records=1, max_chain_steps=7,
                    retained_checkpoint=(2, "ab" * 32))
    output = report.to_dict()
    assert output["result"] == "INCONCLUSIVE"
    assert output["verified_from"] == output["verified_through"] == 1
    assert output["assumptions"] == {
        "authority_trust": "caller_provisioned",
        "status_currentness": "supplied_statements_only",
        "witness_honesty_required": False,
        "allow_unwitnessed": True, "minimum_status_serial": 1,
        "retained_checkpoint_supplied": True, "retained_revoked": False,
        "max_records": 1, "max_chain_steps": 7,
    }


@pytest.fixture
def cli_bundle(tmp_path):
    from casf import crypto
    from casf.canonical.jcs import canonicalize
    from casf.witness import Witness
    from tests.status import active_status, register_active
    from tests.unit.test_writer import (
        AUTH,
        AUTH_PUB,
        LOG_ID,
        WIT,
        _append,
        _manifest_envelope,
        _writer,
    )

    writer = _writer(tmp_path / "writer.db")
    witness = Witness(tmp_path / "witness.db", WIT,
                      authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(witness, _manifest_envelope(), AUTH)
    try:
        records = [_append(writer, n) for n in (1, 2)]
        checkpoint = writer.create_checkpoint(LOG_ID)
        writer.record_receipt(LOG_ID, witness.submit(LOG_ID, checkpoint, records))
        bundle = writer.export_bundle(LOG_ID, tmp_path / "bundle")
        manifest = writer.manifest_envelope(LOG_ID)
        (bundle / "status.jsonl").write_bytes(
            canonicalize(active_status(AUTH, manifest["manifest_hash"])) + b"\n")
        yield bundle, manifest, checkpoint
    finally:
        writer.close()
        witness.close()


@pytest.mark.parametrize("case, exit_code, result", [
    ("pass", 0, "PASS"), ("signature", 1, "FAIL"),
    ("missing_status", 3, "INCONCLUSIVE"), ("timeout", 4, "INCONCLUSIVE"),
])
def test_cli_preserves_complete_reports_for_every_verdict(
        cli_bundle, tmp_path, monkeypatch, capsys, case, exit_code, result):
    import json

    from casf.canonical.jcs import canonicalize
    from casf.cli import main
    from casf.errors import InconclusiveError
    from tests.unit.test_cli import _trust

    bundle, manifest, checkpoint = cli_bundle
    if case == "signature":
        path = bundle / "records.jsonl"
        records = [json.loads(line) for line in path.read_bytes().splitlines()]
        records[1]["signature"] = "A" * 86
        path.write_bytes(b"".join(canonicalize(record) + b"\n" for record in records))
    elif case == "missing_status":
        (bundle / "status.jsonl").unlink()
    elif case == "timeout":
        def unavailable(*args, **kwargs):
            raise InconclusiveError("test timeout")

        monkeypatch.setattr("casf.cli.query_latest", unavailable)
        monkeypatch.setenv("CASF_WITNESS_TOKEN", "synthetic-secret-not-for-report")
    mode = "online" if case == "timeout" else "anchored"
    trust = _trust(tmp_path, manifest, mode=mode, witness_url="https://witness.example")
    assert main(["verify", str(bundle), "--trust", str(trust), "--mode", mode,
                 "--state", str(tmp_path / "state.json"), "--initialize-state", "--json"]) == exit_code
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert not output.err
    assert report["result"] == result
    assert report["mode"] == mode
    assert set(report) == {
        "report_version", "mode", "overall", "result", "protocol_status", "signature_status", "chain_status",
        "trust_status", "anchor_status", "freshness_status", "verified_from", "verified_through",
        "witnessed_through", "unwitnessed_count", "first_failure_seq", "diagnostic_codes",
        "observed_status_serial", "checkpoint_index", "checkpoint_hash", "assumptions",
    }
    assert report["report_version"] == 2
    assert report["assumptions"]["witness_honesty_required"] is True
    assert "synthetic-secret-not-for-report" not in output.out
    assert "actor" not in report and "payload" not in report
    if case == "signature":
        assert report["first_failure_seq"] == 2
        assert report["verified_from"] == report["verified_through"] == 1
        assert report["signature_status"] == "INVALID"
    if case == "pass":
        assert report["checkpoint_hash"] == checkpoint["checkpoint_hash"]
        assert report["checkpoint_index"] == 0
        assert report["witnessed_through"] == 2
    if case == "missing_status":
        assert report["trust_status"] == "UNKNOWN"
        assert report["verified_from"] == 1
        assert report["verified_through"] == 2


def test_late_malformed_bundle_does_not_publish_report_or_checkpoint(cli_bundle, tmp_path, capsys):
    import json

    from casf.cli import main
    from tests.unit.test_cli import _trust

    bundle, manifest, _checkpoint = cli_bundle
    metadata = json.loads((bundle / "export.json").read_text())
    metadata["record_count"] = metadata["through"] = 3
    (bundle / "export.json").write_text(json.dumps(metadata))
    trust = _trust(tmp_path, manifest, mode="anchored")
    state = tmp_path / "state.json"
    assert main(["verify", str(bundle), "--trust", str(trust), "--mode", "anchored",
                 "--state", str(state), "--initialize-state", "--json"]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "error:" in output.err
    if state.exists():
        retained = json.loads(state.read_text())
        assert retained["checkpoint_index"] is None


def test_manifest_failure_does_not_claim_a_verified_record_range():
    manifest = _manifest_env()
    manifest["signature"] = "A" * 86
    report = verify(manifest, _chain(2), _pins(manifest["manifest_hash"]))
    output = report.to_dict()
    assert output["result"] == "FAIL"
    assert output["verified_from"] == output["verified_through"] == 0
    assert output["first_failure_seq"] is None
    assert "MANIFEST_SIGNATURE" in output["diagnostic_codes"]
