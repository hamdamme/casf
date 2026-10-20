# CASF Wide Area Benchmark Results

## Experimental Summary

- Total completed runs: 20
- Records per run: 10,000
- Warmup records per run: 100
- Remote witness: AWS Lightsail
- Writer: Dell Linux
- Statistical method: Run-level bootstrap, 95% intervals

## wan-1kib-10k-batch128

Completed runs: 10

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 0.8039 | [0.6521, 0.9547] | 10 |
| records_per_second | 1273.4174 | [1001.4624, 1553.2978] | 10 |
| witness_p50_ms | 1184.9890 | [1179.0669, 1192.7673] | 10 |
| verify_seconds | 5.6046 | [4.5059, 6.6005] | 10 |


## wan-1kib-10k-batch16

Completed runs: 10

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 0.4617 | [0.4586, 0.4648] | 10 |
| records_per_second | 1461.5372 | [1424.9871, 1501.3405] | 10 |
| witness_p50_ms | 671.3594 | [666.9316, 675.3675] | 10 |
| verify_seconds | 3.1452 | [3.0793, 3.2679] | 10 |


## Methodological Notes

Results are calculated from saved individual run files.
The remote witness was restarted between some runs.
The benchmark runner used network timeout retries.
Reported records_per_second measures append operation time,
not total end-to-end benchmark throughput.
