"""R02/R07/R09: independently pinned writer manifest authority."""

from dataclasses import replace

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.verifier import TrustPins
from casf.writer import Writer
from casf.writer.validation import ManifestContext
from tests.unit.test_writer import (
    AUTH_PUB,
    LOG,
    LOG_ID,
    LOG_PUB,
    WIT_PUB,
    _append,
    _manifest_envelope,
)


def _pins(manifest=None):
    manifest = manifest or _manifest_envelope()
    return TrustPins(
        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
        witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
        log_id=LOG_ID, manifest_hash=manifest["manifest_hash"])


def test_manifest_accepts_independently_pinned_authority():
    manifest = _manifest_envelope()
    context = ManifestContext.read(manifest, pins=_pins())
    assert context.digest == manifest["manifest_hash"]
    assert context.log_key == LOG_PUB
    assert context.witness_key == WIT_PUB


@pytest.mark.parametrize("change", [
    "unknown_authority", "wrong_authority", "authority_id", "signature",
    "log_id", "manifest_hash", "missing_hash", "missing_witness", "wrong_witness",
])
def test_manifest_rejects_untrusted_pins(change):
    manifest, pins = _manifest_envelope(), _pins()
    if change == "unknown_authority":
        pins = replace(pins, authority_keys={})
    elif change in {"wrong_authority", "authority_id"}:
        pins = replace(pins, authority_keys={crypto.key_id(AUTH_PUB): LOG_PUB})
        if change == "authority_id":
            manifest["signature"] = crypto.sign_manifest(LOG, manifest["body"])
    elif change == "signature":
        manifest["signature"] = crypto.b64url_encode(bytes(64))
    elif change == "log_id":
        pins = replace(pins, log_id="223e4567-e89b-42d3-a456-426614174000")
    elif change == "manifest_hash":
        pins = replace(pins, manifest_hash="ab" * 32)
    elif change == "missing_hash":
        pins = replace(pins, manifest_hash=None)
    elif change == "missing_witness":
        pins = replace(pins, witness_keys={})
    else:
        pins = replace(pins, witness_keys={crypto.key_id(WIT_PUB): LOG_PUB})
    with pytest.raises(CasfError):
        ManifestContext.read(manifest, pins=pins)


def test_writer_pins_apply_to_create_reopen_and_restore(tmp_path):
    db = tmp_path / "writer.db"
    pins = {LOG_ID: _pins()}
    writer = Writer(db, LOG, trust_pins=pins, local_only=True)
    try:
        writer.create_log(_manifest_envelope())
        record = _append(writer, 1)
        bundle = writer.export_bundle(LOG_ID, tmp_path / "bundle")
    finally:
        writer.close()
    reader = Writer(db, trust_pins=pins)
    try:
        assert list(reader.records(LOG_ID)) == [record]
    finally:
        reader.close()
    restored = Writer.restore_from_bundle(tmp_path / "restored.db", LOG, bundle,
                                          trust_pins=pins, local_only=True)
    try:
        assert list(restored.records(LOG_ID)) == [record]
        assert _append(restored, 2)["body"]["seq"] == 2
    finally:
        restored.close()


@pytest.mark.parametrize("operation", ["create", "reopen", "restore"])
def test_writer_rejects_forged_authority_at_every_boundary(tmp_path, operation):
    manifest = _manifest_envelope()
    manifest["signature"] = crypto.b64url_encode(bytes(64))
    db = tmp_path / "writer.db"
    pins = {LOG_ID: _pins()}
    if operation == "create":
        writer = Writer(db, LOG, trust_pins=pins, local_only=True)
        try:
            with pytest.raises(CasfError, match="authority signature"):
                writer.create_log(manifest)
            assert writer._db.connection.execute("SELECT COUNT(*) FROM manifests").fetchone() == (0,)
        finally:
            writer.close()
        return
    writer = Writer(db, LOG, local_only=True)  # A legacy local-only store cannot authenticate the issuer.
    try:
        writer.create_log(manifest)
        bundle = writer.export_bundle(LOG_ID, tmp_path / "bundle")
    finally:
        writer.close()
    if operation == "reopen":
        with pytest.raises(CasfError, match="authority signature"):
            Writer(db, LOG, trust_pins=pins, local_only=True)
    else:
        restored = tmp_path / "restored.db"
        with pytest.raises(CasfError, match="authority signature"):
            Writer.restore_from_bundle(restored, LOG, bundle, trust_pins=pins, local_only=True)
        assert not restored.exists()


@pytest.mark.parametrize("configured", [False, True])
def test_writer_never_falls_back_for_unprovisioned_log(tmp_path, configured):
    writer = Writer(tmp_path / "writer.db", LOG, trust_pins={LOG_ID: _pins()} if configured else {}, local_only=True)
    manifest = _manifest_envelope()
    if configured:
        manifest["body"]["log_id"] = "223e4567-e89b-42d3-a456-426614174000"
        manifest["manifest_hash"] = crypto.digest_manifest(manifest["body"])
    try:
        with pytest.raises(CasfError, match="not provisioned"):
            writer.create_log(manifest)
        assert writer._db.connection.execute("SELECT COUNT(*) FROM manifests").fetchone() == (0,)
    finally:
        writer.close()


def test_writer_copies_supplied_trust_policy(tmp_path):
    pins = _pins()
    policy = {LOG_ID: pins}
    writer = Writer(tmp_path / "writer.db", LOG, trust_pins=policy, local_only=True)
    try:
        policy.clear()
        pins.authority_keys.clear()
        pins.witness_keys.clear()
        writer.create_log(_manifest_envelope())
        assert _append(writer, 1)["body"]["seq"] == 1
    finally:
        writer.close()
