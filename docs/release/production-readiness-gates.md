# Production-readiness gates

The Team A remediation fixes bounded code defects and hardening gaps. Passing
those tests is not production certification, a guarantee of no defects, or a
substitute for independent assessment. The project remains experimental.
These gates require separate owners and acceptance evidence; no deployment or
protocol redesign is included in the remediation PR.

| Gate | Required owner and evidence | Status |
| --- | --- | --- |
| Independent cryptographic/security assessment | Independent reviewers: source hashes, canonicalization/domain separation, keys, epoch/trust/status, receipt binding, rollback, parsers, HTTP, SQLite and recovery; tracked unresolved findings. | Open |
| Physical power-loss/filesystem durability | Deployment operator: predefined data-loss/recovery criteria; actual hardware, filesystem/mount/cache settings and Python/SQLite/OpenSSL versions; sudden power loss around commits, WAL, exports, state replacement and directory sync. SIGKILL is insufficient. | Deferred by operator |
| Persistent cross-host TLS rehearsal | Operations/security: separate writer/witness hosts, supervised service, CA/hostname checks, private CA or proxy mTLS where chosen; credential/certificate rotation and expiry, restarts, failure, concurrency/limits, monitoring/redaction. | 22 cross-host checks accepted; boot persistence and operating acceptance still open |
| Administrative separation and retained state | Security/operator: independent authority/writer/witness/verifier/backup domains, authenticated pins/status distribution, separate high-water/revocation storage; compromise, stale state, lost-key and restoration drills. Never delete state to make verification pass. | Open |
| Deployment/access/data governance | Product/operator: tenant/log authorization, least privilege, keys, event provenance, privacy, retention/deletion/legal review, clocks, encrypted backups, restore authorization, migration/rollback, capacity and incident ownership; representative workload testing before real data. Witness hashes cannot restore lost records. | Open |
| Research claims | Research owner: preserve canonical H1's unmet primary expectation. Without a retained client checkpoint, WITNESS_AHEAD is INCONCLUSIVE rather than the predeclared FAIL; retained conflicts yield WITNESS_STATE_CONFLICT. Changing semantics requires a separate ADR/protocol review. | Limitation retained |
| New release and provenance | Maintainer: separately approve a new version, fresh advisories, inspected packages, exact hashes, download and fresh-install checks. Never replace existing rc2 assets. | Open; not authorized here |

The published `0.1.0rc2` build is
`e92194fe0fa6eb37c2ff9016c381b8e734008880`; it contains neither PR 57 nor these
remediation changes. No PyPI upload is part of this work. The
[publication record](publication-0.1.0rc2.md) remains the historical authority.

PR 60 added generated writer/witness recovery sequences; PR 61 added bounded
Python-line-edge-guided JSON parser campaigns. The six locked-dependency CI jobs
each run 2,000 guided mutations plus 25 seed cases. Both PRs passed their CI
matrices. See [adversarial testing](../adversarial-testing.md) for commands and scope. These campaigns and process-crash tests do not exhaust
all protocol states or crash schedules. The fuzz targets exclude HTTP framing,
SQLite files and native cryptographic internals. Physical power-loss testing is
not covered. P02/P03 hardware work remains deferred;
use the [acceptance tracker](internal-deployment-acceptance.md) for current status.
The [review brief](independent-review-brief.md) and
[operations worksheet](internal-operations-worksheet.md) prepare the open review
and deployment gates without claiming they have passed.
