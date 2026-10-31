# RQ4 operational burden evidence (SPEC Section 22)

question source: CASF_SPEC_001.md Section 22
manifest sha256: 656d523697849fa60aea382a574fcab770aa96a15c3b066529e3c3632bf59dc8

Descriptive collection only; no hypothesis and no pass or fail expectation. Repository counts come from a temporary snapshot of tracked files at the measured commit.

## Measured values

| metric | value |
| --- | --- |
| source groups under src/casf | 10 (9 directories plus files directly in src/casf) |
| source files | 23 |
| source total lines | 4457 |
| source non blank lines | 3962 |
| test files | 38 |
| test total lines | 5738 |
| AST function definitions named test_* | 310 |
| benchmark harness files | 10 |
| benchmark harness total lines | 2636 |
| docs markdown files | 24 |
| docs markdown lines | 2461 |
| research/*.md files in measured snapshot | 4 |
| direct runtime dependencies | 1 (cryptography>=41.0) |
| direct external dependencies total (runtime, extras, groups) | 9 |
| locked external packages | 24 |
| specification requirement ids | 12 |
| specification test ids | 22 |
| specification task ids | 13 |
| specification milestone ids | 9 |
| architecture decision records | 2 |
| ci workflow files | 1 |
| ci python versions | 3.12, 3.13, 3.14 |
| installation guide lines | 85 |
| installation bash command blocks | 6 |
| commits at measured commit | 124 |
| commit messages matching 'Merge pull request' | 24 |
| message matches per elapsed calendar day | 1.33 |
| first commit date | 2026-10-11 |
| latest commit date | 2026-10-29 |
| calendar span days | 18 |
| release documents | 11 |
| committed result directories | 9 |

## Source size by group

| group | files | total lines | non blank lines |
| --- | ---: | ---: | ---: |
| canonical | 3 | 198 | 174 |
| cli | 1 | 508 | 443 |
| crypto | 1 | 213 | 171 |
| model | 2 | 224 | 202 |
| storage | 1 | 99 | 89 |
| trust | 2 | 179 | 158 |
| verifier | 1 | 573 | 524 |
| witness | 4 | 1004 | 900 |
| writer | 1 | 721 | 669 |
| files directly in src/casf | 7 | 738 | 632 |

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
- measured_commit: 7c388d385242238a40e572ed67e7e5fc9a1ab194
- platform: macOS-15.6.1-arm64-arm-64bit
- python_version: 3.12.11
- snapshot_method: git archive of selected commit tracked files
