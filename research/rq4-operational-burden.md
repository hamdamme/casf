# RQ4 operational burden evidence

Canonical RQ4 in CASF SPEC 001 Section 22 asks what operational burden and
implementation complexity the constrained approach imposes on a solo
maintained project. This document reports repository complexity and process
proxies. It does not estimate the maintainer's total effort or cost.

## Measurement provenance

All repository counts describe the tracked files at commit
`7c388d385242238a40e572ed67e7e5fc9a1ab194`. The collector reads a temporary
snapshot created from that commit with `git archive`; changes and untracked
files in the collector's checkout are excluded. Git history queries also end
at that commit. The collector implementation and its SHA 256 hash are recorded
separately from the measured commit in
`benchmarks/results/rq4-operational-burden-v1/measurements.v1.json`.

The manifest records metric definitions and counting methods. No session log or
other independent evidence was found to establish that the metrics were
declared before collection, so this report does not make that claim.

## Method

The collector reports source, test, benchmark, documentation, dependency,
specification, CI, installation guide, and repository history counts. Python
test definitions are counted by parsing each test file with Python's abstract
syntax tree and counting `FunctionDef` and `AsyncFunctionDef` nodes whose name
starts with `test_`. This is a syntax based count; it does not establish which
tests pytest discovers or executes.

Source code is grouped into its nine directories under `src/casf` plus one
group for Python files directly in `src/casf`. The research document count is
for `research/*.md` in the selected commit snapshot only; it excludes Markdown
files inside nested research directories.

The history metric counts commits whose messages match the text
`Merge pull request`. Such a message match identifies a merge record, not
evidence that the corresponding pull request received substantive review.
Calendar span is the difference in calendar dates between the first and latest
commit dates in the history of the selected commit. The reported daily rate is
the message match count divided by that elapsed day count.

Reproduce the collection from the repository root with:

```bash
PYTHONPATH=src .venv/bin/python -m benchmarks.rq4_burden \
  benchmarks/rq4-operational-burden.v1.json /tmp/rq4-results \
  --repo . --commit 7c388d385242238a40e572ed67e7e5fc9a1ab194
```

The collector refuses to overwrite an existing output directory.

## Results

| area | measured value |
| --- | --- |
| source under `src/casf` | 23 files, 4,457 lines, 3,962 non blank lines |
| source groups | 9 directories plus a group for files directly in `src/casf` |
| tests | 38 files, 5,738 lines, 310 syntax counted `test_*` function definitions |
| benchmark harnesses | 10 files, 2,636 lines |
| Markdown under `docs` | 24 files, 2,461 lines |
| Markdown at `research` root in the measured snapshot | 4 files |
| direct runtime dependencies | 1 (`cryptography>=41.0`) |
| direct external dependencies, including extras and groups | 9 |
| locked external packages | 24 |
| specification identifiers | 12 requirements, 22 tests, 13 tasks, 9 milestones |
| architecture decision records | 2 |
| CI | 1 workflow, Python 3.12, 3.13, and 3.14 |
| installation guide | 85 lines, 6 Bash command blocks |
| repository history | 124 commits; 24 commit messages matching `Merge pull request` |
| first and latest commit dates | 2026-10-11 to 2026-10-29 |
| elapsed calendar span | 18 days |
| merge message matches per elapsed calendar day | 24 / 18 = 1.33 |
| release documents | 11 |
| benchmark result directories | 9 |

The full counts, grouped source breakdown, collection environment, measured
commit, collector version, and collector hash are in the generated report and
JSON measurement record under `benchmarks/results/rq4-operational-burden-v1/`.
The measured environment was Python 3.12.11 on macOS 15.6.1 arm64.

## Interpretation and limits

These are descriptive complexity and process proxies. The counts do not rank
which part of CASF creates the greatest burden or establish how difficult CASF
is to use. The data do not support comparing risk across pull request
workflows. The 24 merge message matches cannot be read as 24 reviewed pull
requests. The rate
of 1.33 message matches per elapsed calendar day is a property of this commit
history and date span, not a measure of review effort or a steady state rate.

This one repository snapshot cannot establish developer hours, cognitive load,
usability, or total cost. Those quantities were not measured. The numbers also
change as the repository changes, and the history and documentation counts
reflect this maintainer's process rather than a comparable sample of projects.
