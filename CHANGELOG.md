# Changelog

All notable changes to this project are documented here.
Format follows Keep a Changelog; versions follow SemVer after API
stabilization (SPEC §26).

## [Unreleased]
### Added
- Wide area benchmark execution (RQ2, RQ3, H2): 20 runs with the
  writer on a Dell Linux machine and the witness on an AWS Lightsail
  instance, zero failures, raw rows and a verified report in
  benchmarks/results/wide-area-v3/. A witnessed round trip cost
  about 1.18 s at batch 128 and 0.67 s at batch 16 on this path;
  batching cut total witness time per 10000 records from about
  420 s to about 95 s. The report was regenerated from the raw rows
  (means verified to match), with an honest note that the runs
  predate the retry logic and describe one network path only.
- Benchmark runner resilience: a transient witness stall is retried
  with the identical pending checkpoint bytes, which the witness
  deduplicates (SPEC §12, T22), instead of killing a long matrix
  run; retries are counted per run as witness_retries in the raw
  rows and only the successful attempt is measured. 1 new test
  (213 total, all green).
- Remote witness mode for the benchmark runner (RQ2, RQ3): the
  witness may live behind a real network URL, served by the new
  standalone benchmarks.witness_server, which pre registers one
  deterministic log id per run so each run starts fresh on a witness
  that keeps its state. The bearer token comes from an environment
  variable only. benchmarks/manifest.v3.json pins two wide area
  configurations (batch 128 and 16 over 10000 records) and
  benchmarks/wide-area.md is the run sheet for a writer on one
  machine and a witness on a cloud instance in another region.
  2 new tests (212 total, all green).
- Second machine benchmark execution (T19, RQ2, RQ3, RQ4): the
  pinned local subset and the extended matrix ran on an Ubuntu
  laptop, and record counts, witnessed counts, and database sizes
  reproduce the committed macOS rows byte for byte. Findings in
  research/protocol.md: throughput scales down with record size,
  verification grows linearly at about 1 ms per 1 KiB record, and on
  slow hardware witness processing dominates the injected network
  delay, an honest limit on the delay model. Raw rows and reports
  live in benchmarks/results/local-subset-v1-linux/ and
  benchmarks/results/linux-matrix-v2/.
- HTTP witness mode for the benchmark runner (RQ2): the witness may
  run over loopback HTTP behind a proxy that injects a controlled
  round trip delay, so network cost is measured through the real
  wire path rather than assumed. The Linux manifest gains a pinned
  10000 record configuration at 25 ms injected delay; local smoke
  shows witness round trips at about 85 ms against about 50 ms in
  process. research/limitations.md narrows the wide area item to
  uncontrolled multi machine deployments. 2 new tests (210 total,
  all green).
- Benchmark run sheet for the Ubuntu machine
  (benchmarks/linux-matrix.md) with the pinned extended matrix
  (benchmarks/manifest.v2.json): 10000 records at 1 KiB and 4 KiB,
  1000 records at 16 KiB, ten runs each. The manifest runner now
  takes an optional output directory so a second machine replication
  (T19) never overwrites committed results. 1 new test (208 total,
  all green).
- C12: release candidate preparation. Requirement to test
  traceability is now enforced in CI by an audit test covering R01
  to R12 and T01 to T22; the audit found and closed a real gap (T10:
  restored old writer database compared with a newer anchor reports
  ANCHOR_INCOMPLETE instead of passing). Clean install rehearsal:
  wheel and sdist built from the commit install into a fresh
  environment and the full CLI roundtrip ends in verify PASS.
  Package contents inspected: package, license, and metadata only,
  no keys or local data. Dependency advisory review: the single
  runtime dependency cryptography is clean. GitHub private
  vulnerability reporting is enabled and SECURITY.md updated.
  Release notes and the Section 26 checklist with evidence links
  live in docs/release/, with four items explicitly marked blocked
  as maintainer actions (Linux benchmark matrix, disclosure channel
  test submission, external review, final hash approval). Nothing is
  published. 3 new tests (207 total, all green).
- C11 session 2: attack harness and detection matrix (R12; T18,
  T20, T21). Ten predeclared cases (SPEC §23): one mutation per
  controlled copy of a seeded witnessed history, at the beginning,
  the middle, the last witnessed record, and the unwitnessed tail,
  with attacker controls, verifier anchor, connectivity, and
  expected result declared before each run. Confirmed detections:
  content tamper fails at every position; a stolen writer key
  rewriting the witnessed prefix diverges from the anchor. Confirmed
  boundaries, reported as passing rather than hidden: silent tail
  loss (T18), a false suffix under a stolen key (T20), and witness
  rollback against an isolated client with no retained pin (T21,
  conditional failure only). Raw matrix and report committed under
  benchmarks/results/detection-v1/. research/protocol.md and
  research/limitations.md now carry the real design and the honest
  boundaries. 6 new tests (204 total, all green).
