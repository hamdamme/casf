# Replacement experimental 0.1.0rc4 candidate

Prepared 21 November 2026 (America/Chicago). **Unpublished; exact artifact review
and separate publication approval remain pending.** This record supersedes the
[earlier candidate](candidate-0.1.0rc4.md) for release selection. Its files and
evidence remain historical and must not be substituted for the files below.

## Source and artifact identity

Exact build revision: `d4721c43b23ec93a14819390a1d7606f0c74e259`, the public merge
of the C03 and D01–D03 follow-up. Its source tree is identical to reviewed
`0fac103594823a0def2dc92a863dd9563f070359`. The original C01–C06 fixes are included.
Later release-document commits are not inputs to these artifacts. The proposed
release tag is `v0.1.0rc4` at the exact build revision; no tag has been created.

A clean `git archive` export was built using Python 3.12.10 on macOS arm64,
uv 0.13.5, build 1.6.1 and Setuptools 84.2.1, with
`SOURCE_DATE_EPOCH=1795325215`. The export hash, package member hashes and runtime
inventories are in the [machine-readable record](candidate-0.1.0rc4-d4721c4.json).

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc4-py3-none-any.whl` | 112359 | `daebe02190c676d77e6db028a9753cc30c804be35414ec022945d566c9683549` |
| `casf-0.1.0rc4.tar.gz` | 149640 | `b6ef7e6be77826019835d9dca428df0b46193c3bfdd8553d2a2d3f3cd1333172` |

The [checksum record](SHA256SUMS-0.1.0rc4-d4721c4.txt) identifies these exact files.
Package inspection verified 46 wheel members, 56 source-archive files, version,
dependency/license/entry-point metadata and all **40 runtime files** against the
build revision. Both packages include `file_permissions.py` and the corrected
URL and HTTP classification paths. Neither distribution includes private keys,
databases, the test suite, research records or full documentation.

## Exact artifact installation checks

Following the [candidate procedure](candidate-build.md), the same files were
installed into fresh base-wheel, witness-wheel and source-distribution
environments on each platform. Source installation used an isolated build
constrained to `setuptools==84.2.1`. Runtime dependencies used hash-checked locked
exports. Installed checks ran outside the checkout with isolated imports.

| Installation platform | Python | SQLite | Commands | Synthetic workflows |
| --- | --- | --- | --- | --- |
| macOS 15.6.1 arm64, native | 3.12.10 | 3.47.1 | 35/35 passed | Witness wheel and sdist: 21 checks each |
| Ubuntu 24.04 amd64, emulated locally | 3.12.16 | 3.45.1 | 35/35 passed | Witness wheel and sdist: 21 checks each |

Each platform's 35 commands comprise 12 setup/installation commands and 23
verification commands: dependency consistency, CLI startup/version, provenance
and runtime hashes, base/witness smoke checks, public-only verification,
transaction-example help and the two workflows. These are not pytest counts.
Artifact hashes were checked before and after installation and did not change.

Ubuntu used Docker Desktop amd64 emulation on an arm64 Mac. The test phase had
networking disabled and kept synthetic databases on container-local storage.
This is not native Ubuntu hardware evidence. Docker Desktop host-shared SQLite
state storage remains unvalidated after the earlier concurrency failures.

Initial harness attempts stopped on a missing fixture parent directory; one
macOS retry stopped on an incorrect interpreter path. Complete checks passed in
fresh environments after correcting only the harness. Failed-attempt logs remain
retained; CASF source and artifact bytes were unchanged.

## Hosted acceptance matrix

[CI #234](https://github.com/hamdamme/casf/actions/runs/44989456952) passed all ten
jobs on exact merge `d4721c4`. Environment records, pytest XML, package member
hashes and all 20 validation/fuzz archive digests were checked. All 40 imported
runtime hashes match the build source in each configuration.

| Hosted runner | Python | SQLite | Locked | Minimum direct dependencies |
| --- | --- | --- | --- | --- |
| Ubuntu x86_64, image `ubuntu26` | 3.12.16 | 3.46.1 | 1747 passed; 14 skipped | 1747 passed; 14 skipped |
| Ubuntu x86_64, image `ubuntu26` | 3.13.18 | 3.46.1 | 1747 passed; 14 skipped | 1747 passed; 14 skipped |
| Ubuntu x86_64, image `ubuntu26` | 3.14.10 | 3.46.1 | 1747 passed; 14 skipped | 1747 passed; 14 skipped |
| macOS arm64, image `macos15` | 3.12.10 | 3.49.1 | 1761 passed | 1761 passed |
| macOS arm64, image `macos15` | 3.13.17 | 3.50.4 | 1761 passed | Not scheduled |
| macOS arm64, image `macos15` | 3.14.10 | 3.50.4 | 1761 passed | Not scheduled |

There were no failures or unexpected skips. Ubuntu skips only the 14 native
Darwin ACL tests; every macOS job passed them. Applicable lint, typing,
lock/repository, package, base/witness smoke, public verification and 21-check
workflows passed. Parser campaigns passed **72,900 cases**. These hosted runs
close the earlier native-platform validation gap. CI builds its own packages;
its hashes do not identify the exact publication files above. This release-record
PR must pass its own CI; CI #234 is not attributed to later revisions.

## Dependency and security disposition

[Fresh package queries](dependency-review-0.1.0rc4-d4721c4.json) cover 24 locked
external packages plus uv: 50 successful PyPI/OSV requests, no listed findings,
yanked files or pagination remainder. Exact query time, versions, lock hash and
response hashes are retained. Refresh again immediately before publication.
This does not clear native libraries, host patches or every permitted lower
dependency version. Existing [license/native scope](dependency-review-0.1.0rc3.md)
remains applicable.

The maintainer merged the [follow-up corrections](advisory-followup-2026-11-21.md).
No new independent researcher signoff on `d4721c4` is claimed. Final review
disposition and approval of these exact files remain pending. The advisory is
unpublished; affected/patched-version metadata and disclosure are separate work.

## Remaining release gates

1. Review the exact hashes, [notes](notes-0.1.0rc4.md) and this PR's CI; record the
   final follow-up disposition and approve or reject these candidate files.
2. Obtain separate approval to tag the build revision and publish the GitHub
   prerelease using these files. Do not substitute older rc4 files or a new build.
3. Verify public-download hashes and fresh installs after publication; update
   actual patch availability in the advisory and coordinate publication.
4. Create and verify a new version of the existing Zenodo software record,
   preserving rc2/rc3 assets and citations, then record release closeout.

Experimental validation does not establish production readiness, physical
power-loss durability or a whole-project independent security audit. P03/P04
remain pending production evaluations, P05/P06 remain partial, and H1's recorded
research result is unchanged.
