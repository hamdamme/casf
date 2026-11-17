# CASF 0.1.0rc3 — experimental release notes

Published experimental prerelease for synthetic research and evaluation. See the
[publication closeout](publication-0.1.0rc3.md). This is not
production deployment approval. The [candidate record](candidate-0.1.0rc3-c38bf82.md)
identifies the exact build revision, hashes and executed checks.

## Changes since 0.1.0rc2

- Harden direct verifier policies and online-mode validation; reject invalid
  Boolean policies, modes, timeouts and unsupported base-URL components.
- Preserve distinct permanent, schema, trust and temporary witness failures.
  Reject unsupported status values before database writes.
- Prevent malformed bearer credentials and peer-controlled diagnostics from
  leaking through rendered exception chains.
- Refuse backup/migration destinations with existing SQLite sidecars, including
  the tested publication races, without deleting existing evidence.
- Include the merged private-key, input-bound, status-race, epoch-authentication,
  Unicode transport and socket-cleanup corrections from the scoped file review.
- Add generated recovery sequences and bounded Python-line-edge-guided parser
  campaigns alongside existing deterministic and process-crash tests.
- Include the Python synthetic transaction example in the source archive and
  record accepted reboot, USB interruption, Proton restore and permissions evidence.

No wire-profile, cryptographic-domain or evidence-format change is introduced by
this candidate preparation. Existing `casf-v1` rules and explicit storage-migration
requirements remain in effect. The [changelog](../../CHANGELOG.md) has further detail.

## Use and support

Use disposable test keys, synthetic records and isolated state. The Python examples
are scripts supplied with the source archive, not new installed CLI subcommands.
Follow the [demo rules](research-demo-closeout.md), [installation guide](../installation.md)
and [security reporting policy](../../SECURITY.md). No PyPI upload is planned here;
GitHub publication requires separate explicit approval. Published rc2 files remain
unchanged and do not contain these later fixes.

## Unfinished acceptance outside the demo

Canonical H1's primary expectation remains unmet: without retained conflicting
state, WITNESS_AHEAD is INCONCLUSIVE, not the predeclared FAIL. Retained conflicting
checkpoints produce WITNESS_STATE_CONFLICT. Neither the wording nor protocol is
changed to hide that result.

Synthetic tests do not establish production provisioning, independent administration,
real-event provenance or physical power-loss durability. P03 whole-machine power-loss testing is pending future validation; P04
independent security review is pending independent evaluation. Both remain
incomplete and relevant to future production-readiness evaluation, but neither
blocks publication of this experimental research release.
[Production gates](production-readiness-gates.md) and [native-component advisory scope](dependency-review-0.1.0rc3.md)
remain separate. Passing the recorded assertions does not establish absence of all defects.
