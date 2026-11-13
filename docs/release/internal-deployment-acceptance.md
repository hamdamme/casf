# Internal deployment acceptance

The intended first deployment is internal use with real audit records. The Linux
laptop is dedicated to synthetic testing. Real records are not acceptance fixtures.
No release or production rollout is authorized by this plan.

## Work packages

| Session | Task | Acceptance | Status |
| --- | --- | --- | --- |
| 16 | P01 | Cross-host TLS, recovery, authentication, limits and supervised process restart | 22 checks passed; accepted in PR 59 |
| 16 | P02 | Services start after machine reboot without interactive login; preserved history verifies | Deferred by operator |
| 17 | P03 | Physical power-loss and filesystem recovery on identified disposable hardware | Deferred by operator; procedure only |
| 18 | P04 | Independent security assessment with source hashes and resolved findings | Review brief prepared; independent reviewer required |
| 19 | P05 | Administrative separation, retained-state distribution and restore drills | Existing rollback/backup drills rerun; administrative custody still required |
| 19 | P06 | Internal access, provenance, backup, retention, capacity and incident acceptance | Operations worksheet prepared; operator decisions and evidence required |
| 20 | P07 | Expanded generated state-machine and coverage-guided fuzz campaigns | Accepted in PR 61; generated sequences and guided campaigns validated |
| 21 | P08 | Fresh version and artifact provenance, advisories and approved publication | Publication requires separate approval |

These eight tasks extend the accepted 33-task experimental plan. A passing
rehearsal does not close the independent assessment or hardware gates. Canonical
H1 remains unchanged: WITNESS_AHEAD is INCONCLUSIVE without retained conflicting
state; retained conflict is WITNESS_STATE_CONFLICT. No protocol redesign is proposed.

## Reboot acceptance

Deferred at the operator's request. Do not enable lingering or reboot as part of
the current work. The following procedure is retained for later acceptance.

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

## Recovery sequence validation

The generated model in `tests/property/test_recovery_sequences.py` exercises
append/idempotency, checkpoint creation, witness acceptance without recording the
reply, repeated acceptance, rejected forged receipts, receipt retrieval, writer
and witness reopening, and backup inspection. Each transition checks canonical
record/outbox bytes and the witness head against independently tracked model
values. It uses real SQLite and signing operations with synthetic keys.

Targeted command:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/property/test_recovery_sequences.py tests/unit/test_recovery_drills.py -q --hypothesis-show-statistics
```

Result: 9 passed in 5.68 seconds on macOS arm64/Python 3.12.14. Hypothesis
reported 40 passing generated examples; configured maximum length is 30 steps,
not an executed-step count. Existing backup drills retain the external state
during corrupted backup, simultaneous writer/witness rollback, missing record,
lost signing key, full storage and uncertain submission scenarios.

An initial test-helper mistake tried to register the same manifest again during
a witness restart; reopening the existing store without registration corrected
the harness. A restricted execution attempt could not bind a loopback socket;
the successful run allowed the existing local HTTP fixture. Neither was counted
as a passing run or reported as a confirmed runtime defect. Runtime source is
unchanged. Coverage-guided fuzzing and operational custody remain separate work.

A separate reproducible run with `--hypothesis-seed=20261111` passed in
4.64 seconds. PR 59's preceding revision `c53e9c27cab84611b2fa7a0ef606a2860c111cc3`
passed all 12 Linux/macOS Python 3.12–3.14 locked/minimum jobs in
[run 43144281252](https://github.com/hamdamme/casf/actions/runs/43144281252).
That run predates the generated test and does not validate the later revision.

Final local suite: `PYTHONPATH=src .venv/bin/python -m pytest -q` —
1,412 passed in 102.08 seconds. Ruff, strict mypy and repository/link validation
also passed. No runtime source or dependency changes were made.

## Guided parser campaign

PR 60 merged at `aadcc190897ddfe884e97bc21c6a3a2795fe9430` after all 12 CI
jobs passed. The next test-only change adds feedback-guided mutation using
Python line-to-line execution edges in CASF modules. Newly reached edges retain
inputs for future mutation. Native code, other threads, and stateful protocol
operations are not instrumented; this complements the generated recovery model.

The [recorded synthetic campaign](guided-fuzz-2026-11-12.json) on macOS arm64/Python 3.12.14 completed 20,025 inputs
(seed 20261112): 25 corpus cases and 20,000 mutations, 175 observed Python edges,
11 novel-path mutations and 36 retained inputs. No unexpected exception or
round-trip failure was found. Edge counts describe this run, not a coverage
percentage or a security guarantee. Existing documented parser rejections are
expected results.

```sh
PYTHONPATH=src .venv/bin/python -m tests.fuzz --guided --seed 20261112 --cases 20000 --failures /tmp/casf-guided-failures
```

Inputs remain capped at 131,072 bytes, the retained pool at 256 entries, and the
campaign at its case/time budget. Deadline exhaustion reports INCOMPLETE, never
PASS. A deadline is checked between calls; the CI job timeout provides an outer
process bound. Unexpected failures use the existing minimized replay artifact
format and `python -m tests.fuzz --replay PATH`. Only synthetic corpus inputs
are appropriate. Run without Python optimization so assertion oracles remain
active. Fixed-seed reproduction requires the same code and Python version.

Locked CI jobs run 2,025 guided inputs each, alongside the existing deterministic
campaigns. The package has no new dependency and runtime behavior is unchanged.

## Review and operations handoff

Use the [independent review brief](independent-review-brief.md) for P04 and the
[internal operations worksheet](internal-operations-worksheet.md) for P05/P06.
These documents specify the source baseline, questions and acceptance evidence.
They do not assign an external reviewer or claim an operational deployment.
