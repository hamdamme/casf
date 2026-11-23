# Experimental 0.1.0rc4 candidate from 492f330

Prepared 22 November 2026. **Unpublished; exact-file approval and separate
publication approval remain pending.** This candidate replaces the
[3333d00 files](candidate-0.1.0rc4-3333d00.md), which omit the small-order
Ed25519 correction. Preserve all earlier artifacts and evidence as historical;
do not publish them as the corrected rc4.

## Source and artifact identity

Exact build revision: `492f330c0be93a1b722314bbdc2f91ab0cb37e11`, the merge of
[PR 84](https://github.com/hamdamme/casf/pull/84). Its tree matches reviewed
`fe6ec45f2de1507754a808ae61a35292acc33631`. It includes the C01–C06 and
C03/D01–D03 corrections, SQLite permissions, canonical JSONL enforcement,
small-order Ed25519 public-key rejection and explicit retained-checkpoint
argument handling. Later documentation commits are not build inputs.
The proposed release tag is `v0.1.0rc4` at this exact build revision; no tag was created.

A clean `git archive` export was built with Python 3.12.14 on native macOS
27.2.1 arm64, uv 0.13.5, build 1.6.1 and Setuptools 84.2.1. The tracked checkout
was clean; 12 existing untracked files were preserved and excluded by the export.
`SOURCE_DATE_EPOCH=1795391781` was set. This records a controlled
build input, not proof of reproducibility across machines.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc4-py3-none-any.whl` | 113967 | `b29656586fc8de81ca9c47d937f8d2cbcbdd669124c0c53eb6bb5b824058ec87` |
| `casf-0.1.0rc4.tar.gz` | 151208 | `78a9ee3946582f4383208b2ac3c07501e4a3b8942ea794f1fec545e19a781362` |

The [checksum file](SHA256SUMS-0.1.0rc4-492f330.txt) and
[machine-readable record](candidate-0.1.0rc4-492f330.json) retain source identity,
package-member hashes, installation inventories and CI evidence. Inspection
verified all **40 runtime files**, 46 wheel members, 56 source-archive files,
wheel RECORD and version/dependency/license/entry-point metadata. Runtime and
packaged example bytes match the build commit, including the corrected key
loader, verifier argument checks and CLI handling. No private keys, databases,
tests or full documentation are packaged.

## Exact artifact installation checks

The [candidate procedure](../candidate-build.md) was run with these exact files in
fresh base-wheel, witness-wheel and sdist environments on each platform.
Runtime dependencies used hash-checked locked exports. Sdist installation used
an isolated build constrained to `setuptools==84.2.1`. Checks ran outside the
checkout with isolated imports and no `PYTHONPATH` or `PYTHONHOME` override.

| Installation platform | Python | SQLite | Commands | Synthetic workflows |
| --- | --- | --- | --- | --- |
| macOS 27.2.1 arm64, native | 3.12.14 | 3.53.1 | 38/38 passed | Witness wheel and sdist: 21 checks each |
| Ubuntu 24.04.5 amd64, emulated locally | 3.12.16 | 3.45.1 | 38/38 passed | Witness wheel and sdist: 21 checks each |

Each platform's 38 commands comprise 12 setup/installation commands and 26
verification commands. They cover dependency consistency, CLI startup/version,
installed metadata and all 40 runtime hashes, base/witness smoke checks,
public-only verification, transaction-example help and two workflows.
These are command counts, not pytest totals. All four workflows produced the
expected tamper `FAIL` and unavailable-witness `INCONCLUSIVE` results.

Security checks in all six installations rejected every libsodium blocklist
entry and noncanonical public-key y value with both sign bits, while accepting
a generated key. A real-authority manifest with an identity log key failed
`MANIFEST_KEY_SCHEMA` in all three modes. Invalid authority/witness pins and
witness registration were rejected. Unanchored integrity verification with a
retained checkpoint raised `ValueError`. Existing checks also confirmed mode
`600` for database/WAL/SHM under umask `022`, rejection of unsafe existing stores,
and rejection of noncanonical records/checkpoints/receipts/status JSONL.
Artifact hashes were verified before and after installation and did not change.

Ubuntu exact-file checks used Docker Desktop amd64 emulation on an arm64 Mac.
The test phase had networking disabled and synthetic databases on container-local
storage. This is not native hardware evidence; Docker Desktop host-shared SQLite
state storage remains unvalidated. Native hosted CI below is separate evidence
and builds its own packages, not the exact candidate files identified above.

## Post-merge acceptance matrix

[CI 242](https://github.com/hamdamme/casf/actions/runs/45085913856) passed all ten
jobs on exact merge `492f330`. All 20 validation/fuzz archive digests were checked;
imported and packaged runtime hashes match this source in every configuration.

| Hosted runner | Python | SQLite | Locked | Minimum direct dependencies |
| --- | --- | --- | --- | --- |
| Ubuntu x86_64 | 3.12.16 | 3.46.1 | 1883 passed; 20 skipped | 1883 passed; 20 skipped |
| Ubuntu x86_64 | 3.13.18 | 3.46.1 | 1883 passed; 20 skipped | 1883 passed; 20 skipped |
| Ubuntu x86_64 | 3.14.10 | 3.46.1 | 1883 passed; 20 skipped | 1883 passed; 20 skipped |
| macOS arm64 | 3.12.10 | 3.49.1 | 1903 passed | 1903 passed |
| macOS arm64 | 3.13.17 | 3.50.4 | 1903 passed | Not scheduled |
| macOS arm64 | 3.14.10 | 3.50.4 | 1903 passed | Not scheduled |

There were no failures or unexpected skips. Linux skips only native Darwin ACL
tests, which passed on macOS. Every configuration includes the 16 advisory
regressions and 18 Ed25519 edge vectors. Applicable lint, typing, repository/lock
checks, package inspection, installed-wheel checks and 21-check workflows passed.
Parser campaigns passed **72,900 cases**. The JSON retains dependency versions,
runner identifiers, exact skip reasons and archive hashes. These results cover
the recorded SQLite versions; SQLite 3.42.0 was not rerun for these files.
This documentation PR requires its own CI; CI 242 is not attributed to later commits.

## Remaining release gates

1. Review these exact files, hashes, [release notes](notes-0.1.0rc4.md) and the
   documentation PR's CI; record final review disposition and artifact approval.
2. Refresh package advisory queries immediately before publication. The
   [previous query record](dependency-review-0.1.0rc4-d4721c4.json) is historical,
   not a new query. Native-library and host-patch assessment remain separate;
   no new independent researcher signoff is claimed.
3. Obtain separate approval to tag this build revision and publish these exact
   GitHub prerelease files. No release, tag or advisory publication was performed.
   Do not substitute an older rc4 artifact or an unreviewed new build.
4. After approved publication, verify public downloads and installations,
   coordinate advisory disposition, then create and verify a new version of the
   existing Zenodo software record. Preserve prior assets and citations.

Experimental validation does not close production gates P03/P04 or partial
P05/P06, establish physical power-loss durability, or change H1's historical
research result. See the [release checklist](../checklist-v0.1.md).
