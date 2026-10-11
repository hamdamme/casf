# Changelog

All notable changes to this project are documented here.
Format follows Keep a Changelog; versions follow SemVer after API
stabilization (SPEC §26).

## [Unreleased]
### Added
- C07 session 1: witness acceptance state machine (R05; T08, T09,
  T22). Durable per log state in its own SQLite store: retained count
  and head, checkpoint index and digest, receipt chain tip, sealed
  flag, every accepted checkpoint and receipt, and record digests by
  sequence with bodies discarded. Acceptance runs in one serialized
  transaction; an identical checkpoint replays the stored receipt,
  bad extensions and count moves leave the high water state
  untouched, reused indexes and wrong previous digests raise
  ConflictError with safe evidence identifiers, and a crash after
  commit replays the same receipt on retry. Concurrent fork test
  shows at most one accepted extension. Manifest registration
  verifies the authority signature and requires the manifest to name
  this witness. 21 new tests (119 total, all green).
- C06: evidence bundles, export and restore (R09; T15). Directory
  export with the exact Section 20 file set, one canonical envelope
  per JSONL line, snapshot read in a single transaction, write to a
  sibling temporary directory then one rename, never overwrites.
  Bundle import rejects symlinks, nonregular files, byte order marks,
  blank lines and lines over 128 KiB, and cross checks the export
  metadata against the actual record count. Restore builds a fresh
  store after verifying every record hash, chain link and signature;
  a restore behind an external anchor still stores the data but seals
  the log and every later append reports RESTORE_BEHIND_WITNESS.
  15 new tests (98 total, all green).
- C05 hardening: append-only triggers on records and manifests,
  consistent backup through the SQLite backup API (never overwrites),
  startup head verification against the records table, the remaining
  T07 kill points (before insert, after commit before return), and a
  transient contention retry test. 11 new tests (83 total, all green).
- C05: writer and SQLite storage (R04; T06/T07). Transactional append
  with BEGIN IMMEDIATE, event ID idempotency via request digest,
  contiguous sequences under concurrent writers, WAL with
  synchronous=FULL and foreign keys verified at startup, bounded lock
  retries with BusyError, crash recovery by same ID retry. Checkpoint
  and outbox tables deferred to C07/C08. 12 new tests (72 total).
- C04: independent verifier (R03, R07; T05/T12/T13). Public key only
  verification of manifest, record stream, checkpoints, receipts and
  status statements; integrity and anchored modes; enum typed report
  with verified range, first failure sequence, unwitnessed count and
  machine diagnostic codes. No writer, storage or HTTP imports.
  18 new tests (60 total, all green).
- Frozen conformance vectors for the M1 gate: crypto_kat.json (test
  keys, schema valid bodies for all six protocol objects, digests,
  genesis hash, signatures, negative cases), jcs_reject.json (malformed
  wire cases), deterministic generator, and tests/conformance consuming
  them (8 tests; 42 total, all green). jcs_kat.json independently cross
  checked against the rfc8785 reference package and frozen.
- CASF SPEC 001 rev 0.9 as Markdown (`docs/specification/CASF_SPEC_001.md`),
  converted from the Word original for diffable version control.
- `casf.types`: recursive JsonValue/JsonObject aliases for the SPEC §9
  data profile (C03.1).
### Fixed
- Schema: genesis manifests rejected. SPEC §10 allows predecessor=null
  for an initial log; the null check now permits the predecessor kind.
  Found by the vector work; failing test added first, per review rule.
- CI workflow: broken matrix template expression; pytest now runs the
  whole `tests/` tree so empty milestone suite dirs cannot fail the build.
- mypy --strict and ruff are clean across `src/` and `tests/` (C03.1).
### Changed
- Renamed AGENTS.md to DEVELOPMENT.md and made the wording in the spec
  and contribution guide tool neutral.
- Demo run artifacts (audit.db, checkpoint.json, events.jsonl,
  pubkeys.json, registry.json) are no longer tracked; demo.py
  regenerates them on every run.
- Repository hygiene: .gitignore added; __pycache__, *.pyc, egg-info
  and build/ artifacts removed from tracking (C03.1).
### Added (milestones C01-C03)
    - C03: domain-separated crypto (R02, T03/T04): key-id/manifest/
      genesis/record/request/checkpoint/receipt/latest/status domains;
      pure Ed25519 sign/verify via cryptography; base64url canonical
      re-encode checks; 12 new unit tests (32 total, all green).
    - C02: RFC 8785 JCS canonicalizer with restricted data profile;
      strict schema validation for all six protocol bodies; SPEC §9
      limits; 20 unit tests green (T01/T02); vectors/v1/jcs_kat.json
      (implementation-derived; independent cross-check pending M1).
- Repository scaffold (C01): src layout, pyproject, CI skeleton,
  LICENSE (Apache-2.0), SECURITY.md, CONTRIBUTING.md, DEVELOPMENT.md.
- Documentation baseline: D01 source reconciliation, ADR-001..004
  (approved 2026-10-11), historical docs 01-05, exploratory prototype
  (tag `exploratory-prototype`).

## [exploratory-prototype] - 2026-10-10
- Pre-spec prototype (`auditfw/` package) and design docs 01-05.
  Superseded by CASF SPEC 001; retained as historical evidence only.
