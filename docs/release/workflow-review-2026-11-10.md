# Workflow and critical-change review

Reviewed 10 November 2026, starting from PR 51's merge
`6441e4569e8c420f5e8a71e55950af88ce46f336`. This is a scoped implementation and
documentation review for the experimental candidate, not an independent security
audit or a claim of exhaustive specification conformance. The review covers
the accepted startup, recovery, worker, storage and public evidence changes,
plus active instructions and their executable demonstration.

## Findings and disposition

| Finding | Resolution and evidence |
| --- | --- |
| No complete current synthetic workflow linked from the entry documentation | Added the [21-check demo](../demo.md), using the public CLI entry point and an actual temporary loopback witness. It checks verified initialization, idempotent append, worker submission, three verification modes, tamper rejection, backup, authenticated restore and final sealing. |
| Source commands could use a stale installed package or depend on editable import hooks | Active development commands now select `PYTHONPATH=src` with the named environment; locked setup uses a non-editable installation. Candidate-wheel commands remain distinct. |
| Bare CLI commands did not explain environment activation | Installation now activates the checked wheel environment and explains the source-command alternative. Key provisioning uses a protected input prompt instead of a literal placeholder passphrase. |
| Legacy remote benchmark discarded URL scheme and other components | Six regressions demonstrated unsupported URLs reaching the plain HTTP submitter. The runner now rejects HTTPS/other schemes, credentials, path prefixes, queries and fragments before constructing it. No external request was made to reproduce the issue. HTTPS support for that research runner remains future work. |
| Linux/cloud run sheets reused historical paths and fixed obsolete test counts | Replaced active instructions with a revision-specific reproduction procedure and a deferred remote evaluation plan. Original run sheets remain linked at the reviewed merge revision. Historical outputs and frozen manifests are unchanged. |
| Worker guide implied missing schema tables were created on opening | Corrected it to require explicit migration of unversioned stores; a damaged version 1 schema is rejected. |
| Obsolete alternate test runner listed in the original audit | Confirmed `tests/_runner.py` was already removed in `b1a5fdf0502f6c1b45fd624edbe0c2b73552f99a`. Pytest remains the maintained runner; no duplicate removal was needed. |

The URL finding concerns `benchmarks/runner.py`. The runtime transport in
`src/casf/transport.py` has a separate HTTPS path using a validating SSL context;
it is unchanged by this review. The benchmark fix rejects unsupported transport
rather than pretending to provide TLS. Plain HTTP remains a research option
for an explicitly protected network path, not a public deployment recommendation.

## Critical paths examined

| Area | Reviewed invariant | Regression evidence rerun in the complete suite |
| --- | --- | --- |
| Startup and independent state | Durable write hold before authorization; signed active status at retained serial; revocation and checkpoint history cannot be rolled back; persist external evidence before resuming | [Verified startup](../../tests/unit/test_verified_startup.py), [writer trust](../../tests/unit/test_writer_trust.py), [CLI startup](../../tests/unit/test_cli_verified_startup.py) |
| Witness reconciliation | Fresh signed view, bounded backward journal traversal, matching pending bytes, transactional journal application, terminal record-loss seal | [Reconciliation](../../tests/unit/test_writer_reconciliation.py), [recovery drills](../../tests/unit/test_recovery_drills.py), [process recovery](../../tests/process/test_submission_crashes.py) |
| Restore and export | New destinations; authenticate records and journals; preserve final seals; keyless default restored handle; snapshot/prefix export and exclusive publication | [Integrity and restore](../../tests/unit/test_writer_integrity_recovery.py), [backup failures](../../tests/unit/test_backup_failures.py), [export tests](../../tests/unit/test_export_contract.py) |
| Worker | Verified authorization, consistent lock order, one pending checkpoint, persisted retry deadlines, same-byte retry and explicit pending reports | [Worker](../../tests/unit/test_checkpoint_worker.py), [CLI worker](../../tests/unit/test_cli_checkpoint_worker.py), [submission retries](../../tests/unit/test_submission_retry.py) |
| Storage | Exact schema/version identity, integrity/foreign-key checks, atomic initialization and explicit copy migration | [Storage migrations](../../tests/unit/test_storage_migrations.py) |
| Public verification | Explicit pinned anchor, owned evidence, bounded input, complete stream consumption before accepting a checkpoint, independent status observations | [Bundle verification](../../tests/unit/test_verify_bundle.py), [incremental verification](../../tests/unit/test_incremental_verification.py), [report semantics](../../tests/unit/test_report_semantics.py) |

The source review concentrated on `writer/startup.py`, `writer/recovery.py`,
restore/export in `writer/__init__.py`, `writer/worker.py`, `trust/state.py`,
`storage/versioning.py`, `verifier/anchor.py`, `verifier/bundle.py`, CLI
verification completion and filesystem publication. Existing generated and
process tests supplement these inspected paths. This does not represent
line-by-line review of every file, novel cryptographic analysis or exhaustive
concurrent execution analysis. No unresolved release blocker was identified
within this reviewed experimental scope after the fixes above.

## Executed checks

- Full local suite: **1199 passed** on macOS arm64, Python 3.12.11. Six
  traceability checks also passed after the evidence map update.
- Ruff across source, tests, benchmarks and examples; strict typing of the
  38 runtime source files; unchanged dependency lock check: passed.
- Both demo tests passed, covering the complete workflow, restoration of prior
  credential environment values, public-only outputs and overwrite refusal.
- The documented demo plus first/repeated anchored CLI verification ran from
  clean commit `d1d77bca648fdff168469ff4d8ef1c506a0b80ad`. The source inventory
  verified all 39 package files. The first observation initialized retained
  state; the repeated check passed without reinitialization. Both retained the
  status-currentness diagnostic rather than claiming globally current status.
- The first development rehearsal exposed an unsupported context-manager use
  in the new example; it was corrected to close the writer explicitly before
  the successful committed rehearsal. Failed output was retained separately.
- All 260 files under the protected research/results, historical manuals and
  original technical-document paths were compared with the reviewed baseline
  and remained unchanged. The active run sheets changed; their original text
  remains in Git history.

The proposed PR must pass all twelve supported CI configurations. CI results
identify that PR's exact head and tested merge revision; the recorded local
rehearsal is not a claim that later documentation commits were its source.

## Deferred and separate acceptance

The maintainer deferred the additional Linux machine and cloud witness
evaluation. Routine Ubuntu CI continues. No cloud resources, new Linux/WAN
measurements or public service were created. The research runner still needs
tested HTTPS support or an explicitly measured protected tunnel before a new
remote study.

The private real-document demonstration remains historical; the new example
uses synthetic text only. Independent witness administration, deployed TLS,
supervisor behavior, physical power-loss durability and deployment-specific
storage are not established by this local rehearsal. Supplied authority status
does not establish globally current revocation knowledge. H1's documented
primary expectation mismatch remains unchanged.

Final candidate version selection, exact source/wheel builds, fresh-install
acceptance, refreshed advisory/license review, publication approval and public
download verification remain open in the [completion tracker](completion-tracker.md).
No package metadata, authenticated protocol bytes or runtime implementation
changed, and no release was published by this work.
