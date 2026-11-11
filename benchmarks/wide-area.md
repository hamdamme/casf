# Remote witness evaluation

Additional Linux/cloud evaluation is deferred. No server provisioning, remote
experiment or deployment is performed by this documentation update. The
[historical wide-area report](results/wide-area-v3/report.md) and raw rows remain
evidence only for their recorded revisions and network path.

The [previous run sheet](https://github.com/hamdamme/casf/blob/6441e4569e8c420f5e8a71e55950af88ce46f336/benchmarks/wide-area.md)
records the earlier AWS Lightsail experiment. Its public port instructions,
fixed test count, manifest edits, reused output directory and suggestion that
restarting the runner resumes an interrupted experiment are obsolete.

## Two distinct future evaluations

| Evaluation | Purpose | Required setup |
| --- | --- | --- |
| Candidate operating workflow | Exercise clean installation, verified startup, the automatic worker, service restarts, outages, backup and recovery | Candidate wheel with recorded hash, current service API, protected provisioning and HTTPS |
| Research rerun | Measure specified workload and network behavior against declared hypotheses | A committed plan, fixed source/import identity, frozen workload and order, fresh synthetic state and complete raw evidence |

The legacy `runner.py` remote submitter uses `HTTPConnection`. It now rejects
HTTPS and other unsupported URL schemes, embedded credentials, path prefixes,
queries and fragments before creating a submitter. It supports only a plain
HTTP origin, for a separately protected research network path. The benchmark
service and deterministic test keys are research fixtures. Do not expose that
runner/service with a bearer token on the public Internet as a current
deployment recipe. Before a new remote study, either implement and test the
required HTTPS transport or specify a protected tunnel and explicitly measure
and report the resulting network path. This transport work is still pending.

The current reference witness service also needs a configured HTTPS reverse
proxy for wider deployment; see [server operation](../docs/witness-server.md).
Its resource limits and the benchmark server's purpose must not be confused.

## Plan before provisioning

1. Select the candidate/source revision, purpose, workload, expected outcomes,
   number of runs and output location. Record changed methods separately from
   the historical study. An operational smoke check is not a performance study.
2. Choose writer and witness hosts, locations, network protection, separate
   credentials and the intended administrative trust boundary. Separate
   machines alone do not demonstrate an independently administered witness.
3. Set a spending limit and cleanup procedure. Record instance type, storage,
   CPU behavior, host load and measured network latency. CPU credit limits or
   shared-host effects must not be hidden in performance comparisons.
4. Provision fresh synthetic keys and witness state for each new experiment.
   Never reuse accepted checkpoint state to silently replace a failed trial.
   Protocol retry of one pending checkpoint is different from rerunning a
   whole manifest with a new writer database.
5. Preserve commands, source/import inventories, start/end times, successful
   and failed attempts, complete raw outputs and checksums. Publish reviewed
   public evidence and remove temporary infrastructure after collection.

The writer-side legacy measurements do not observe remote witness storage or
CPU. A stored `witness_bytes: 0` means unavailable measurement, not zero storage
cost. Append throughput excludes checkpoint submission time. Report measured
client elapsed time and its limits; one host pair does not represent the
Internet or every deployment.

The [current local follow-up](../research/current-evidence-2026-11-10.md)
preserves these historical limits. The next server evaluation must use a new
plan and new result locations; existing records and preprint values stay intact.
