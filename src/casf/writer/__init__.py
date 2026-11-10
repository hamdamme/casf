"""Sequencing and idempotent append (SPEC §11, §17).

Manifest storage, transactional record append, verified local startup,
bundle export/restore, and explicit checkpoint and receipt operations.
Explicit fresh witness reconciliation is available; scheduling is separate work.

Writers serialize through the database (BEGIN IMMEDIATE), never
through a process mutex alone. Return success only after COMMIT; a
caller with an uncertain outcome retries with the same event ID.
"""

import http.client
import json
import os
import random
import re
import sqlite3
import tempfile
import time
from collections.abc import Iterable, Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.bundle import read_bundle
from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import MAX_CANONICAL_BODY_BYTES, MAX_CHECKPOINT_BATCH, SAFE_INT_MAX
from casf.errors import CasfError, InconclusiveError, LimitError, SchemaError, TrustError
from casf.filesystem import rename_directory_exclusive, sync_directory
from casf.model.api import AppendResult, EventRequest, WitnessState
from casf.model.operations import ExportResult, Manifest, WitnessResult
from casf.model.schema import validate_protocol_body
from casf.online import LatestView
from casf.storage import Database
from casf.transport import ResponseLimitError
from casf.transport import request as http_request
from casf.trust.state import StateTransaction
from casf.types import JsonObject
from casf.verifier import Result, TrustPins, TrustStatus, verify
from casf.writer.startup import StartupPolicy, authorize, authorized, reserve_database
from casf.writer.validation import CheckpointChain, ManifestContext

__all__ = ["AppendResult", "BusyError", "EventIdConflictError", "EventRequest",
           "ReconciliationRequiredError", "RestoreBehindWitnessError", "SealedError",
           "StartupPolicy", "WitnessState", "Writer"]

ZERO_HASH = "00" * 32  # hex(Z), the null previous checkpoint digest


class BusyError(CasfError):
    """Lock contention outlived the bounded retries (SPEC §17)."""


class EventIdConflictError(CasfError):
    """Same event ID with a different request digest (SPEC §11)."""


class SealedError(CasfError):
    """No append follows sealing (SPEC §12, §16)."""


class ReconciliationRequiredError(SealedError):
    """Fresh witness reconciliation must succeed before new writes resume."""


class RestoreBehindWitnessError(SealedError):
    """Restored history is behind an external witness anchor (T15).

    The restore completes so the data stays readable, but the log is
    sealed and every later append fails with RESTORE_BEHIND_WITNESS.
    """


