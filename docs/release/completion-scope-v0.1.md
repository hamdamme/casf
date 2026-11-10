# Experimental v0.1 completion scope

The maintainer selected an experimental v0.1 release for research and evaluation
and authorized implementation on 9 November 2026. The next review candidate is
planned as 0.1.0rc2 because the old 0.1.0rc1 artifact approval does not cover new
source changes. Version metadata will change during final candidate preparation;
no artifact or publication is approved by this scope record.

## Release boundary

The release includes the Python library and CLI, SQLite writer, reference
witness, evidence export and verification, key lifecycle functions, synthetic
demonstrations, and reproducibility documentation. Python 3.12, 3.13 and 3.14
remain the validation targets on Ubuntu CI. Local macOS validation is recorded
separately. Windows and production deployment readiness are not claimed.
Support remains best effort for an experimental project, with the existing
private reporting channel and clearly documented limitations.

Preserve casf-v1 authenticated bytes, domain separation, trust assumptions,
result semantics, frozen vectors and historical research records. New results
must use new output locations. No additional cryptographic algorithm, cloud
service, dashboard, or real-data deployment is in this completion scope.

## Requirement decisions for the first implementation batch

Implement the already specified local startup verification and restore
preservation requirements. Compare local metadata with cryptographically
verified records and signed checkpoint/receipt chains. Preserve final seals,
accepted receipts, checkpoint indices and supplied pending bytes during restore.
Reject malformed evidence, mismatching prefixes and wrong signing keys. Keep
record/journal restoration atomic. Tests must first demonstrate missing behavior.

Independent authority provisioning, authenticated external anchors, fresh
witness reconciliation and automatic scheduling remain mandatory follow-up
work where required by the agreed release contract. Local consistency must not
be described as establishing authority trust or freshness. No trust rule is
waived by this batch. A change to a normative trust or recovery rule requires
its own architecture decision and review before dependent implementation.

## Audit findings and acceptance mapping

| Finding | Completion tasks | Required evidence |
|---|---|---|
| A01 Restore loses seals and evidence | F07–F08 | Signed journal preservation; final seals cannot reopen; continuation accepted by original witness; malformed evidence rejected; atomic interruption tests. |
| A02 Partial startup checks | F05–F06 | Corrupt bodies/signatures/indexes/journals rejected; key bindings checked; correct concurrent snapshot behavior; independent trust and external-state boundary documented and completed separately. |
| A03 Scheduling, storage and API differences | F09–F12 | Outage/restart tests; reviewed schema/migrations; executable API and report contracts. |
| A04 Missing property/fuzz coverage | F13–F16 | Actual generated-input and fuzz cases, process failures and full supported matrix. Empty directories do not count. |
| A05 Obsolete alternate runner | F19 | Remove the unused shim; pytest remains the single maintained runner and all tests still pass. |
| A06 Historical/current documentation | F18–F20 | Reconcile PR 29, executable instructions and current status; preserve dated records and measurements. |
| A07 Stale installed local package | F21–F22 | Verify actual import path; locked environment and clean installed candidate tests; never confuse installed old code with the checked-out source. |
| A08 Presentation and handoff | F19, F24, F27 | Runnable demonstration, navigable documentation, release metadata and maintenance instructions. |

All required gates must pass or remain explicitly incomplete. Writing a
limitation does not by itself satisfy a mandatory implementation requirement.
Passing local tests does not substitute for the full release matrix, maintainer
review, final artifact hashes, or publication approval.

## Delivery and review

Use isolated changes for review and retain the clean Desktop main checkout.
PR 29 is a separate open documentation change based on the audited source;
reconcile its current-reference statements with subsequent code changes before
combining them. The maintainer reviews changes before merge. Prepare the exact
release packages, notes and hashes before requesting separate publication
approval. No release or deployment is authorized by "start fixing" alone.
