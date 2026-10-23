# Benchmark report: linux-matrix-v2

manifest: manifest.v2.json

## linux-1kib-10k

runs: 10, records per run: 10000, witnessed through: 10100, database bytes: 22265856, wall clock: 1875.9 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 11.3275 | [11.3264, 11.3283] | 10 |
| records_per_second | 74.9346 | [73.8637, 76.0815] | 10 |
| witness_p50_ms | 196.0226 | [188.1474, 204.6769] | 10 |
| verify_seconds | 10.1076 | [10.0945, 10.1200] | 10 |

## linux-4kib-10k

runs: 10, records per run: 10000, witnessed through: 10100, database bytes: 51232768, wall clock: 2532.2 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 11.3890 | [11.3827, 11.3953] | 10 |
| records_per_second | 60.1083 | [59.0908, 61.0998] | 10 |
| witness_p50_ms | 343.8461 | [339.8807, 348.9993] | 10 |
| verify_seconds | 23.8130 | [23.7850, 23.8401] | 10 |

## linux-16kib-1k

runs: 10, records per run: 1000, witnessed through: 1100, database bytes: 18477056, wall clock: 577.8 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 22.5392 | [22.5379, 22.5405] | 10 |
| records_per_second | 39.3847 | [39.1724, 39.6325] | 10 |
| witness_p50_ms | 165.4092 | [162.3934, 168.0999] | 10 |
| verify_seconds | 8.4371 | [8.4266, 8.4480] | 10 |

## linux-1kib-10k-http25ms

runs: 10, records per run: 10000, witnessed through: 10100, database bytes: 22265856, wall clock: 1942.3 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 11.3259 | [11.3247, 11.3278] | 10 |
| records_per_second | 73.0307 | [66.5931, 76.8510] | 10 |
| witness_p50_ms | 209.1511 | [203.0110, 215.1902] | 10 |
| verify_seconds | 10.1614 | [10.1495, 10.1749] | 10 |
