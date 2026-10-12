"""Witness acceptance state machine (SPEC §13).

The witness is a stateful verifier with its own storage, not a
timestamp signer. A submission carries the checkpoint envelope and
the complete record envelopes from the retained count plus 1 through
the proposed count. Acceptance runs in one serialized per log
transaction: an identical checkpoint replays its stored receipt, a
conflicting proposal is rejected with CONFLICT and the retained high
water state never moves. The receipt is created, stored and
committed before it is returned; a crash after commit replays the
same receipt on retry (T22).

Retained per log: the immutable manifest, current count and head,
current checkpoint index and digest, the receipt chain tip, the
sealed flag, every accepted checkpoint and receipt, and the accepted
record digests by sequence. Record bodies are discarded after
validation and commit. HTTP transport arrives with C07 session 2.
"""

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import SAFE_INT_MAX, WITNESS_MAX_RECORDS
from casf.errors import CasfError, NoCheckpointError, SchemaError
from casf.model.schema import validate_protocol_body
from casf.storage import Database
from casf.types import JsonObject

__all__ = ["ConflictError", "NoCheckpointError", "UnknownLogError", "Witness"]

ZERO_HASH = "00" * 32  # hex(Z), the null previous digest (SPEC §13)

SCHEMA = """
CREATE TABLE IF NOT EXISTS manifests(
    log_id TEXT PRIMARY KEY,
    manifest_hash TEXT NOT NULL UNIQUE,
    envelope BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS w_state(
    log_id TEXT PRIMARY KEY,
    count INTEGER NOT NULL,
    head_hash TEXT NOT NULL,
    checkpoint_index INTEGER NOT NULL,
    checkpoint_hash TEXT NOT NULL,
    receipt_hash TEXT NOT NULL,
    sealed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS w_checkpoints(
    log_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    checkpoint_hash TEXT NOT NULL,
    envelope BLOB NOT NULL,
    UNIQUE(log_id, idx),
    UNIQUE(log_id, checkpoint_hash)
);
CREATE TABLE IF NOT EXISTS w_receipts(
    checkpoint_hash TEXT PRIMARY KEY,
    envelope BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS w_record_digests(
    log_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    record_hash TEXT NOT NULL,
    UNIQUE(log_id, seq)
);
-- Append-only guards (SPEC §17), same intent as the writer store.
CREATE TRIGGER IF NOT EXISTS w_checkpoints_no_update
BEFORE UPDATE ON w_checkpoints
BEGIN SELECT RAISE(ABORT, 'checkpoints are append only'); END;
CREATE TRIGGER IF NOT EXISTS w_checkpoints_no_delete
BEFORE DELETE ON w_checkpoints
BEGIN SELECT RAISE(ABORT, 'checkpoints are append only'); END;
CREATE TRIGGER IF NOT EXISTS w_receipts_no_update
BEFORE UPDATE ON w_receipts
BEGIN SELECT RAISE(ABORT, 'receipts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS w_receipts_no_delete
BEFORE DELETE ON w_receipts
BEGIN SELECT RAISE(ABORT, 'receipts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS w_digests_no_update
BEFORE UPDATE ON w_record_digests
BEGIN SELECT RAISE(ABORT, 'record digests are append only'); END;
CREATE TRIGGER IF NOT EXISTS w_digests_no_delete
BEFORE DELETE ON w_record_digests
BEGIN SELECT RAISE(ABORT, 'record digests are append only'); END;
CREATE TRIGGER IF NOT EXISTS w_manifests_no_update
BEFORE UPDATE ON manifests
BEGIN SELECT RAISE(ABORT, 'manifests are immutable'); END;
CREATE TRIGGER IF NOT EXISTS w_manifests_no_delete
BEFORE DELETE ON manifests
BEGIN SELECT RAISE(ABORT, 'manifests are immutable'); END;
"""


class ConflictError(CasfError):
    """Conflicting proposal against retained state (SPEC §13 CONFLICT).

    Carries the safe evidence identifiers of both sides so an
    operator can investigate without request bodies.
    """

    def __init__(self, message: str, *, existing: str = "",
                 proposed: str = "") -> None:
        super().__init__(message)
        self.existing = existing
        self.proposed = proposed


