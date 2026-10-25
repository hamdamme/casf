# Verification status and resource budgets

Verification requires an authority signed status statement for the expected
manifest with a serial at least as large as the provisioned minimum. Supply
statements as `status_envelopes` to the Python verifier or as `status.jsonl`
in a bundle. Provision the initial active statement using the authority
workflow. Exporting writer records does not authorize the writer to create
an authority statement.

A missing or unrelated statement reports `STATUS_MISSING`, UNKNOWN trust,
and FAIL. The CLI returns exit code 3. Invalid signatures, issuer mismatches,
stale serials, and revocation also fail. A verified revoked statement cannot
be undone by an active statement later in the supplied list.

A signed active statement proves its signed content, not that no later
revocation exists. `STATUS_CURRENTNESS_UNCONFIRMED` records this limitation.
An online witness response does not establish current authority status.
Previously accepted bundles without status evidence must obtain an authentic
statement; do not disable trust checks to recover an overall PASS.

## Work and input limits

The Python verifier accepts positive integer `max_chain_steps` and
`max_records` arguments. Defaults are 10000 and 1000000 respectively.
Checkpoint, receipt, and status streams each have the chain budget. One
additional item may be consumed to detect excess input, but it is not
validated cryptographically. Budget exhaustion is INCONCLUSIVE unless an
existing failure already prevents acceptance. The CLI honors the trust
policy's `max_chain_steps` and returns code 4 for an inconclusive result.

Bundle reads reject symbolic links and nonregular files, use bounded object
and line reads, and share a total byte budget across all bundle members,
including status.jsonl. Defaults are 128 KiB per record line, 32 KiB per
protocol envelope, 1000000 records, 100000 objects per evidence file, and
256 MiB total input. Limits are checked before parsing the excess input.
Invalid input returns CLI code 2. Oversized inputs do not reach cryptographic
verification.

Use `read_bundle` arguments `max_records`, `max_evidence_objects`, and
`max_total_bytes` to select smaller or larger budgets. The CLI exposes
`--max-records`, `--max-evidence-objects`, and `--max-bundle-bytes`.
Choose limits for the expected archive and available memory. Decoded records
are still retained in memory, and the verifier retains record digests. Peak
memory is not equal to input byte size and is not constant in record count.
A fully streaming bundle representation remains outside this bounded fix.

These changes do not alter signed bytes, key algorithms, or existing evidence.
The file reader targets macOS and Linux. Local macOS checks are recorded;
GitHub Linux validation of this change is pending. Windows portability of
its filesystem flags has not been established.
