# Internal operations acceptance worksheet

Status: proposed acceptance requirements, not a deployed configuration. Intended
use is internal business-transaction audit records. Source system, event classification, readers,
operators and recovery targets await operator decisions. Keep synthetic data in
the existing rehearsal. Completing this worksheet does not itself pass P05/P06.

Use [administration](../administration.md), [writer recovery](../writer-recovery.md),
[recovery drills](../recovery-drills.md) and [witness service](../witness-server.md)
for implemented behavior. Do not introduce enterprise tenancy, encryption
protocols or new trust rules as implicit prerequisites to this reference project.

## Decisions to record before real records

| Decision | Required answer | Current state |
| --- | --- | --- |
| First event source | Business transactions; application/system, authenticated producer, event schema and stable retry ID | Record category confirmed; source application pending |
| Data classification | Fields permitted in records; prohibited secrets/personal data; payload access owner | Awaiting operator |
| Readers and writers | Readers must be authorized users; name the approving owner, roles and append/export/receipt permissions | Reader restriction confirmed; identities and enforcement pending |
| Custody | Authority, writer, witness, verifier-state and backup administrators; shared-access exceptions | Awaiting operator |
| Trust distribution | Authenticated public-pin/status channel and independent identity confirmation | Awaiting operator |
| Retention | Record/backup/log lifetime, approved deletion procedure and policy owner | Awaiting operator |
| Recovery | Maximum acceptable loss, maximum recovery time, backup frequency and restore approver | Awaiting operator |
| Capacity | Expected peak events/second, record size, daily volume, outage duration and available storage | Awaiting operator |
| Alerts and incidents | Recipient, response target, escalation and maintenance owner | Awaiting operator |

No retention period, legal basis, recovery guarantee or named owner is inferred.
The source-system owner must decide which events are authoritative and whether
omissions can be detected; a valid CASF signature does not prove an event occurred.

## Business-transaction integration acceptance

The operator selected business transactions as the first record category. The
following are proposed integration checks, not an implemented accounting system
or a finalized event schema:

- Identify the authoritative transaction ID and event ID separately. A retry of
  one event must reuse its event ID; a later correction/refund is a distinct event
  linked to the original transaction rather than an edit to signed history.
- Define which transitions are recorded (for example created, approved, posted,
  reversed) with the source owner. Do not infer business completion from a locally
  appended CASF event or from a witness receipt.
- If amounts are included, agree currency and exact integer-unit or canonical
  string representation before integration. CASF wire JSON rejects floating-point
  numbers; do not silently round amounts or assume all currencies use two decimals.
- Use synthetic transaction identifiers for testing. Exclude passwords, access
  tokens and payment credentials; decide explicitly which customer/account fields
  are needed and who may read/export them. Payload confidentiality requires
  deployment controls outside CASF's signatures.
- Reconcile source transaction/event counts and identifiers with CASF records.
  Exercise missing events, duplicate delivery, out-of-order delivery, source
  outages, replay after restart and corrections. Signing cannot detect an event
  that was never supplied without an independent completeness check.
- Document the boundary between the business database commit and the CASF append.
  Do not claim they form one atomic transaction. Select and test the application's
  durable delivery/retry mechanism before using real transactions.

Source application, reader roles, accepted schema, delivery design and expected
volume are still unassigned. No source-system integration is authorized by this
worksheet alone; its implementation must follow the confirmed application scope.

## Access and custody acceptance

| Role | Necessary material | Acceptance check |
| --- | --- | --- |
| Authority custodian | Authority signing key and status/manifest publication process | Signing key absent from writer/witness deployment; public pins confirmed independently of bundles. |
| Writer operator | Log key, independent pins, signed status, protected writer state and submission credential | Verified startup succeeds; missing/stale trust prevents writes; retries retain event IDs/pending bytes. |
| Witness operator | Witness key/database and provisioned authority public keys | Separate administrative access where threat model requires it; no writer or authority private keys; authenticated reads/submissions. |
| Verifier custodian | Public trust and separately retained checkpoints/status | No private signing key needed; restoring writer/witness backups cannot roll back this state. |
| Backup custodian | Approved encrypted backups and separately protected restore material | Unauthorized access fails; authorized restore verifies against independently retained evidence. |

Separate directories or two computers under the same administrator are not
independent custody. Record actual accounts, privileges and shared recovery
access. If all roles remain under one operator, document that assumption and
seek explicit deployment acceptance rather than marking separation established.
Do not claim per-tenant authorization from a shared reference-witness token.

## Recovery rehearsal evidence

Use a disposable copy and fresh output paths. Keep the original and independent
state untouched. Record source hash, backup time/hash, acknowledged sequence,
retained checkpoint/status serial, commands, outputs and elapsed time.

1. Restore the approved encrypted backup using the organization's chosen backup
   system; verify decryption access and file integrity. CASF does not encrypt
   plaintext payload storage or provide a backup-encryption system.
2. Authenticate the restored evidence using independently provisioned pins and
   retained signed anchors. Offline restore does not establish freshness.
3. Perform verified startup against the live authenticated witness with the
   established external state. Never delete/reinitialize that state to pass.
4. Show that a stale backup missing committed records cannot resume signing, and
   that rollback of both writer and witness is detected by independently retained
   state. Exercise a stale status statement and terminal revocation separately.
5. Resolve an accepted-but-unrecorded submission by retrieving its authentic
   receipt or retrying the identical pending checkpoint. Retain evidence if the
   outcome remains inconclusive.
6. Record recovery time and missing-record count against the targets agreed above.
   Approve promotion separately; keep the old store for investigation.

Existing automated backup/rollback drills provide software evidence. They do
not demonstrate the organization's encrypted backup system, access controls or
independent custody. Physical power-loss and reboot tests remain deferred and
must not be silently replaced by these restore checks.

## Monitoring and incident acceptance

Define thresholds from the workload and recovery targets before testing them.
The following are operator-owned requirements, not features claimed to be built:

- Accepted witness checkpoint age, pending-record count/age and repeated retries.
- Witness/proxy health, certificate expiry, authentication failures and bounded
  capacity rejection; demonstrate alert delivery to the named operator.
- Disk capacity, SQLite/persistence failures, backup age and periodic restore
  results, clock synchronization and credential rotation dates.
- Redaction checks across application, proxy, supervisor and backup logs using
  synthetic tokens/passphrases/record markers. Restrict who can read those logs.

On trust failure, corruption or conflicting state, preserve evidence and stop
uncertain signing. Treat temporary unavailability as inconclusive; do not use
`--local-only` to bypass verified startup. Follow the exact
[submission categories](../adr/ADR-016-submission-error-categories.md); not every
HTTP failure is retryable. Record incident owner, start time, affected revisions,
last accepted checkpoint and recovery authorization without placing secrets in
the incident report.

## Closeout

P05 needs the actual custody/access arrangement, authenticated trust distribution,
and successful independent-state recovery drills. P06 needs completed decisions,
access/redaction/alert/backup tests, representative workload measurements and
explicit operator acceptance. Evidence must include failures and unmet criteria.
No production rollout, release publication or real-data migration is authorized
by a documentation merge.
