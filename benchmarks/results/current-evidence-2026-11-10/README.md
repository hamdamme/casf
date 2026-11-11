# Current implementation follow-up measurements

Measurements ran on 11 November 2026, 01:24:25–01:26:38 UTC (10 November
locally), from clean source `09feba1676e0ba319b4e36cb6c2fa76264842b47`.
RQ4 instead measures the explicitly selected PR 50 merge revision
`b3cf12be89455f5515a8ad001295086c91527342`.

Read the [follow-up interpretation](../../../research/current-evidence-2026-11-10.md)
and [plan recorded before collection](../../../research/refresh-plan-2026-11-10.md).

| Directory | Contents |
| --- | --- |
| `detection/` | Ten-case matrix and generated report |
| `h1/` | Ten rollback trials, six cases each, frozen manifest and report |
| `local/` | Twenty raw performance runs, frozen manifest and report |
| `h3/` | Twenty raw outage/healthy runs, frozen manifest, order, environment, paired summary and report |
| `rq4/` | Descriptive repository measurements, original manifest and report; the command overrides its historical default commit |

`provenance.json` records actual arguments, import setting, commit, source and
manifest hashes, timestamps and exit statuses. `source-environment.json`
verifies the 39 imported CASF files (38 Python files plus `py.typed`) against
the clean checkout. `host-details.json` supplements the runtime inventory with
CPU and APFS details collected after the measurements. The H3 recorder's raw
`filesystem_type` value `/` is not a filesystem identifier; use the supplemental
record. Neither record claims the host was otherwise idle or isolated.

`review.json` records checks of counts, outcomes, diagnostics and completed
recovery. All 525 entries in the original H3 full-output checksum list were
verified before selecting public files. `historical-files.json` records the
193 existing result, manifest, protocol and preprint files checked unchanged.
An output checksum proves file identity, not correctness of the measurement.

The 57 files listed in `publication.json` are byte-for-byte copies of collected
JSON and reports; there are no transformations. Frozen manifest copies are
additional. Generated databases, bundles, keys and verifier state are excluded
from this public subset. The full raw output and original H3 checksum list are
retained separately. The new root and H3 checksum lists cover their public
subsets only; they do not claim the omitted runtime files are downloadable.

The generated H3 report's feasibility-pilot references refer to the original
historical pilot, which was not rerun here. This follow-up's preflight used the
47 focused harness tests, outside measured runs. H3 recovery remains manual;
the implementation's automatic worker was not exercised by this experiment.

Verify the public files from this directory:

```bash
shasum -a 256 -c SHA256SUMS.txt
```

For a new run, check out the measurement commit, install its locked environment,
set `PYTHONPATH=src` and use the plan's commands with a new output directory.
Do not reuse the recorded temporary paths or an existing results directory.
