# Dependency review for ce6cd67

Fresh [OSV](https://google.github.io/osv.dev/post-v1-query/) and [PyPI](https://docs.pypi.org/api/json/) queries completed at **2026-11-23 04:05:23 UTC** for build revision `ce6cd67c01df2af283b2e07fc1b832e79bb14821`.

- Scope: **29 exact version pairs** — 24 external packages from this commit's lockfile, required tooling `uv==0.13.5`, and four additional pairs observed in minimum validation: `cryptography==50.0.0`, `click==8.5.1`, `setuptools==77.0.3`, `wheel==0.45.1`.
- **58/58 requests succeeded**. No yanked files, incomplete pagination, query errors, or locked distribution mismatches. All **442** distribution SHA-256 values from the lockfile matched PyPI metadata.
- The 24 locked packages, uv, cryptography 50.0.0, and click 8.5.1 have **no listed advisories** in these responses.
- Minimum-only build tools retain **four upstream advisories**, with exactly the same OSV identifier sets as the preceding 492f330 review. Setuptools has five OSV records representing three upstream advisories; wheel has two records representing one. Alias records are not additional vulnerabilities.

| Minimum package | Existing upstream advisory | Trigger and scope |
| --- | --- | --- |
| setuptools 77.0.3 | [GHSA-5rjg-fvgr-3xxf](https://github.com/pypa/setuptools/security/advisories/GHSA-5rjg-fvgr-3xxf) | An attacker-controlled URL processed by legacy `PackageIndex.download` can cause arbitrary file writes; fixed in 78.1.1. This API is absent from CASF's runtime and checked candidate build/install procedure. |
| setuptools 77.0.3 | [GHSA-h35f-9h28-mq5c](https://github.com/pypa/setuptools/security/advisories/GHSA-h35f-9h28-mq5c) | Non-ASCII manifest exclusions can fail across NFC/NFD normalization during macOS source-distribution builds; fixed in 83.0.0. CASF's manifest patterns are ASCII and the locked backend is 84.2.1. Actual archive inspection remains separate evidence. |
| setuptools 77.0.3 | [GHSA-xmj3-9gf7-h52w](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w) | A crafted Windows `namespace_packages.txt` passed to legacy `Wheel.install_as_egg` can create a fixed-content file outside its destination; fixed in 84.1.0. This path is absent from the checked CASF runtime and Ubuntu/macOS installation procedure. |
| wheel 0.45.1 | [GHSA-8rrh-rw8j-w5fx](https://github.com/pypa/wheel/security/advisories/GHSA-8rrh-rw8j-w5fx) | Unpacking a crafted archive with `wheel.cli.unpack` can modify permissions outside its destination; fixed in 0.46.2. This is minimum compatibility tooling, outside the locked candidate dependency set; the vulnerable unpack API is absent from the checked CASF source/CI workflow. |

The former cryptography 41.0.0 compatibility minimum is no longer supported by this commit. Its earlier advisory findings are historical; the supported 50.0.0 minimum returned no listed advisories in this refresh.

This refresh found **no new runtime or locked release-tool package finding, and no new dependency-query reason to replace the intended locked candidate artifacts**. It preserves the preceding disposition of minimum-only build-tool findings. Passing minimum-dependency tests establishes compatibility, not security clearance or a recommendation to use those old tools. Existing installations can retain older satisfying build tools; use the reviewed locked environment for candidate builds and experiments. This scoped review does not itself approve publication.

Native OpenSSL, Python TLS, SQLite, host patches, all permitted dependency ranges, and minimum development-tool versions are outside this query scope. Queries are dated snapshots, not proof of absence of vulnerabilities. PyPI license declarations are retained; mypy-extensions 1.1.0 still has no license fields/classifier in its JSON response. Its MIT file evidence remains in the existing dependency-review documentation and was not independently refreshed here. No new legal or bundled-native license clearance is claimed.

The [machine-readable record](dependency-review-0.1.0rc4-ce6cd67.json) retains query timestamps, response hashes, distribution comparisons, license fields and the previous-review comparison. All 140 retained request/response/distribution records were rehashed successfully. The [candidate record](candidate-0.1.0rc4-ce6cd67.md) identifies the separately inspected artifacts and installation results. Refresh queries if publication is delayed.
