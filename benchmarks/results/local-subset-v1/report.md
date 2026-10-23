# Benchmark report: local-subset-v1

manifest: manifest.v1.json

## append-1kib-batch128

runs: 10, records per run: 1000, witnessed through: 1100, database bytes: 2379776, wall clock: 19.1 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 0.6805 | [0.6787, 0.6824] | 10 |
| records_per_second | 1412.7043 | [1386.1399, 1432.1117] | 10 |
| witness_p50_ms | 50.2524 | [50.1405, 50.3757] | 10 |
| verify_seconds | 0.4325 | [0.4312, 0.4340] | 10 |

## append-1kib-batch16

runs: 10, records per run: 1000, witnessed through: 1100, database bytes: 2273280, wall clock: 23.7 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 0.6797 | [0.6784, 0.6809] | 10 |
| records_per_second | 1425.2732 | [1413.8506, 1434.5385] | 10 |
| witness_p50_ms | 7.0317 | [7.0162, 7.0454] | 10 |
| verify_seconds | 0.4325 | [0.4312, 0.4344] | 10 |
