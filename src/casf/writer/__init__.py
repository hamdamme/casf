"""Sequencing and idempotent append (SPEC §11, §17).

C05 scope: manifest storage with genesis, transactional record append,
event ID idempotency, contention bounds. C06 adds bundle export and
restore (SPEC §18, §20). C08 adds checkpoint production with a durable
outbox and receipt acquisition (SPEC §12).

Writers serialize through the database (BEGIN IMMEDIATE), never
through a process mutex alone. Return success only after COMMIT; a
caller with an uncertain outcome retries with the same event ID.
"""

import http.client
import json
import os
import random
import shutil
import sqlite3
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.bundle import read_bundle
from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import MAX_CHECKPOINT_BATCH, SAFE_INT_MAX
from casf.errors import CasfError, SchemaError
from casf.model.schema import validate_protocol_body
from casf.storage import Database
from casf.types import JsonObject

__all__ = ["BusyError", "EventIdConflictError",
           "RestoreBehindWitnessError", "SealedError", "Writer"]

ZERO_HASH = "00" * 32  # hex(Z), the null previous checkpoint digest


class BusyError(CasfError):
    """Lock contention outlived the bounded retries (SPEC §17)."""


class EventIdConflictError(CasfError):
    """Same event ID with a different request digest (SPEC §11)."""


class SealedError(CasfError):
    """No append follows sealing (SPEC §12, §16)."""


class RestoreBehindWitnessError(SealedError):
    """Restored history is behind an external witness anchor (T15).

    The restore completes so the data stays readable, but the log is
    sealed and every later append fails with RESTORE_BEHIND_WITNESS.
    """


