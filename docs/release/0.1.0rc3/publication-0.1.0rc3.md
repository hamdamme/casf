# CASF 0.1.0rc3 publication closeout

Recorded 17 November 2026. P08 is complete for the experimental research release.

## Published artifacts and revisions

The approved [GitHub prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc3)
was published on 16 November 2026 in America/Chicago
(`2026-11-17T04:41:37Z`). Tag `v0.1.0rc3` identifies build
`c38bf821af013eaa4efa96a799577dab60250b48`; the accepted review revision is
`90c84d02ad3775e685f3dd6c69b939adc71148d9` (PR 75).
[Post-merge CI](https://github.com/hamdamme/casf/actions/runs/44018097812)
passed all twelve configurations of that revision's matrix.

The wheel, source archive and checksum file were published with the
[approved hashes](SHA256SUMS-0.1.0rc3.txt). Public unauthenticated downloads on
Mac and Linux matched those exact hashes. Fresh installation checks passed:
33 on Mac (base wheel, witness wheel and source archive), and 20 on Linux
(witness wheel and source archive). Each of the four witness-capable installed
environments completed the 21-check synthetic demo. These are installation
checks, not an additional full source-suite run.

The [publication evidence](publication-0.1.0rc3.json) retains asset identities,
download hashes and individual check exit codes. The
[build record](candidate-0.1.0rc3-c38bf82.md) retains package inspection and
runtime evidence. The pre-publication advisory refresh queried PyPI and OSV
for 24 locked external packages plus uv 0.13.5: all 50 queries succeeded with
no listed advisories. This is dated package evidence, not a native-library or
host-patch assessment. No PyPI upload occurred; rc2 release assets were unchanged.

## Zenodo and subsequent repository changes

[Zenodo DOI 10.5281/zenodo.24321232](https://doi.org/10.5281/zenodo.24321232)
archives the rc3 source distribution as a ZIP of 55 regular files. The public
ZIP download passed integrity validation and matched SHA-256
`1ab5cfa6f5267fe720cae3e7acce7dea23e9c7a16f90c63b7c8f19c61a4ab552`.
This software deposit does not include the separate manuscript or full repository.

PR 76 added the citation and changed the hosted matrix to ten jobs. Its merge
`44b629209c0addfd485452aef9a09d260dff1b2c` passed
[post-merge CI](https://github.com/hamdamme/casf/actions/runs/44154136420).
These later documentation/workflow changes are not changes to published rc3 bytes.
The [current matrix](../validation-matrix.md) distinguishes ongoing coverage from
historical twelve-job results.

## Remaining work

The research-demo publication scope is closed. P03 whole-machine power-loss
testing remains pending future validation; P04 independent security review
remains pending independent evaluation. P05 production provisioning and P06
real-use acceptance remain incomplete. None is claimed complete by synthetic
checks. Canonical H1's primary expectation remains unmet. Future releases need
separate approval; this closeout authorizes no deployment or production keys.
