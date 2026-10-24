# Wide area benchmark: run sheet

The writer runs on your fast machine (Dell Linux), the witness runs
on a cloud instance in another region (AWS Lightsail). This produces
the real network numbers that RQ2 and RQ3 need; the injected delay
model from manifest.v2 stays as the controlled reference. Everything
is synthetic: dedicated benchmark keys, a throwaway bearer token,
no production data.

## 1. Lightsail side (witness)

Create the smallest Ubuntu Lightsail instance in a region far from
you. In its networking tab, open TCP port 8080. Then:

```
sudo apt update && sudo apt install -y python3 python3-venv git
git clone https://github.com/hamdamme/casf.git && cd casf
python3 -m venv .venv-tools
.venv-tools/bin/python -m pip install "uv==0.13.5"
.venv-tools/bin/uv sync --locked --extra witness --python python3
export CASF_BENCH_TOKEN='pick-a-long-random-string'
.venv/bin/python -m benchmarks.witness_server \
    --host 0.0.0.0 --port 8080 --token-env CASF_BENCH_TOKEN \
    --seeds 7,8,9,10,11,12,13,14,15,16 --runs 10
```

Leave this running; it prints the port and waits. It pre registers
one log per run and keeps state between runs, which is what a real
witness does.

## 2. Dell side (writer)

```
git clone https://github.com/hamdamme/casf.git && cd casf
python3 -m venv .venv-tools
.venv-tools/bin/python -m pip install "uv==0.13.5"
.venv-tools/bin/uv sync --locked --extra witness --extra dev --python python3
.venv/bin/python -m pytest -q    # must say 212 passed
export CASF_BENCH_TOKEN='the-same-random-string'
```

Edit `benchmarks/manifest.v3.json`: replace `LIGHTSAIL_IP` (both
configs) with the instance public IP. Then:

```
.venv/bin/python -m benchmarks.run_manifest benchmarks/manifest.v3.json
```

Expected wall clock: roughly 30 to 60 minutes depending on the real
round trip time. Results land in `benchmarks/results/wide-area-v3/`.

## 3. Keep the evidence

```
git checkout -b wide-area-results
git add benchmarks/results/wide-area-v3
git commit -m "Wide area benchmark results"
git push origin wide-area-results
```

Then delete the Lightsail instance so it stops billing.

## Honesty notes

- Record the instance region and your own location in the report;
  round trip time is meaningless without geography.
- The witness store size is not measurable from the writer side, so
  witness_bytes is 0 in these raw rows by design.
- One instance pair is one network path; say "this path", not "the
  internet".
- A transient network stall is retried with the identical pending
  checkpoint bytes, which the witness deduplicates; retries are
  counted per run as witness_retries in the raw rows. If a run dies
  anyway, confirm the witness window is still alive and rerun the
  same manifest; already accepted checkpoints replay their stored
  receipts, so the rerun continues cleanly.
