"""Lifecycle operations (SPEC §16): status, rotation, revocation.

Normal rotation closes the old log with a final checkpoint and its
witness receipt, and the successor manifest carries their digests in
its predecessor object; the link is validated against trusted old
keys. Revocation statements are terminal, and the largest observed
serial per manifest is retained outside the log store in a small
atomic state file.
"""

import json
import os
import re
from pathlib import Path
from typing import cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.canonical.jcs import parse
from casf.canonical.limits import SAFE_INT_MAX
from casf.errors import CasfError, SchemaError
from casf.model.schema import validate_protocol_body
from casf.types import JsonObject, JsonValue

__all__ = ["StatusBook", "rotate_epoch", "sign_status",
           "verify_predecessor"]


def _expect(env: JsonObject, hash_field: str) -> tuple[JsonObject, str, str]:
    fields = {"body", "signature"} if hash_field == "" \
        else {"body", hash_field, "signature"}
    if set(env) != fields:
        raise SchemaError("envelope has the wrong fields")
    body = env["body"]
    sig = env["signature"]
    digest = "" if hash_field == "" else env[hash_field]
    if not isinstance(body, dict) or not isinstance(sig, str) \
            or not isinstance(digest, str):
        raise SchemaError("envelope field types are wrong")
    return body, digest, sig


def sign_status(authority_priv: Ed25519PrivateKey, *, serial: int,
                manifest_hash: str, status: str, issued_at: str,
                reason: str) -> JsonObject:
    """Sign a root status statement (SPEC §16). Envelope {body,
    signature}; revocation is terminal for that manifest."""
    if status not in ("active", "revoked"):
        raise CasfError("status must be active or revoked")
    if not isinstance(serial, int) or serial < 1:
        raise CasfError("serial must be a positive safe integer")
    body: JsonObject = {
        "version": 1, "type": "status",
        "issuer_id": crypto.key_id(crypto.public_key_raw(authority_priv)),
        "serial": serial, "manifest_hash": manifest_hash,
        "status": status, "issued_at": issued_at, "reason": reason,
    }
    validate_protocol_body("status", body)
    return {"body": body,
            "signature": crypto.sign_status(authority_priv, body)}


