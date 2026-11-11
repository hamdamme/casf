# CASF 0.1.0rc2

This is a preparation-time record. The [publication record](publication-0.1.0rc2.md)
now establishes the published status; original approval language and artifact
evidence below describe their recorded stage, not pending publication work.

Experimental release candidate for research and evaluation. These are prepared
release notes; the candidate is not published or approved for publication.

## Changes since the earlier candidate

- Writer startup now authenticates independent trust pins, signed authority
  status, complete local history and fresh witness continuity before signing.
  Durable retained state prevents silent rollback of accepted evidence.
- Restore preserves verified checkpoint/receipt journals and terminal seals.
  Lost records behind an authenticated anchor leave a sealed recovery state.
  Offline restore does not claim a fresh witness observation.
- The checkpoint worker persists retry deadlines and pending bytes, handles
  repeated submissions, and reports committed, witnessed and pending counts.
- SQLite stores have explicit schema identities and versions. Legacy stores
  require a copy migration; unknown or damaged schemas are rejected.
- Typed public operations, streaming verification, trusted incremental anchors
  and complete diagnostics have regression coverage. Export needs no private key.
- Generated-input tests, bounded parser fuzzing and process-crash checks extend
  the conformance suite. The supported CI matrix covers Ubuntu x86_64 and
  macOS arm64 on Python 3.12, 3.13 and 3.14.
- A runnable synthetic example exercises initialization, idempotent append,
  witnessing, verification, tamper rejection, backup, restore and final sealing.
  The source archive includes that example and the dependency lockfile.

## Installation and migration

Use the exact checked wheel or source archive identified in the
[approval checklist](approval-0.1.0rc2.md). There is no authorized package-index
installation yet. The optional `witness` extra supplies the HTTP server
dependencies. See [installation](../installation.md) and the
[synthetic example](../demo.md).

Use maintained security-patched Python and native libraries for operation.
Metadata dependency bounds describe compatibility, not current security
recommendations. The [dependency review](dependency-review-0.1.0rc2.md) records
exact query outcomes, actual runtime components and native advisory limits.

Back up existing stores with SQLite's backup facility and retain trust/state
independently. Stop writers and witnesses before the explicit
[legacy-store migration](../storage-migrations.md); retain the original copy.
Authenticated `casf-v1` bytes are unchanged. Verified opening and restore have
stricter trust/status/state requirements than the older candidate. Explicit
local-only operation does not establish independent trust or freshness.

## Evidence and limits

The [identified candidate files](candidate-0.1.0rc2.md) passed package inspection
and 32 clean-install checks. The same wheel also passed 1199 tests and the full
synthetic workflow on Python 3.12.16. CI builds separate artifacts and records
their tested revision; it does not substitute its files for the retained local
candidate hashes. No cross-machine build reproducibility claim is made.

CASF is not a production security service or an independently audited protocol.
Its guarantees depend on correctly provisioned authority/witness identities,
independently retained state, honest durable witness operation and the host's
storage behavior. Supplied authority status cannot establish globally current
revocation information. An unavailable witness yields an inconclusive freshness
result. Neither process-crash tests nor SQLite settings establish physical
power-loss durability on arbitrary hardware.

Research results remain tied to their recorded revisions and conditions. The
current H1 primary expectation remains unmet; original WAN/Linux measurements
are historical. Additional Linux/cloud deployment and independent witness
operation are deferred. Windows, 32-bit systems and other architectures are
outside the validated platform scope.

## Support and security reporting

Support is best effort for an experimental project; no long-term maintenance
or response guarantee is offered. Report suspected vulnerabilities through
[private reporting](https://github.com/hamdamme/casf/security/advisories/new),
using synthetic reproduction material. The [security policy](../../SECURITY.md)
states response targets and reporting details. The setting was checked during
this review; no new report was sent to test it.

CASF is Apache-2.0. Its distributions do not bundle the separately installed
Python dependencies or platform libraries, which retain their own terms and
notices. Publication requires separate approval of the exact files, tag target,
notes and stated limitations.
