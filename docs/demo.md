# Verified synthetic workflow

This runnable example exercises the current CLI and a real loopback HTTP
witness. It uses fresh synthetic keys and a generated text document. It does
not read personal files or reproduce the separate historical private PDF demo.
No cloud account or Linux server is needed.

## Run from a source checkout

Complete the locked [developer setup](dependencies.md), including the witness
extra. From the repository root, using Python 3.12–3.14:

```bash
CASF_DEMO_ROOT="$(mktemp -d)"
PYTHONPATH=src .venv/bin/python -m examples.verified_workflow "$CASF_DEMO_ROOT/public"
```

The output ends with `Completed 21 checks`. A nonzero exit means the workflow
did not complete; an incomplete summary retains the steps reached. Every run
requires a new output directory. Existing output is never overwritten.

The [example](../examples/verified_workflow.py) calls the public CLI entry point
for its commands and the witness server API to start a temporary service.
The full test suite runs the same example against both source and installed
package configurations. Examples are checkout material, not an installed CLI
subcommand or an approved release artifact.

## What it checks

| Stage | Expected behavior |
| --- | --- |
| Provisioning | Create encrypted keys, signed manifest, active status and explicit trust pins; register the witness |
| Initialization | Verify startup and witness the empty checkpoint before signing records |
| Append and retry | Record the synthetic document fingerprint; an identical event retry leaves exactly one record |
| Worker | A one-shot foreground tick submits the pending work and reports one committed and witnessed record |
| Export and verify | Export without the private signing key; integrity, anchored and online verification all pass |
| Tampering | A modified record fails; the verifier's retained state remains unchanged |
| Backup and restore | Inspect a SQLite backup; authenticate an exported bundle against a retained signed checkpoint/receipt pair |
| Promotion and seal | Reopen the restored writer through verified startup, seal it and obtain its final receipt |
| Offline witness | After stopping the service, online verification returns INCONCLUSIVE and exit 4 |

The output directory contains only the synthetic text document, the initial
public evidence bundle, public trust configuration and `summary.json`.
The summary includes separate verification dimensions and diagnostics; a
`PASS` with `STATUS_CURRENTNESS_UNCONFIRMED` does not prove the supplied
authority statement is globally current. The exported bundle precedes the
restore/seal exercise; the final seal is reported in the summary, not silently
substituted into that bundle.

Keys, writer/witness databases, backup, tampered copy and retained state live
in a temporary owner-only directory and are removed when the example finishes.
The randomly generated demo credentials are restored out of the process
environment afterward. Never use this disposable-state behavior for real logs.

## Verify the public output again

The demo witness has stopped, so use offline verification. This creates a
separate, explicit first observation of synthetic evidence:

```bash
mkdir -m 700 "$CASF_DEMO_ROOT/verifier-state"
PYTHONPATH=src .venv/bin/casf verify "$CASF_DEMO_ROOT/public/bundle" \
  --trust "$CASF_DEMO_ROOT/public/trust.json" \
  --state "$CASF_DEMO_ROOT/verifier-state/state.json" \
  --initialize-state --mode anchored --json
```

For another check, reuse that state and omit `--initialize-state`. Its trust
file's loopback address belonged to the now-stopped demonstration service;
do not reuse the address for another service or treat it as a deployed witness.

## Boundaries

The document fingerprint is an application-supplied claim. The example compares
it with the generated file separately; ordinary CASF bundle verification does
not open external files or establish that a claimed real event occurred.
The demo uses one host and one owner, without TLS or independent witness
administration. HTTPS, protected provisioning, supervisor operation, separate
hosts and deployment recovery belong to a later server evaluation.

This is a functional rehearsal, not a performance study, physical power-loss
test, independent security audit, or release approval. For real operation use
the [administration](administration.md), [worker](checkpoint-worker.md) and
[recovery](recovery-drills.md) guides with independently retained state.
