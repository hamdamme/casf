# CASF 0.1.0rc4 publication record

The approved experimental [GitHub prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc4)
was published on **22 November 2026 in America/Chicago**
(`2026-11-23T04:25:03Z`). Tag `v0.1.0rc4` identifies exact build
`ce6cd67c01df2af283b2e07fc1b832e79bb14821`. The accepted documentation review
revision is `0a91df52ad0ce73cc4a5b886ab8d29bfe9e33f6c` (PR 88).
Later documentation is not part of these artifacts.

## Published artifacts

Independent unauthenticated public downloads on macOS and Ubuntu matched these
[approved checksums](SHA256SUMS-0.1.0rc4-ce6cd67.txt). The downloaded checksum
file also matched the tracked record byte for byte.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `casf-0.1.0rc4-py3-none-any.whl` | 113107 | `980101b0459bf6d155a2394930eefcbaa46972373ce396a3ff24b5f97a538578` |
| `casf-0.1.0rc4.tar.gz` | 149681 | `07d6d65660c515570205efabe0b3bde158d8e978042b654db5f5d1cd204cdac3` |
| `SHA256SUMS-0.1.0rc4-ce6cd67.txt` | 184 | `569c89b3f07f7f9560fc33e23b59848b97ee6d31584e04f8fbec3a737390bc31` |

The [machine-readable publication record](publication-0.1.0rc4.json) retains
asset identities, download hashes and installation results. The
[candidate record](candidate-0.1.0rc4-ce6cd67.md) retains build provenance and
inspection of the 40 packaged runtime files, examples and metadata. Earlier
candidate records, checksums and rc2/rc3 release records remain unchanged.

## Public-download installation checks

Fresh base-wheel, witness-wheel and source-distribution environments used each
platform's own public downloads, hash-checked locked dependencies and
cryptography 50.0.2. All installed runtime hashes matched the build revision.

| Platform | Python | SQLite | Installation checks | Synthetic workflows |
| --- | --- | --- | --- | --- |
| Native macOS 27.2.1 arm64 | 3.12.14 | 3.53.1 | 38/38 passed | Witness wheel and sdist: 21 checks each |
| Ubuntu 24.04.5 amd64, locally emulated | 3.12.16 | 3.45.1 | 38/38 passed | Witness wheel and sdist: 21 checks each |

These are 76 installation/setup commands across six fresh environments, not
an additional full pytest run. All four workflows produced the expected
tamper `FAIL` and unavailable-witness `INCONCLUSIVE` results. Installed
security checks covered the earlier corrections and new-key passphrase
rejection, legacy key loading, permissions and no-overwrite behavior. Public
asset hashes remained unchanged after installation.

Ubuntu used amd64 emulation on an arm64 Mac, with networking disabled during
the test phase and synthetic SQLite state on container-local storage. This is
not native hardware evidence; Docker Desktop host-shared SQLite storage
remains unvalidated. The [candidate's hosted matrix](candidate-0.1.0rc4-ce6cd67.md#post-merge-acceptance-matrix)
is separate source evidence: CI 248 passed all ten jobs on `ce6cd67`.
CI 249 and 250 also passed all ten jobs for the documentation review and merge;
they do not change the published build revision. SQLite 3.42.0 was not rerun.

## Dependency review and remaining work

The [candidate dependency review](dependency-review-0.1.0rc4-ce6cd67.md) was
refreshed before publication; the final responses and hashes are retained in
the [publication JSON](publication-0.1.0rc4.json). The refresh completed 58
successful OSV/PyPI queries across 29 exact version pairs and verified 442
locked distribution hashes. No listed advisories were returned
for the locked packages. Four known upstream advisories remain scoped to
minimum-only build tools; passing their compatibility tests is not security
clearance. Queries are dated package evidence, not a native-library or
host-patch assessment.

No PyPI upload occurred. Separate security-advisory publication is **Pending**;
no advisory publication or new independent researcher signoff is claimed.
The rc4 Zenodo archive and DOI are **Pending**. The historical
[rc3 software DOI](https://doi.org/10.5281/zenodo.24321232) identifies rc3 only.

P03 whole-machine power-loss testing and P04 independent security review
remain open. P05 production provisioning and P06 real-use acceptance remain
incomplete, and H1's historical primary expectation remains unmet. This
experimental release makes no production-readiness or independent-audit claim.
