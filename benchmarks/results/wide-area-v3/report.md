# CASF Wide Area Benchmark Results

## Experimental summary

- Total completed runs: 20 (10 per configuration), zero failed runs
- Records per run: 10000, warmup per run: 100
- Writer: Dell Linux (Python 3.14.4), witness: AWS Lightsail instance
- Executed at commit 84c5444; raw rows in this directory
- Statistical method: run level bootstrap, 95% intervals

## wan-1kib-10k-batch128

Completed runs: 10, checkpoints per run: 80, mean witness time per run: about 95 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 0.8039 | [0.6521, 0.9547] | 10 |
| records_per_second | 1273.4174 | [1001.4624, 1553.2978] | 10 |
| witness_p50_ms | 1184.9890 | [1179.0669, 1192.7673] | 10 |
| verify_seconds | 5.6046 | [4.5059, 6.6005] | 10 |

## wan-1kib-10k-batch16

Completed runs: 10, checkpoints per run: 626, mean witness time per run: about 420 s

| metric | mean | 95% interval | runs |
| --- | ---: | ---: | ---: |
| append_p50_ms | 0.4617 | [0.4586, 0.4648] | 10 |
| records_per_second | 1461.5372 | [1424.9871, 1501.3405] | 10 |
| witness_p50_ms | 671.3594 | [666.9316, 675.3675] | 10 |
| verify_seconds | 3.1452 | [3.0793, 3.2679] | 10 |

## Methodological notes

Results are calculated from the raw run files in this directory. The
remote witness was restarted between some runs. These 20 runs
executed at commit 84c5444, before the runner gained timeout retry
logic; no stall occurred during these runs, and any future stall is
retried with identical bytes (counted as witness_retries).
records_per_second measures append operation time, not end to end
throughput. The witness instance address belongs to the AWS
eu-central-1 range; the writer location was not recorded in the
artifacts, so round trip times describe this one network path only
and no general wide area claim is made. witness_bytes is 0 by
design: the remote store is not measurable from the writer side.
