# Test coverage status for the review candidate

This is a source inspection summary, not a claim that every listed test has
passed for this candidate. Candidate validation results belong in the PR and
its checks.

## Coverage present

- Protocol schemas and canonical bytes have focused unit and vector tests.
- Writer, checkpoint, witness state, and verifier behavior have unit tests.
- HTTP witness and online paths are exercised through local server tests.
- Rollback H1 and outage H3 have separate experiment harnesses and recorded
  outputs; those records are not an exhaustive test suite.
- Several malformed and adversarial cases are covered by tests under
  `tests/unit`, including release gap regressions. The directory names
  `tests/adversarial` and `tests/integration` alone contain no test cases.
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
