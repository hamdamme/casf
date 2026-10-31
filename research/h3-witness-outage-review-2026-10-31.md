# H3 candidate rerun after bounded transport changes

This supplemental run checks whether the existing H3 outage result still
holds after the online verifier and writer gained total request deadlines
and bounded response reads. The original H3 report and result directory are
preserved unchanged. This run is not pooled with the original measurements.

## Outcome

The frozen H3 manifest completed all 20 runs: ten healthy and ten outage
runs. In all ten outage runs, online freshness returned `INCONCLUSIVE` with
`FRESHNESS_INCONCLUSIVE` and exit status 4, while offline integrity passed.
The maximum pending unwitnessed suffix was 16 records in each outage run.
The original H3 behavioral conclusions therefore remain supported within
this experiment's stated scope.

The new record 24 commit to persisted receipt medians were 9,671,708 ns for
healthy runs and 2,999,388,792 ns for outage runs. These are a new candidate
run's values, not replacements for the historical result. Small timing
differences across separate runs are not treated as a performance regression
without a controlled comparison design.

## Provenance

- Source commit recorded by the runner: `b95348b77b73c71ac77dad8e99a191284e390b2e`.
- Frozen manifest SHA 256: `9cda30cdbc1ca38c73b0aabb168a3ae4c2294e97bde72dbcdd1120cf19cef730`.
- Candidate results: [`benchmarks/results/h3-witness-outage-review-2026-10-31-v1/`](../benchmarks/results/h3-witness-outage-review-2026-10-31-v1/).
- The committed result set contains the frozen manifest, environment and
  source hashes, run order, summary, all 20 run records, report, and checksums
  for those files. Those checksums passed after copying the files.
- The full runner output, including generated SQLite databases and verifier
  state files, is retained in the maintainer's local evidence directory
  outside the repository. Its original runner checksum list was verified
  before creating the repository's smaller evidence set. Those local state
  files are not part of the public result set.
- Environment: macOS 15.6.1 arm64, Python 3.12.11, SQLite 3.54.0,
  cryptography 50.0.2, eight logical CPUs, and 16 GiB memory.

The experiment uses synthetic events and keys, one loopback accept and drop
fault mode, a three second outage, and one explicit recovery submission. It
does not establish behavior for wide area networks, other fault modes, or an
automatic retry worker.
