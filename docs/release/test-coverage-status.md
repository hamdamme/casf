# Test coverage status for the review candidate

This is a source inspection summary, not a claim that every listed test has
passed for this candidate. Candidate validation results belong in the PR and
its checks.

## Coverage present

- Protocol schemas and canonical bytes have focused unit and vector tests.
- Writer, checkpoint, witness state, and verifier behavior have unit tests.
- HTTP witness and online paths are exercised through local server tests.
- Fresh writer reconciliation covers missing journal retrieval, retained-state
  conflicts, pending/final preservation, record loss, shared deadlines, write
  serialization and a process exit during journal insertion. Verified startup
  now invokes reconciliation by default and enforces retained authority status.
  Tests cover terminal revocation, state persistence failures, bootstrap retry
  and the public CLI workflow. Explicit local-only mode remains available.
- Rollback H1 and outage H3 have separate experiment harnesses and recorded
  outputs; those records are not an exhaustive test suite.
- [Recovery drills](../recovery-drills.md) cover SQLite exhaustion, backup
  publication failures, corrupt backups, lost signing keys, writer/witness
  rollback and pending receipt recovery after an outage. Selected process
  exits and injected filesystem errors do not establish physical disk or
  power-loss durability.
- [Checkpoint worker](../checkpoint-worker.md) tests cover the record/time
  triggers, bounded batch draining, durable backoff, interrupted attempts,
  restarts, lost replies, final seals, concurrent workers and safe reports.
- [Storage migration](../storage-migrations.md) tests use frozen unversioned
  writer and witness fixtures. They check exact row/BLOB preservation, schema
  identity and constraints, WAL snapshots, final receipt replay, interrupted
  copies, publication failures and refusal of unknown or modified schemas.
- [Export and report](../export-and-reports.md) regressions cover prefix and
  journal boundaries, exact envelope bytes, bounded Python allocations,
  destination races, filesystem failures, process exits and full CLI reports
  on successful, failed and inconclusive verification. Linux/macOS native
  exclusive-rename behavior is exercised on the corresponding test host.
- [Typed append](../append-api.md) tests cover nested input mutation, detached
  results, pending/accepted coverage, same-event retries, failed commits,
  uncertain responses, concurrent processes, body limits and verified
  retained-state authorization. Existing dictionary callers remain covered.
- [Verification report](../verification.md) regressions cover canonical enums,
  missing-evidence verdicts, version and schema failures, unchecked dimensions,
  strict status/pin validation, CLI exit categories and checkpoint non-advancement.
- [Typed log operations](../log-api.md) cover immutable protocol values,
  manifest/receipt mutation after validation, strict checkpoint flags, failed
  commits, exact retry bytes, export snapshot metadata and authorization checks.
- Several malformed, adversarial and integration cases are covered under
  `tests/unit`, including release gap regressions. Empty `adversarial`,
  `integration` and `property` directory scaffolds and the obsolete pytest
  shim runner were removed. New test categories must contain actual coverage.
- The review candidate adds duplicate JSON, negative zero, bounded network
  response and total deadline cases, plus administration and wheel checks.

## Coverage still absent or limited

- No test uses Hypothesis property generators, despite Hypothesis being a
  development dependency. Property based coverage is deferred; the package
  must not claim it has been exercised.
- No maintained fuzzing corpus or fuzzing job was found.
- Crash recovery and concurrent process behavior have selected deterministic
  unit tests, not a complete process level crash matrix.
- The review candidate adds signed initial status provisioning and terminal
  witness revocation enforcement. This only proves behavior when the witness
  receives the statement; it cannot prove that a newer authority statement
  was not withheld.

Before a stable 1.0 release, map every mandatory specification outcome to a
passing automated test or a reviewed manual check. The property, fuzzing, and
full crash matrix limits remain explicit.
