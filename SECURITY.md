# Security Policy

## Supported versions
| Version | Support status |
|---|---|
| 0.1.0rc4 | Unpublished candidate; next experimental prerelease with fixes for privately reported issues (C01–C06, D01–D03), SQLite permissions, canonical JSONL and small-order Ed25519 keys; replacement artifacts prepared, approval pending |
| 0.1.0rc3 | Latest published experimental GitHub prerelease; best-effort reports; affected by the Ed25519 key-validation issue; users should upgrade to rc4 once published |
| 0.1.0rc2 | Superseded; affected by the Ed25519 key-validation issue; no backports |
| 1.0+ | To be defined before 1.0 (decision D10) |

## Reporting a vulnerability
**Private channel:** [GitHub private vulnerability reporting](https://github.com/hamdamme/casf/security/advisories/new).
Private reporting was enabled and a real report
was received through the channel during release preparation. This confirms
delivery for that report; it is not an independent security audit and does
not establish a response service level.

Please include: affected version/commit, configuration, minimal
**synthetic** reproduction evidence, and impact assessment. Do **not**
send production private keys or real audit data.

## Response targets (best effort, solo project)
- Acknowledgement within 7 days
- Triage update within 14 days
If delayed, reporters will be informed.

## Triage categories
Parser denial of service · signature or trust bypass · witness
equivocation bugs · secret exposure · documentation overclaims.

## Claim discipline
Do not describe this project as "tamper-proof", "audited", or
"compliant" in vulnerability reports or elsewhere without specific
evidence (see README and SPEC §29).