class Writer:
    """Appends signed records to one SQLite store."""

    def __init__(self, db_path: str | Path,
                 log_priv: Ed25519PrivateKey | None = None, *,
                 busy_timeout_ms: int = 5000, max_retries: int = 3,
                 retry_jitter: float = 0.05,
                 local_only: bool = False,
                 trust_pins: Mapping[str, TrustPins] | None = None) -> None:
        if type(local_only) is not bool:
            raise SchemaError("local_only must be boolean")
        if log_priv is not None and not local_only:
            raise TrustError("use Writer.open_verified for signing; local_only=True is explicit")
        self._startup_policy: StartupPolicy | None = None
        self._startup_log_id: str | None = None
        self._startup_serial = 0
        self._startup_failed = False
        self._active_state: StateTransaction | None = None
        self._bootstrapping = False
        self._trust_pins: dict[str, TrustPins] | None = None
        if trust_pins is not None:
            self._trust_pins = {}
            for log_id, pins in trust_pins.items():
                if log_id != pins.log_id:
                    raise TrustError("trust policy log identity is inconsistent")
                self._trust_pins[log_id] = TrustPins(
                    authority_keys=dict(pins.authority_keys),
                    witness_keys=dict(pins.witness_keys),
                    log_id=pins.log_id, manifest_hash=pins.manifest_hash,
                    minimum_status_serial=pins.minimum_status_serial)
        self._db = Database(db_path, busy_timeout_ms)
        self._log_priv = log_priv
        self._log_pub = (crypto.public_key_raw(log_priv)
                         if log_priv is not None else None)
        self._log_key_id = (crypto.key_id(self._log_pub)
                            if self._log_pub is not None else None)
        self._max_retries = max_retries
        self._retry_jitter = retry_jitter
        try:
            self._check_heads()
        except BaseException:
            self._db.close()
            raise

    def close(self) -> None:
        self._db.close()

    @classmethod
    def open_verified(cls, db_path: str | Path, log_priv: Ed25519PrivateKey, *,
                       trust_pins: Mapping[str, TrustPins], startup: StartupPolicy) -> "Writer":
        """Verify status, fresh witness history and retained state before signing."""
        if not Path(db_path).is_file():
            raise CasfError("verified startup requires an existing database")
        writer = cls(db_path, log_priv, trust_pins=trust_pins, local_only=True)
        try:
            authorize(writer, startup)
            return writer
        except BaseException:
            writer.close()
            raise

    @classmethod
    def initialize_verified(cls, db_path: str | Path, log_priv: Ed25519PrivateKey,
                             manifest: JsonObject, *, trust_pins: Mapping[str, TrustPins],
                             startup: StartupPolicy) -> "Writer":
        """Establish a witnessed empty checkpoint before authorizing the first record."""
        body = manifest.get("body")
        if not isinstance(body, dict) or not isinstance(body.get("log_id"), str):
            raise SchemaError("manifest log identity is invalid")
        pins = trust_pins.get(cast(str, body["log_id"]))
        if pins is None:
            raise TrustError("initialization requires independent manifest pins")
        ManifestContext.read(manifest, pins=pins)
        reserve_database(db_path)
        writer = cls(db_path, log_priv, trust_pins=trust_pins, local_only=True)
        try:
            writer.create_log(manifest)
            authorize(writer, startup)
            return writer
        except BaseException:
            writer.close()
            raise

    def _manifest_context(self, value: JsonObject) -> ManifestContext:
        pins = None
        if self._trust_pins is not None:
            body = value.get("body")
            log_id = body.get("log_id") if isinstance(body, dict) else None
            if not isinstance(log_id, str):
                raise SchemaError("manifest log identity is invalid")
            pins = self._trust_pins.get(log_id)
            if pins is None:
                raise TrustError("manifest log is not provisioned in the trust policy")
        return ManifestContext.read(value, pins=pins)

    def _signing_key(self) -> tuple[Ed25519PrivateKey, bytes, str]:
        if self._log_priv is None or self._log_pub is None \
                or self._log_key_id is None:
            raise CasfError("this operation requires the log signing key")
        return self._log_priv, self._log_pub, self._log_key_id

    def backup(self, dest_path: str | Path) -> None:
        """Consistent backup through the SQLite backup API (SPEC §18).

        Copying only the live database file is not an approved
        procedure; this includes the required WAL state. Never
        overwrites an existing file.
        """
        self._db.backup(dest_path)

    def _check_heads(self) -> None:
        """Verify local records, indexes and journal in one snapshot.

        Manifest keys are local consistency inputs, not independently
        trusted authority pins. A newer external witness must still be
        reconciled before promoting a restored or suspect store.
        """
        con = self._db.connection
        owns_snapshot = not con.in_transaction
        if owns_snapshot:
            con.execute("BEGIN")
        try:
            for table in ("heads", "records", "checkpoints", "outbox"):
                if con.execute(
                        f"SELECT 1 FROM {table} t LEFT JOIN manifests m "
                        "ON m.log_id = t.log_id WHERE m.log_id IS NULL LIMIT 1"
                        ).fetchone():
                    raise CasfError("stored data has no matching manifest")
            if con.execute(
                    "SELECT 1 FROM receipts r LEFT JOIN checkpoints c "
                    "ON c.checkpoint_hash = r.checkpoint_hash "
                    "WHERE c.checkpoint_hash IS NULL LIMIT 1").fetchone():
                raise CasfError("stored receipt has no matching checkpoint")
            for log_id, stored_manifest_hash, blob in con.execute(
                    "SELECT log_id, manifest_hash, envelope FROM manifests"):
                context = self._manifest_context(self._stored_object(blob))
                if context.body["log_id"] != log_id \
                        or context.digest != stored_manifest_hash:
                    raise CasfError("stored manifest index is inconsistent")
                head = con.execute(
                    "SELECT count, head_hash, sealed FROM heads WHERE log_id = ?",
                    (log_id,)).fetchone()
                if head is None:
                    raise CasfError("stored manifest has no head")
                count, head_hash, sealed = head
                self._debug_hook("after_heads_read")
                expected = crypto.genesis_hash(context.digest)
                verified_count = 0
                for index, row in enumerate(con.execute(
                        "SELECT seq, event_id, request_digest, record_hash, envelope "
                        "FROM records WHERE log_id = ? ORDER BY seq", (log_id,)), 1):
                    seq, event_id, request_digest, digest, raw = row
                    verified_hash, request = context.record(
                        self._stored_object(raw), index, expected)
                    if seq != index or event_id != request["event_id"] \
                            or request_digest != crypto.request_digest(request) \
                            or digest != verified_hash:
                        raise CasfError("stored record index is inconsistent")
                    expected, verified_count = verified_hash, index
                if count != verified_count or head_hash != expected:
                    raise CasfError("stored head disagrees with verified records")
                self._check_journal(log_id, context, verified_count, sealed)
        finally:
            if owns_snapshot:
                con.rollback()

    @staticmethod
    def _stored_object(blob: object) -> JsonObject:
        if not isinstance(blob, bytes):
            raise CasfError("stored envelope is not a byte string")
        value = parse(blob)
        if not isinstance(value, dict):
            raise CasfError("stored envelope is not an object")
        return value

    def _record_head(self, log_id: str, context: ManifestContext, count: int) -> str:
        if count == 0:
            return crypto.genesis_hash(context.digest)
        row = self._db.connection.execute(
            "SELECT record_hash FROM records WHERE log_id = ? AND seq = ?",
            (log_id, count)).fetchone()
        if row is None or not isinstance(row[0], str):
            raise CasfError("checkpoint has no matching local record")
        return row[0]

    def _check_journal(self, log_id: str, context: ManifestContext,
                       count: int, sealed: int) -> None:
        con = self._db.connection
        chain = CheckpointChain(context, lambda n: self._record_head(log_id, context, n),
                                count)
        pending = False
        for index, cp_count, digest, blob, state in con.execute(
                "SELECT idx, count, checkpoint_hash, envelope, state "
                "FROM checkpoints WHERE log_id = ? ORDER BY idx", (log_id,)):
            if pending:
                raise CasfError("checkpoint follows a pending checkpoint")
            base_count = chain.count
            body = chain.checkpoint(self._stored_object(blob))
            if (index, cp_count, digest) != (chain.index, chain.count, chain.digest):
                raise CasfError("stored checkpoint index is inconsistent")
            receipt = con.execute(
                "SELECT envelope FROM receipts WHERE checkpoint_hash = ?",
                (digest,)).fetchone()
            if state == "accepted" and receipt is not None:
                chain.receipt(self._stored_object(receipt[0]), body)
            elif state == "pending" and receipt is None:
                pending = True
                outbox = con.execute(
                    "SELECT checkpoint_hash, from_seq, to_seq FROM outbox "
                    "WHERE log_id = ?", (log_id,)).fetchone()
                if outbox != (digest, base_count + 1, chain.count):
                    raise CasfError("pending checkpoint disagrees with the outbox")
            else:
                raise CasfError("checkpoint state disagrees with its receipt")
        if not pending and con.execute(
                "SELECT 1 FROM outbox WHERE log_id = ?", (log_id,)).fetchone():
            raise CasfError("outbox has no pending checkpoint")
        if sealed not in (0, 1, 2, 3) \
                or (sealed not in (1, 3) and (sealed == 2) != chain.final):
            raise CasfError("stored seal disagrees with the checkpoint journal")

    def _debug_hook(self, stage: str) -> None:
        """Test hook; no-op in production."""

    # ---------------------------------------------------------- manifest

    def create_log(self, manifest_envelope: JsonObject) -> str:
        """Store the manifest and genesis transactionally (SPEC §10)."""
        if self._startup_policy is not None:
            raise TrustError("initialize a separate verified writer for a new log")
        manifest_envelope = Manifest(manifest_envelope).to_dict()
        con = self._db.connection
        con.execute("BEGIN IMMEDIATE")
        try:
            manifest_hash = self._insert_log(manifest_envelope)
            con.commit()
            return manifest_hash
        except sqlite3.IntegrityError as exc:
            con.rollback()
            raise CasfError("log already exists") from exc
        except BaseException:
            con.rollback()
            raise

    def _insert_log(self, manifest_envelope: JsonObject) -> str:
        """Insert inside the caller's transaction, including during restore."""
        _log_priv, _log_pub, log_key_id = self._signing_key()
        if set(manifest_envelope) != {"body", "manifest_hash", "signature"}:
            raise SchemaError("manifest envelope must be exactly "
                              "body, manifest_hash, signature")
        body = manifest_envelope["body"]
        manifest_hash = manifest_envelope["manifest_hash"]
        if not isinstance(body, dict) or not isinstance(manifest_hash, str):
            raise SchemaError("manifest envelope field types are wrong")
        validate_protocol_body("manifest", body)
        self._manifest_context(manifest_envelope)
        if crypto.digest_manifest(body) != manifest_hash:
            raise SchemaError("manifest_hash does not match the body")
        if body["log_key_id"] != log_key_id:
            raise CasfError("writer key does not match the manifest log key")
        log_id = body["log_id"]
        if not isinstance(log_id, str):
            raise SchemaError("log_id: expected string")
        genesis = crypto.genesis_hash(manifest_hash)
        blob = canonicalize(manifest_envelope)
        con = self._db.connection
        con.execute("INSERT INTO manifests VALUES (?, ?, ?)",
                    (log_id, manifest_hash, blob))
        con.execute("INSERT INTO heads VALUES (?, 0, ?, 0)", (log_id, genesis))
        return manifest_hash

    def manifest_envelope(self, log_id: str) -> JsonObject:
        row = self._db.connection.execute(
            "SELECT envelope FROM manifests WHERE log_id = ?", (log_id,)).fetchone()
        if row is None:
            raise CasfError("unknown log")
        env = parse(bytes(row[0]))
        if not isinstance(env, dict):
            raise CasfError("stored manifest is corrupt")
        return env

    def records(self, log_id: str) -> Iterator[JsonObject]:
        """Stream record envelopes ordered by sequence."""
        cursor = self._db.connection.execute(
            "SELECT envelope FROM records WHERE log_id = ? ORDER BY seq", (log_id,))
        for (blob,) in cursor:
            env = parse(bytes(blob))
            if not isinstance(env, dict):
                raise CasfError("stored record is corrupt")
            yield env

    # ------------------------------------------------------------- append

    @authorized
    def append(self, log_id: str, *, event_id: str, actor: str,
               event_type: str, payload: JsonObject,
               attributes: JsonObject) -> JsonObject:
        """Compatibility API returning an owned record envelope dictionary."""
        _ = self._signing_key()
        request = EventRequest(event_id=event_id, actor=actor, event_type=event_type,
                               payload=payload, attributes=attributes)
        return self._append_request(log_id, request).record

    @authorized
    def append_event(self, log_id: str, request: EventRequest) -> AppendResult:
        """Append an immutable request and report its committed witness state."""
        _ = self._signing_key()
        if not isinstance(request, EventRequest):
            raise SchemaError("append_event requires an EventRequest")
        return self._append_request(log_id, request)

    def _append_request(self, log_id: str, event: EventRequest) -> AppendResult:
        request = event.to_dict()
        request_digest = crypto.request_digest(request)
        attempts = max(1, self._max_retries)
        for attempt in range(attempts):
            try:
                return self._append_once(log_id, request, request_digest)
            except sqlite3.OperationalError as e:
                if getattr(e, "sqlite_errorcode", 0) & 0xff not in (
                        sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                    raise
                if attempt + 1 >= attempts:
                    raise BusyError("append could not acquire the write lock "
                                    "within the retry budget") from e
                time.sleep(self._retry_jitter * (attempt + 1)
                           * (1 + random.random()))
        raise BusyError("unreachable")  # pragma: no cover

    def _append_once(self, log_id: str, request: JsonObject,
                     request_digest: str) -> AppendResult:
        log_priv, _log_pub, log_key_id = self._signing_key()
        if self._manifest_context(self.manifest_envelope(log_id)).body["log_key_id"] != log_key_id:
            raise CasfError("writer key does not match the manifest log key")
        con = self._db.connection
        con.execute("BEGIN IMMEDIATE")
        try:
            row = con.execute(
                "SELECT request_digest, envelope FROM records "
                "WHERE log_id = ? AND event_id = ?",
                (log_id, request["event_id"])).fetchone()
            if row is not None:
                stored_digest, blob = row
                env = parse(bytes(blob))
                if stored_digest != request_digest:
                    raise EventIdConflictError(
                        "event ID already used with a different request")
                if not isinstance(env, dict):
                    raise CasfError("stored record is corrupt")
                result = self._append_result(log_id, env)
                con.commit()
                return result
            head = con.execute(
                "SELECT count, head_hash, sealed FROM heads WHERE log_id = ?",
                (log_id,)).fetchone()
            if head is None:
                raise CasfError("unknown log")
            count, head_hash, sealed = head
            if sealed == 3:
                raise ReconciliationRequiredError(
                    "RECONCILIATION_REQUIRED: reconcile fresh witness state before writing")
            if sealed == 1:
                raise RestoreBehindWitnessError(
                    "RESTORE_BEHIND_WITNESS: this log was restored behind "
                    "an external anchor; writes stop here")
            if sealed:
                raise SealedError("log is sealed; no append follows sealing")
            seq = count + 1
            if seq > SAFE_INT_MAX:
                raise CasfError("sequence overflow; a new epoch is required")
            body: JsonObject = {
                "version": 1, "type": "record", "log_id": log_id,
                "manifest_hash": self._manifest_hash(log_id),
                "seq": seq,
                "event_id": request["event_id"],
                "recorded_at": datetime.now(UTC).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"),
                "actor": request["actor"], "event_type": request["event_type"],
                "payload": request["payload"],
                "attributes": request["attributes"],
                "prev_hash": head_hash, "key_id": log_key_id,
            }
            validate_protocol_body("record", body)
            if len(canonicalize(body)) > MAX_CANONICAL_BODY_BYTES:
                raise LimitError("record body exceeds the canonical byte budget")
            record_hash = crypto.digest_record(body)
            envelope: JsonObject = {
                "body": body, "record_hash": record_hash,
                "signature": crypto.sign_record(log_priv, body),
            }
            self._debug_hook("before_insert")
            con.execute(
                "INSERT INTO records VALUES (?, ?, ?, ?, ?, ?)",
                (log_id, seq, request["event_id"], request_digest,
                 record_hash, canonicalize(envelope)))
            con.execute(
                "UPDATE heads SET count = ?, head_hash = ? WHERE log_id = ?",
                (seq, record_hash, log_id))
            self._debug_hook("after_insert")
            result = self._append_result(log_id, envelope)
            con.commit()
            self._debug_hook("after_commit")
            return result
        except BaseException:
            con.rollback()
            raise

    def _append_result(self, log_id: str, record: JsonObject) -> AppendResult:
        """Observe coverage while the append/idempotency transaction is held."""
        body = cast(JsonObject, record["body"])
        seq = cast(int, body["seq"])
        con = self._db.connection
        accepted = con.execute(
            "SELECT MAX(count) FROM checkpoints WHERE log_id=? AND state='accepted'",
            (log_id,)).fetchone()[0]
        pending = con.execute(
            "SELECT c.count FROM outbox o JOIN checkpoints c "
            "ON c.log_id=o.log_id AND c.checkpoint_hash=o.checkpoint_hash "
            "WHERE o.log_id=? AND c.state='pending'", (log_id,)).fetchone()
        state = (WitnessState.WITNESSED if accepted is not None and seq <= accepted else
                 WitnessState.PENDING_WITNESS if pending is not None and seq <= pending[0] else
                 WitnessState.COMMITTED_LOCAL)
        return AppendResult(record, state)

    def _manifest_hash(self, log_id: str) -> str:
        row = self._db.connection.execute(
            "SELECT manifest_hash FROM manifests WHERE log_id = ?",
            (log_id,)).fetchone()
        if row is None:
            raise CasfError("unknown log")
        value = row[0]
        if not isinstance(value, str):
            raise CasfError("stored manifest is corrupt")
        return value

    # ------------------------------------------------------------- bundle

    def export_bundle(self, log_id: str, dest_dir: str | Path, *,
                      through: int | None = None) -> Path:
        """Stream a prefix from one snapshot and publish without replacement.

        ``through=None`` selects the snapshot's head. Accepted evidence is
        limited to that prefix. A pending final seal still blocks export.
        """
        return self.export_bundle_result(log_id, dest_dir, through=through).destination

    def export_bundle_result(self, log_id: str, dest_dir: str | Path, *,
                             through: int | None = None) -> ExportResult:
        """Return metadata from the published snapshot without rereading the store."""
        if through is not None and (type(through) is not int or not 0 <= through <= SAFE_INT_MAX):
            raise SchemaError("through must be a nonnegative safe integer")
        dest = Path(dest_dir)
        if os.path.lexists(dest):
            raise CasfError("export destination already exists")
        if not dest.parent.is_dir():
            raise CasfError("export destination parent does not exist")
        with tempfile.TemporaryDirectory(prefix=".casf-export-", dir=dest.parent) as staging:
            temporary = Path(staging) / "bundle"
            temporary.mkdir(mode=0o700)
            con = self._db.connection
            con.execute("BEGIN")
            try:
                row = con.execute(
                    "SELECT m.manifest_hash, m.envelope, h.count FROM manifests m "
                    "JOIN heads h ON h.log_id=m.log_id WHERE m.log_id=?", (log_id,)).fetchone()
                if row is None:
                    raise CasfError("unknown log")
                manifest_hash, manifest, count = row
                limit = count if through is None else through
                if limit > count:
                    raise SchemaError("through exceeds the snapshot head")
                pending = self.pending_checkpoint(log_id)
                if pending is not None:
                    pending_body = pending[0].get("body")
                    if isinstance(pending_body, dict) and pending_body.get("final") is True:
                        raise CasfError(
                            "final checkpoint receipt is pending; obtain its receipt "
                            "before bundle export, or use backup to preserve pending state")
                metadata: JsonObject = {
                    "version": 1, "type": "export", "log_id": log_id,
                    "manifest_hash": manifest_hash, "through": limit, "record_count": limit,
                    "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                }
                result = ExportResult(dest, metadata)
                self._write_member(temporary / "manifest.json", manifest + b"\n")
                self._write_member(temporary / "records.jsonl", self._export_records(log_id, limit))
                self._write_member(temporary / "checkpoints.jsonl",
                                   self._export_journal(log_id, limit, receipts=False))
                self._write_member(temporary / "receipts.jsonl",
                                   self._export_journal(log_id, limit, receipts=True))
                self._write_member(temporary / "export.json", canonicalize(metadata) + b"\n")
            finally:
                con.rollback()
            sync_directory(temporary)
            try:
                rename_directory_exclusive(temporary.absolute(), dest.absolute())
            except FileExistsError as exc:
                raise CasfError("export destination already exists") from exc
            sync_directory(dest.absolute().parent)
        return result

    def _export_records(self, log_id: str, through: int) -> Iterator[bytes]:
        seen = 0
        for seq, blob in self._db.connection.execute(
                "SELECT seq, envelope FROM records WHERE log_id=? AND seq<=? ORDER BY seq",
                (log_id, through)):
            if seq != seen + 1 or not isinstance(blob, bytes):
                raise CasfError("stored export record range is inconsistent")
            seen = seq
            yield blob + b"\n"
        if seen != through:
            raise CasfError("stored export record range is incomplete")

    def _export_journal(self, log_id: str, through: int, *, receipts: bool) -> Iterator[bytes]:
        for checkpoint, receipt in self._db.connection.execute(
                "SELECT c.envelope, r.envelope FROM checkpoints c "
                "LEFT JOIN receipts r ON r.checkpoint_hash=c.checkpoint_hash "
                "WHERE c.log_id=? AND c.count<=? AND c.state='accepted' ORDER BY c.idx",
                (log_id, through)):
            if not isinstance(checkpoint, bytes) or not isinstance(receipt, bytes):
                raise CasfError("accepted checkpoint is missing its receipt")
            yield (receipt if receipts else checkpoint) + b"\n"

    @staticmethod
    def _write_member(path: Path, data: bytes | Iterable[bytes]) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            if isinstance(data, bytes):
                stream.write(data)
            else:
                for chunk in data:
                    stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())

    @classmethod
    def restore_from_bundle(cls, db_path: str | Path,
                            log_priv: Ed25519PrivateKey,
                            bundle_dir: str | Path, *,
                            anchor: JsonObject | None = None,
                            anchor_checkpoint: JsonObject | None = None,
                            anchor_receipt: JsonObject | None = None,
                            require_active_status: bool = False,
                            local_only: bool = False,
                            trust_pins: Mapping[str, TrustPins] | None = None) -> "Writer":
        """Restore verified records and their checkpoint/receipt journal.

        A final checkpoint keeps the log sealed. A supplied pending tail
        keeps its original signed bytes for retry. The caller must establish
        independent manifest trust and authenticate a bare external anchor.
        Signed anchor pairs are authenticated with supplied pins. Optional
        active-status policy checks the bundled statements and provisioned
        serial minimum; it does not establish globally current status.
        This local operation cannot establish that an older export is current.
        A history behind the supplied anchor is retained sealed for inspection.
        """
        if os.path.lexists(db_path):
            raise CasfError("restore destination already exists")
        bundle = read_bundle(bundle_dir)
        if type(local_only) is not bool:
            raise SchemaError("local_only must be boolean")
        context = ManifestContext.read(bundle.manifest)
        if type(require_active_status) is not bool:
            raise SchemaError("require_active_status must be a boolean")
        if require_active_status:
            pins = (trust_pins.get(cast(str, context.body["log_id"]))
                    if trust_pins is not None else None)
            if pins is None:
                raise TrustError("restore status policy requires independent trust pins")
            context = ManifestContext.read(bundle.manifest, pins=pins)
            if type(pins.minimum_status_serial) is not int \
                    or not 1 <= pins.minimum_status_serial <= SAFE_INT_MAX:
                raise SchemaError("minimum_status_serial must be a positive safe integer")
            report = verify(bundle.manifest, bundle.records, pins,
                            status_envelopes=bundle.statuses)
            if report.trust_status is not TrustStatus.TRUSTED:
                raise TrustError("restore authority status rejected: "
                                 + ", ".join(report.diagnostic_codes))
            if report.result is not Result.PASS:
                raise CasfError("restore evidence verification failed: "
                                + ", ".join(report.diagnostic_codes))
        if anchor_checkpoint is not None or anchor_receipt is not None:
            if anchor_checkpoint is None or anchor_receipt is None or anchor is not None:
                raise SchemaError("supply both anchor envelopes without a bare anchor")
            log_id = cast(str, context.body["log_id"])
            pins = trust_pins.get(log_id) if trust_pins is not None else None
            if pins is None:
                raise TrustError("signed restore anchors require independent trust pins")
            context = ManifestContext.read(bundle.manifest, pins=pins)
            checkpoint = context.anchor(anchor_checkpoint, anchor_receipt)
            index = cast(int, checkpoint["index"])
            if index < len(bundle.checkpoints) and bundle.checkpoints[index].get(
                    "checkpoint_hash") != anchor_checkpoint["checkpoint_hash"]:
                raise CasfError("anchor conflicts with the restored checkpoint journal")
            if cast(int, checkpoint["count"]) <= len(bundle.records):
                if index >= len(bundle.checkpoints):
                    raise CasfError("anchor is missing from the restored checkpoint journal")
                if index < len(bundle.receipts):
                    if bundle.receipts[index].get("receipt_hash") != anchor_receipt["receipt_hash"]:
                        raise CasfError("anchor conflicts with the restored receipt journal")
                elif index == len(bundle.receipts) == len(bundle.checkpoints) - 1:
                    bundle.receipts.append(anchor_receipt)
                else:
                    raise CasfError("anchor receipt chain is missing from the restored journal")
            anchor = {"log_id": log_id, "manifest_hash": context.digest,
                      "count": checkpoint["count"], "head_hash": checkpoint["head_hash"]}
        anchor_count = 0
        if anchor is not None:
            value, digest = anchor.get("count"), anchor.get("head_hash")
            if type(value) is not int or not 0 <= value <= SAFE_INT_MAX \
                    or not isinstance(digest, str) \
                    or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise SchemaError("anchor requires a safe count and a head digest")
            if anchor.get("log_id", context.body["log_id"]) != context.body["log_id"] \
                    or anchor.get("manifest_hash", context.digest) != context.digest:
                raise CasfError("anchor belongs to a different manifest")
            anchor_count = value
        # Reserve a new destination atomically, including refusal of symlinks.
        if any(os.path.lexists(str(db_path) + suffix) for suffix in ("-wal", "-shm")):
            raise CasfError("restore destination has existing SQLite sidecars")
        try:
            fd = os.open(db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise CasfError("restore destination already exists") from exc
        os.close(fd)
        writer: Writer | None = None
        behind = anchor_count > len(bundle.records)
        try:
            writer = cls(db_path, log_priv, trust_pins=trust_pins, local_only=True)
            con = writer._db.connection
            con.execute("BEGIN IMMEDIATE")
            try:
                writer._insert_log(bundle.manifest)
                log_id_value = context.body["log_id"]
                if not isinstance(log_id_value, str):
                    raise SchemaError("manifest log_id is not a string")
                log_id = log_id_value
                prev_hash = crypto.genesis_hash(context.digest)
                for index, value in enumerate(bundle.records, start=1):
                    prev_hash, request = context.record(value, index, prev_hash)
                    con.execute(
                        "INSERT INTO records VALUES (?, ?, ?, ?, ?, ?)",
                        (log_id, index, request["event_id"], crypto.request_digest(request),
                         prev_hash, canonicalize(value)))
                sealed = writer._restore_journal(log_id, context, bundle.checkpoints,
                                                  bundle.receipts, len(bundle.records))
                if anchor is not None and not behind \
                        and anchor["head_hash"] != writer._record_head(
                            log_id, context, anchor_count):
                    raise CasfError("restored history disagrees with the anchor")
                con.execute(
                    "UPDATE heads SET count = ?, head_hash = ?, sealed = ? "
                    "WHERE log_id = ?",
                    (len(bundle.records), prev_hash, 1 if behind else sealed, log_id))
                con.commit()
            except BaseException:
                con.rollback()
                raise
        except BaseException:
            if writer is not None:
                writer.close()
            for suffix in ("", "-wal", "-shm"):
                Path(str(db_path) + suffix).unlink(missing_ok=True)
            raise
        if behind:
            writer.close()
            raise RestoreBehindWitnessError(
                f"RESTORE_BEHIND_WITNESS: anchor count {anchor_count} "
                f"exceeds the restored {len(bundle.records)} records; "
                "the log is sealed")
        if not local_only:
            writer._log_priv = writer._log_pub = writer._log_key_id = None
        return writer

    def _restore_journal(self, log_id: str, context: ManifestContext,
                         checkpoints: list[JsonObject], receipts: list[JsonObject],
                         count: int) -> int:
        """Restore a complete accepted prefix and at most one pending tail."""
        if len(receipts) > len(checkpoints) or len(checkpoints) - len(receipts) > 1:
            raise CasfError("restore requires a complete checkpoint and receipt prefix")
        con = self._db.connection
        chain = CheckpointChain(context, lambda n: self._record_head(log_id, context, n),
                                count)
        for index, checkpoint in enumerate(checkpoints):
            base_count = chain.count
            body = chain.checkpoint(checkpoint)
            accepted = index < len(receipts)
            if accepted:
                chain.receipt(receipts[index], body)
            con.execute("INSERT INTO checkpoints VALUES (?, ?, ?, ?, ?, ?)",
                        (log_id, index, chain.count, chain.digest, canonicalize(checkpoint),
                         "accepted" if accepted else "pending"))
            if accepted:
                con.execute("INSERT INTO receipts VALUES (?, ?)",
                            (chain.digest, canonicalize(receipts[index])))
            else:
                con.execute("INSERT INTO outbox VALUES (?, ?, ?, ?, 0, 0)",
                            (log_id, chain.digest, base_count + 1, chain.count))
        return 2 if chain.final else 0

    # -------------------------------------------------------- checkpoints

    @authorized
    def create_checkpoint(self, log_id: str, *,
                          final: bool = False) -> JsonObject:
        """Create a pending checkpoint with its extension range in the
        durable outbox before any submission (SPEC §12).

        At most one checkpoint is pending per log; the next one may
        only be created after the current receipt is validated and
        stored. A final checkpoint covers the whole committed head
        and seals appends in the same transaction.
        """
        if type(final) is not bool:
            raise SchemaError("final must be boolean")
        log_priv, _log_pub, log_key_id = self._signing_key()
        context = self._manifest_context(self.manifest_envelope(log_id))
        if context.body["log_key_id"] != log_key_id:
            raise CasfError("writer key does not match the manifest log key")
        con = self._db.connection
        con.execute("BEGIN IMMEDIATE")
        try:
            head = con.execute(
                "SELECT count, head_hash, sealed FROM heads WHERE log_id = ?",
                (log_id,)).fetchone()
            if head is None:
                raise CasfError("unknown log")
            count, head_hash, sealed = head
            bootstrap = self._bootstrapping and count == 0 and not con.execute(
                "SELECT 1 FROM checkpoints WHERE log_id=?", (log_id,)).fetchone()
            if sealed == 3 and not bootstrap:
                raise ReconciliationRequiredError(
                    "RECONCILIATION_REQUIRED: reconcile fresh witness state before checkpointing")
            pending = con.execute(
                "SELECT checkpoint_hash FROM outbox WHERE log_id = ?",
                (log_id,)).fetchone()
            if pending is not None:
                raise CasfError(
                    "a checkpoint is pending; retry the identical bytes "
                    "or store its receipt first")
            if sealed and not bootstrap:
                raise SealedError("log is sealed; no further checkpoint")
            last = con.execute(
                "SELECT idx, count, checkpoint_hash FROM checkpoints "
                "WHERE log_id = ? AND state = 'accepted' "
                "ORDER BY idx DESC LIMIT 1", (log_id,)).fetchone()
            index = last[0] + 1 if last else 0
            base_count = last[1] if last else 0
            prev_cp = last[2] if last else ZERO_HASH
            backlog = count - base_count
            if final and backlog > MAX_CHECKPOINT_BATCH:
                raise CasfError(
                    "PENDING_DRAIN: drain normal checkpoints before "
                    "the final seal")
            to_seq = base_count + min(backlog, MAX_CHECKPOINT_BATCH)
            if to_seq == count:
                tip = head_hash
            elif to_seq == 0:
                tip = crypto.genesis_hash(self._manifest_hash(log_id))
            else:
                row = con.execute(
                    "SELECT record_hash FROM records WHERE log_id = ? "
                    "AND seq = ?", (log_id, to_seq)).fetchone()
                if row is None:
                    raise CasfError("extension record missing")
                tip = row[0]
            body: JsonObject = {
                "version": 1, "type": "checkpoint", "log_id": log_id,
                "manifest_hash": self._manifest_hash(log_id),
                "index": index, "count": to_seq, "head_hash": tip,
                "previous_checkpoint_hash": prev_cp,
                "key_id": log_key_id,
                "issued_at": datetime.now(UTC).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"),
                "final": final,
            }
            validate_protocol_body("checkpoint", body)
            envelope: JsonObject = {
                "body": body,
                "checkpoint_hash": crypto.digest_checkpoint(body),
                "signature": crypto.sign_checkpoint(log_priv, body),
            }
            con.execute(
                "INSERT INTO checkpoints VALUES (?, ?, ?, ?, ?, 'pending')",
                (log_id, index, to_seq, envelope["checkpoint_hash"],
                 canonicalize(envelope)))
            con.execute(
                "INSERT INTO outbox VALUES (?, ?, ?, ?, 0, 0)",
                (log_id, envelope["checkpoint_hash"], base_count + 1,
                 to_seq))
            if final:
                con.execute(
                    "UPDATE heads SET sealed = 2 WHERE log_id = ?",
                    (log_id,))
            con.commit()
            return envelope
        except BaseException:
            con.rollback()
            raise

    def pending_checkpoint(self, log_id: str
                           ) -> tuple[JsonObject, int, int] | None:
        """The pending checkpoint and its range, or None.

        Recovery after a crash returns the identical signed bytes;
        inventing a different checkpoint for the same index is
        forbidden (SPEC §12).
        """
        row = self._db.connection.execute(
            "SELECT o.from_seq, o.to_seq, c.envelope FROM outbox o "
            "JOIN checkpoints c ON c.checkpoint_hash = o.checkpoint_hash "
            "WHERE o.log_id = ?", (log_id,)).fetchone()
        if row is None:
            return None
        env = parse(bytes(row[2]))
        if not isinstance(env, dict):
            raise CasfError("stored checkpoint is corrupt")
        return env, row[0], row[1]

    @authorized
    def record_receipt(self, log_id: str, receipt: JsonObject) -> None:
        """Validate and store the receipt for the pending checkpoint.

        The outbox entry clears and the checkpoint becomes accepted in
        the same transaction (SPEC §12).
        """
        receipt = WitnessResult(receipt).receipt
        if set(receipt) != {"body", "receipt_hash", "signature"}:
            raise SchemaError("receipt envelope must be exactly "
                              "body, receipt_hash, signature")
        body = receipt["body"]
        receipt_hash = receipt["receipt_hash"]
        signature = receipt["signature"]
        if (not isinstance(body, dict) or not isinstance(receipt_hash, str)
                or not isinstance(signature, str)):
            raise SchemaError("receipt envelope field types are wrong")
        validate_protocol_body("receipt", body)
        if crypto.digest_receipt(body) != receipt_hash:
            raise SchemaError("receipt_hash does not match the body")
        manifest = self.manifest_envelope(log_id)["body"]
        if not isinstance(manifest, dict):
            raise CasfError("stored manifest is corrupt")
        if body["log_id"] != log_id \
                or body["witness_id"] != manifest["witness_id"]:
            raise CasfError("receipt does not belong to this log")
        if body["manifest_hash"] != self._manifest_hash(log_id):
            raise CasfError("receipt manifest binding is invalid")
        witness_key = manifest["witness_public_key"]
        if not isinstance(witness_key, str):
            raise CasfError("stored manifest is corrupt")
        crypto.verify_receipt(crypto.b64url_decode(witness_key), body,
                              signature)
        con = self._db.connection
        con.execute("BEGIN IMMEDIATE")
        try:
            pending = con.execute(
                "SELECT checkpoint_hash FROM outbox WHERE log_id = ?",
                (log_id,)).fetchone()
            if pending is None:
                raise CasfError("no pending checkpoint for this receipt")
            if body["checkpoint_hash"] != pending[0]:
                raise CasfError("receipt names a different checkpoint")
            stored = con.execute(
                "SELECT envelope FROM checkpoints "
                "WHERE checkpoint_hash = ?", (pending[0],)).fetchone()
            if stored is None:
                raise CasfError("pending checkpoint is missing")
            cp_env = parse(bytes(stored[0]))
            if not isinstance(cp_env, dict):
                raise CasfError("stored checkpoint is corrupt")
            cp_body = cp_env["body"]
            if not isinstance(cp_body, dict):
                raise CasfError("stored checkpoint is corrupt")
            if body["count"] != cp_body["count"] \
                    or body["head_hash"] != cp_body["head_hash"] \
                    or body["checkpoint_index"] != cp_body["index"]:
                raise CasfError("receipt view disagrees with the pending "
                                "checkpoint")
            previous_digest = ZERO_HASH
            index = cp_body["index"]
            if type(index) is not int:
                raise CasfError("stored checkpoint index is invalid")
            if index != 0:
                previous = con.execute(
                    "SELECT r.envelope FROM receipts r JOIN checkpoints c "
                    "ON c.checkpoint_hash = r.checkpoint_hash "
                    "WHERE c.log_id = ? AND c.idx = ? AND c.state = 'accepted'",
                    (log_id, index - 1)).fetchone()
                if previous is None:
                    raise CasfError("previous checkpoint receipt is missing")
                digest = self._stored_object(previous[0]).get("receipt_hash")
                if not isinstance(digest, str):
                    raise CasfError("stored previous receipt hash is invalid")
                previous_digest = digest
            if body["previous_receipt_hash"] != previous_digest:
                raise CasfError("receipt chain disagrees with the previous receipt")
            con.execute("INSERT INTO receipts VALUES (?, ?)",
                        (pending[0], canonicalize(receipt)))
            con.execute(
                "UPDATE checkpoints SET state = 'accepted' "
                "WHERE checkpoint_hash = ?", (pending[0],))
            con.execute("DELETE FROM outbox WHERE log_id = ?", (log_id,))
            if self._active_state is not None:
                self._startup_failed = True
                self._active_state.save(self._startup_serial, (index, pending[0]))
            con.commit()
            self._startup_failed = False
        except BaseException:
            con.rollback()
            if self._startup_failed:
                from casf.writer.recovery import hold_writer

                hold_writer(self, log_id)
            raise

    @authorized
    def submit_pending(self, log_id: str, base_url: str, token: str, *,
                       timeout: float = 10.0) -> JsonObject:
        """Submit the pending checkpoint to the witness and store the
        returned receipt. Failure keeps the identical bytes for retry.
        """
        pending = self.pending_checkpoint(log_id)
        if pending is None:
            raise CasfError("no pending checkpoint for this log")
        envelope, from_seq, to_seq = pending
        cursor = self._db.connection.execute(
            "SELECT envelope FROM records WHERE log_id = ? "
            "AND seq BETWEEN ? AND ? ORDER BY seq",
            (log_id, from_seq, to_seq))
        records: list[JsonObject] = []
        for (blob,) in cursor:
            env = parse(bytes(blob))
            if not isinstance(env, dict):
                raise CasfError("stored record is corrupt")
            records.append(env)
        request = json.dumps(
            {"checkpoint": envelope, "records": records}).encode()
        con = self._db.connection
        con.execute("BEGIN IMMEDIATE")
        try:
            changed = con.execute(
                "UPDATE outbox SET attempts=MIN(attempts + 1, ?) "
                "WHERE log_id=? AND checkpoint_hash=?",
                (SAFE_INT_MAX, log_id, envelope["checkpoint_hash"])).rowcount
            if changed != 1:
                raise CasfError("pending checkpoint changed before submission")
            con.commit()
        except BaseException:
            con.rollback()
            raise
        try:
            status, payload = http_request(
                base_url, "POST", f"/v1/logs/{log_id}/checkpoints", token,
                request, timeout=timeout)
        except (OSError, http.client.HTTPException, ResponseLimitError) as e:
            raise InconclusiveError(
                "witness unreachable; the pending checkpoint keeps its "
                "bytes for retry") from e
        except ValueError as e:
            if str(e) == "HTTP requires a literal loopback address; use HTTPS":
                raise CasfError("HTTP requires a literal loopback address; use HTTPS") from e
            raise CasfError("invalid witness request configuration") from e
        if status in (429, 503):
            raise InconclusiveError("witness temporarily unavailable; pending bytes are retained")
        if status not in (200, 201):
            raise CasfError(f"witness rejected the submission (HTTP {status})")
        try:
            data = parse(payload)
        except CasfError as e:
            raise CasfError("witness answer was not valid JSON") from e
        if not isinstance(data, dict) \
                or not isinstance(data.get("receipt"), dict):
            raise CasfError("witness answer carried no receipt object")
        receipt = data["receipt"]
        if not isinstance(receipt, dict):
            raise CasfError("witness answer carried no receipt object")
        self.record_receipt(log_id, receipt)
        return receipt

    def reconcile_witness(self, log_id: str, base_url: str, token: str, *,
                          timeout: float = 10.0, max_chain_steps: int = 10_000,
                          retained_checkpoint: tuple[int, str] | None = None) -> LatestView:
        """Reconcile a fresh witness journal against verified local records.

        Independent pins are required. Failure retains a durable write hold;
        success preserves pending bytes and final seals. Authority status and
        external high-water persistence remain the caller's responsibility.
        """
        from casf.writer.recovery import reconcile_witness

        return reconcile_witness(self, log_id, base_url, token, timeout=timeout,
                                 max_chain_steps=max_chain_steps,
                                 retained_checkpoint=retained_checkpoint)

    def recover_pending_receipt(self, log_id: str, base_url: str, token: str, *,
                                timeout: float = 10.0) -> JsonObject:
        """Recover an already accepted receipt using the pending digest.

        Requires independent manifest pins, but no private signing key.
        Failure preserves the outbox; lookup does not establish freshness.
        """
        if self._trust_pins is None:
            raise TrustError("receipt recovery requires independent trust pins")
        context = self._manifest_context(self.manifest_envelope(log_id))
        pending = self.pending_checkpoint(log_id)
        if pending is None:
            raise InconclusiveError("no pending checkpoint for receipt recovery")
        checkpoint = pending[0]
        try:
            status, payload = http_request(
                base_url, "GET", f"/v1/logs/{log_id}/receipts/{checkpoint['checkpoint_hash']}",
                token, b"", timeout=timeout)
        except (OSError, http.client.HTTPException, ResponseLimitError) as exc:
            raise InconclusiveError("receipt lookup unavailable; pending checkpoint unchanged") from exc
        except ValueError as exc:
            raise SchemaError("invalid witness request configuration") from exc
        if status != 200:
            raise InconclusiveError("receipt unavailable; pending checkpoint unchanged")
        data = parse(payload)
        if not isinstance(data, dict) or set(data) != {"checkpoint", "receipt"} \
                or not isinstance(data["receipt"], dict):
            raise SchemaError("receipt lookup must return checkpoint and receipt objects")
        if data["checkpoint"] != checkpoint:
            raise CasfError("receipt lookup returned a different pending checkpoint")
        receipt = data["receipt"]
        context.anchor(checkpoint, receipt)
        self.record_receipt(log_id, receipt)
        return receipt

    def seal_log(self, log_id: str) -> JsonObject:
        """Seal the log with a final checkpoint (SPEC §12).

        Requires no pending checkpoint and at most 128 unwitnessed
        records, otherwise PENDING_DRAIN. No append follows sealing,
        even if the witness is offline; receipt acquisition for the
        final checkpoint may still be retried afterwards.
        """
        return self.create_checkpoint(log_id, final=True)
