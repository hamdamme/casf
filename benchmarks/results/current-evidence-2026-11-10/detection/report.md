# Detection matrix (SPEC Section 23)

history: 38 records, checkpoint batch 8, witnessed through 32, seed 41

| case | spec | mode | attacker controls | expected | observed | match |
| --- | --- | --- | --- | --- | --- | --- |
| tamper-beginning | Section 23 | integrity | writer store | FAIL | FAIL | True |
| tamper-middle | Section 23 | integrity | writer store | FAIL | FAIL | True |
| tamper-last-witnessed | Section 23 | integrity | writer store | FAIL | FAIL | True |
| tamper-tail | Section 23 | integrity | writer store | FAIL | FAIL | True |
| truncate-tail-integrity | T18 | integrity | writer store | PASS | PASS | True |
| truncate-tail-anchored | T18 | anchored | writer store | PASS | PASS | True |
| stolen-key-prefix-anchored | T20 | anchored | writer store, log key | FAIL | FAIL | True |
| stolen-key-suffix | T20 | anchored | writer store, log key | PASS | PASS | True |
| witness-rollback-retained | T21 | online | witness store | FAIL | FAIL | True |
| witness-rollback-isolated | T21 | online | witness store, writer store | PASS | PASS | True |

Notes per case are in attacks.v1.json; cases expected to PASS are documented non detections, not failures of the harness.
