"""Immutable caller requests and append observations (SPEC §§11 and 19)."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, cast

from casf import crypto
from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import MAX_CANONICAL_BODY_BYTES, MAX_WIRE_ENVELOPE_BYTES
from casf.errors import LimitError, SchemaError
from casf.model.schema import DIGEST_RE, RECORD_FIELDS, validate_body, validate_protocol_body
from casf.types import JsonObject

__all__ = ["AppendResult", "EventRequest", "WitnessState"]

_REQUEST_FIELDS = {name: RECORD_FIELDS[name] for name in
                   ("event_id", "actor", "event_type", "payload", "attributes")}


def _request_bytes(value: JsonObject) -> bytes:
    encoded = canonicalize(value)
    if len(encoded) > MAX_CANONICAL_BODY_BYTES:
        raise LimitError("event request exceeds the record body budget")
    # Validate the owned snapshot; caller mutation after this point cannot
    # separate the request digest from the record that will be signed.
    validate_body(parse(encoded), _REQUEST_FIELDS, "event")
    return encoded


@dataclass(frozen=True, slots=True, init=False)
class EventRequest:
    """Validated five-field event. Nested objects are copied on input and access."""

    _encoded: bytes = field(repr=False)

    def __init__(self, *, event_id: str, actor: str, event_type: str,
                 payload: JsonObject, attributes: JsonObject) -> None:
        object.__setattr__(self, "_encoded", _request_bytes({
            "event_id": event_id, "actor": actor, "event_type": event_type,
            "payload": payload, "attributes": attributes,
        }))

    @classmethod
    def from_dict(cls, value: JsonObject) -> "EventRequest":
        request = object.__new__(cls)
        object.__setattr__(request, "_encoded", _request_bytes(value))
        return request

    def to_dict(self) -> JsonObject:
        return cast(JsonObject, parse(self._encoded))

    @property
    def event_id(self) -> str:
        return cast(str, self.to_dict()["event_id"])

    @property
    def actor(self) -> str:
        return cast(str, self.to_dict()["actor"])

    @property
    def event_type(self) -> str:
        return cast(str, self.to_dict()["event_type"])

    @property
    def payload(self) -> JsonObject:
        return cast(JsonObject, self.to_dict()["payload"])

    @property
    def attributes(self) -> JsonObject:
        return cast(JsonObject, self.to_dict()["attributes"])


class WitnessState(str, Enum):
    COMMITTED_LOCAL = "COMMITTED_LOCAL"
    PENDING_WITNESS = "PENDING_WITNESS"
    WITNESSED = "WITNESSED"


@dataclass(frozen=True, slots=True, init=False)
class AppendResult:
    """Committed record and witness coverage observed in its append transaction.

    This value is a local observation, not independently signed commit evidence.
    The writer returns it only after commit succeeds. Retrying an event can
    return a newer witness observation with the same record bytes.
    """

    _encoded: bytes = field(repr=False)
    witness_state: WitnessState

    def __init__(self, record: JsonObject, witness_state: WitnessState) -> None:
        if not isinstance(witness_state, WitnessState):
            raise SchemaError("witness_state must be a WitnessState")
        encoded = canonicalize(record)
        if len(encoded) > MAX_WIRE_ENVELOPE_BYTES:
            raise LimitError("record envelope exceeds the wire budget")
        snapshot = parse(encoded)
        if not isinstance(snapshot, dict) or set(snapshot) != {"body", "record_hash", "signature"}:
            raise SchemaError("append record envelope fields are wrong")
        validate_protocol_body("record", snapshot["body"])
        if len(canonicalize(snapshot["body"])) > MAX_CANONICAL_BODY_BYTES:
            raise LimitError("record body exceeds the canonical byte budget")
        if not isinstance(snapshot["record_hash"], str) or not isinstance(snapshot["signature"], str):
            raise SchemaError("append record envelope field types are wrong")
        if DIGEST_RE.fullmatch(snapshot["record_hash"]) is None:
            raise SchemaError("append record hash must be a lowercase digest")
        if len(crypto.b64url_decode(snapshot["signature"])) != 64:
            raise SchemaError("append record signature must contain 64 bytes")
        object.__setattr__(self, "_encoded", encoded)
        object.__setattr__(self, "witness_state", witness_state)

    @property
    def committed(self) -> Literal[True]:
        return True

    @property
    def record(self) -> JsonObject:
        return cast(JsonObject, parse(self._encoded))

    def to_dict(self) -> JsonObject:
        return {"record": self.record, "committed": True, "witness_state": self.witness_state.value}
