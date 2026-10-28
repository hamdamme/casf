# Verification review

Review date: 2026-10-25. Base commit: `2a9786e`.
Scope: escaping assertion, explicit requirement evidence, and minimum direct
dependency compatibility. No application implementation changes were needed.
This is a historical review record. Later Linux checks and current gate status
are in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md).

## Completed checks

| Environment | Full suite | Package build | Installed witness check |
| --- | --- | --- | --- |
| macOS ARM, Python 3.12.11, minimum direct dependencies | 240 passed | Wheel and source archive passed | Passed |
| macOS ARM, Python 3.13.17, minimum direct dependencies | 240 passed | Wheel and source archive passed | Passed |
| macOS ARM, Python 3.14.9, minimum direct dependencies | 240 passed | Wheel and source archive passed | Passed |
| Existing locked environment, macOS ARM | 240 passed | Not repeated in this batch | Covered by existing release evidence |

All three minimum environments selected cryptography 41.0.0, h11 0.16.0,
Uvicorn 0.54.0, and Setuptools 77.0.3. The runner was pytest 9.1.1, with
build 1.6.1 and wheel 0.45.1. Transitive dependencies were resolved to
compatible available versions. These runs establish compatibility for the
recorded environments, not the advisory status of older packages or every
possible dependency combination.

The minimum checks used an installed wheel and ran the complete suite.
Lint passed, typing passed for 22 source files, the lockfile check passed,
and the workflow YAML parsed with the existing and new jobs present.
Git whitespace checks passed. At the time of this review, GitHub had not yet
executed the new workflow and Linux validation was pending. The later results
are recorded in the [Phase 3 closeout record](phase3-closeout-2026-10-28.md).

The escaping test rejected deliberately incorrect output. Four new audit
regression cases reject self reference, comments posing as tests, renamed
target functions, and paths outside the test directory. Replacing the two
old audit tests with six checks brings the suite from 236 to 240 tests.

## Evidence and limitations

The [requirement review](requirement-evidence.md) and
[explicit map](../../tests/requirement_evidence.json) link all 12 requirements
and 22 specification test cases to 58 existing test functions. Seven cases
retain explicit scenario review notes. The audit validates structural links;
it cannot certify complete or correct assertions. The release evidence gate
therefore remains open.

The existing required GitHub checks and branch protection settings are
unchanged. The new minimum jobs must be reviewed after their first GitHub
run before deciding whether to require them for merging.

Application source, pyproject.toml, uv.lock, LICENSE, and frozen vectors are
unchanged. All 119 protected files matched their preservation baseline or the
previously approved documentation corrections. Original commits, research
measurements, and local backups remain preserved.
