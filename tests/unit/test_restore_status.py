"""R07/R09: explicit restore policy verifies supplied authority status."""

import json
from dataclasses import replace

import pytest

from casf import crypto
from casf.errors import CasfError, TrustError
from casf.lifecycle import sign_status
from casf.writer import Writer
from tests.unit.test_restore_anchors import evidence
from tests.unit.test_writer import AUTH, LOG, LOG_ID


def status(manifest_hash, serial=1, state="active"):
    return sign_status(AUTH, serial=serial, manifest_hash=manifest_hash,
                       status=state, issued_at="2026-10-11T00:00:00.000000Z", reason="")


@pytest.mark.parametrize("serial", [1, 3])
def test_restore_accepts_active_status_at_provisioned_minimum(tmp_path, serial):
    path, bundle, pins = evidence(tmp_path)
    pins[LOG_ID] = replace(pins[LOG_ID], minimum_status_serial=serial)
    (path / "status.jsonl").write_text(json.dumps(status(bundle.manifest_hash, serial)) + "\n")
    writer = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, path,
                                        trust_pins=pins, require_active_status=True, local_only=True)
    try:
        assert list(writer.records(LOG_ID)) == bundle.records
    finally:
        writer.close()


@pytest.mark.parametrize("change", [
    "missing", "forged", "revoked", "revoked_then_active", "old_serial",
    "unrelated", "wrong_issuer", "no_pins", "unprovisioned",
])
def test_restore_rejects_untrusted_status_before_creating_store(tmp_path, change):
    path, bundle, pins = evidence(tmp_path)
    statements = [status(bundle.manifest_hash)]
    if change == "missing":
        statements = []
    elif change == "forged":
        statements[0]["signature"] = crypto.b64url_encode(bytes(64))
    elif change in {"revoked", "revoked_then_active"}:
        statements = [status(bundle.manifest_hash, 2, "revoked")]
        if change == "revoked_then_active":
            statements.append(status(bundle.manifest_hash, 3))
    elif change == "old_serial":
        pins[LOG_ID] = replace(pins[LOG_ID], minimum_status_serial=2)
    elif change == "unrelated":
        statements = [status("ab" * 32)]
    elif change == "wrong_issuer":
        statements[0]["body"]["issuer_id"] = crypto.key_id(crypto.public_key_raw(LOG))
        statements[0]["signature"] = crypto.sign_status(LOG, statements[0]["body"])
    elif change == "no_pins":
        pins = None
    else:
        pins = {}
    (path / "status.jsonl").write_text("".join(json.dumps(s) + "\n" for s in statements))
    dest = tmp_path / "restored.db"
    with pytest.raises(TrustError):
        Writer.restore_from_bundle(dest, LOG, path, trust_pins=pins, require_active_status=True, local_only=True)
    assert not dest.exists()


def test_status_policy_does_not_accept_corrupt_records(tmp_path):
    path, bundle, pins = evidence(tmp_path)
    (path / "status.jsonl").write_text(json.dumps(status(bundle.manifest_hash)) + "\n")
    bundle.records[0]["signature"] = crypto.b64url_encode(bytes(64))
    (path / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in bundle.records))
    dest = tmp_path / "restored.db"
    with pytest.raises(CasfError):
        Writer.restore_from_bundle(dest, LOG, path, trust_pins=pins, require_active_status=True, local_only=True)
    assert not dest.exists()
