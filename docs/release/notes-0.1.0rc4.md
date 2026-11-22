# CASF 0.1.0rc4 — experimental candidate

Unpublished. Prepared for research and evaluation with synthetic records and
disposable keys. The [replacement candidate](candidate-0.1.0rc4-3333d00.md) is
built from merge `3333d00` and includes every correction below. Exact-file
installation checks and post-merge CI passed; artifact review and separate
publication approval remain pending.

## Fixes since rc3

- Reserve new SQLite databases with mode `600`; check existing database,
  sidecar and directory permissions without disturbing SQLite locks.
- Enforce canonical JSONL bytes during bundle import, verification and restore;
  formatting-only variants now fail as malformed input (CLI exit `2`).
- C01: require ASCII digits and an exact match for protocol timestamps.
- C02: reject nonfinite stored scheduling times on open and migration, including
  SQLite versions whose SQL float boundary accepts infinity.
- C03: apply consistent witness HTTP error categories to latest-view and receipt
  lookup/recovery calls; preserve pending evidence on failures.
- C04: validate authority public-key length and identifier when loading trust pins.
- C05: reject unsafe trust-file ownership, writable permissions, symlinks and
  nonregular files; read through checked file descriptors.
- C06: reject unsupported witness origins when creating trust configuration.
- C03 follow-up: malformed, empty and unrecognized latest-view HTTP 404 bodies
  produce an operational response error (exit 5). Explicit `NO_CHECKPOINT`
  remains inconclusive; receipt-lookup absence retains its existing policy.
- D01: reject extended macOS ACLs and ACL inspection failures on sensitive files
  and directories, including newly created key and retained-state files.
- D02: reject malformed loaded/effective witness origins, including whitespace,
  control characters and invalid hostnames, as configuration errors (exit 2)
  before secrets, transport callbacks or persistent state creation.
- D03: unsigned HTTP 409 responses on reads produce an operational response
  error (exit 5); submission conflicts retain their existing classification.

[PR 78](https://github.com/hamdamme/casf/pull/78) and the
[remediation record](advisory-remediation-2026-11-17.md) identify the reproductions,
regressions, decisions and executed validation. The
[follow-up record](advisory-followup-2026-11-21.md) covers the later corrections
merged at `d4721c4`. Credit: @adzguy. No new independent signoff is claimed.

## Compatibility and upgrade

Valid casf-v1 bytes, cryptographic domains and database schemas are unchanged.
Non-ASCII timestamps previously accepted contrary to the specified format are
now rejected; do not rewrite signed evidence to make it pass. Trust files must
be regular files owned by the current user or root, with neither file nor its
immediate directory writable by group/others. Ancestor directories still require
trusted administration. On macOS, sensitive paths must have no extended ACL
entries, even restrictive ones; inspection errors fail closed. Provision
compatible paths explicitly rather than silently removing ACLs. Supported HTTPS,
IDNA, trailing DNS dots, valid ports and IP literals retain compatibility.
Invalid authority pins and witness origins now fail at
configuration boundaries. Read failures follow the documented HTTP categories.
See [administration](../administration.md) and [storage migration](../storage-migrations.md).

Existing readable SQLite files need an owner-only parent directory or explicit
permission remediation while services are stopped. CASF never changes their
permissions automatically. Standard canonical bundles remain valid; reformatted
bundles that previously passed are rejected. See the
[verification compatibility policy](../verification.md#public-verification-api).

Published rc2 and rc3 remain affected and unchanged. This candidate is not yet a
published safe-update option. No PyPI upload or production deployment is planned.
The rc3 Zenodo DOI continues to identify rc3, not this candidate.

## Release boundary

Record the final follow-up review disposition and resolve any reproducible release
blockers, then approve the exact revision, files and checksums. If packaged inputs change,
rebuild and validate the replacement candidate before approval. After approved
GitHub publication, verify public downloads and installation, then create a new
version of the existing Zenodo software record and verify its file and citation.
Do not replace rc2/rc3 assets or the existing Zenodo archive.

This closes the experimental release work, not production acceptance. P03
whole-machine power-loss testing is pending future validation; P04 independent
security review is pending independent evaluation. A scoped follow-up review does
not close P04. P05/P06 remain partial. Canonical H1's primary expectation remains
unmet: WITNESS_AHEAD without retained conflicting state is INCONCLUSIVE, not the
predeclared FAIL. Historical research and deployment evidence retain their revisions.
