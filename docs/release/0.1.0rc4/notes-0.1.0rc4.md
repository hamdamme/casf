# CASF 0.1.0rc4 — experimental prerelease

Published 22 November 2026 in America/Chicago (`2026-11-23T04:25:03Z`) for
research and evaluation. The [GitHub prerelease](https://github.com/hamdamme/casf/releases/tag/v0.1.0rc4)
contains the exact wheel and source distribution built from `ce6cd67`, PR 87's
merge. The [publication record](publication-0.1.0rc4.md) verifies public downloads
and fresh installations. The [build record](candidate-0.1.0rc4-ce6cd67.md) remains
the historical pre-publication evidence; its files and hashes are unchanged.

The `492f330` and earlier rc4 candidates remain superseded and must not be
substituted for this release. The [dependency review](dependency-review-0.1.0rc4-ce6cd67.md)
and publication refresh retain minimum-only build-tool findings separately from
the locked release environment. This experimental prerelease is not an
independent audit or production-readiness claim.

## Fixes since rc3

- Require at least 16 bytes for newly generated key-file passphrases while
  preserving encrypted PKCS8 PEM and legacy short-passphrase loading. Atomic
  creation, filesystem protections and no-overwrite guarantees are unchanged.
- Raise the cryptography minimum to 50.0.0; the locked version remains 50.0.2.
- Add author, keywords, Alpha/audience/Python/cryptography/typing classifiers,
  and Changelog and Security links to package metadata. Apache-2.0 is unchanged.

- Reject small-order Ed25519 public keys, including identity keys that allow
  universal signatures, and every noncanonical public-key y encoding. A real
  authority signature cannot make an unsafe embedded key acceptable. Published
  rc2 and rc3 are affected. See [ADR-018](../../adr/ADR-018-ed25519-verification-profile.md).
- Raise `ValueError` for `INTEGRITY` verification with a retained checkpoint
  but no explicit anchor; the checkpoint can no longer be silently ignored.
  The CLI reports configuration exit `2` without changing saved state; use
  anchored or online mode when a checkpoint has already been retained.
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
[remediation record](../reviews/advisory-remediation-2026-11-17.md) identify the reproductions,
regressions, decisions and executed validation. The
[follow-up record](../reviews/advisory-followup-2026-11-21.md) covers the later corrections
merged at `d4721c4`. Credit: @adzguy. No new independent signoff is claimed.

## Compatibility and upgrade

Valid casf-v1 bytes, cryptographic domains and database schemas are unchanged.
The key-passphrase and package updates also preserve signature verification
semantics and evidence formats. New key generation rejects passphrases below
16 bytes, including empty input; existing encrypted keys using shorter
passphrases still load. A byte-length minimum does not guarantee strength:
copied encrypted files permit offline guessing. Use long, randomly generated
passphrases from a password manager. See the measured PKCS8 encryption parameters
in [administration](../../operations/administration.md#create-keys-and-public-key-files).
Existing environments must satisfy the new cryptography minimum before installing
the updated package; older versions are no longer supported.
Normal generated Ed25519 keys remain compatible. Evidence depending on rejected
public keys must not be trusted or rewritten to pass; provision legitimate keys
and a newly authorized manifest. Pure Ed25519, cofactorless verification and
`S < L` remain required. The correction does not add prime-subgroup validation.
Callers using a retained checkpoint must select an appropriate anchored/online
verification mode or supply an explicit anchor in integrity mode.
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
See [administration](../../operations/administration.md) and [storage migration](../../reference/storage-migrations.md).

Existing readable SQLite files need an owner-only parent directory or explicit
permission remediation while services are stopped. CASF never changes their
permissions automatically. Standard canonical bundles remain valid; reformatted
bundles that previously passed are rejected. See the
[verification compatibility policy](../../guide/verification.md#public-verification-api).

Published rc2 and rc3 remain affected and unchanged; upgrade to rc4 after
reviewing these compatibility requirements. No PyPI upload or production
deployment was performed. The [rc4 Zenodo software archive](https://doi.org/10.5281/zenodo.24454789),
published 23 November 2026, contains `casf-0.1.0rc4.tar.gz` (149,681 bytes).
Downloads from Zenodo and GitHub were byte-identical at `2026-11-23T05:21:11Z`,
with SHA-256 `07d6d65660c515570205efabe0b3bde158d8e978042b654db5f5d1cd204cdac3`.
The existing rc3 DOI identifies only the rc3 software archive; the concept DOI
[10.5281/zenodo.24321231](https://doi.org/10.5281/zenodo.24321231) is unchanged.

## Release boundary

The approved GitHub publication, public-download installation checks and Zenodo
file/citation verification are complete. Security-advisory publication remains
Pending separate approval. If packaged inputs change, rebuild and validate the
replacement candidate before approval. Do not replace rc2/rc3 assets or their
Zenodo archives.

This closes the experimental release work, not production acceptance. P03
whole-machine power-loss testing is pending future validation; P04 independent
security review is pending independent evaluation. A scoped follow-up review does
not close P04. P05/P06 remain partial. Canonical H1's primary expectation remains
unmet: WITNESS_AHEAD without retained conflicting state is INCONCLUSIVE, not the
predeclared FAIL. Historical research and deployment evidence retain their revisions.
