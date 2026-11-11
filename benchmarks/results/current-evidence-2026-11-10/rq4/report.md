# RQ4 operational burden evidence (SPEC Section 22)

question source: CASF_SPEC_001.md Section 22
manifest sha256: 656d523697849fa60aea382a574fcab770aa96a15c3b066529e3c3632bf59dc8

Descriptive collection only; no hypothesis and no pass or fail expectation. Repository counts come from a temporary snapshot of tracked files at the measured commit.

## Measured values

| metric | value |
| --- | --- |
| source groups under src/casf | 10 (9 directories plus files directly in src/casf) |
| source files | 38 |
| source total lines | 7803 |
| source non blank lines | 6988 |
| test files | 92 |
| test total lines | 13936 |
| AST function definitions named test_* | 649 |
| benchmark harness files | 11 |
| benchmark harness total lines | 3061 |
| docs markdown files | 50 |
| docs markdown lines | 4835 |
| research/*.md files in measured snapshot | 7 |
| direct runtime dependencies | 1 (cryptography>=41.0) |
| direct external dependencies total (runtime, extras, groups) | 9 |
| locked external packages | 24 |
| specification requirement ids | 12 |
| specification test ids | 22 |
| specification task ids | 13 |
| specification milestone ids | 9 |
| architecture decision records | 11 |
| ci workflow files | 1 |
| ci python versions | 3.12, 3.13, 3.14 |
| installation guide lines | 97 |
| installation bash command blocks | 6 |
| commits at measured commit | 269 |
| commit messages matching 'Merge pull request' | 45 |
| message matches per elapsed calendar day | 1.50 |
| first commit date | 2026-10-11 |
| latest commit date | 2026-11-10 |
| calendar span days | 30 |
| release documents | 16 |
| committed result directories | 11 |

## Source size by group

| group | files | total lines | non blank lines |
| --- | ---: | ---: | ---: |
| canonical | 3 | 273 | 243 |
| cli | 1 | 1087 | 975 |
| crypto | 1 | 213 | 171 |
| model | 4 | 509 | 423 |
| storage | 4 | 574 | 538 |
| trust | 2 | 181 | 162 |
| verifier | 4 | 957 | 881 |
| witness | 4 | 1048 | 943 |
| writer | 5 | 1884 | 1732 |
| files directly in src/casf | 10 | 1077 | 920 |

## Interpretation limits

- Per SPEC Section 23, line counts, dependency counts, documentation, and repository history describe complexity, but they are proxies rather than objective measures of usability or total cost.
- All repository values are a snapshot of one commit's tracked files; they change as the project evolves. Runtime details describe the collector environment.
- Git history and document counts record the maintainer's own process, so they carry self report bias and cannot be compared with projects that follow a different process.
- This collection makes no claim about developer hours, cognitive load, or monetary cost, none of which are measured here.
- Commit messages matching 'Merge pull request' are message-pattern counts only; they do not establish substantive review. The rate divides those matches by elapsed calendar days (latest date minus earliest date).

## Environment

- collector_version: 2.0.0
- collector_sha256: 25513096a07ea989dc2dd11ae821afa9af6e51648c7d2582d0093c3b4963ab1b
- cpu_count: 8
- dependency_lock_sha256: 74d7a79ae1f872337d26b1b0242c38d8eafd293d673b8a1193ef5b84a08d98fe
- machine: arm64
- measured_commit: b3cf12be89455f5515a8ad001295086c91527342
- platform: macOS-15.6.1-arm64-arm-64bit
- python_version: 3.12.11
- snapshot_method: git archive of selected commit tracked files
