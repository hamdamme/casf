# Research-demo closeout and operating rules

Scope: single-operator research and evaluation using synthetic transactions only.
No production deployment, real records, new application, protocol redesign or
operational-key provisioning is part of this closeout.

## Accepted evidence

- PR 57 at `e59fd64feed2d7136c0ee4ae543455ba90d3e572` accepted the scoped
  [tracked-file review](line-review-2026-11-11.md). Its inventory and methods apply
  to that revision; later changes are not retroactively manually reviewed.
- PR 69 accepted the [normal reboot rehearsal](reboot-2026-11-16.md).
- PR 70 accepted the [USB-only interruption result](usb-interruption-2026-11-16.md),
  not whole-machine power-loss durability.
- PR 71 at `e2c406ac1a83b6686e363266714651118f027f39` accepted the scoped
  [permissions inspection and Proton restore record](backup-custody-2026-11-16.md).
  The synthetic 20-record restore is complete; operational key recovery is not.
- PR 72 at `40382b1ed5355fef9b7716919a7c141037528455` accepted the existing
  [Python transaction example](../synthetic-transactions.md) and its Mac/Linux
  demonstration. [Post-merge CI](https://github.com/hamdamme/casf/actions/runs/43994726679)
  passed all twelve jobs. The cross-host evidence remains tied to its recorded
  implementation revision, distinct from the merge and the next release build.

## Adopted operating rules

| Decision | Research-demo rule |
| --- | --- |
| Access | One operator only; no independent-administration claim. |
| Data | Synthetic transactions and disposable test keys only. |
| Placement | Mac writer/authority administration and separate retained state; Linux witness rehearsal. No production key deployment. |
| Backup | Daily manual consistent snapshot uploaded to the private Proton folder. Keep 7 daily, 4 weekly and 3 monthly copies, plus pre-change snapshots. |
| Restore checks | Download and test a restore monthly against separately retained evidence. |
| Recovery targets | At most one day of lost demo data; aim to restore within one working day. These are adopted targets, not measured guarantees. Missed backups can exceed the loss target. |
| Daily inspection | Confirm witness reachability, no stuck submissions, and that the backup completed. |
| Failures | Preserve evidence and investigate; never bypass trust failures, delete retained state to pass, or report local append as witnessed acceptance. |

Backups, retention cleanup, monthly restore checks and daily inspection are manual
responsibilities. No scheduler or reminder is configured. Only the recorded
synthetic restore has been executed; an ongoing daily backup history is not claimed.
The temporary transaction witness/tunnel were stopped after demonstration; the
example is not an always-running business application.

## Closeout boundary

The research demo and its operating decisions are recorded. Release candidate
preparation and review remain separate from publication. P05/P06 stay partial:
production access, key/pin provisioning, event provenance, representative workloads,
alerts, operational recovery and real-use acceptance are outside this scope.
Independent assessment and whole-machine power-loss work remain unscheduled and
unperformed, not completed. P08 stays open until an approved new release is published
and its downloaded files are validated. Published rc2 assets must not be replaced.
Canonical H1 remains unmet: without retained conflicting state, WITNESS_AHEAD is
INCONCLUSIVE rather than the predeclared FAIL. No protocol change is proposed.