- C11 session 1: benchmark harness (R12; T19). Deterministic seeded
  workload generator that reports the honest minimum stored record
  size measured through the real writer path instead of pretending
  an impossible target was met (SPEC §22). The runner starts each
  run from a fresh writer and local witness, discards a warmup,
  measures append latency per record, witness round trips per
  checkpoint, and one final full verification, and writes raw
  measurements per run with the operating system, Python, SQLite,
  cryptography, and commit pinned. Analysis summarizes at run level
  with bootstrap intervals, never record level pooling. The pinned
  local subset (1 KiB records, 1000 records per run, 10 runs for
  two checkpoint batch sizes) is committed with its raw output and
  report; rerunning the manifest reproduces sizes and counts (T19).
  7 new tests (198 total, all green).
- C10 session 2: the casf CLI (R10; T16, T17). All Section 19
  commands: key generate, init, append, checkpoint, witness submit,
  export, verify, seal and status, each with --json for stable
  structured output and human output that names the mode that ran.
  Stable exit codes: 0 pass, 1 invalid evidence or divergence,
  2 usage or schema error, 3 unknown, revoked or unsupported trust,
  4 inconclusive, pending or unavailable, 5 local I/O or internal
  error. Secrets come only from named environment variables and no
  error output prints a passphrase or token (T17). A hostile bundle
  is rejected inside the byte limits with a bounded error (T16).
  Bundle export now includes accepted checkpoints with their
  receipts; a pending checkpoint is never exported as if witnessed.
  11 new tests (191 total, all green).
- C09 session 1: lifecycle operations (R08; T13, T14). Encrypted
  key provider: Ed25519 keys stored as encrypted PKCS8 PEM, atomic
  creation that never overwrites, owner only permissions, stable
  errors for wrong passphrases. seal_log issues the final checkpoint
  and no append follows sealing, while old public evidence stays
  inspectable. Linked epoch rotation builds the successor manifest
  with the old final checkpoint and receipt digests in its
  predecessor object, rejects a nonfinal checkpoint, and verifies
  the link against trusted old keys; an emergency restart keeps
  predecessor null so the discontinuity stays visible. Status
  statements sign and verify, revocation is terminal, and the
  StatusBook retains the largest observed serial per manifest
  outside the log store so a serial rollback never moves the high
  water mark. 13 new tests (180 total, all green).
- C08 session 2: checkpoint production and online mode (R06, R11;
  T18). The writer keeps at most one pending checkpoint per log,
  stores the signed checkpoint with its exact extension range in a
  durable outbox before any submission, retries identical bytes
  across restarts, caps extensions at 128 records, and seals appends
  in the same transaction that creates a final checkpoint (with
  PENDING_DRAIN when more than 128 records are unwitnessed). Receipt
  acquisition validates the witness signature and clears the outbox.
  The verifier gains online mode: a fresh witness view is compared
  to the evidence and a retained high water pin, a behind or
  divergent view is WITNESS_STATE_CONFLICT, a newer view needs more
  evidence (WITNESS_AHEAD, inconclusive), a partition is
  inconclusive, and an unwitnessed suffix is never described as
  witnessed. 20 new tests (167 total, all green).
- C08 session 1: online freshness (SPEC §14; T11). The witness signs
  its committed view over a caller nonce with the matching checkpoint
  and receipt attached, and reports NO_CHECKPOINT before any
  acceptance. The client generates a fresh random 32 byte nonce per
  query and never reuses one, checks the nonce echo before any other
  validation so replay never passes freshness, validates the witness
  signature plus the checkpoint and receipt bindings, and maps a
  timeout or partition to inconclusive rather than evidence of
  rollback. 12 new tests (147 total, all green).
- C07 session 2: witness HTTP transport (SPEC §14). Authenticated
  POST of exactly checkpoint plus records returns 201 on first
  acceptance and 200 with the same stored receipt on an identical
  retry; receipt lookup returns the stored checkpoint and receipt
  with distinct 404 codes for a missing log and a missing receipt.
  Errors carry exactly code, message and retryable with no stack
  traces, payloads, keys or tokens; the bearer credential never
  appears in a URL or log line, and request bodies are drained
  before early error responses so connections stay clean. Request
  size and concurrency are bounded (413 and 429). The witness
  serializes handler threads through one lock, matching the single
  serialized transaction rule. 15 new tests (135 total, all green).
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
- C05 hardening: append only triggers on records and manifests,
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
    - C03: domain separated crypto (R02, T03/T04): key-id/manifest/
      genesis/record/request/checkpoint/receipt/latest/status domains;
      pure Ed25519 sign/verify via cryptography; base64url canonical
      re-encode checks; 12 new unit tests (32 total, all green).
    - C02: RFC 8785 JCS canonicalizer with restricted data profile;
      strict schema validation for all six protocol bodies; SPEC §9
      limits; 20 unit tests green (T01/T02); vectors/v1/jcs_kat.json
      (implementation derived; independent cross check pending M1).
- Repository scaffold (C01): src layout, pyproject, CI skeleton,
  LICENSE (Apache-2.0), SECURITY.md, CONTRIBUTING.md, DEVELOPMENT.md.
- Documentation baseline: D01 source reconciliation, ADR-001..004
  (approved 2026-10-11), historical docs 01-05, exploratory prototype
  (tag `exploratory prototype`).

## [exploratory prototype] - 2026-10-10
- Pre-spec prototype (`auditfw/` package) and design docs 01-05.
  Superseded by CASF SPEC 001; retained as historical evidence only.
