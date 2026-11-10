"""R02/R03/R04/R09: independently pinned writer manifest authority."""

from dataclasses import replace

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.verifier import TrustPins
from casf.writer.validation import ManifestContext
from tests.unit.test_writer import AUTH_PUB, LOG, LOG_ID, LOG_PUB, WIT_PUB, _manifest_envelope


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
