# H1 writer rollback experiment (SPEC Section 22)

hypothesis source: CASF_SPEC_001.md Section 22
manifest sha256: af144a3032c21cadb560c54310e6ae5fda4550e47add52900a818131aa01d4b3

configuration: old snapshot 24 records, current 32 records, checkpoint batch 8, 10 runs, fixed seeds

| case | expected | observed values | as declared | mismatch | against | invalid |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| b_current_control | PASS | PASS | 10 | 0 | 0 | 0 |
| c_current_control | PASS | PASS | 10 | 0 | 0 | 0 |
| b_restored_old | PASS | PASS | 10 | 0 | 0 | 0 |
| c_restored_old_primary | FAIL | INCONCLUSIVE | 0 | 10 | 0 | 0 |
| c_restored_old_retained_pin | FAIL | FAIL | 10 | 0 | 0 | 0 |
| c_recovered_control | PASS | PASS | 10 | 0 | 0 | 0 |

## Verification timing (decisive call, milliseconds)

- c_current_control: mean 15.03 ms, 95 percent interval [14.62, 15.71] over 10 runs
- c_restored_old_primary: mean 15.81 ms, 95 percent interval [14.80, 16.69] over 10 runs
- c_restored_old_retained_pin: mean 11.73 ms, 95 percent interval [11.29, 12.13] over 10 runs
- c_recovered_control: mean 27.45 ms, 95 percent interval [26.61, 28.16] over 10 runs

## Diagnostic codes observed

- b_current_control: none
- c_current_control: ['STATUS_CURRENTNESS_UNCONFIRMED']
- b_restored_old: none
- c_restored_old_primary: ['STATUS_CURRENTNESS_UNCONFIRMED', 'WITNESS_AHEAD']
- c_restored_old_retained_pin: ['STATUS_CURRENTNESS_UNCONFIRMED', 'WITNESS_STATE_CONFLICT']
- c_recovered_control: ['STATUS_CURRENTNESS_UNCONFIRMED']

## Environment

- casf_module_path: /Users/nazar/Desktop/PROJECTS/casf/src/casf/__init__.py
- casf_source_tree_sha256: 5d074fe95783b70610060a70a6c795e5addb5cd51b0a4a443ba35888e21e2022
- commit: 7fc4273a941845eac838a5f9fdcba5f2329c9c74
- cpu_count: 8
- cryptography: 50.0.2
- dependency_lock_sha256: 74d7a79ae1f872337d26b1b0242c38d8eafd293d673b8a1193ef5b84a08d98fe
- harness_sha256: b37ed166dea2982b1c72148af4d830e94f3b4da51d092843acc9a33613c6e28e
- machine: arm64
- os: macOS-15.6.1-arm64-arm-64bit
- python: 3.12.11
- ram_bytes: 17179869184
- sqlite: 3.54.0
- working_tree_status: M research/limitations.md
 M research/protocol.md
?? benchmarks/h3-witness-outage-pilot.v1.json
?? benchmarks/h3-witness-outage.v1.json
?? benchmarks/h3_witness_outage.py
?? benchmarks/manifest.rq2.json
?? benchmarks/results/h3-witness-outage-pilot-v1/
?? benchmarks/results/h3-witness-outage-v1/
?? benchmarks/rq2.md
?? benchmarks/rq2.py
?? research/h3-witness-outage.md
?? tests/test_h3_witness_outage.py
