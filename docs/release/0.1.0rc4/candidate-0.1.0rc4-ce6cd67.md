# Experimental 0.1.0rc4 candidate from ce6cd67

Prepared 22 November 2026. **Unpublished; exact-file review and separate
publication approval remain pending.** This candidate replaces the
[492f330 files](candidate-0.1.0rc4-492f330.md), which omit PR 87's key-passphrase
and package changes. All earlier rc4 artifacts and evidence remain historical;
do not publish them as this candidate.

## Source and artifact identity

Exact build revision: `ce6cd67c01df2af283b2e07fc1b832e79bb14821`, the merge of
[PR 87](https://github.com/hamdamme/casf/pull/87). Its tree matches reviewed
`c21cb2173d2ff7a06866afb5cc879c38114145b8`. It contains the earlier advisory,
SQLite, canonical JSONL, Ed25519 and retained-checkpoint corrections, plus the
16-byte key-generation passphrase minimum, legacy key-loading compatibility,
cryptography minimum 50.0.0 and package metadata updates. Protocol bytes,
signing domains and verification semantics are unchanged by PR 87.
The proposed tag is `v0.1.0rc4` at this exact revision; no tag was created.

A clean `git archive` export was built with Python 3.12.14 on native macOS
27.2.1 arm64, uv 0.13.5, build 1.6.1 and Setuptools 84.2.1. The tracked checkout
was clean; 48 unrelated untracked files were preserved and excluded from the
export. `SOURCE_DATE_EPOCH=1795405478` records the commit timestamp. This is a
controlled build input, not a cross-machine reproducibility claim. Later
release-documentation commits are not build inputs.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc4-py3-none-any.whl` | 113107 | `980101b0459bf6d155a2394930eefcbaa46972373ce396a3ff24b5f97a538578` |
| `casf-0.1.0rc4.tar.gz` | 149681 | `07d6d65660c515570205efabe0b3bde158d8e978042b654db5f5d1cd204cdac3` |

The [checksum file](SHA256SUMS-0.1.0rc4-ce6cd67.txt) and
[machine-readable record](candidate-0.1.0rc4-ce6cd67.json) retain source identity,
package-member hashes, installation inventories and CI evidence. Inspection
verified all **40 runtime files**, 46 wheel members, 56 source-archive files,
wheel RECORD, packaged examples and metadata against the build revision.
Author, keywords, classifiers, license, project URLs and dependency bounds also
passed strict metadata validation. No private keys, databases, untracked copies,
tests or full documentation are packaged.

## Exact artifact installation checks

The [candidate procedure](../candidate-build.md) used these exact files in fresh
base-wheel, witness-wheel and sdist environments on each platform. Dependencies
came from hash-checked locked exports; cryptography was 50.0.2 in every install.
Sdist installation used isolated builds constrained to Setuptools 84.2.1.
Checks ran outside the source tree with isolated imports and no `PYTHONPATH` or
`PYTHONHOME` override. Installed metadata and all 40 runtime hashes matched.

| Installation platform | Python | SQLite | Commands | Synthetic workflows |
| --- | --- | --- | --- | --- |
| macOS 27.2.1 arm64, native | 3.12.14 | 3.53.1 | 38/38 passed | Witness wheel and sdist: 21 checks each |
| Ubuntu 24.04.5 amd64, emulated locally | 3.12.16 | 3.45.1 | 38/38 passed | Witness wheel and sdist: 21 checks each |

Each platform's 38 commands comprise 12 setup/installation commands and 26
verification commands, not pytest totals. All four workflows produced the
expected tamper `FAIL` and unavailable-witness `INCONCLUSIVE` results.

All six installations passed the Ed25519 small-order/noncanonical-key, identity
log manifest, authority/witness pin, witness registration, retained-checkpoint,
private SQLite/sidecar and canonical JSONL checks. New installed checks reject
four short-passphrase cases before filesystem access, accept ASCII and UTF-8
16-byte passphrases, load three legacy short-passphrase keys, reject wrong
passwords, and preserve ciphertext, mode `0600` and no-overwrite behavior.
Artifact hashes were checked before and after installation and did not change.

Ubuntu exact-file checks used Docker Desktop amd64 emulation on an arm64 Mac.
The test phase had networking disabled and synthetic SQLite state on
container-local storage. This is not native hardware evidence; Docker Desktop
host-shared SQLite state storage remains unvalidated. Native CI below builds
its own packages and is separate from these exact-file installations.

## Post-merge acceptance matrix

[CI 248](https://github.com/hamdamme/casf/actions/runs/45107762353) passed all ten
jobs on exact merge `ce6cd67`. All 20 validation/fuzz archive digests were
verified; source imports, installed wheels and packaged runtime bytes match
the build revision in every configuration.

| Hosted runner | Python | SQLite | Locked | Minimum direct dependencies |
| --- | --- | --- | --- | --- |
| Ubuntu x86_64 | 3.12.16 | 3.46.1 | 1894 passed; 20 skipped | 1894 passed; 20 skipped |
| Ubuntu x86_64 | 3.13.18 | 3.46.1 | 1894 passed; 20 skipped | 1894 passed; 20 skipped |
| Ubuntu x86_64 | 3.14.10 | 3.46.1 | 1894 passed; 20 skipped | 1894 passed; 20 skipped |
| macOS arm64 | 3.12.10 | 3.49.1 | 1914 passed | 1914 passed |
| macOS arm64 | 3.13.17 | 3.50.4 | 1914 passed | Not scheduled |
| macOS arm64 | 3.14.10 | 3.50.4 | 1914 passed | Not scheduled |

No failures or unexpected skips occurred. Ubuntu skips only native Darwin ACL
tests, which passed on macOS. Every configuration includes the 11 new key-file
regressions, 16 Ed25519 advisory cases and 18 Ed25519 edge vectors. Applicable
lint, typing, repository/lock, package, installed-wheel and workflow checks
passed. Parser campaigns passed **72,900 cases**. Locked cryptography/Setuptools
versions were 50.0.2/84.2.1; minimum versions were 50.0.0/77.0.3.
SQLite 3.42.0 was not rerun. This documentation PR requires its own CI; CI 248
is evidence for the build revision, not for later documentation commits.

## Dependency review and remaining release gates

The [fresh dependency review](dependency-review-0.1.0rc4-ce6cd67.md) records
29 exact package/version pairs, 58 successful OSV/PyPI requests and 442 verified
locked distribution hashes. No listed advisories were returned for the locked
packages, uv, cryptography 50.0.0 or click 8.5.1. Previously recorded advisories
remain for minimum-only Setuptools 77.0.3 and wheel 0.45.1; their compatibility
tests do not establish security suitability. See the review for scope and limits.

1. Review these exact files, hashes, release notes, dependency findings and the
   documentation PR's own CI; record artifact approval.
2. Refresh dependency queries if publication is delayed. Native-library and
   host-patch assessment and final CASF advisory disposition remain separate;
   no new independent researcher signoff is claimed.
3. Obtain separate approval to tag the exact build and publish these GitHub
   prerelease files. No tag, release, package upload or advisory publication
   was performed. Do not substitute another build.
4. After approved publication, verify public downloads and installations,
   coordinate advisory disposition, then verify a new Zenodo version and citation.

This experimental candidate does not close P03/P04 or partial P05/P06, establish
physical power-loss durability, or change H1's historical research result.
