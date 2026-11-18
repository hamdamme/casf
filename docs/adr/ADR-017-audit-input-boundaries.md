# Audit input boundaries and compatible storage validation

CASF-C01–C06 refine validation and diagnostics without changing signed bytes,
cryptographic domains, evidence precedence or database schema version 1.

- Timestamps use ASCII digits and a full-string match, implementing SPEC §11.
  Previously accepted Unicode-digit encodings are invalid protocol inputs.
- Storage opening and legacy migration independently require finite retry and
  checkpoint scheduling values. SQLite 3.42 can round the existing maximum
  float SQL literal to infinity; Python checks do not depend on that expression.
  Preserve the schema and valid finite values rather than narrowing the range
  or refusing an otherwise compatible SQLite version. Invalid stored values
  raise CasfError before migration publication; the source remains unchanged.
- Extend ADR-016's status mapping to latest-view queries, intervening receipt
  lookup and pending-receipt recovery. HTTP 404 with NO_CHECKPOINT remains the
  latest endpoint's explicit no-checkpoint result. Receipt lookup 404 remains
  inconclusive. Error bodies never override 401/403 or 429/503 categories.
- CLI authority pins must decode to 32 bytes and match their issuer key IDs.
  Invalid configuration raises SchemaError before evidence verification.
- CLI trust files must be regular files owned by the current user or root and
  not group/world writable. The immediate containing directory follows the same
  ownership/write policy. Open both without following final-component symlinks,
  validate descriptors, and read through the checked file descriptor. Public
  readability is allowed. Trust input from stdin is unsupported. Administrators
  must keep ancestor directories under trusted control; this is not a filesystem
  sandbox or protection against a compromised account/root.
- Validate a supplied witness URL when creating trust pins. Empty URLs remain
  allowed for offline modes; online creation requires an origin. Accepted URLs
  follow the existing transport policy, with no prefix-routing support.

These changes do not close production provisioning or independent-review gates.
The published rc3 artifacts remain unchanged; remediation requires a later release.
