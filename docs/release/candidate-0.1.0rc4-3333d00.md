# Experimental 0.1.0rc4 candidate from 3333d00

Prepared 22 November 2026. **Unpublished; exact-file approval and separate
publication approval remain pending.** This candidate replaces the
[d4721c4 files](candidate-0.1.0rc4-d4721c4.md), which omit the SQLite permissions
and canonical JSONL corrections. Preserve all earlier artifacts and evidence.

## Source and artifact identity

Exact build revision: `3333d0025388e97a3e54b7ae29974b7369545f81`, the merge of
[PR 82](https://github.com/hamdamme/casf/pull/82). Its tree matches reviewed
`02065904108f0cbb13e08347d5c1b3a42b7a4dfa`. It includes the earlier C01–C06 and
C03/D01–D03 fixes plus private SQLite creation, existing-store permission checks
and canonical JSONL enforcement. Later documentation commits are not build inputs.
The proposed release tag is `v0.1.0rc4` at this exact build revision; no tag was created.

A clean `git archive` export was built with Python 3.12.10 on native macOS arm64,
uv 0.13.5, build 1.6.1 and Setuptools 84.2.1. The tracked checkout was clean;
12 existing untracked files were preserved and excluded by the committed export.
`SOURCE_DATE_EPOCH=1795374395` was set. This records a build
input, not proof of reproducibility across machines.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc4-py3-none-any.whl` | 113427 | `e4c7c8747d77998e6b8f05e042319b584a19911b3773536544014702e5dadad7` |
| `casf-0.1.0rc4.tar.gz` | 150620 | `0b65a4514909d4289336911a67f296bd08d667ac65521134261d500d6fd0f447` |

The [checksum file](SHA256SUMS-0.1.0rc4-3333d00.txt) and
[machine-readable record](candidate-0.1.0rc4-3333d00.json) retain source identity,
package-member hashes, installation inventories and CI evidence. Inspection
verified all **40 runtime files**, 46 wheel members, 56 source-archive files and
version/dependency/license/entry-point metadata. Runtime bytes match the exact
build commit, including the corrected storage, ACL and bundle implementations.
No private keys, databases, tests or full documentation are packaged.

## Exact artifact installation checks

The [candidate procedure](candidate-build.md) was run with these exact files in
fresh base-wheel, witness-wheel and sdist environments on each platform.
Runtime dependencies used hash-checked locked exports. Sdist installation used
an isolated build constrained to `setuptools==84.2.1`. Checks ran outside the
checkout with isolated imports and no `PYTHONPATH` or `PYTHONHOME` override.

| Installation platform | Python | SQLite | Commands | Synthetic workflows |
| --- | --- | --- | --- | --- |
| macOS 15.6.1 arm64, native | 3.12.10 | 3.47.1 | 38/38 passed | Witness wheel and sdist: 21 checks each |
| Ubuntu 24.04 amd64, emulated locally | 3.12.16 | 3.45.1 | 38/38 passed | Witness wheel and sdist: 21 checks each |

Each platform's 38 commands comprise 12 setup/installation commands and 26
verification commands. They cover dependency consistency, CLI startup/version,
installed metadata and all 40 runtime hashes, base/witness smoke checks,
public-only verification, transaction-example help and the two workflows.
Additional security checks in every installation confirmed mode `600` for the
database/WAL/SHM under umask `022`, rejection of an unsafe existing store, and
rejection of noncanonical records/checkpoints/receipts/status JSONL.
These are command counts, not pytest totals. All four workflows produced the
expected tamper `FAIL` and unavailable-witness `INCONCLUSIVE` results. Artifact
hashes were verified before and after installation and did not change.

Ubuntu exact-file checks used Docker Desktop amd64 emulation on an arm64 Mac.
The test phase had networking disabled and synthetic databases on container-local
storage. It is not native hardware evidence, and Docker Desktop host-shared
SQLite state storage remains unvalidated. The native hosted matrix below is
separate evidence; its packages are not the exact files identified above.

## Post-merge acceptance matrix

[CI 238](https://github.com/hamdamme/casf/actions/runs/45058864531) passed all ten
jobs on exact merge `3333d00`. All 20 validation/fuzz archive digests were checked;
imported and packaged runtime hashes match this build source in each configuration.

| Hosted runner | Python | SQLite | Locked | Minimum direct dependencies |
| --- | --- | --- | --- | --- |
| Ubuntu x86_64 | 3.12.16 | 3.46.1 | 1788 passed; 20 skipped | 1788 passed; 20 skipped |
| Ubuntu x86_64 | 3.13.18 | 3.46.1 | 1788 passed; 20 skipped | 1788 passed; 20 skipped |
| Ubuntu x86_64 | 3.14.10 | 3.46.1 | 1788 passed; 20 skipped | 1788 passed; 20 skipped |
| macOS arm64 | 3.12.10 | 3.49.1 | 1808 passed | 1808 passed |
| macOS arm64 | 3.13.17 | 3.50.4 | 1808 passed | Not scheduled |
| macOS arm64 | 3.14.10 | 3.50.4 | 1808 passed | Not scheduled |

There were no failures or unexpected skips. Linux skips only native Darwin ACL
tests, which passed on macOS. Applicable lint, typing, repository/lock checks,
package inspection, installed-wheel/public verification and 21-check workflows
passed. Parser campaigns passed **72,900 cases**. Full dependency versions and
runner identifiers are recorded in the JSON evidence. These results cover the
listed SQLite versions; SQLite 3.42.0 was not rerun for these files.
This documentation PR requires its own CI; CI 238 is not attributed to later commits.

## Remaining release gates

1. Review these exact files, hashes, [release notes](notes-0.1.0rc4.md) and the
   documentation PR's CI; record final review disposition and artifact approval.
2. Refresh package advisory queries immediately before publication. The
   [previous query record](dependency-review-0.1.0rc4-d4721c4.json) covers the
   unchanged lockfile but is historical, not a new query. Native-library and
   host-patch assessment remain separate; no new independent researcher signoff
   is claimed.
3. Obtain separate approval to tag this build revision and publish these exact
   GitHub prerelease files. No release, tag or advisory publication was performed
   during this preparation. Do not substitute an older rc4 artifact or a new build.
4. After approved publication, verify public downloads and installations,
   coordinate advisory disposition, then create and verify a new version of the
   existing Zenodo software record. Preserve prior assets and citations.

Experimental validation does not close production gates P03/P04 or partial
P05/P06, establish physical power-loss durability, or change H1's historical
research result. See the [release checklist](checklist-v0.1.md).
