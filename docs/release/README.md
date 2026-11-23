# Release records

## Current

rc4 is published as an experimental GitHub prerelease from `ce6cd67`. Public
downloads and six fresh installations verified the exact approved files.
The [rc4 Zenodo archive](https://doi.org/10.5281/zenodo.24454789) contains the
same source distribution. Security-advisory publication remains Pending.

- [Publication record](0.1.0rc4/publication-0.1.0rc4.md)
- [Release checklist](checklist-v0.1.md)
- [ce6cd67 build and validation record](0.1.0rc4/candidate-0.1.0rc4-ce6cd67.md)
- [rc4 release notes and upgrade guidance](0.1.0rc4/notes-0.1.0rc4.md)
- [Published checksums](0.1.0rc4/SHA256SUMS-0.1.0rc4-ce6cd67.txt)
- [Dependency review](0.1.0rc4/dependency-review-0.1.0rc4-ce6cd67.md)
- [Production readiness gates](production-readiness-gates.md)
- [Completion tracker](completion-tracker.md)
- [Independent review brief](independent-review-brief.md)

## Latest published

- [rc4 publication record](0.1.0rc4/publication-0.1.0rc4.md)
- [v0.1.0rc4 GitHub prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc4)
- [rc4 Zenodo software archive](https://doi.org/10.5281/zenodo.24454789)

## Earlier published releases

- [rc3 publication record](0.1.0rc3/publication-0.1.0rc3.md)
- [v0.1.0rc3 GitHub prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc3)

Earlier rc4 candidate artifacts are historical and must not be published.
This includes `candidate-0.1.0rc4-492f330.*`, `candidate-0.1.0rc4-3333d00.*`,
`candidate-0.1.0rc4-d4721c4.*` and rc4 candidate/artifact evidence without a
revision suffix. Current release notes, this index and the checklist describe
ongoing work; they do not approve old artifact bytes.

Every other file in this folder is historical evidence for the revision it
names; it must not be attributed to a later implementation.

## Project status and release history

**Latest published release:** [0.1.0rc4 experimental prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc4) · **Protocol:** proposed `casf-v1` profile

The repository includes an implemented Python library, command line interface, SQLite writer, reference HTTP witness, evidence export and verification, automated tests, and research experiments. CI checks Python 3.12, 3.13, and 3.14.

The protocol specification remains a design review document. The project has not undergone an independent security audit and should not be treated as production ready security infrastructure.

Start with the [operating and maintenance handoff](../operations/operating-handoff.md). The
[rc2 publication record](0.1.0rc2/publication-0.1.0rc2.md) retains the earlier release
files and download evidence. The [rc3 release](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc3)
retains its historical [publication and installation evidence](0.1.0rc3/publication-0.1.0rc3.md) and
[Zenodo archive](https://doi.org/10.5281/zenodo.24321232). The current
[rc4 publication record](0.1.0rc4/publication-0.1.0rc4.md) identifies the new files.
The [rc4 Zenodo archive](https://doi.org/10.5281/zenodo.24454789), published
23 November 2026, contains the byte-identical GitHub source distribution from
`ce6cd67`. No PyPI release has been published.

The scoped [tracked-file review](reviews/line-review-2026-11-11.md) and corrections
were accepted in PR 57 at `e59fd64`; that review does not cover every later change.
Subsequent fixes and the [synthetic transaction demo](../guide/synthetic-transactions.md)
were accepted through PR 72 at `40382b1`, whose post-merge CI passed.
The [research-demo closeout](reviews/research-demo-closeout.md) records the
accepted evidence and operating rules. Published rc2 downloads predate these fixes.
The rc3 experimental release includes these fixes and the synthetic demo.

P03 (whole-machine power-loss testing) is **Pending future validation**. P04
(independent security review) is **Pending independent evaluation**. Both remain
incomplete and relevant to future production-readiness evaluation. Neither blocks
publication of experimental research releases; future releases still require
separate publication approval and artifact validation.

The published **0.1.0rc4** includes the corrections from
[PR 78](https://github.com/hamdamme/casf/pull/78),
[PR 82](https://github.com/hamdamme/casf/pull/82),
[PR 84](https://github.com/hamdamme/casf/pull/84) and
[PR 87](https://github.com/hamdamme/casf/pull/87). Published rc2/rc3 are affected
by the Ed25519 issue. The `492f330` and earlier candidate files remain historical.
The [ce6cd67 build](0.1.0rc4/candidate-0.1.0rc4-ce6cd67.md) was accepted through
PR 88 and separately approved for publication. [Public verification](0.1.0rc4/publication-0.1.0rc4.md)
passed on the exact files. CI 248 covers the build; CI 250 covers the documentation
merge. See the [rc4 notes](0.1.0rc4/notes-0.1.0rc4.md).

## Moved paths

The table records the documentation reorganization. Frozen JSON, checksum files
and other hashed evidence retain their original bytes and revision-specific path
names; resolve those names with this table. Markdown navigation uses the new
locations. Links pinned to historical Git revisions still describe those trees.
The former implementation-reference URL has a forwarding page so existing
package metadata remains useful. No release artifact was rebuilt by these moves.

| Old repository path | New repository path |
| --- | --- |
| `docs/01-technical-description.md` | [docs/historical/01-technical-description.md](../historical/01-technical-description.md) |
| `docs/02-architecture.md` | [docs/historical/02-architecture.md](../historical/02-architecture.md) |
| `docs/03-implementation-plan.md` | [docs/historical/03-implementation-plan.md](../historical/03-implementation-plan.md) |
| `docs/04-operation-manual.md` | [docs/historical/04-operation-manual.md](../historical/04-operation-manual.md) |
| `docs/05-verification-manual.md` | [docs/historical/05-verification-manual.md](../historical/05-verification-manual.md) |
| `docs/administration.md` | [docs/operations/administration.md](../operations/administration.md) |
| `docs/adversarial-testing.md` | [docs/testing/adversarial-testing.md](../testing/adversarial-testing.md) |
| `docs/append-api.md` | [docs/reference/append-api.md](../reference/append-api.md) |
| `docs/checkpoint-worker.md` | [docs/reference/checkpoint-worker.md](../reference/checkpoint-worker.md) |
| `docs/current-reference.md` | [docs/reference/current-reference.md](../reference/current-reference.md) |
| `docs/demo.md` | [docs/guide/demo.md](../guide/demo.md) |
| `docs/dependencies.md` | [docs/reference/dependencies.md](../reference/dependencies.md) |
| `docs/export-and-reports.md` | [docs/reference/export-and-reports.md](../reference/export-and-reports.md) |
| `docs/installation.md` | [docs/guide/installation.md](../guide/installation.md) |
| `docs/log-api.md` | [docs/reference/log-api.md](../reference/log-api.md) |
| `docs/operating-handoff.md` | [docs/operations/operating-handoff.md](../operations/operating-handoff.md) |
| `docs/process-crash-testing.md` | [docs/testing/process-crash-testing.md](../testing/process-crash-testing.md) |
| `docs/recovery-drills.md` | [docs/operations/recovery-drills.md](../operations/recovery-drills.md) |
| `docs/release/SHA256SUMS-0.1.0rc2.txt` | [docs/release/0.1.0rc2/SHA256SUMS-0.1.0rc2.txt](0.1.0rc2/SHA256SUMS-0.1.0rc2.txt) |
| `docs/release/SHA256SUMS-0.1.0rc3-a0ac1bf.txt` | [docs/release/0.1.0rc3/SHA256SUMS-0.1.0rc3-a0ac1bf.txt](0.1.0rc3/SHA256SUMS-0.1.0rc3-a0ac1bf.txt) |
| `docs/release/SHA256SUMS-0.1.0rc3.txt` | [docs/release/0.1.0rc3/SHA256SUMS-0.1.0rc3.txt](0.1.0rc3/SHA256SUMS-0.1.0rc3.txt) |
| `docs/release/SHA256SUMS-0.1.0rc4-3333d00.txt` | [docs/release/0.1.0rc4/SHA256SUMS-0.1.0rc4-3333d00.txt](0.1.0rc4/SHA256SUMS-0.1.0rc4-3333d00.txt) |
| `docs/release/SHA256SUMS-0.1.0rc4-492f330.txt` | [docs/release/0.1.0rc4/SHA256SUMS-0.1.0rc4-492f330.txt](0.1.0rc4/SHA256SUMS-0.1.0rc4-492f330.txt) |
| `docs/release/SHA256SUMS-0.1.0rc4-d4721c4.txt` | [docs/release/0.1.0rc4/SHA256SUMS-0.1.0rc4-d4721c4.txt](0.1.0rc4/SHA256SUMS-0.1.0rc4-d4721c4.txt) |
| `docs/release/SHA256SUMS-0.1.0rc4.txt` | [docs/release/0.1.0rc4/SHA256SUMS-0.1.0rc4.txt](0.1.0rc4/SHA256SUMS-0.1.0rc4.txt) |
| `docs/release/advisory-followup-2026-11-21.md` | [docs/release/reviews/advisory-followup-2026-11-21.md](reviews/advisory-followup-2026-11-21.md) |
| `docs/release/advisory-remediation-2026-11-17.md` | [docs/release/reviews/advisory-remediation-2026-11-17.md](reviews/advisory-remediation-2026-11-17.md) |
| `docs/release/approval-0.1.0rc2.md` | [docs/release/0.1.0rc2/approval-0.1.0rc2.md](0.1.0rc2/approval-0.1.0rc2.md) |
| `docs/release/backup-custody-2026-11-16.md` | [docs/release/reviews/backup-custody-2026-11-16.md](reviews/backup-custody-2026-11-16.md) |
| `docs/release/candidate-0.1.0rc2.json` | [docs/release/0.1.0rc2/candidate-0.1.0rc2.json](0.1.0rc2/candidate-0.1.0rc2.json) |
| `docs/release/candidate-0.1.0rc2.md` | [docs/release/0.1.0rc2/candidate-0.1.0rc2.md](0.1.0rc2/candidate-0.1.0rc2.md) |
| `docs/release/candidate-0.1.0rc3-c38bf82.json` | [docs/release/0.1.0rc3/candidate-0.1.0rc3-c38bf82.json](0.1.0rc3/candidate-0.1.0rc3-c38bf82.json) |
| `docs/release/candidate-0.1.0rc3-c38bf82.md` | [docs/release/0.1.0rc3/candidate-0.1.0rc3-c38bf82.md](0.1.0rc3/candidate-0.1.0rc3-c38bf82.md) |
| `docs/release/candidate-0.1.0rc3.json` | [docs/release/0.1.0rc3/candidate-0.1.0rc3.json](0.1.0rc3/candidate-0.1.0rc3.json) |
| `docs/release/candidate-0.1.0rc3.md` | [docs/release/0.1.0rc3/candidate-0.1.0rc3.md](0.1.0rc3/candidate-0.1.0rc3.md) |
| `docs/release/candidate-0.1.0rc4-3333d00.json` | [docs/release/0.1.0rc4/candidate-0.1.0rc4-3333d00.json](0.1.0rc4/candidate-0.1.0rc4-3333d00.json) |
| `docs/release/candidate-0.1.0rc4-3333d00.md` | [docs/release/0.1.0rc4/candidate-0.1.0rc4-3333d00.md](0.1.0rc4/candidate-0.1.0rc4-3333d00.md) |
| `docs/release/candidate-0.1.0rc4-492f330.json` | [docs/release/0.1.0rc4/candidate-0.1.0rc4-492f330.json](0.1.0rc4/candidate-0.1.0rc4-492f330.json) |
| `docs/release/candidate-0.1.0rc4-492f330.md` | [docs/release/0.1.0rc4/candidate-0.1.0rc4-492f330.md](0.1.0rc4/candidate-0.1.0rc4-492f330.md) |
| `docs/release/candidate-0.1.0rc4-d4721c4.json` | [docs/release/0.1.0rc4/candidate-0.1.0rc4-d4721c4.json](0.1.0rc4/candidate-0.1.0rc4-d4721c4.json) |
| `docs/release/candidate-0.1.0rc4-d4721c4.md` | [docs/release/0.1.0rc4/candidate-0.1.0rc4-d4721c4.md](0.1.0rc4/candidate-0.1.0rc4-d4721c4.md) |
| `docs/release/candidate-0.1.0rc4.json` | [docs/release/0.1.0rc4/candidate-0.1.0rc4.json](0.1.0rc4/candidate-0.1.0rc4.json) |
| `docs/release/candidate-0.1.0rc4.md` | [docs/release/0.1.0rc4/candidate-0.1.0rc4.md](0.1.0rc4/candidate-0.1.0rc4.md) |
| `docs/release/completion-scope-v0.1.md` | [docs/release/0.1.0rc2/completion-scope-v0.1.md](0.1.0rc2/completion-scope-v0.1.md) |
| `docs/release/dependency-review-0.1.0rc2.json` | [docs/release/0.1.0rc2/dependency-review-0.1.0rc2.json](0.1.0rc2/dependency-review-0.1.0rc2.json) |
| `docs/release/dependency-review-0.1.0rc2.md` | [docs/release/0.1.0rc2/dependency-review-0.1.0rc2.md](0.1.0rc2/dependency-review-0.1.0rc2.md) |
| `docs/release/dependency-review-0.1.0rc3-c38bf82.json` | [docs/release/0.1.0rc3/dependency-review-0.1.0rc3-c38bf82.json](0.1.0rc3/dependency-review-0.1.0rc3-c38bf82.json) |
| `docs/release/dependency-review-0.1.0rc3.json` | [docs/release/0.1.0rc3/dependency-review-0.1.0rc3.json](0.1.0rc3/dependency-review-0.1.0rc3.json) |
| `docs/release/dependency-review-0.1.0rc3.md` | [docs/release/0.1.0rc3/dependency-review-0.1.0rc3.md](0.1.0rc3/dependency-review-0.1.0rc3.md) |
| `docs/release/dependency-review-0.1.0rc4-d4721c4.json` | [docs/release/0.1.0rc4/dependency-review-0.1.0rc4-d4721c4.json](0.1.0rc4/dependency-review-0.1.0rc4-d4721c4.json) |
| `docs/release/dependency-review-0.1.0rc4.json` | [docs/release/0.1.0rc4/dependency-review-0.1.0rc4.json](0.1.0rc4/dependency-review-0.1.0rc4.json) |
| `docs/release/dependency-review-2026-10-24.json` | [docs/release/reviews/dependency-review-2026-10-24.json](reviews/dependency-review-2026-10-24.json) |
| `docs/release/dependency-review-2026-10-28.json` | [docs/release/reviews/dependency-review-2026-10-28.json](reviews/dependency-review-2026-10-28.json) |
| `docs/release/dependency-review.md` | [docs/release/reviews/dependency-review.md](reviews/dependency-review.md) |
| `docs/release/guided-fuzz-2026-11-12.json` | [docs/release/reviews/guided-fuzz-2026-11-12.json](reviews/guided-fuzz-2026-11-12.json) |
| `docs/release/http-dependency-review.md` | [docs/release/reviews/http-dependency-review.md](reviews/http-dependency-review.md) |
| `docs/release/http-validation.md` | [docs/release/reviews/http-validation.md](reviews/http-validation.md) |
| `docs/release/install-rehearsal-2026-10-27.md` | [docs/release/reviews/install-rehearsal-2026-10-27.md](reviews/install-rehearsal-2026-10-27.md) |
| `docs/release/line-review-2026-11-11.md` | [docs/release/reviews/line-review-2026-11-11.md](reviews/line-review-2026-11-11.md) |
| `docs/release/notes-0.1.0rc2.md` | [docs/release/0.1.0rc2/notes-0.1.0rc2.md](0.1.0rc2/notes-0.1.0rc2.md) |
| `docs/release/notes-0.1.0rc3.md` | [docs/release/0.1.0rc3/notes-0.1.0rc3.md](0.1.0rc3/notes-0.1.0rc3.md) |
| `docs/release/notes-0.1.0rc4.md` | [docs/release/0.1.0rc4/notes-0.1.0rc4.md](0.1.0rc4/notes-0.1.0rc4.md) |
| `docs/release/notes-review-candidate-2026-10-31.md` | [docs/release/reviews/notes-review-candidate-2026-10-31.md](reviews/notes-review-candidate-2026-10-31.md) |
| `docs/release/notes-v0.1.md` | [docs/release/reviews/notes-v0.1.md](reviews/notes-v0.1.md) |
| `docs/release/phase3-closeout-2026-10-28.md` | [docs/release/reviews/phase3-closeout-2026-10-28.md](reviews/phase3-closeout-2026-10-28.md) |
| `docs/release/proton-restore-2026-11-16.json` | [docs/release/reviews/proton-restore-2026-11-16.json](reviews/proton-restore-2026-11-16.json) |
| `docs/release/publication-0.1.0rc2.json` | [docs/release/0.1.0rc2/publication-0.1.0rc2.json](0.1.0rc2/publication-0.1.0rc2.json) |
| `docs/release/publication-0.1.0rc2.md` | [docs/release/0.1.0rc2/publication-0.1.0rc2.md](0.1.0rc2/publication-0.1.0rc2.md) |
| `docs/release/publication-0.1.0rc3.json` | [docs/release/0.1.0rc3/publication-0.1.0rc3.json](0.1.0rc3/publication-0.1.0rc3.json) |
| `docs/release/publication-0.1.0rc3.md` | [docs/release/0.1.0rc3/publication-0.1.0rc3.md](0.1.0rc3/publication-0.1.0rc3.md) |
| `docs/release/reboot-2026-11-16.json` | [docs/release/reviews/reboot-2026-11-16.json](reviews/reboot-2026-11-16.json) |
| `docs/release/reboot-2026-11-16.md` | [docs/release/reviews/reboot-2026-11-16.md](reviews/reboot-2026-11-16.md) |
| `docs/release/release-manifest-0.1.0rc2.json` | [docs/release/0.1.0rc2/release-manifest-0.1.0rc2.json](0.1.0rc2/release-manifest-0.1.0rc2.json) |
| `docs/release/repository-files.json` | [docs/release/reviews/repository-files.json](reviews/repository-files.json) |
| `docs/release/repository-review.md` | [docs/release/reviews/repository-review.md](reviews/repository-review.md) |
| `docs/release/research-demo-closeout.md` | [docs/release/reviews/research-demo-closeout.md](reviews/research-demo-closeout.md) |
| `docs/release/runtime-review-0.1.0rc2.json` | [docs/release/0.1.0rc2/runtime-review-0.1.0rc2.json](0.1.0rc2/runtime-review-0.1.0rc2.json) |
| `docs/release/session3-validation.md` | [docs/release/reviews/session3-validation.md](reviews/session3-validation.md) |
| `docs/release/streaming-validation.md` | [docs/release/reviews/streaming-validation.md](reviews/streaming-validation.md) |
| `docs/release/team-a-advisories.json` | [docs/release/reviews/team-a-advisories.json](reviews/team-a-advisories.json) |
| `docs/release/team-a-remediation.md` | [docs/release/reviews/team-a-remediation.md](reviews/team-a-remediation.md) |
| `docs/release/transactions-2026-11-16.json` | [docs/release/reviews/transactions-2026-11-16.json](reviews/transactions-2026-11-16.json) |
| `docs/release/two-host-2026-11-11.json` | [docs/release/reviews/two-host-2026-11-11.json](reviews/two-host-2026-11-11.json) |
| `docs/release/two-host-proxy.example.json` | [docs/release/reviews/two-host-proxy.example.json](reviews/two-host-proxy.example.json) |
| `docs/release/two-host-rehearsal.md` | [docs/release/reviews/two-host-rehearsal.md](reviews/two-host-rehearsal.md) |
| `docs/release/usb-interruption-2026-11-16.json` | [docs/release/reviews/usb-interruption-2026-11-16.json](reviews/usb-interruption-2026-11-16.json) |
| `docs/release/usb-interruption-2026-11-16.md` | [docs/release/reviews/usb-interruption-2026-11-16.md](reviews/usb-interruption-2026-11-16.md) |
| `docs/release/verification-review.md` | [docs/release/reviews/verification-review.md](reviews/verification-review.md) |
| `docs/release/workflow-review-2026-11-10.md` | [docs/release/reviews/workflow-review-2026-11-10.md](reviews/workflow-review-2026-11-10.md) |
| `docs/storage-migrations.md` | [docs/reference/storage-migrations.md](../reference/storage-migrations.md) |
| `docs/synthetic-transactions.md` | [docs/guide/synthetic-transactions.md](../guide/synthetic-transactions.md) |
| `docs/verification.md` | [docs/guide/verification.md](../guide/verification.md) |
| `docs/verifier-api.md` | [docs/reference/verifier-api.md](../reference/verifier-api.md) |
| `docs/witness-server.md` | [docs/operations/witness-server.md](../operations/witness-server.md) |
| `docs/writer-recovery.md` | [docs/operations/writer-recovery.md](../operations/writer-recovery.md) |
