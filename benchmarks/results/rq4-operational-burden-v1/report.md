# RQ4 operational burden evidence (SPEC Section 22)

question source: CASF_SPEC_001.md Section 22
manifest sha256: 4f5e321dbe01e717ecdf0dfd79c045dde255a530f0b53be54074ca5a51bfd701

Descriptive collection only; no hypothesis and no pass or fail expectation. All values measured at collection time.

## Measured values

| metric | value |
| --- | --- |
| source modules under src/casf | 10 |
| source files | 23 |
| source total lines | 4457 |
| source non blank lines | 3962 |
| test files | 39 |
| test total lines | 5855 |
| test functions | 319 |
| benchmark harness files | 11 |
| benchmark harness total lines | 2949 |
| docs markdown files | 24 |
| docs markdown lines | 2461 |
| research top level markdown files | 4 |
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
| merged pull requests | 24 |
| first commit date | 2026-10-11 |
| latest commit date | 2026-10-29 |
| calendar span days | 18 |
| release documents | 11 |
| committed result directories | 9 |

## Source size by module

| module | files | total lines | non blank lines |
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
| (top level) | 7 | 738 | 632 |

## Interpretation limits

- Per SPEC Section 23, lines of code, dependency counts, deployment steps, and maintenance notes describe complexity, but they are proxies rather than objective measures of usability or total cost.
- All values are a snapshot of one commit on one machine; they change as the project evolves.
- Git history and document counts record the maintainer's own process, so they carry self report bias and cannot be compared with projects that follow a different process.
- This collection makes no claim about developer hours, cognitive load, or monetary cost, none of which are measured here.

## Environment

- commit: 7c388d385242238a40e572ed67e7e5fc9a1ab194
- cpu_count: 8
- dependency_lock_sha256: 74d7a79ae1f872337d26b1b0242c38d8eafd293d673b8a1193ef5b84a08d98fe
- harness_sha256: 21334a27576cc5730c3a5717ffbcde03391c4f95a4581378524da40dbe546edb
- machine: arm64
- platform: macOS-15.6.1-arm64-arm-64bit
- python_version: 3.12.11
- working_tree_status: M research/limitations.md
 M research/protocol.md
?? benchmarks/rq4-operational-burden.v1.json
?? benchmarks/rq4_burden.py
?? research/editorial/
?? research/preprint/
?? tests/unit/test_rq4_burden.py
