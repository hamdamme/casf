"""Schema version 1. Authenticated envelopes remain opaque BLOBs."""

VERSION = 1
WRITER_ID = 0x43415346
WITNESS_ID = 0x43415357

WRITER = """
CREATE TABLE IF NOT EXISTS manifests(
    log_id TEXT PRIMARY KEY NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    manifest_hash TEXT NOT NULL UNIQUE
        CHECK(typeof(manifest_hash)='text'
              AND length(manifest_hash)=64
              AND manifest_hash NOT GLOB '*[^0-9a-f]*'),
    envelope BLOB NOT NULL CHECK(typeof(envelope)='blob' AND length(envelope)>0)
);
CREATE TABLE IF NOT EXISTS records(
    log_id TEXT NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    seq INTEGER NOT NULL CHECK(typeof(seq)='integer' AND seq BETWEEN 1 AND 9007199254740991),
    event_id TEXT NOT NULL CHECK(typeof(event_id)='text' AND length(event_id)=36),
    request_digest TEXT NOT NULL
        CHECK(typeof(request_digest)='text'
              AND length(request_digest)=64
              AND request_digest NOT GLOB '*[^0-9a-f]*'),
    record_hash TEXT NOT NULL
        CHECK(typeof(record_hash)='text'
              AND length(record_hash)=64
              AND record_hash NOT GLOB '*[^0-9a-f]*'),
    envelope BLOB NOT NULL CHECK(typeof(envelope)='blob' AND length(envelope)>0),
    UNIQUE(log_id, seq),
    UNIQUE(log_id, event_id),
    FOREIGN KEY(log_id) REFERENCES manifests(log_id)
);
CREATE TABLE IF NOT EXISTS heads(
    log_id TEXT PRIMARY KEY NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    count INTEGER NOT NULL CHECK(typeof(count)='integer' AND count BETWEEN 0 AND 9007199254740991),
    head_hash TEXT NOT NULL
        CHECK(typeof(head_hash)='text'
              AND length(head_hash)=64
              AND head_hash NOT GLOB '*[^0-9a-f]*'),
    sealed INTEGER NOT NULL DEFAULT 0 CHECK(typeof(sealed)='integer' AND sealed BETWEEN 0 AND 3),
    FOREIGN KEY(log_id) REFERENCES manifests(log_id)
);
CREATE TABLE IF NOT EXISTS checkpoints(
    log_id TEXT NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    idx INTEGER NOT NULL CHECK(typeof(idx)='integer' AND idx BETWEEN 0 AND 9007199254740991),
    count INTEGER NOT NULL CHECK(typeof(count)='integer' AND count BETWEEN 0 AND 9007199254740991),
    checkpoint_hash TEXT NOT NULL
        CHECK(typeof(checkpoint_hash)='text'
              AND length(checkpoint_hash)=64
              AND checkpoint_hash NOT GLOB '*[^0-9a-f]*'),
    envelope BLOB NOT NULL CHECK(typeof(envelope)='blob' AND length(envelope)>0),
    state TEXT NOT NULL CHECK(typeof(state)='text' AND state IN ('pending','accepted')),
    UNIQUE(log_id, idx),
    UNIQUE(log_id, checkpoint_hash),
    FOREIGN KEY(log_id) REFERENCES manifests(log_id),
    UNIQUE(checkpoint_hash)
);
CREATE TABLE IF NOT EXISTS receipts(
    checkpoint_hash TEXT PRIMARY KEY NOT NULL
        CHECK(typeof(checkpoint_hash)='text'
              AND length(checkpoint_hash)=64
              AND checkpoint_hash NOT GLOB '*[^0-9a-f]*'),
    envelope BLOB NOT NULL CHECK(typeof(envelope)='blob' AND length(envelope)>0),
    FOREIGN KEY(checkpoint_hash) REFERENCES checkpoints(checkpoint_hash)
);
CREATE TABLE IF NOT EXISTS outbox(
    log_id TEXT PRIMARY KEY NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    checkpoint_hash TEXT NOT NULL
        CHECK(typeof(checkpoint_hash)='text'
              AND length(checkpoint_hash)=64
              AND checkpoint_hash NOT GLOB '*[^0-9a-f]*'),
    from_seq INTEGER NOT NULL
        CHECK(typeof(from_seq)='integer'
              AND from_seq BETWEEN 1
              AND 9007199254740992),
    to_seq INTEGER NOT NULL CHECK(typeof(to_seq)='integer' AND to_seq BETWEEN 0 AND 9007199254740991),
    attempts INTEGER NOT NULL DEFAULT 0
        CHECK(typeof(attempts)='integer'
              AND attempts BETWEEN 0
              AND 9007199254740991),
    next_attempt_at REAL NOT NULL DEFAULT 0
        CHECK(typeof(next_attempt_at) IN ('integer','real')
              AND next_attempt_at>=0
              AND next_attempt_at<=1.7976931348623157e308),
    FOREIGN KEY(log_id) REFERENCES manifests(log_id),
    FOREIGN KEY(log_id, checkpoint_hash) REFERENCES checkpoints(log_id, checkpoint_hash),
    CHECK(from_seq<=to_seq+1)
);
CREATE TABLE IF NOT EXISTS checkpoint_schedule(
    log_id TEXT PRIMARY KEY NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    checkpoint_hash TEXT NOT NULL
        CHECK(typeof(checkpoint_hash)='text'
              AND length(checkpoint_hash)=64
              AND checkpoint_hash NOT GLOB '*[^0-9a-f]*'),
    next_checkpoint_at REAL NOT NULL
        CHECK(typeof(next_checkpoint_at) IN ('integer','real')
              AND next_checkpoint_at>=0
              AND next_checkpoint_at<=1.7976931348623157e308),
    FOREIGN KEY(log_id) REFERENCES manifests(log_id),
    FOREIGN KEY(log_id, checkpoint_hash) REFERENCES checkpoints(log_id, checkpoint_hash)
);
-- Append-only guards (SPEC §17). These deter accidental modification;
-- they are not protection against a file administrator.
CREATE TRIGGER IF NOT EXISTS records_no_update BEFORE UPDATE ON records
BEGIN SELECT RAISE(ABORT, 'records are append only'); END;
CREATE TRIGGER IF NOT EXISTS records_no_delete BEFORE DELETE ON records
BEGIN SELECT RAISE(ABORT, 'records are append only'); END;
CREATE TRIGGER IF NOT EXISTS manifests_no_update BEFORE UPDATE ON manifests
BEGIN SELECT RAISE(ABORT, 'manifests are immutable'); END;
CREATE TRIGGER IF NOT EXISTS manifests_no_delete BEFORE DELETE ON manifests
BEGIN SELECT RAISE(ABORT, 'manifests are immutable'); END;
"""

