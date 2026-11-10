"""Frozen unversioned layouts; used only to recognize migration inputs."""

WRITER = """
CREATE TABLE IF NOT EXISTS manifests(
    log_id TEXT PRIMARY KEY,
    manifest_hash TEXT NOT NULL UNIQUE,
    envelope BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS records(
    log_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    envelope BLOB NOT NULL,
    UNIQUE(log_id, seq),
    UNIQUE(log_id, event_id)
);
CREATE TABLE IF NOT EXISTS heads(
    log_id TEXT PRIMARY KEY,
    count INTEGER NOT NULL,
    head_hash TEXT NOT NULL,
    sealed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS checkpoints(
    log_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    count INTEGER NOT NULL,
    checkpoint_hash TEXT NOT NULL,
    envelope BLOB NOT NULL,
    state TEXT NOT NULL,
    UNIQUE(log_id, idx),
    UNIQUE(log_id, checkpoint_hash)
);
CREATE TABLE IF NOT EXISTS receipts(
    checkpoint_hash TEXT PRIMARY KEY,
    envelope BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox(
    log_id TEXT PRIMARY KEY,
    checkpoint_hash TEXT NOT NULL,
    from_seq INTEGER NOT NULL,
    to_seq INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS checkpoint_schedule(
    log_id TEXT PRIMARY KEY,
    checkpoint_hash TEXT NOT NULL,
    next_checkpoint_at REAL NOT NULL
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
CREATE TABLE IF NOT EXISTS w_status(
    manifest_hash TEXT PRIMARY KEY,
    serial INTEGER NOT NULL CHECK(serial >= 1),
    status TEXT NOT NULL CHECK(status IN ('active', 'revoked'))
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
