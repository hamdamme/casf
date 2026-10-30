# RQ4 operational burden evidence

Canonical research question (CASF SPEC 001 Section 22): what operational
burden and implementation complexity does the constrained approach impose
on a solo maintained project?

Status: executed on 2026-10-30. Measured values and the generated report
live in `benchmarks/results/rq4-operational-burden-v1/`. The predeclared
manifest is `benchmarks/rq4-operational-burden.v1.json`; it declares the
metrics and counting methods and deliberately contains no numbers.

## Method

Unlike H1 and H3, RQ4 is not a runtime experiment and has no hypothesis.
It is answered from repository evidence: the size of the code, tests,
benchmark harnesses, and documentation; the direct and locked dependency
surface; the identifier burden of the governing specification
(requirements R01 to R12, tests T01 to T22, tasks C00 to C12, milestones
M0 to M8, plus architecture decision records); the CI matrix; the
installation guide; and the maintenance history recorded in git.

The collector `benchmarks/rq4_burden.py` measures every value at run
time; nothing is hand entered. Reproduce with:

```bash
PYTHONPATH=src .venv/bin/python -m benchmarks.rq4_burden benchmarks/rq4-operational-burden.v1.json benchmarks/results/rq4-operational-burden-v1
```

## Measured values (commit 7c388d3)

| area | measured value |
| --- | --- |
| source under src/casf | 23 files, 4457 total lines, 10 modules |
| tests | 39 files, 5855 lines, 319 test functions |
| benchmark harnesses | 11 files, 2949 lines |
| documentation under docs | 24 markdown files, 2461 lines |
| direct runtime dependencies | 1 (cryptography) |
| direct external dependencies, all extras and groups | 9 |
| locked external packages | 24 |
| specification identifiers | 12 requirements, 22 tests, 13 tasks, 9 milestones |
| architecture decision records | 2 |
| CI | 1 workflow, 3 Python versions |
| installation guide | 85 lines, 6 command blocks |
| maintenance history | 124 commits and 24 merged pull requests over 18 calendar days |

## Findings

The constrained approach concentrates its burden in process rather than
in runtime dependencies. The deployed dependency surface is small: one
direct runtime dependency and 24 locked external packages including
development and build tooling. The code under src/casf is compact
relative to the evidence around it: tests exceed source lines, and the
benchmark harnesses plus documentation together are comparable in size
to the source itself.

The specification imposes the largest measurable burden on a solo
maintainer: 12 requirements, 22 tracked tests, 13 ordered tasks, and 9
milestones, all kept traceable in CI, plus per change review rules and
release gates. The maintenance history shows what this means in
practice: 124 commits and 24 reviewed pull requests in 18 days, an
average of several reviewed units per day, before the release candidate
was approved.

## Limitations

Per SPEC Section 23, lines of code, dependency counts, deployment steps,
and maintenance notes describe complexity, but they are proxies rather
than objective measures of usability or total cost. In particular:

- All values are a snapshot of one commit; they change as the project
  evolves.
- Git history and document counts record the maintainer's own process,
  so they carry self report bias and cannot be compared with projects
  that follow a different process. A project without the pull request
  discipline would look lighter by these measures while carrying more
  unexamined risk.
- No developer hours, cognitive load, or monetary cost are measured
  here; RQ4 cannot be answered in those terms from repository evidence.
- The 18 day calendar span reflects an intensive development period,
  not a steady state maintenance rate.
