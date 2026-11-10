"""Immutable writer operation inputs and observations (SPEC §19)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Literal, cast

from casf import crypto
from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import MAX_PROTOCOL_BODY_BYTES, MAX_WIRE_ENVELOPE_BYTES
from casf.errors import LimitError, SchemaError
from casf.model.api import WitnessState
from casf.model.schema import DIGEST_RE, Field, validate_body, validate_protocol_body
from casf.types import JsonObject


def _envelope_bytes(value: JsonObject, kind: str) -> bytes:
    encoded = canonicalize(value)
    if len(encoded) > MAX_WIRE_ENVELOPE_BYTES:
        raise LimitError(f'{kind} envelope exceeds the wire budget')
    snapshot = parse(encoded)
    digest_field = kind + '_hash'
    if not isinstance(snapshot, dict) or set(snapshot) != {'body', digest_field, 'signature'}:
        raise SchemaError(f'invalid {kind} envelope fields')
    body = snapshot['body']
    validate_protocol_body(kind, body)
    if len(canonicalize(body)) > MAX_PROTOCOL_BODY_BYTES:
        raise LimitError(f'{kind} body exceeds the protocol budget')
    digest, signature = snapshot[digest_field], snapshot['signature']
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        raise SchemaError(f'invalid {kind} digest')
    if not isinstance(signature, str) or len(crypto.b64url_decode(signature)) != 64:
        raise SchemaError(f'invalid {kind} signature encoding')
    digest_function = {'manifest': crypto.digest_manifest, 'checkpoint': crypto.digest_checkpoint,
                       'receipt': crypto.digest_receipt}[kind]
    if digest_function(body) != digest:
        raise SchemaError(f'{kind} digest does not match the body')
    return encoded


@dataclass(frozen=True, slots=True, init=False)
class _Envelope:
    _encoded: bytes = field(repr=False)
    _kind: ClassVar[str]

    def __init__(self, envelope: JsonObject) -> None:
        object.__setattr__(self, '_encoded', _envelope_bytes(envelope, self._kind))

    def _snapshot(self) -> JsonObject:
        return cast(JsonObject, parse(self._encoded))

    def to_dict(self) -> JsonObject:
        return self._snapshot()

    @property
    def body(self) -> JsonObject:
        return cast(JsonObject, self._snapshot()['body'])

    @property
    def digest(self) -> str:
        return cast(str, self._snapshot()[self._kind + '_hash'])

    @property
    def log_id(self) -> str:
        return cast(str, self.body['log_id'])


@dataclass(frozen=True, slots=True, init=False)
class Manifest(_Envelope):
    """Owned manifest bytes; construction does not establish authority trust."""
    _kind: ClassVar[str] = 'manifest'

    @property
    def manifest_hash(self) -> str:
        return self.digest


@dataclass(frozen=True, slots=True, init=False)
class Checkpoint(_Envelope):
    """Owned checkpoint bytes; a checkpoint alone does not establish witnessing."""
    _kind: ClassVar[str] = 'checkpoint'

    @property
    def checkpoint_hash(self) -> str:
        return self.digest

    @property
    def index(self) -> int:
        return cast(int, self.body['index'])

    @property
    def count(self) -> int:
        return cast(int, self.body['count'])

    @property
    def final(self) -> bool:
        return cast(bool, self.body['final'])


@dataclass(frozen=True, slots=True, init=False)
class WitnessResult(_Envelope):
    """Receipt returned only after the writer verifies and commits it locally."""
    _kind: ClassVar[str] = 'receipt'

    @property
    def receipt(self) -> JsonObject:
        return self._snapshot()

    @property
    def checkpoint_hash(self) -> str:
        return cast(str, self.body['checkpoint_hash'])

    @property
    def count(self) -> int:
        return cast(int, self.body['count'])

    @property
    def stored(self) -> Literal[True]:
        return True

    @property
    def witness_state(self) -> WitnessState:
        return WitnessState.WITNESSED

    def to_dict(self) -> JsonObject:
        return {'receipt': self.receipt, 'stored': True, 'witness_state': self.witness_state.value}


_EXPORT_FIELDS = {
    'version': Field('int', min_value=1, max_value=1), 'type': Field('str'),
    'log_id': Field('uuid'), 'manifest_hash': Field('digest'),
    'through': Field('int', min_value=0), 'record_count': Field('int', min_value=0),
    'generated_at': Field('ts'),
}


@dataclass(frozen=True, slots=True, init=False)
class ExportResult:
    """Published destination and metadata from the export's single read snapshot."""
    destination: Path
    _encoded: bytes = field(repr=False)

    def __init__(self, destination: str | Path, metadata: JsonObject) -> None:
        encoded = canonicalize(metadata)
        if len(encoded) > MAX_PROTOCOL_BODY_BYTES:
            raise LimitError('export metadata exceeds the protocol budget')
        snapshot = parse(encoded)
        validate_body(snapshot, _EXPORT_FIELDS, 'export')
        assert isinstance(snapshot, dict)
        if snapshot['type'] != 'export' or snapshot['through'] != snapshot['record_count']:
            raise SchemaError('export metadata type or count is inconsistent')
        object.__setattr__(self, 'destination', Path(destination))
        object.__setattr__(self, '_encoded', encoded)

    @property
    def metadata(self) -> JsonObject:
        return cast(JsonObject, parse(self._encoded))

    @property
    def published(self) -> Literal[True]:
        return True

    @property
    def through(self) -> int:
        return cast(int, self.metadata['through'])

    def to_dict(self) -> JsonObject:
        return {'destination': str(self.destination), 'published': True, 'metadata': self.metadata}