class StatusBook:
    """Largest observed serial per manifest, outside the log store.

    A statement is retained only when it advances the serial; a
    rollback or a statement after revocation returns False and the
    retained state never moves.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._state: dict[str, JsonObject] = {}
        if self._path.exists():
            try:
                raw = self._path.read_bytes()
                if len(raw) > 1024 * 1024:
                    raise ValueError("status book exceeds its size limit")
                data = parse(raw)
            except (OSError, CasfError, ValueError) as e:
                raise CasfError("status book is corrupt") from e
            if not isinstance(data, dict) or any(
                    not isinstance(digest, str)
                    or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                    or not isinstance(entry, dict)
                    or set(entry) != {"serial", "status"}
                    or type(entry["serial"]) is not int
                    or not 1 <= entry["serial"] <= SAFE_INT_MAX
                    or entry["status"] not in ("active", "revoked")
                    for digest, entry in data.items()):
                raise CasfError("status book is corrupt")
            self._state = cast(dict[str, JsonObject], data)

    def observed_serial(self, manifest_hash: str) -> int:
        entry = self._state.get(manifest_hash)
        if entry is None:
            return 0
        serial = entry.get("serial")
        return serial if isinstance(serial, int) else 0

    def observe(self, envelope: JsonObject,
                authority_pub: bytes) -> bool:
        """Validate one statement; retain only a serial advance."""
        body, sig = _expect_status(envelope)
        validate_protocol_body("status", body)
        crypto.verify_status(authority_pub, body, sig)
        manifest_hash = body["manifest_hash"]
        serial = body["serial"]
        status = body["status"]
        if (not isinstance(manifest_hash, str)
                or not isinstance(serial, int)
                or not isinstance(status, str)):
            raise SchemaError("status body field types are wrong")
        entry = self._state.get(manifest_hash)
        if entry is not None:
            if entry.get("status") == "revoked":
                return False  # revocation is terminal
            kept = entry.get("serial")
            if isinstance(kept, int) and serial <= kept:
                return False  # serial rollback
        self._state[manifest_hash] = {"serial": serial, "status": status}
        self._save()
        return True

    def _save(self) -> None:
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(json.dumps(self._state, sort_keys=True))
        os.replace(tmp, self._path)


def _expect_status(env: JsonObject) -> tuple[JsonObject, str]:
    if set(env) != {"body", "signature"}:
        raise SchemaError("status envelope must be exactly body, signature")
    body, sig = env["body"], env["signature"]
    if not isinstance(body, dict) or not isinstance(sig, str):
        raise SchemaError("status envelope field types are wrong")
    return body, sig


def _final_evidence(final_checkpoint: JsonObject,
                    final_receipt: JsonObject) -> dict[str, JsonValue]:
    """Validate the old final checkpoint and receipt pair."""
    cp_body, cp_hash, _cp_sig = _expect(final_checkpoint,
                                        "checkpoint_hash")
    rc_body, rc_hash, _rc_sig = _expect(final_receipt, "receipt_hash")
    if cp_body.get("final") is not True:
        raise CasfError("rotation requires the old final checkpoint")
    if crypto.digest_checkpoint(cp_body) != cp_hash:
        raise SchemaError("checkpoint_hash does not match the body")
    if crypto.digest_receipt(rc_body) != rc_hash:
        raise SchemaError("receipt_hash does not match the body")
    if rc_body["checkpoint_hash"] != cp_hash:
        raise CasfError("receipt does not match the final checkpoint")
    return {
        "log_id": cp_body["log_id"],
        "manifest_hash": cp_body["manifest_hash"],
        "final_checkpoint_hash": cp_hash,
        "final_receipt_hash": rc_hash,
    }


def rotate_epoch(*, authority_priv: Ed25519PrivateKey,
                 new_log_priv: Ed25519PrivateKey, new_log_id: str,
                 witness_pub: bytes, created_at: str,
                 final_checkpoint: JsonObject,
                 final_receipt: JsonObject) -> JsonObject:
    """Build the successor manifest linked to the old final evidence
    (SPEC §16). Sequences restart at 1 in the new log."""
    predecessor = _final_evidence(final_checkpoint, final_receipt)
    new_pub = crypto.public_key_raw(new_log_priv)
    body: JsonObject = {
        "version": 1, "type": "manifest", "log_id": new_log_id,
        "issuer_id": crypto.key_id(crypto.public_key_raw(authority_priv)),
        "log_key_id": crypto.key_id(new_pub),
        "log_public_key": crypto.b64url_encode(new_pub),
        "witness_id": crypto.key_id(witness_pub),
        "witness_public_key": crypto.b64url_encode(witness_pub),
        "created_at": created_at, "predecessor": predecessor,
    }
    validate_protocol_body("manifest", body)
    return {"body": body,
            "manifest_hash": crypto.digest_manifest(body),
            "signature": crypto.sign_manifest(authority_priv, body)}


def verify_predecessor(manifest_envelope: JsonObject,
                       final_checkpoint: JsonObject,
                       final_receipt: JsonObject,
                       old_log_pub: bytes, witness_pub: bytes) -> None:
    """Check a rotation link against trusted old keys (SPEC §16).

    The predecessor object must match the supplied final evidence
    exactly, the checkpoint must be final, and both signatures must
    verify against the old log key and the witness key.
    """
    body, _mh, _sig = _expect(manifest_envelope, "manifest_hash")
    expected = _final_evidence(final_checkpoint, final_receipt)
    if body.get("predecessor") != expected:
        raise CasfError("predecessor does not match the final evidence")
    cp_body, _cp_hash, cp_sig = _expect(final_checkpoint,
                                        "checkpoint_hash")
    rc_body, _rc_hash, rc_sig = _expect(final_receipt, "receipt_hash")
    crypto.verify_checkpoint(old_log_pub, cp_body, cp_sig)
    crypto.verify_receipt(witness_pub, rc_body, rc_sig)
    if rc_body["witness_id"] != crypto.key_id(witness_pub):
        raise CasfError("receipt names a different witness")