class UnknownLogError(CasfError):
    """Submission names a log the witness has not registered."""


class Witness:
    """Durable witness for checkpoint acceptance and receipts."""

    def __init__(self, db_path: str | Path, witness_priv: Ed25519PrivateKey,
                 *, authority_keys: dict[str, bytes] | None = None,
                 busy_timeout_ms: int = 5000) -> None:
        # One connection shared by HTTP handler threads; the lock
        # serializes every call, which matches the one serialized
        # transaction rule of Section 13.
        self._lock = threading.RLock()
        self._db = Database(db_path, busy_timeout_ms, schema=SCHEMA,
                            check_same_thread=False)
        self._priv = witness_priv
        self._pub = crypto.public_key_raw(witness_priv)
        self._witness_id = crypto.key_id(self._pub)
        self._authority_keys = dict(authority_keys or {})

    def close(self) -> None:
        self._db.close()

    def _debug_hook(self, stage: str) -> None:
        """Test hook; no-op in production."""

    # ------------------------------------------------------ registration

    def register_log(self, manifest_envelope: JsonObject) -> str:
        """Register a preapproved manifest (SPEC §10, §13).

        This is the local administrator command; remote callers
        cannot register logs. The authority signature is verified
        against the configured pins and the manifest must name this
        witness.
        """
        with self._lock:
            return self._register_log(manifest_envelope)

    def _register_log(self, manifest_envelope: JsonObject) -> str:
        if set(manifest_envelope) != {"body", "manifest_hash", "signature"}:
            raise SchemaError("manifest envelope must be exactly "
                              "body, manifest_hash, signature")
        body = manifest_envelope["body"]
        manifest_hash = manifest_envelope["manifest_hash"]
        signature = manifest_envelope["signature"]
        if (not isinstance(body, dict) or not isinstance(manifest_hash, str)
                or not isinstance(signature, str)):
            raise SchemaError("manifest envelope field types are wrong")
        validate_protocol_body("manifest", body)
        if crypto.digest_manifest(body) != manifest_hash:
            raise SchemaError("manifest_hash does not match the body")
        issuer = body["issuer_id"]
        authority = self._authority_keys.get(issuer) \
            if isinstance(issuer, str) else None
        if authority is None:
            raise CasfError("no authority key configured for the issuer")
        crypto.verify_manifest(authority, body, signature)
        if body["witness_id"] != self._witness_id:
            raise CasfError("manifest names a different witness")
        witness_key_value = body["witness_public_key"]
        log_key_value = body["log_public_key"]
        if not isinstance(witness_key_value, str) \
                or not isinstance(log_key_value, str):
            raise SchemaError("manifest key fields must be strings")
        witness_pub = crypto.b64url_decode(witness_key_value)
        if witness_pub != self._pub:
            raise CasfError("manifest witness key does not match this witness")
        log_pub = crypto.b64url_decode(log_key_value)
        if crypto.key_id(log_pub) != body["log_key_id"]:
            raise CasfError("manifest log key id does not match its key")
        log_id = body["log_id"]
        if not isinstance(log_id, str):
            raise SchemaError("log_id: expected string")
        con = self._db.connection
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT INTO manifests VALUES (?, ?, ?)",
                        (log_id, manifest_hash,
                         canonicalize(manifest_envelope)))
            con.execute(
                "INSERT INTO w_state VALUES (?, 0, ?, -1, ?, ?, 0)",
                (log_id, crypto.genesis_hash(manifest_hash),
                 ZERO_HASH, ZERO_HASH))
            con.commit()
        except sqlite3.IntegrityError as e:
            con.rollback()
            raise CasfError("log already registered") from e
        return log_id

    def _manifest(self, log_id: str) -> tuple[JsonObject, str, bytes]:
        row = self._db.connection.execute(
            "SELECT envelope FROM manifests WHERE log_id = ?", (log_id,)
        ).fetchone()
        if row is None:
            raise UnknownLogError("unknown log; register the manifest first")
        env = parse(bytes(row[0]))
        if not isinstance(env, dict):
            raise CasfError("stored manifest is corrupt")
        body = env["body"]
        manifest_hash = env["manifest_hash"]
        if not isinstance(body, dict) or not isinstance(manifest_hash, str):
            raise CasfError("stored manifest is corrupt")
        log_key_value = body["log_public_key"]
        if not isinstance(log_key_value, str):
            raise CasfError("stored manifest is corrupt")
        return body, manifest_hash, crypto.b64url_decode(log_key_value)

    # -------------------------------------------------------- acceptance

    def submit(self, log_id: str, checkpoint: JsonObject,
               records: list[JsonObject]) -> JsonObject:
        """Accept one checkpoint extension and return its receipt.

        The whole acceptance runs in one serialized transaction. An
        identical previously accepted checkpoint replays the stored
        receipt without a second state transition (SPEC §13, T22).
        """
        receipt, _accepted = self._submit(log_id, checkpoint, records)
        return receipt

    def _submit(self, log_id: str, checkpoint: JsonObject,
                records: list[JsonObject]) -> tuple[JsonObject, bool]:
        """Submit and report whether a new acceptance happened.

        The transport layer needs the flag for 201 versus 200.
        """
        with self._lock:
            return self._submit_locked(log_id, checkpoint, records)

    def _submit_locked(self, log_id: str, checkpoint: JsonObject,
                       records: list[JsonObject]) -> tuple[JsonObject, bool]:
        if not isinstance(records, list):
            raise SchemaError("records must be a list of envelopes")
        _body, manifest_hash, log_pub = self._manifest(log_id)
        checkpoint_hash = self._validate_checkpoint(
            log_id, manifest_hash, log_pub, checkpoint)
        con = self._db.connection
        con.execute("BEGIN IMMEDIATE")
        try:
            state = con.execute(
                "SELECT count, head_hash, checkpoint_index, "
                "checkpoint_hash, receipt_hash, sealed "
                "FROM w_state WHERE log_id = ?", (log_id,)).fetchone()
            if state is None:
                raise UnknownLogError("unknown log")
            count, head_hash, cp_index, cp_hash, receipt_tip, sealed = state
            stored = con.execute(
                "SELECT envelope FROM w_receipts WHERE checkpoint_hash = ?",
                (checkpoint_hash,)).fetchone()
            if stored is not None:
                con.commit()
                receipt = parse(bytes(stored[0]))
                if not isinstance(receipt, dict):
                    raise CasfError("stored receipt is corrupt")
                return receipt, False
            if sealed:
                raise CasfError(
                    "log is sealed; only receipt retrieval is accepted")
            body = checkpoint["body"]
            if not isinstance(body, dict):
                raise SchemaError("checkpoint envelope field types are wrong")
            if body["index"] <= cp_index:
                raise ConflictError(
                    "checkpoint index already accepted with a different "
                    "digest", existing=cp_hash, proposed=checkpoint_hash)
            if body["index"] != cp_index + 1:
                raise CasfError("checkpoint index gap; the next index is "
                                f"{cp_index + 1}")
            if body["previous_checkpoint_hash"] != cp_hash:
                raise ConflictError(
                    "previous checkpoint digest does not match the retained "
                    "tip", existing=cp_hash, proposed=checkpoint_hash)
            proposed_count = body["count"]
            if not isinstance(proposed_count, int) \
                    or proposed_count > SAFE_INT_MAX:
                raise SchemaError("checkpoint count: expected safe integer")
            if proposed_count < count:
                raise ConflictError(
                    "checkpoint count decreases below the retained count",
                    existing=cp_hash, proposed=checkpoint_hash)
            new_records = proposed_count - count
            if new_records > WITNESS_MAX_RECORDS:
                raise CasfError(
                    f"extension over the {WITNESS_MAX_RECORDS} record limit")
            if len(records) != new_records:
                raise CasfError("extension records do not match the "
                                "checkpoint count")
            tip = self._validate_extension(
                con, log_id, manifest_hash, log_pub, records, count,
                head_hash)
            if tip != body["head_hash"]:
                raise CasfError("calculated head digest does not equal the "
                                "checkpoint head_hash")
            receipt = self._accept(
                con, log_id, checkpoint, checkpoint_hash, body,
                receipt_tip, tip)
            con.execute(
                "UPDATE w_state SET count = ?, head_hash = ?, "
                "checkpoint_index = ?, checkpoint_hash = ?, "
                "receipt_hash = ?, sealed = ? WHERE log_id = ?",
                (proposed_count, tip, body["index"], checkpoint_hash,
                 receipt["receipt_hash"],
                 1 if body["final"] else 0, log_id))
            con.commit()
            self._debug_hook("after_commit")
            return receipt, True
        except BaseException:
            con.rollback()
            raise

    def _validate_checkpoint(self, log_id: str, manifest_hash: str,
                             log_pub: bytes,
                             checkpoint: JsonObject) -> str:
        """Cheap checks outside the lock; returns the envelope hash."""
        if set(checkpoint) != {"body", "checkpoint_hash", "signature"}:
            raise SchemaError("checkpoint envelope must be exactly "
                              "body, checkpoint_hash, signature")
        body = checkpoint["body"]
        checkpoint_hash = checkpoint["checkpoint_hash"]
        signature = checkpoint["signature"]
        if (not isinstance(body, dict) or not isinstance(checkpoint_hash, str)
                or not isinstance(signature, str)):
            raise SchemaError("checkpoint envelope field types are wrong")
        validate_protocol_body("checkpoint", body)
        if body["log_id"] != log_id:
            raise CasfError("checkpoint log_id does not match the request")
        if body["manifest_hash"] != manifest_hash:
            raise CasfError("checkpoint manifest binding is wrong")
        if crypto.digest_checkpoint(body) != checkpoint_hash:
            raise SchemaError("checkpoint_hash does not match the body")
        if body["key_id"] != crypto.key_id(log_pub):
            raise CasfError("checkpoint key_id does not match the manifest")
        crypto.verify_checkpoint(log_pub, body, signature)
        return checkpoint_hash

    def _validate_extension(self, con: sqlite3.Connection, log_id: str,
                            manifest_hash: str, log_pub: bytes,
                            records: list[JsonObject], base_count: int,
                            base_head: str) -> str:
        """Validate and retain the new record digests; return the tip."""
        tip = base_head
        for offset, envelope in enumerate(records, start=1):
            seq = base_count + offset
            if set(envelope) != {"body", "record_hash", "signature"}:
                raise SchemaError("record envelope must be exactly "
                                  "body, record_hash, signature")
            body = envelope["body"]
            record_hash = envelope["record_hash"]
            signature = envelope["signature"]
            if (not isinstance(body, dict)
                    or not isinstance(record_hash, str)
                    or not isinstance(signature, str)):
                raise SchemaError("record envelope field types are wrong")
            validate_protocol_body("record", body)
            if body["log_id"] != log_id:
                raise CasfError("record log_id does not match the request")
            if body["manifest_hash"] != manifest_hash:
                raise CasfError("record manifest binding is wrong")
            if body["seq"] != seq:
                raise CasfError("extension records are not contiguous")
            if body["prev_hash"] != tip:
                raise CasfError("extension does not build on the retained "
                                "head")
            if body["key_id"] != crypto.key_id(log_pub):
                raise CasfError("record key_id does not match the manifest")
            if crypto.digest_record(body) != record_hash:
                raise SchemaError("record_hash does not match the body")
            crypto.verify_record(log_pub, body, signature)
            con.execute(
                "INSERT INTO w_record_digests VALUES (?, ?, ?)",
                (log_id, seq, record_hash))
            tip = record_hash
        return tip

    def _accept(self, con: sqlite3.Connection, log_id: str,
                checkpoint: JsonObject, checkpoint_hash: str,
                body: JsonObject, receipt_tip: str,
                head_hash: str) -> JsonObject:
        """Create and store the receipt inside the state transaction."""
        receipt_body: JsonObject = {
            "version": 1, "type": "receipt",
            "witness_id": self._witness_id, "log_id": log_id,
            "manifest_hash": body["manifest_hash"],
            "checkpoint_hash": checkpoint_hash,
            "checkpoint_index": body["index"],
            "count": body["count"], "head_hash": head_hash,
            "previous_receipt_hash": receipt_tip,
            "accepted_at": datetime.now(UTC).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        receipt: JsonObject = {
            "body": receipt_body,
            "receipt_hash": crypto.digest_receipt(receipt_body),
            "signature": crypto.sign_receipt(self._priv, receipt_body),
        }
        con.execute("INSERT INTO w_checkpoints VALUES (?, ?, ?, ?)",
                    (log_id, body["index"], checkpoint_hash,
                     canonicalize(checkpoint)))
        con.execute("INSERT INTO w_receipts VALUES (?, ?)",
                    (checkpoint_hash, canonicalize(receipt)))
        return receipt

    # ---------------------------------------------------------- retrieval

    def latest(self, log_id: str, nonce: bytes) -> JsonObject:
        """Sign the committed view over a fresh nonce (SPEC §14).

        The response carries the matching checkpoint and receipt.
        Before any accepted checkpoint there is no success assertion
        and NO_CHECKPOINT is reported instead.
        """
        if len(nonce) != 32:
            raise SchemaError("nonce must be exactly 32 bytes")
        with self._lock:
            con = self._db.connection
            row = con.execute(
                "SELECT manifest_hash FROM manifests WHERE log_id = ?",
                (log_id,)).fetchone()
            if row is None:
                raise UnknownLogError("unknown log")
            manifest_hash = row[0]
            state = con.execute(
                "SELECT count, head_hash, checkpoint_index, "
                "checkpoint_hash, sealed FROM w_state WHERE log_id = ?",
                (log_id,)).fetchone()
            if state is None:
                raise UnknownLogError("unknown log")
            count, head_hash, cp_index, cp_hash, sealed = state
            if cp_index < 0:
                raise NoCheckpointError(
                    "NO_CHECKPOINT: no accepted checkpoint yet")
            checkpoint, receipt = self._receipt_locked(cp_hash)
            receipt_hash = receipt["receipt_hash"]
            if not isinstance(receipt_hash, str):
                raise CasfError("stored receipt is corrupt")
            body: JsonObject = {
                "version": 1, "type": "latest",
                "nonce": crypto.b64url_encode(nonce),
                "witness_id": self._witness_id, "log_id": log_id,
                "manifest_hash": manifest_hash,
                "checkpoint_hash": cp_hash,
                "receipt_hash": receipt_hash,
                "checkpoint_index": cp_index,
                "count": count, "head_hash": head_hash,
                "final": bool(sealed),
                "responded_at": datetime.now(UTC).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"),
            }
            return {
                "body": body,
                "signature": crypto.sign_latest(self._priv, body),
                "checkpoint": checkpoint, "receipt": receipt,
            }

    def log_registered(self, log_id: str) -> bool:
        """True when a manifest for this log is registered."""
        with self._lock:
            row = self._db.connection.execute(
                "SELECT 1 FROM manifests WHERE log_id = ?",
                (log_id,)).fetchone()
            return row is not None

    def receipt(self, checkpoint_hash: str
                ) -> tuple[JsonObject, JsonObject]:
        """Stored checkpoint and receipt for a digest (SPEC §14)."""
        with self._lock:
            return self._receipt_locked(checkpoint_hash)

    def _receipt_locked(self, checkpoint_hash: str
                        ) -> tuple[JsonObject, JsonObject]:
        con = self._db.connection
        row = con.execute(
            "SELECT envelope FROM w_checkpoints WHERE checkpoint_hash = ?",
            (checkpoint_hash,)).fetchone()
        rrow = con.execute(
            "SELECT envelope FROM w_receipts WHERE checkpoint_hash = ?",
            (checkpoint_hash,)).fetchone()
        if row is None or rrow is None:
            raise CasfError("no stored receipt for this checkpoint digest")
        checkpoint = parse(bytes(row[0]))
        receipt = parse(bytes(rrow[0]))
        if not isinstance(checkpoint, dict) or not isinstance(receipt, dict):
            raise CasfError("stored evidence is corrupt")
        return checkpoint, receipt
