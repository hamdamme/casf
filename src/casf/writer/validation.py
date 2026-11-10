"""Local writer consistency checks using the existing casf-v1 byte rules.

These checks authenticate records and witness receipts against manifest keys.
They do not establish independent authority trust or current witness state.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from casf import crypto
from casf.canonical.limits import MAX_CHECKPOINT_BATCH
from casf.errors import CasfError, SchemaError
from casf.model.schema import validate_protocol_body
from casf.types import JsonObject

ZERO = "00" * 32


def envelope(value: JsonObject, kind: str) -> tuple[JsonObject, str, str]:
    field = kind + "_hash"
    if set(value) != {"body", field, "signature"}:
        raise SchemaError(f"invalid {kind} envelope fields")
    body, digest, signature = value["body"], value[field], value["signature"]
    if not isinstance(body, dict) or not isinstance(digest, str) \
            or not isinstance(signature, str):
        raise SchemaError(f"invalid {kind} envelope types")
    validate_protocol_body(kind, body)
    return body, digest, signature


@dataclass(frozen=True)
class ManifestContext:
    body: JsonObject
    digest: str
    log_key: bytes
    witness_key: bytes

    @classmethod
    def read(cls, value: JsonObject) -> "ManifestContext":
        body, digest, signature = envelope(value, "manifest")
        if crypto.digest_manifest(body) != digest:
            raise CasfError("manifest hash disagrees with its body")
        log_key = crypto.b64url_decode(cast(str, body["log_public_key"]))
        witness_key = crypto.b64url_decode(cast(str, body["witness_public_key"]))
        if len(log_key) != 32 or len(witness_key) != 32 \
                or len(crypto.b64url_decode(signature)) != 64:
            raise SchemaError("invalid manifest key or signature length")
        if crypto.key_id(log_key) != body["log_key_id"] \
                or crypto.key_id(witness_key) != body["witness_id"]:
            raise CasfError("manifest public key binding is invalid")
        return cls(body, digest, log_key, witness_key)

    def record(self, value: JsonObject, seq: int,
               previous: str) -> tuple[str, JsonObject]:
        body, digest, signature = envelope(value, "record")
        if body["log_id"] != self.body["log_id"] \
                or body["manifest_hash"] != self.digest \
                or body["key_id"] != self.body["log_key_id"]:
            raise CasfError("record manifest or key binding is invalid")
        if body["seq"] != seq or body["prev_hash"] != previous:
            raise CasfError("record sequence or predecessor is invalid")
        if crypto.digest_record(body) != digest:
            raise CasfError("record hash disagrees with its body")
        crypto.verify_record(self.log_key, body, signature)
        request: JsonObject = {key: body[key] for key in (
            "event_id", "actor", "event_type", "payload", "attributes")}
        return digest, request


class CheckpointChain:
    """Validate an ordered journal against already verified local records."""

    def __init__(self, manifest: ManifestContext,
                 head_at: Callable[[int], str], record_count: int) -> None:
        self.manifest = manifest
        self.head_at = head_at
        self.record_count = record_count
        self.index = -1
        self.count = 0
        self.digest = ZERO
        self.receipt_digest = ZERO
        self.final = False

    def checkpoint(self, value: JsonObject) -> JsonObject:
        body, digest, signature = envelope(value, "checkpoint")
        if self.final:
            raise CasfError("checkpoint follows a final seal")
        if body["log_id"] != self.manifest.body["log_id"] \
                or body["manifest_hash"] != self.manifest.digest \
                or body["key_id"] != self.manifest.body["log_key_id"]:
            raise CasfError("checkpoint manifest or key binding is invalid")
        if body["index"] != self.index + 1 \
                or body["previous_checkpoint_hash"] != self.digest:
            raise CasfError("checkpoint chain is incomplete or inconsistent")
        count = cast(int, body["count"])
        if not self.count <= count <= min(self.count + MAX_CHECKPOINT_BATCH,
                                          self.record_count):
            raise CasfError("checkpoint count is outside the verified history")
        if body["head_hash"] != self.head_at(count):
            raise CasfError("checkpoint head disagrees with verified records")
        if body["final"] and count != self.record_count:
            raise CasfError("records follow the final checkpoint")
        if crypto.digest_checkpoint(body) != digest:
            raise CasfError("checkpoint hash disagrees with its body")
        crypto.verify_checkpoint(self.manifest.log_key, body, signature)
        self.index += 1
        self.count, self.digest, self.final = count, digest, cast(bool, body["final"])
        return body

    def receipt(self, value: JsonObject, checkpoint: JsonObject) -> None:
        body, digest, signature = envelope(value, "receipt")
        if body["witness_id"] != self.manifest.body["witness_id"] \
                or body["log_id"] != self.manifest.body["log_id"] \
                or body["manifest_hash"] != self.manifest.digest:
            raise CasfError("receipt manifest or witness binding is invalid")
        if body["checkpoint_hash"] != self.digest \
                or body["checkpoint_index"] != self.index \
                or body["count"] != checkpoint["count"] \
                or body["head_hash"] != checkpoint["head_hash"]:
            raise CasfError("receipt does not match its checkpoint")
        if body["previous_receipt_hash"] != self.receipt_digest:
            raise CasfError("receipt chain is incomplete or inconsistent")
        if crypto.digest_receipt(body) != digest:
            raise CasfError("receipt hash disagrees with its body")
        crypto.verify_receipt(self.manifest.witness_key, body, signature)
        self.receipt_digest = digest