class Writer:
    """Appends signed records to one SQLite store."""

    def __init__(self, db_path: str | Path, log_priv: Ed25519PrivateKey, *,
                 busy_timeout_ms: int = 5000, max_retries: int = 3,
                 retry_jitter: float = 0.05) -> None:
        self._db = Database(db_path, busy_timeout_ms)
        self._log_priv = log_priv
        self._log_pub = crypto.public_key_raw(log_priv)
        self._log_key_id = crypto.key_id(self._log_pub)
        self._max_retries = max_retries
        self._retry_jitter = retry_jitter
        self._check_heads()

    def close(self) -> None:
        self._db.close()

    def backup(self, dest_path: str | Path) -> None:
        """Consistent backup through the SQLite backup API (SPEC §18).

        Copying only the live database file is not an approved
        procedure; this includes the required WAL state. Never
        overwrites an existing file.
        """
        dest = str(dest_path)
        if os.path.exists(dest):
            raise CasfError("backup destination already exists")
        target = sqlite3.connect(dest)
        try:
            self._db.connection.backup(target)
        finally:
            target.close()

    def _check_heads(self) -> None:
        """Startup check: stored heads must match the records table
        (SPEC §17). Full chain verification uses casf.verifier.

        The reads run inside one snapshot transaction; otherwise a
        concurrent commit between the heads read and the records read
        reports a false mismatch (caught by CI under process load).
        """
        con = self._db.connection
        con.execute("BEGIN")
        try:
            for log_id, count, head_hash in con.execute(
                    "SELECT log_id, count, head_hash FROM heads"):
                self._debug_hook("after_heads_read")
                actual = con.execute(
                    "SELECT COUNT(*), MAX(seq) FROM records WHERE log_id = ?",
                    (log_id,)).fetchone()
                if actual[0] != count:
                    raise CasfError(
                        f"head count {count} disagrees with {actual[0]} "
                        "stored records; restore or recovery required")
                if count == 0:
                    expected = crypto.genesis_hash(self._manifest_hash(log_id))
                else:
                    row = con.execute(
                        "SELECT record_hash FROM records WHERE log_id = ? "
                        "AND seq = ?", (log_id, count)).fetchone()
                    if row is None:
                        raise CasfError(
                            "head record missing; restore or recovery "
                            "required")
                    expected = row[0]
                if head_hash != expected:
                    raise CasfError(
                        "head hash disagrees with stored records; "
                        "restore or recovery required")
        finally:
            con.rollback()

    def _debug_hook(self, stage: str) -> None:
        """Test hook; no-op in production."""

    # ---------------------------------------------------------- manifest

    def create_log(self, manifest_envelope: JsonObject) -> str:
        """Store the manifest and genesis transactionally (SPEC §10)."""
        if set(manifest_envelope) != {"body", "manifest_hash", "signature"}:
            raise SchemaError("manifest envelope must be exactly "
                              "body, manifest_hash, signature")
        body = manifest_envelope["body"]
        manifest_hash = manifest_envelope["manifest_hash"]
        if not isinstance(body, dict) or not isinstance(manifest_hash, str):
            raise SchemaError("manifest envelope field types are wrong")
        validate_protocol_body("manifest", body)
        if crypto.digest_manifest(body) != manifest_hash:
            raise SchemaError("manifest_hash does not match the body")
        if body["log_key_id"] != self._log_key_id:
            raise CasfError("writer key does not match the manifest log key")
        log_id = body["log_id"]
        if not isinstance(log_id, str):
            raise SchemaError("log_id: expected string")
        genesis = crypto.genesis_hash(manifest_hash)
        blob = canonicalize(manifest_envelope)
        con = self._db.connection
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO manifests VALUES (?, ?, ?)",
                (log_id, manifest_hash, blob))
            con.execute(
                "INSERT INTO heads VALUES (?, 0, ?, 0)",
                (log_id, genesis))
            con.commit()
        except sqlite3.IntegrityError as e:
            con.rollback()
            raise CasfError("log already exists") from e
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

    def append(self, log_id: str, *, event_id: str, actor: str,
               event_type: str, payload: JsonObject,
               attributes: JsonObject) -> JsonObject:
        """Append one record; idempotent by event ID (SPEC §11, §17)."""
        if not isinstance(payload, dict) or not isinstance(attributes, dict):
            raise SchemaError("payload and attributes must be objects")
        request: JsonObject = {
            "event_id": event_id, "actor": actor, "event_type": event_type,
            "payload": payload, "attributes": attributes,
        }
        request_digest = crypto.request_digest(request)
        attempts = max(1, self._max_retries)
        for attempt in range(attempts):
            try:
                return self._append_once(log_id, request, request_digest)
            except sqlite3.OperationalError as e:
                if "locked" not in str(e) or attempt + 1 >= attempts:
                    raise BusyError("append could not acquire the write lock "
                                    "within the retry budget") from e
                time.sleep(self._retry_jitter * (attempt + 1)
                           * (1 + random.random()))
        raise BusyError("unreachable")  # pragma: no cover

    def _append_once(self, log_id: str, request: JsonObject,
                     request_digest: str) -> JsonObject:
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
                con.commit()
                if not isinstance(env, dict):
                    raise CasfError("stored record is corrupt")
                return env
            head = con.execute(
                "SELECT count, head_hash, sealed FROM heads WHERE log_id = ?",
                (log_id,)).fetchone()
            if head is None:
                raise CasfError("unknown log")
            count, head_hash, sealed = head
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
                "prev_hash": head_hash, "key_id": self._log_key_id,
            }
            validate_protocol_body("record", body)
            record_hash = crypto.digest_record(body)
            envelope: JsonObject = {
                "body": body, "record_hash": record_hash,
                "signature": crypto.sign_record(self._log_priv, body),
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
            con.commit()
            self._debug_hook("after_commit")
            return envelope
        except BaseException:
            con.rollback()
            raise

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

    def export_bundle(self, log_id: str, dest_dir: str | Path) -> Path:
        """Export one log as a bundle directory (SPEC §20).

        The read runs inside one snapshot transaction. Files are
        written to a sibling temporary directory, flushed, then moved
        into place with a single rename; an existing destination is
        never overwritten.
        """
        dest = Path(dest_dir)
        if dest.exists():
            raise CasfError("export destination already exists")
        if not dest.parent.is_dir():
            raise CasfError("export destination parent does not exist")
        tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
        if tmp.exists():
            raise CasfError("stale export temporary directory in the way")

        con = self._db.connection
        con.execute("BEGIN")
        try:
            manifest = self.manifest_envelope(log_id)
            records = list(self.records(log_id))
        finally:
            con.rollback()
        manifest_hash = self._manifest_hash(log_id)

        metadata: JsonObject = {
            "version": 1, "type": "export", "log_id": log_id,
            "manifest_hash": manifest_hash,
            "through": len(records), "record_count": len(records),
            "generated_at": datetime.now(UTC).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        try:
            tmp.mkdir()
            self._write_member(tmp / "manifest.json",
                               canonicalize(manifest) + b"\n")
            self._write_member(tmp / "records.jsonl", b"".join(
                canonicalize(env) + b"\n" for env in records))
            # checkpoints and receipts arrive with C08; the members
            # exist so the file set is already the §20 shape
            self._write_member(tmp / "checkpoints.jsonl", b"")
            self._write_member(tmp / "receipts.jsonl", b"")
            self._write_member(tmp / "export.json",
                               canonicalize(metadata) + b"\n")
            os.rename(tmp, dest)
        except BaseException:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        return dest

    @staticmethod
    def _write_member(path: Path, data: bytes) -> None:
        with open(path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

    @classmethod
    def restore_from_bundle(cls, db_path: str | Path,
                            log_priv: Ed25519PrivateKey,
                            bundle_dir: str | Path, *,
                            anchor: JsonObject | None = None) -> "Writer":
        """Build a fresh store from a bundle (SPEC §18, §20).

        Every record hash and signature is verified against the
        manifest key before anything is written. When an external
        anchor reports a count beyond the restored history, the data
        is still stored but the log is sealed and every later append
        reports RESTORE_BEHIND_WITNESS (T15).
        """
        if os.path.exists(db_path):
            raise CasfError("restore destination already exists")
        bundle = read_bundle(bundle_dir)
        sealed = 0
        anchor_count = 0
        writer = cls(db_path, log_priv)
        try:
            writer.create_log(bundle.manifest)
            con = writer._db.connection
            con.execute("BEGIN IMMEDIATE")
            try:
                manifest_body = bundle.manifest["body"]
                if not isinstance(manifest_body, dict):
                    raise CasfError("manifest envelope field types are wrong")
                log_id_value = manifest_body["log_id"]
                if not isinstance(log_id_value, str):
                    raise CasfError("manifest envelope field types are wrong")
                log_id = log_id_value
                prev_hash = crypto.genesis_hash(bundle.manifest_hash)
                for index, envelope in enumerate(bundle.records, start=1):
                    prev_hash = writer._restore_record(
                        con, log_id, index, envelope, prev_hash)
                if anchor is not None:
                    count_value = anchor.get("count")
                    if isinstance(count_value, int):
                        anchor_count = count_value
                        restored = len(bundle.records)
                        if anchor_count > restored:
                            sealed = 1
                        elif (anchor_count == restored
                              and anchor.get("head_hash") is not None
                              and anchor["head_hash"] != prev_hash):
                            raise CasfError(
                                "restored history disagrees with the anchor")
                con.execute(
                    "UPDATE heads SET count = ?, head_hash = ?, sealed = ? "
                    "WHERE log_id = ?",
                    (len(bundle.records), prev_hash, sealed, log_id))
                con.commit()
            except BaseException:
                con.rollback()
                raise
        except BaseException:
            writer.close()
            raise
        if sealed:
            writer.close()
            raise RestoreBehindWitnessError(
                f"RESTORE_BEHIND_WITNESS: anchor count {anchor_count} "
                f"exceeds the restored {len(bundle.records)} records; "
                "the log is sealed")
        return writer

    def _restore_record(self, con: sqlite3.Connection, log_id: str,
                        index: int, envelope: JsonObject,
                        prev_hash: str) -> str:
        """Verify one restored record and insert it; return its hash."""
        if set(envelope) != {"body", "record_hash", "signature"}:
            raise SchemaError("record envelope must be exactly "
                              "body, record_hash, signature")
        body = envelope["body"]
        record_hash = envelope["record_hash"]
        signature = envelope["signature"]
        if (not isinstance(body, dict) or not isinstance(record_hash, str)
                or not isinstance(signature, str)):
            raise SchemaError("record envelope field types are wrong")
        validate_protocol_body("record", body)
        if body["log_id"] != log_id:
            raise CasfError("record log_id disagrees with the bundle")
        if body["manifest_hash"] != self._manifest_hash(log_id):
            raise CasfError("record manifest_hash disagrees with the bundle")
        if body["seq"] != index:
            raise CasfError("records are not ordered by sequence")
        if body["prev_hash"] != prev_hash:
            raise CasfError("record chain is broken at the restore input")
        if crypto.digest_record(body) != record_hash:
            raise CasfError("record_hash does not match the body")
        crypto.verify_record(self._log_pub, body, signature)
        request: JsonObject = {
            "event_id": body["event_id"], "actor": body["actor"],
            "event_type": body["event_type"], "payload": body["payload"],
            "attributes": body["attributes"],
        }
        con.execute(
            "INSERT INTO records VALUES (?, ?, ?, ?, ?, ?)",
            (log_id, index, body["event_id"], crypto.request_digest(request),
             record_hash, canonicalize(envelope)))
        return record_hash

    # -------------------------------------------------------- checkpoints

    def create_checkpoint(self, log_id: str, *,
                          final: bool = False) -> JsonObject:
        """Create a pending checkpoint with its extension range in the
        durable outbox before any submission (SPEC §12).

        At most one checkpoint is pending per log; the next one may
        only be created after the current receipt is validated and
        stored. A final checkpoint covers the whole committed head
        and seals appends in the same transaction.
        """
        con = self._db.connection
        con.execute("BEGIN IMMEDIATE")
        try:
            pending = con.execute(
                "SELECT checkpoint_hash FROM outbox WHERE log_id = ?",
                (log_id,)).fetchone()
            if pending is not None:
                raise CasfError(
                    "a checkpoint is pending; retry the identical bytes "
                    "or store its receipt first")
            head = con.execute(
                "SELECT count, head_hash, sealed FROM heads WHERE log_id = ?",
                (log_id,)).fetchone()
            if head is None:
                raise CasfError("unknown log")
            count, head_hash, sealed = head
            if sealed:
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
                "key_id": self._log_key_id,
                "issued_at": datetime.now(UTC).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"),
                "final": bool(final),
            }
            validate_protocol_body("checkpoint", body)
            envelope: JsonObject = {
                "body": body,
                "checkpoint_hash": crypto.digest_checkpoint(body),
                "signature": crypto.sign_checkpoint(self._log_priv, body),
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

    def record_receipt(self, log_id: str, receipt: JsonObject) -> None:
        """Validate and store the receipt for the pending checkpoint.

        The outbox entry clears and the checkpoint becomes accepted in
        the same transaction (SPEC §12).
        """
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
            con.execute("INSERT INTO receipts VALUES (?, ?)",
                        (pending[0], canonicalize(receipt)))
            con.execute(
                "UPDATE checkpoints SET state = 'accepted' "
                "WHERE checkpoint_hash = ?", (pending[0],))
            con.execute("DELETE FROM outbox WHERE log_id = ?", (log_id,))
            con.commit()
        except BaseException:
            con.rollback()
            raise

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
        parts = urlsplit(base_url)
        if not parts.hostname:
            raise CasfError("witness URL has no host")
        request = json.dumps(
            {"checkpoint": envelope, "records": records}).encode()
        try:
            conn = http.client.HTTPConnection(parts.hostname,
                                              parts.port or 80,
                                              timeout=timeout)
            try:
                conn.request(
                    "POST", f"/v1/logs/{log_id}/checkpoints", body=request,
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {token}"})
                resp = conn.getresponse()
                payload = resp.read()
                status = resp.status
            finally:
                conn.close()
        except (OSError, http.client.HTTPException) as e:
            self._db.connection.execute(
                "UPDATE outbox SET attempts = attempts + 1 "
                "WHERE log_id = ?", (log_id,))
            self._db.connection.commit()
            raise CasfError(
                "witness unreachable; the pending checkpoint keeps its "
                "bytes for retry") from e
        try:
            data = json.loads(payload)
        except ValueError as e:
            raise CasfError("witness answer was not valid JSON") from e
        if status not in (200, 201) or not isinstance(data, dict) \
                or not isinstance(data.get("receipt"), dict):
            code = data.get("code") if isinstance(data, dict) else None
            raise CasfError(f"witness rejected the submission: "
                            f"{code or status}")
        receipt = data["receipt"]
        if not isinstance(receipt, dict):
            raise CasfError("witness answer carried no receipt object")
        self.record_receipt(log_id, receipt)
        return receipt
