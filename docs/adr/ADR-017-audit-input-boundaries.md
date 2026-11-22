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

## Follow-up decisions before rc4

- Latest-view HTTP 404 is a no-checkpoint result only when its parsed object
  contains `code=NO_CHECKPOINT`. Empty, malformed and unrecognized 404 bodies
  raise WitnessResponseError. Receipt lookup 404 remains inconclusive.
- HTTP 409 on read operations (including the POST latest-view query) is an
  unexpected response, not authenticated evidence of divergence. It raises
  WitnessResponseError. Submission 409 retains ADR-016's conflict category;
  that server assertion is not independently authenticated proof of tampering.
- Verification retains INCONCLUSIVE freshness for an unexpected read response,
  with diagnostic WITNESS_RESPONSE_ERROR. The CLI returns exit 5 while preserving
  the report. Recognized missing evidence, 429/503 and transport unavailability
  retain exit 4. Existing schema/trust precedence is unchanged. A read error
  never advances an accepted checkpoint; independently authenticated status
  observations may still be retained under the existing monotonic status policy.
- Validate nonempty witness origins when loading trust configuration. Stored
  online mode and effective online overrides require a nonempty origin. Validate
  the effective writer startup origin before loading secrets or opening the writer.
  Invalid configuration raises SchemaError (CLI exit 2). Offline empty origins
  remain supported; invalid stored origins must be corrected even with an override.
  Reject whitespace and control characters before URL parsing can strip them.
  Hosts must be IP literals or valid DNS labels after the standard library's IDNA
  conversion, with DNS label/name length limits. Preserve internationalized names,
  a trailing DNS dot, explicit ports and the existing loopback HTTP policy.
- On Darwin, sensitive files and immediate directories must have no extended ACL
  entries, including inherited or restrictive entries. Check the opened descriptor,
  reject inspection errors and preserve existing ownership/mode/link requirements.
  Administrators must review ACLs explicitly; CASF does not remove them. Apply this
  to trust inputs, encrypted keys, retained state and consumers of the shared state
  permission check, including locks and status books. Check newly created sensitive
  files before writing bytes. This conservative policy avoids implementing a second
  ACL authorization engine. Linux retains POSIX mode/mask checks.

Darwin's descriptor API reports an absent ACL as NULL/ENOENT through
[acl_get_fd_np](https://github.com/apple-oss-distributions/Libc/blob/main/posix1e/acl_file.c).
The implementation checks errno and descriptor validity; NULL by itself is not
accepted. Nonempty ACLs are rejected after validated entry inspection. The native
regressions cover plain files, explicit ACL grants, inherited ACLs and bad descriptors.
These decisions change diagnostics and local configuration acceptance, not protocol
bytes, cryptographic domains or database schemas.
