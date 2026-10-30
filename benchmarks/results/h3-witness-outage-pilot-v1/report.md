# Canonical H3 feasibility pilot

This is one matched synthetic pilot pair using the separate pilot manifest. It is excluded from measured results and provides no inferential estimate.

- Healthy run: complete; baseline and final online checks: {'anchor_status': 'OK', 'diagnostic_codes': ['STATUS_CURRENTNESS_UNCONFIRMED', 'VERIFIER_STATE_INITIALIZED', 'CHECKPOINT_FIRST_OBSERVATION'], 'freshness_status': 'FRESH_WITNESS_VIEW', 'mode': 'online', 'result': 'PASS', 'trust_status': 'OK', 'unwitnessed_count': 0, 'verified_through': 16, 'witnessed_through': 16} and {'anchor_status': 'OK', 'diagnostic_codes': ['STATUS_CURRENTNESS_UNCONFIRMED', 'VERIFIER_STATE_INITIALIZED', 'CHECKPOINT_FIRST_OBSERVATION'], 'freshness_status': 'FRESH_WITNESS_VIEW', 'mode': 'online', 'result': 'PASS', 'trust_status': 'OK', 'unwitnessed_count': 0, 'verified_through': 32, 'witnessed_through': 32}.
- Outage run: complete; online freshness result: {'anchor_status': 'OK', 'diagnostic_codes': ['STATUS_CURRENTNESS_UNCONFIRMED', 'FRESHNESS_INCONCLUSIVE'], 'freshness_status': 'INCONCLUSIVE', 'mode': 'online', 'result': 'INCONCLUSIVE', 'trust_status': 'OK', 'unwitnessed_count': 0, 'verified_through': 16, 'witnessed_through': 16}, exit 4; offline integrity result: {'anchor_status': 'NOT_REQUESTED', 'diagnostic_codes': ['STATUS_CURRENTNESS_UNCONFIRMED', 'VERIFIER_STATE_INITIALIZED'], 'freshness_status': 'NOT_REQUESTED', 'mode': 'integrity', 'result': 'PASS', 'trust_status': 'OK', 'unwitnessed_count': 0, 'verified_through': 16, 'witnessed_through': None}, exit 0.
- Fault delivery: {'blocked_requests': 2, 'forwarded_requests': 6}; witness state during the block: {'checkpoint_index': 1, 'count': 16}.
- Checkpoint through record 24: initial result failed_pending; same pending bytes after failure: True; same checkpoint accepted after restoration: True.
- Maximum pending suffix: 16 records.

These outcomes established that the frozen timeout, outage duration, and recovery deadline were feasible for the measured run. They are not included in the measured analysis.

Command used for the pilot: `.venv/bin/python -m benchmarks.h3_witness_outage --manifest benchmarks/h3-witness-outage-pilot.v1.json --output benchmarks/results/h3-witness-outage-pilot-v1`

That output directory is protected from overwrite. A future pilot run needs a new output directory, for example `benchmarks/results/h3-witness-outage-pilot-reproduction-v1`.

Run JSON preserves full CLI output, diagnostics, exit codes, monotonic timestamps, and errors. Environment provenance is in `environment.json`; hashes are in `SHA256SUMS.txt`.
