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
- [Incremental and bundle verification](../verifier-api.md) tests cover anchor
  ownership/authentication, absolute suffix ranges, retained-state conflicts,
  status/revocation, online freshness outcomes, extension budgets, receipt
  binding, final checkpoints and sequence boundaries. Bundle tests cover EOF
  failures after early verdicts, descriptor closure, complete-input budgets,
  skipped-prefix disclosure and conflicting anchor evidence. Installed-wheel
  checks exercise both APIs without loading writer or storage modules.
- [Generated inputs and parser fuzzing](../adversarial-testing.md) add 12
  Hypothesis properties, a 25-case parser corpus and three bounded mutation
  campaigns per CI job. Generated scenarios cover serialization, record edits,
  truncation, trusted suffixes and work budgets. Unexpected parser failures
  produce replay artifacts; reviewed findings are committed as regressions.
- [Process crash tests](../process-crash-testing.md) add 27 parameterized
  cases with parent-controlled SIGKILL at append, checkpoint, witness and
  state-file boundaries. They cover competing processes, exact HTTP receipt
  replay, final seals and verified restart when retained state leads the
  local receipt journal.
- [Validation provenance](validation-matrix.md) covers the 12 Ubuntu/macOS
  configurations. Import guards reject stale, incomplete or wrongly located
  CASF packages; each job retains runtime inventories and pytest reports.
- Several malformed, adversarial and integration cases are covered under
  `tests/unit`, including release gap regressions. Empty `adversarial` and
  `integration` scaffolds and the obsolete pytest shim runner were removed.
  `tests/property` now contains executable generated tests, not a placeholder.
  New test categories must contain actual coverage.
- The review candidate adds duplicate JSON, negative zero, bounded network
  response and total deadline cases, plus administration and wheel checks.

## Coverage still absent or limited

- Generated properties cover selected serialization and verifier contracts,
  not every protocol rule or a complete writer/witness state machine.
- Fuzzing is bounded, deterministic byte mutation against wire/config JSON.
  There is no coverage-guided campaign over transport, storage or crypto internals.
- The process crash matrix covers named transaction and replacement boundaries.
  It does not cover every instruction, host reboot, torn writes or physical
  power loss. Exact supported-platform results are reviewed against the
  [matrix](validation-matrix.md), separately from final artifact acceptance.
- The review candidate adds signed initial status provisioning and terminal
  witness revocation enforcement. This only proves behavior when the witness
  receives the statement; it cannot prove that a newer authority statement
  was not withheld.

Before a stable 1.0 release, map every mandatory specification outcome to a
passing automated test or a reviewed manual check. The scope of generated tests,
fuzz targets and the bounded process crash matrix remains explicit.

## Audit branch review

The [Team A remediation](team-a-remediation.md) adds strict direct-API policy,
HTTP status/receipt category, preserved pending-byte, no-connection configuration,
and peer-diagnostic redaction assertions. Coverage inspection selected receipt
manifest/witness/count/head/index/previous-receipt checks and latest-response
hash/binding checks for direct tests with individually valid synthetic signatures.
These assert the intended rejection branch rather than failing earlier at a
bad digest. Existing concurrency, recovery and socket-cleanup cases remain in
the required suite. Whole-runtime branch reports are retained with the PR
validation outputs; percentages are review aids, not acceptance thresholds.
Expanded state-machine generation and coverage-guided fuzzing remain separate
work in the [production follow-up](production-readiness-gates.md).
