# Dependency review for experimental 0.1.0rc3

The latest package-query refresh is retained in the [c38bf82 results](dependency-review-0.1.0rc3-c38bf82.json)
and [candidate refresh](candidate-0.1.0rc3-c38bf82.md). Earlier query results and
native-component inventories below remain tied to their original builds.

Queried 17 November 2026 UTC for build revision
`a0ac1bfa61d3406c99b6bf758c62f6e840b633f3`. The
[saved query record](dependency-review-0.1.0rc3.json) retains the lockfile hash,
exact versions, UTC time, source URLs, response hashes and declared licenses.

All 24 locked external packages plus uv 0.13.5 were queried at their exact
versions through both the PyPI version JSON API and OSV query API. All **50
requests succeeded**, with no listed vulnerabilities, pagination remainder or
yanked files. This is dated package-advisory evidence, not native-library or
host-patch clearance. Refresh immediately before approved publication.

No external dependency versions changed. The prior
[license and notice inventory](../0.1.0rc2/dependency-review-0.1.0rc2.md#license-and-redistribution-inventory)
remains historical evidence for those identical package versions, not a new
inspection of every dependency distribution. Current PyPI license declarations
are retained in the new query record. The new CASF distributions retain the
Apache-2.0 LICENSE and pass exact member/metadata inspection: 45 wheel members,
55 source-archive regular files and 39 matching runtime files. They do not bundle
the separately installed Python/native/dependency binaries.

## Actual installed native components

| Environment | Python | Python TLS | SQLite | cryptography OpenSSL |
| --- | --- | --- | --- | --- |
| macOS arm64 local | 3.12.14 | OpenSSL 3.5.8 | 3.53.1 | 4.0.3 |
| Linux x86_64 laptop | 3.14.4 | OpenSSL 3.5.5 | 3.46.1 | 4.0.3 |

These are compatibility-test environments, not a recommendation to deploy these
versions. No host patching or new native-code security assessment was performed.
The earlier [native findings and applicability discussion](../0.1.0rc2/dependency-review-0.1.0rc2.md#native-component-findings-and-disposition)
are preserved; their source queries and dispositions are dated, not refreshed
by the package-only queries above. In particular, the recorded Mac SQLite
version is below the earlier recorded 3.53.2 fixes. Distributor backports and
new advisories require an operating-environment review before real use.
CI records its own actual interpreters/components; its newer catalog selection
must not be substituted for these exact local inventories.

The [candidate record](candidate-0.1.0rc3.md) records successful synthetic installs
on both machines. Release review must accept this experimental scope explicitly;
it must not advertise a security-cleared runtime or production readiness.
