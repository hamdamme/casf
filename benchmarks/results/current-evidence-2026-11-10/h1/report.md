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

- c_current_control: mean 15.01 ms, 95 percent interval [14.71, 15.43] over 10 runs
- c_restored_old_primary: mean 12.14 ms, 95 percent interval [11.89, 12.44] over 10 runs
- c_restored_old_retained_pin: mean 9.91 ms, 95 percent interval [9.78, 10.08] over 10 runs
- c_recovered_control: mean 21.17 ms, 95 percent interval [19.86, 21.92] over 10 runs

## Diagnostic codes observed

- b_current_control: none
- c_current_control: ['STATUS_CURRENTNESS_UNCONFIRMED']
- b_restored_old: none
- c_restored_old_primary: ['STATUS_CURRENTNESS_UNCONFIRMED', 'WITNESS_AHEAD']
- c_restored_old_retained_pin: ['STATUS_CURRENTNESS_UNCONFIRMED', 'WITNESS_STATE_CONFLICT']
- c_recovered_control: ['STATUS_CURRENTNESS_UNCONFIRMED']

## Environment

- casf_module_path: /private/tmp/casf-validation-20261110/src/casf/__init__.py
- casf_source_tree_sha256: b33333764dd2d6841969160e0597f7894a884c21ba2a4fdd1ba96fe19d4e751c
- commit: 09feba1676e0ba319b4e36cb6c2fa76264842b47
- cpu_count: 8
- cryptography: 50.0.2
- dependency_lock_sha256: 74d7a79ae1f872337d26b1b0242c38d8eafd293d673b8a1193ef5b84a08d98fe
- harness_sha256: 8f7d6e40cde9f7b29a1c5f8a66374342bbc45d5f0b4e10fbe9ec7abca48e6f79
- machine: arm64
- os: macOS-15.6.1-arm64-arm-64bit
- python: 3.12.11
- ram_bytes: 17179869184
- sqlite: 3.54.0
- working_tree_status: clean
