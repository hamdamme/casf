# Backup and custody rehearsal — 16 November 2026

This rehearsal was accepted by merged PR 71. Decisions described below reflect
that rehearsal; the later [research-demo closeout](research-demo-closeout.md)
adopts a Mac writer and demo recovery targets. Production placement/provisioning
and real-use recovery acceptance remain separate.

## Agreed operating model

One administrator initially controls the deployment. Authority administration
and separately retained verification state belong on the Mac; the witness belongs
on Linux. The writer location awaits selection of the transaction application.
Proton Drive is the chosen private cloud backup destination. This is a selected
operating model, not a completed production key deployment or independent custody.
Separate hosts under one administrator do not establish administrative independence.

## Read-only permissions checks

The current synthetic Mac rehearsal role directories were owner-only (`0700`).
Authority, writer and witness key files, passphrases, bearer tokens and retained
writer state were `0600`. No additional ACL access appeared on the specifically
checked root, authority directory/key, retained-state and backup-baseline paths.
The independent backup baseline was `0644` inside a `0700` directory: the parent
restricted traversal. These findings do not cover every historical fixture or
other applications on the Mac.

On Linux, the rehearsal root and witness directory were `0700`. Witness keys,
passphrase, token, database and WAL/SHM files, TLS private key and proxy configuration
were `0600`, owned by the service account, with no symlinks in those inspected paths.
ACL checks on the root, witness directory, key, passphrase, token and TLS key
showed owner-only access. Authority/writer private-role directories were absent
from that rehearsal root; this was not a full-host search for copied secrets.
Both user services ran under the same login account with `UMask=0077` and
`NoNewPrivileges=yes`. They were not isolated into separate service accounts.
No permission changes were needed or made.

Checks used filesystem ownership/mode inspection, macOS `ls -lde`, Linux `getfacl`,
and `systemctl --user show`. Secret contents were not displayed. Synthetic key
passphrases remain alongside rehearsal keys under owner-only directories; this
is not evidence of production key recovery protection or protection from compromise
of that account. Operational authority keys, their recovery storage and authentic
pin/status distribution still need configuration and acceptance.

## Manual Proton backup roundtrip

[Recorded results](proton-restore-2026-11-16.json) identify source
`792e461f7cd27b1b16413d648c74f571333a7f52` and the exact downloaded archive hash.
A fresh synthetic writer created 20 signed records. `Writer.backup()` produced a
consistent SQLite snapshot; public bundle evidence and per-file SHA-256 values
were packaged in a ZIP. No private keys, passphrases, tokens or real records were
included. Public test-fixture keys are unsuitable for production.

The operator reported enabling account two-factor authentication, retaining a
recovery phrase outside the account, and creating a private, unshared Proton
folder. These settings were not independently inspected. The ZIP was not locally
password-encrypted: cloud encryption relies on Proton Drive's service. This test
did not audit provider encryption or recovery implementation.

After the operator reported upload and download, the downloaded ZIP matched the
original SHA-256 and every packaged checksum. It was restored into a fresh local
directory. SQLite integrity returned `ok`; CASF offline signature/chain validation
returned PASS; all 20 sequences and hashes matched an independently saved baseline
outside the uploaded archive. A valid older 10-record snapshot also passed offline
integrity but failed the independent exact-history comparison and was not accepted.
This was a harness comparison, not online witness reconciliation or operational
key restoration. Active-status evidence came from synthetic fixture signing.

The first downloaded archive contained unrelated historical repository files;
it was identified as the wrong artifact and was not restored. Only the subsequent
matching synthetic archive is counted as the successful roundtrip. Scripts and
local evidence remain in `outputs/proton-backup-20261116/` on the control computer.

## Daily backup policy

- Create a consistent CASF snapshot daily, then upload a dated archive to the
  private Proton folder. Never synchronize or copy only a live SQLite main file.
- Retain seven daily, four weekly and three monthly snapshots. Retention describes
  backup copies, not a policy for deleting original transaction/audit records.
- Take an additional snapshot before upgrades or configuration changes.
- Download and test a restore monthly into a fresh destination; compare against
  separately retained trusted state before authorizing use.
- Keep recovery credentials outside the cloud account and verification state
  separate from database restores. Do not overwrite newer state with a backup's
  older copy to make verification succeed.

This is an agreed manual policy. Automatic snapshots, uploads, retention cleanup,
monthly tests and reminders are not configured; the operator declined a reminder.
No unattended schedule or completed daily history is claimed. Daily frequency
can leave roughly a day's transactions exposed between successful backups, and
longer if a backup is missed. Accepted loss/recovery targets remain undecided.
Production private-key backup and recovery require a separate approved procedure;
do not add unprotected keys to these data archives.

## Remaining acceptance

The successful synthetic restore and permissions inspection do not close all
custody or operations requirements. Remaining work includes operational key and
pin provisioning, writer placement, real event-source integration, recovery targets,
access/alert decisions and evidence that the agreed backup procedure is operated.
Independent external review is outside the current queue at the operator's request
and remains unperformed. Whole-machine power-loss testing remains unscheduled.
No release or real-data rollout is authorized by this record.