WITNESS = """
CREATE TABLE IF NOT EXISTS manifests(
    log_id TEXT PRIMARY KEY NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    manifest_hash TEXT NOT NULL UNIQUE
        CHECK(typeof(manifest_hash)='text'
              AND length(manifest_hash)=64
              AND manifest_hash NOT GLOB '*[^0-9a-f]*'),
    envelope BLOB NOT NULL CHECK(typeof(envelope)='blob' AND length(envelope)>0)
);
CREATE TABLE IF NOT EXISTS w_state(
    log_id TEXT PRIMARY KEY NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    count INTEGER NOT NULL CHECK(typeof(count)='integer' AND count BETWEEN 0 AND 9007199254740991),
    head_hash TEXT NOT NULL
        CHECK(typeof(head_hash)='text'
              AND length(head_hash)=64
              AND head_hash NOT GLOB '*[^0-9a-f]*'),
    checkpoint_index INTEGER NOT NULL
        CHECK(typeof(checkpoint_index)='integer'
              AND checkpoint_index BETWEEN -1
              AND 9007199254740991),
    checkpoint_hash TEXT NOT NULL
        CHECK(typeof(checkpoint_hash)='text'
              AND length(checkpoint_hash)=64
              AND checkpoint_hash NOT GLOB '*[^0-9a-f]*'),
    receipt_hash TEXT NOT NULL
        CHECK(typeof(receipt_hash)='text'
              AND length(receipt_hash)=64
              AND receipt_hash NOT GLOB '*[^0-9a-f]*'),
    sealed INTEGER NOT NULL DEFAULT 0 CHECK(typeof(sealed)='integer' AND sealed BETWEEN 0 AND 1),
    FOREIGN KEY(log_id) REFERENCES manifests(log_id)
);
CREATE TABLE IF NOT EXISTS w_status(
    manifest_hash TEXT PRIMARY KEY NOT NULL
        CHECK(typeof(manifest_hash)='text'
              AND length(manifest_hash)=64
              AND manifest_hash NOT GLOB '*[^0-9a-f]*'),
    serial INTEGER NOT NULL CHECK(typeof(serial)='integer' AND serial BETWEEN 1 AND 9007199254740991),
    status TEXT NOT NULL CHECK(typeof(status)='text' AND status IN ('active','revoked')),
    FOREIGN KEY(manifest_hash) REFERENCES manifests(manifest_hash)
);
CREATE TABLE IF NOT EXISTS w_checkpoints(
    log_id TEXT NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    idx INTEGER NOT NULL CHECK(typeof(idx)='integer' AND idx BETWEEN 0 AND 9007199254740991),
    checkpoint_hash TEXT NOT NULL
        CHECK(typeof(checkpoint_hash)='text'
              AND length(checkpoint_hash)=64
              AND checkpoint_hash NOT GLOB '*[^0-9a-f]*'),
    envelope BLOB NOT NULL CHECK(typeof(envelope)='blob' AND length(envelope)>0),
    UNIQUE(log_id, idx),
    UNIQUE(log_id, checkpoint_hash),
    FOREIGN KEY(log_id) REFERENCES manifests(log_id),
    UNIQUE(checkpoint_hash)
);
CREATE TABLE IF NOT EXISTS w_receipts(
    checkpoint_hash TEXT PRIMARY KEY NOT NULL
        CHECK(typeof(checkpoint_hash)='text'
              AND length(checkpoint_hash)=64
              AND checkpoint_hash NOT GLOB '*[^0-9a-f]*'),
    envelope BLOB NOT NULL CHECK(typeof(envelope)='blob' AND length(envelope)>0),
    FOREIGN KEY(checkpoint_hash) REFERENCES w_checkpoints(checkpoint_hash)
);
CREATE TABLE IF NOT EXISTS w_record_digests(
    log_id TEXT NOT NULL CHECK(typeof(log_id)='text' AND length(log_id)=36),
    seq INTEGER NOT NULL CHECK(typeof(seq)='integer' AND seq BETWEEN 1 AND 9007199254740991),
    record_hash TEXT NOT NULL
        CHECK(typeof(record_hash)='text'
              AND length(record_hash)=64
              AND record_hash NOT GLOB '*[^0-9a-f]*'),
    UNIQUE(log_id, seq),
    FOREIGN KEY(log_id) REFERENCES manifests(log_id)
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
