# Benchmark report: local-subset-v1

manifest: manifest.v1.json

## append-1kib-batch128

runs: 10, records per run: 1000, witnessed through: 1100, database bytes: 2379776, wall clock: 682.4 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 45.4162 | [11.3334, 96.2118] | 10 |
| records_per_second | 59.6102 | [39.3982, 73.5550] | 10 |
| witness_p50_ms | 232.9860 | [171.0481, 319.1908] | 10 |
| verify_seconds | 1.1454 | [1.1184, 1.1799] | 10 |

## append-1kib-batch16

runs: 10, records per run: 1000, witnessed through: 1100, database bytes: 2273280, wall clock: 248.7 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 11.3357 | [11.3338, 11.3378] | 10 |
| records_per_second | 74.7026 | [74.1635, 75.2897] | 10 |
| witness_p50_ms | 38.6055 | [38.4608, 38.7439] | 10 |
| verify_seconds | 1.1049 | [1.0985, 1.1129] | 10 |
