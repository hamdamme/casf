# Supported validation matrix

Updated 10 November 2026 after PR 49 merged as
`4d89e764050455d8d0fe289bd6bb27710ec3b3bb`. This is source validation for the
experimental v0.1 work. Final package selection, advisory review, artifact
approval and publication remain separate gates in the [checklist](checklist-v0.1.md).

## Required configurations

The [workflow](../../.github/workflows/ci.yml) runs 12 jobs on each pull request
and main push. All configurations must pass; one failure does not cancel the
others. Each job has a 20-minute limit.

| Runner | Python | Locked dependencies | Minimum direct dependencies |
| --- | --- | --- | --- |
| Ubuntu x86_64 (`ubuntu-latest`) | 3.12, 3.13, 3.14 | Full source suite, lint, typing, build and isolated wheel checks | Full installed-wheel suite, minimum backend build and wheel checks |
| macOS arm64 (`macos-15`) | 3.12, 3.13, 3.14 | Same checks | Same checks |

These are GitHub's [standard hosted runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
They do not pin every operating-system patch or component. Each job records its
actual platform, architecture, interpreter, SQLite, Python TLS, cryptography
OpenSSL, installed package versions and runner image identifiers when available.
Windows, other architectures and other Python versions are outside this matrix.

Every full suite includes frozen conformance vectors, deterministic regressions,
the [12 generated properties](../adversarial-testing.md), the parser corpus,
the [27 process-crash cases](../process-crash-testing.md), and traceability checks.
Each job also runs three seeded parser campaigns of 2000 mutations plus 25
corpus replays each. Generated examples and fuzz mutations are separate from
pytest totals. The minimum jobs resolve the lowest compatible direct runtime
and backend dependencies; transitive packages and development-tool minima are
not a complete minimum-version matrix.

## Import and source evidence

Locked jobs explicitly import `src/casf` through `PYTHONPATH`; a stale installed
package cannot stand in for the source suite. Minimum jobs run against their
newly built wheel. Base and witness wheel checks run with isolated Python
imports, and the wheel CLI step clears `PYTHONPATH`.

The [environment recorder](../../tests/validation_environment.py) rejects the
wrong import location and compares all imported CASF Python files and
`py.typed` against the checkout by filename and SHA-256. It records both the
actual checked-out commit and the proposed PR head, together with the dirty
worktree flag. A PR workflow normally checks GitHub's temporary merge commit;
these two identifiers must not be confused. Hash equality covers the imported
CASF files, not the entire distribution's contents or reproducible builds.

Only a fixed list of CI context variables is included. The recorder does not
dump the environment, credentials, private keys, databases or event payloads.
The tests use synthetic material. Action references are pinned to reviewed
commit IDs; checkout and setup-python use their Node 24 releases, with read-only
repository permissions and no persisted checkout credential.

## Retained evidence and review

Each job uploads `validation-MODE-RUNNER-PYTHON` containing:

- `environment.json`: source/import identity, runtime and dependency inventory.
- `pytest.xml`: test outcomes, including failures and skips.
- `pytest.log`: complete pytest output and actual Hypothesis statistics.
- Locked jobs also include base and witness wheel environment inventories.

Parser summaries and any findings remain separate
`parser-fuzz-MODE-RUNNER-PYTHON` artifacts. Both artifact groups have 14-day
retention and upload after failures when files exist. Early setup failure or a
hard timeout can prevent evidence creation; absent evidence is not a pass.
Explicit Bash pipe failure handling preserves a failing test or fuzz exit code
when output is copied into a log.

Before accepting a revision, match its PR head and tested merge commit to the
12 successful jobs, confirm no unexpected skips, review runtime/import records,
and verify builds, base/witness smoke checks and public verification. Retain
the source hashes and run/job links in a dated review record before artifacts
expire. CI logs remain additional evidence; a workflow badge alone is insufficient.

Local macOS checks supplement this matrix and must name their actual interpreter
and import mode. The [dependency guide](../dependencies.md) describes setup.
Historical manual macOS records remain historical; hosted macOS coverage begins
with this workflow change.

## Remaining boundaries

Passing the matrix establishes the listed assertions for the tested revision.
It does not prove all specification rules, arbitrary concurrent schedules,
physical power-loss durability, production suitability, current revocation
knowledge, or safety on network filesystems. Independent operational trust and
witness recovery assumptions still apply. Historical research measurements do
not become measurements of this source; affected experiments remain separate work.
