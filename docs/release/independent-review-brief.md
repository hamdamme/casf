# Independent security review brief

Status: prepared for reviewer selection; no independent assessment has been
performed or commissioned by this document. No external outreach is authorized.
The intended deployment is internal business-transaction audit records; validation data
must remain synthetic until deployment acceptance is approved.

## Exact review subject

Repository: [hamdamme/casf](https://github.com/hamdamme/casf).
Pinned baseline: `c263d6e0ca8ec29e2edd6cbc6c593ae087fe9021` (PR 61 merge).
Runtime `src/` bytes are unchanged from the PR 58 merge
`cb3febff53a7cf8274a4b871f5be1382ebaedd33`; later commits added validation and
documentation. The current package metadata still says `0.1.0rc2`, but published
rc2 assets were built from `e92194fe0fa6eb37c2ff9016c381b8e734008880` and omit
later fixes. Review the pinned source, not an unqualified package version.

Create a separate checkout, preserving full history for historical-data tests:

```sh
git clone https://github.com/hamdamme/casf.git casf-independent-review
cd casf-independent-review
git checkout --detach c263d6e0ca8ec29e2edd6cbc6c593ae087fe9021
git rev-parse HEAD
git status --porcelain
```

Record both outputs before installing dependencies. Use the pinned lock/tooling
instructions in [dependencies](../dependencies.md) and the
[validation matrix](validation-matrix.md). Record actual import locations and
runtime versions. If reviewing another revision, identify its hash and examine
the intervening diff; do not silently carry findings across revisions.

## Required inputs and evidence

Read [DEVELOPMENT.md](../../DEVELOPMENT.md), the
[specification](../specification/CASF_SPEC_001.md),
[ADRs](../adr/), and [current reference](../current-reference.md).
The [requirement map](requirement-evidence.md) identifies assertions, not a claim
that every behavior was reviewed. Preserve the
[Team A remediation](team-a-remediation.md),
[line-review corrections](line-review-2026-11-11.md),
[cross-host record](two-host-rehearsal.md), and
[guided campaign](guided-fuzz-2026-11-12.json) as prior evidence.

PR 60's generated recovery sequences passed the
[12-job matrix](https://github.com/hamdamme/casf/actions/runs/43151328225).
PR 61's guided parser work passed the
[12-job matrix](https://github.com/hamdamme/casf/actions/runs/43343122455),
1,421 local tests, and a 20,025-input local campaign. These are maintainer
validation results; independently reproduce relevant claims. Download CI
artifacts before their 14-day retention expires if they are needed for review.

## Review questions

| Area | Entry points | Required negative evidence |
| --- | --- | --- |
| Canonical bytes and domains | `src/casf/canonical/`, `src/casf/crypto/`, conformance vectors | Ambiguous encodings, wrong domains, altered signed fields and boundary inputs cannot authenticate. |
| Key lifecycle and filesystem | `src/casf/keys.py`, `src/casf/filesystem.py`, lifecycle and administration | Wrong keys, symlinks, permissions, interrupted publication and missing credentials fail safely without disclosure. |
| Trust and revocation | `src/casf/trust/`, writer startup, verifier | Evidence cannot supply its own authority; stale status and rollback cannot clear independently retained revocation/high-water state. |
| Epoch and witness binding | `src/casf/witness/`, lifecycle, verifier anchor | Authenticated predecessor required; cross-log receipts, conflicting checkpoints and duplicate retries preserve binding and durable state. |
| Writer and recovery | `src/casf/writer/`, `src/casf/storage/`, bundle | Commit uncertainty, stale backups, storage failures and lost replies cannot silently authorize conflicting history. |
| Network boundary | transport, online client, witness HTTP/protocol/server | Certificate/hostname authentication, time/body/concurrency bounds, malformed responses, permanent rejection categories and token redaction. |
| Public API and reporting | CLI, typed APIs, verifier/report | Invalid policy types fail closed; trust, anchoring, freshness and completeness remain distinct; failure precedence matches the specification. |
| Packaging and claims | workflows, lockfile, release/research records | Tested imports match identified artifacts; published-version and research claims match actual evidence. |

The reviewer chooses additional adversarial methods and records what was and
was not examined. Native crypto libraries and host patches need their own
version/advisory assessment. No invented cryptographic or protocol changes:
questions affecting bytes, domains, trust or failure semantics require an ADR.

## Finding and acceptance record

For every finding retain: identifier, severity/rationale, examined revision,
affected API/path, synthetic reproduction, expected versus observed outcome,
impact assumptions, failing regression, fix revision, retest result and reviewer
disposition. Keep reproducible failures even if existing tests pass. Use the
[private disclosure process](../../SECURITY.md) for sensitive findings; do not
place real records, credentials or keys in public issues or patches.

Close P04 only when an identified independent reviewer supplies a signed or
otherwise attributable report with scope, source hashes, methods, findings and
unresolved items, and the maintainer records resolution or explicit disposition
of each finding. The operator has no reviewer selected and requested a handoff package. Reviewer
identity, engagement scope, timing and report location remain **unassigned**. A prepared brief or a green CI run does not close P04.

## Deployment questions that remain open

Reboot and physical power-loss validation are deferred. The two-host rehearsal
used one administrator; it does not establish administrative independence.
The [operating worksheet](internal-operations-worksheet.md) still needs real
owners and acceptance evidence. Canonical H1 retains its unmet primary result:
without retained conflicting evidence WITNESS_AHEAD is INCONCLUSIVE, not the
predeclared FAIL. Changed semantics require separate protocol review.
