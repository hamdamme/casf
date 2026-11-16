# USB storage interruption — 16 November 2026

One sudden USB removal during synthetic CASF appends passed recovery comparison:
all 638 acknowledged records were recovered, in order, with identical hashes
and payload sequence values. SQLite integrity returned `ok`; CASF signature and
chain verification returned PASS. No extra records were recovered.
[Machine-readable evidence](usb-interruption-2026-11-16.json) records the exact
source revision, environment, file fingerprints and comparison results.

## Procedure and evidence

The operator authorized erasing a dedicated approximately 16 GB SanDisk 3.2Gen1
stick. Its existing partition was formatted ext4 and mounted with
`nodev,nosuid,noexec`. The laptop remained powered throughout. The existing
witness rehearsal and internal storage were not the interrupted target.

An isolated source export of `0923c8e5203a00b7e9678899f747d80c22fd51a2` used
Python 3.14.4 and the existing rehearsal environment. This was not a new locked
dependency installation. Synthetic writer fixtures created a fresh local-only
log on the USB; SQLite reported WAL and synchronous=2 (FULL). This storage test
made no online freshness or independent-witness claim.

After each successful append, the control computer saved its sequence and hash
and flushed the acknowledgement log with fsync before authorizing the next
append. The operator unplugged the stick without ejecting it while the campaign
was running. The writer stopped with OperationalError. Exactly 638 completed
appends had been recorded independently; no writer remained running when the
stick was reconnected. The harness caught the storage error and exited normally;
its zero process exit code was not interpreted as a successful uninterrupted write.

Linux marked the old mount shut down; the reconnected USB was initially unmounted.
The stale mount was removed and the entire partition was copied to an image on
the laptop's internal storage, with a SHA-256 digest recorded. The original image
was preserved. A separate image copy was mounted, allowing normal ext4 journal
recovery there; no filesystem repair utility was run. Database, WAL and SHM files
were fingerprinted and copied again before opening SQLite. Verification used
only this inspection copy. The acknowledgement log remained on the control host.

Read-only inspection showed the pre-recovery SHM file was three bytes long;
SQLite recovered successfully from the copied artifacts without manual removal
of any sidecar. `PRAGMA integrity_check`, CASF verification, and an independent
sequence/hash/payload comparison all passed. The local evidence folder
`outputs/usb-loss-20261116/` retains the harness, acknowledgement log, environment,
recovered records and comparison. Private keys and raw disk images are not published.

## Scope

This is one interruption at an uncontrolled write timing on this USB and filesystem.
It does not establish exhaustive crash schedules, checkpoint/submission recovery,
internal-SSD durability, or sudden whole-machine electrical power loss. No new
software regression suite or release was required for this operational test.
Whole-machine power-loss and forced-shutdown testing are unscheduled at the
operator's request and are not prerequisites for the current work. The broader
physical durability gate remains unverified; the USB result does not close it.
