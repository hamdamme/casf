# Internal deployment acceptance

The intended first deployment is internal use with real audit records. The Linux
laptop is dedicated to synthetic testing. Real records are not acceptance fixtures.
No release or production rollout is authorized by this plan.

## Work packages

| Session | Task | Acceptance | Status |
| --- | --- | --- | --- |
| 16 | P01 | Cross-host TLS, recovery, authentication, limits and supervised process restart | 22 checks passed; review pending |
| 16 | P02 | Services start after machine reboot without interactive login; preserved history verifies | Awaiting operator setup and reboot |
| 17 | P03 | Physical power-loss and filesystem recovery on identified disposable hardware | Procedure below; not executed |
| 18 | P04 | Independent security assessment with source hashes and resolved findings | Reviewer must be selected |
| 19 | P05 | Administrative separation, retained-state distribution and restore drills | Operator roles and independent storage required |
| 19 | P06 | Internal access, provenance, backup, retention, capacity and incident acceptance | Decisions below required |
| 20 | P07 | Expanded generated state-machine and coverage-guided fuzz campaigns | Not yet implemented |
| 21 | P08 | Fresh version and artifact provenance, advisories and approved publication | Publication requires separate approval |

These eight tasks extend the accepted 33-task experimental plan. A passing
rehearsal does not close the independent assessment or hardware gates. Canonical
H1 remains unchanged: WITNESS_AHEAD is INCONCLUSIVE without retained conflicting
state; retained conflict is WITNESS_STATE_CONFLICT. No protocol redesign is proposed.

## Reboot acceptance

The test account's user services currently run under systemd. Enable lingering
with `sudo loginctl enable-linger northern`, then enable only the two rehearsal
units. Record service configuration, current boot ID, witness database integrity,
last accepted checkpoint and independently retained client state before reboot.
The operator reboots only after the control machine has saved this evidence.
After reconnecting, check a changed boot ID, both services active without desktop
login, authenticated fresh witness response, unchanged accepted head and successful
verification. Record boot journal errors and elapsed recovery time. A graceful
reboot is not a physical power-loss test.

## Physical power-loss procedure: preparation only

Observed hardware: Dell XPS 15 9520 with BAT0; Linux root uses ext4 on NVMe.
Disconnecting its charger leaves battery power and is not this test. Do not open
or disconnect an internal battery as part of these instructions. Select suitable
externally powered disposable hardware or a manufacturer-supported safe test
method before executing a power cut. An external drive test covers that drive's
failure mode, not loss of power to the laptop's internal NVMe.

Before execution, agree the following acceptance criteria and retain the oracle
on the control machine, outside the tested storage:

- Every acknowledged committed record remains present, or recovery explicitly
  refuses/inconclusively reports missing or conflicting evidence. Silent success
  with rolled-back acknowledged history fails acceptance.
- Accepted witness heads cannot regress unnoticed against retained client state.
- An uncertain submission remains recoverable; pending canonical bytes survive
  rejected or interrupted submission and recovery never invents a receipt.
- SQLite integrity passes after recovery; partial exports/state replacements are
  rejected, with the previous complete artifact preserved where promised.
- Report actual loss and recovery time. Do not assume a zero-loss guarantee from
  filesystem names, SIGKILL results, or a small sample of power cuts.

Record machine/storage model and firmware, filesystem/mount options, disk-cache
and power-protection settings, OS/kernel, Python/SQLite/OpenSSL versions, source
hash, command, scenario, independent acknowledged sequence and exact cut/restart
times. Exercise writer commit/WAL, witness commit/WAL, retained-state replacement,
export publication and directory synchronization separately. Each needs a
repeatable workload, external acknowledgement journal and recovery validator
before a manual cut is requested. Define repetitions and recovery-time target
before running; retain failed attempts. Never repair by deleting retained state.

## Independent review packet

Review runtime baseline `cb3febff53a7cf8274a4b871f5be1382ebaedd33` plus the exact
accepted validation PR revision. Supply DEVELOPMENT.md, specification and ADRs,
current-reference, requirement-evidence, Team A remediation, prior reproduction
results and this acceptance record. The reviewer must be independent of the
implementation and record examined hashes, methods, reproductions and unresolved
findings. Cover canonicalization/domains, key lifecycle, manifest/epoch trust,
status/revocation distribution, receipt binding, rollback, resource limits,
HTTP authentication, SQLite durability and recovery. Passing maintainer tests is
not an independent review. No external outreach is authorized by this document.

## Internal operations decisions

Before real data, the operator must identify:

1. Audit-event producers and who may append, read, verify, administer and restore.
   Establish event provenance; signing cannot prove the original event was true.
2. Independent authority, witness, verifier-state and backup custodians and the
   authenticated channel used for public pins and signed revocation/status.
3. Data classification, retention/deletion obligations and approved backup
   encryption/key custody. Witness hashes cannot reconstruct lost records.
4. Recovery-point/time targets, backup frequency and restore approval. Rehearse
   old backups, witness rollback, lost keys and stale status against independent
   retained state without clearing safeguards.
5. Representative event rate/size, storage capacity, clock synchronization,
   certificate/token expiry alerts, monitoring and an incident owner.
6. Upgrade/migration rollback procedure and explicit go/no-go approval after
   acceptance evidence is reviewed.

Until these are decided, continue with synthetic records. New published artifacts
must use a new version and fresh hashes; never replace 0.1.0rc2 assets.
