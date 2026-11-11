# Benchmark report: local-subset-v1

manifest: manifest.v1.json

## append-1kib-batch128

runs: 10, records per run: 1000, witnessed through: 1100, database bytes: 2404352, wall clock: 31.8 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 1.6594 | [1.6565, 1.6621] | 10 |
| records_per_second | 592.7904 | [588.8610, 596.4730] | 10 |
| witness_p50_ms | 58.0398 | [57.9611, 58.1623] | 10 |
| verify_seconds | 0.5059 | [0.5025, 0.5103] | 10 |

## append-1kib-batch16

runs: 10, records per run: 1000, witnessed through: 1100, database bytes: 2654208, wall clock: 37.1 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 1.6578 | [1.6556, 1.6600] | 10 |
| records_per_second | 594.4329 | [590.2965, 598.0259] | 10 |
| witness_p50_ms | 7.9425 | [7.9355, 7.9500] | 10 |
| verify_seconds | 0.5028 | [0.5008, 0.5051] | 10 |
