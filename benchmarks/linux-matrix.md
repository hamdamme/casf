# Linux benchmark matrix: run sheet

The full benchmark matrix runs on the Ubuntu machine. Everything is
synthetic; no private keys or services are needed (SPEC §23). The
harness pins the operating system, Python, SQLite, cryptography, and
commit inside every raw row, so results from this machine are
directly comparable with the committed local subset.

## 1. Prepare

```
sudo apt update && sudo apt install -y python3.12 python3.12-venv git
git clone https://github.com/hamdamme/casf.git
cd casf
python3.12 -m venv .venv
.venv/bin/pip install -q ".[dev]"
```

## 2. Sanity: the suite must be green first

```
.venv/bin/python -m pytest -q
```

Expected: 207 passed. Do not run benchmarks on a red suite.

## 3. T19 replication: rerun the committed local subset

```
.venv/bin/python -m benchmarks.run_manifest benchmarks/manifest.v1.json benchmarks/results/local-subset-v1-linux
```

The second argument keeps the committed macOS results untouched.
Then confirm the procedure reproduces (SPEC T19): record counts,
witnessed counts, and database sizes must equal the committed values
in `benchmarks/results/local-subset-v1/`. Latencies will differ; that
is expected and reported, not hidden.

## 4. Extended matrix

```
.venv/bin/python -m benchmarks.run_manifest benchmarks/manifest.v2.json
```

Four pinned configurations, ten runs each: 10000 records at 1 KiB
and 4 KiB, 1000 at 16 KiB, and 10000 at 1 KiB with the witness over
loopback HTTP behind a 25 ms injected round trip delay. Expect
roughly 15 to 20 minutes total. Raw rows and the report land in
`benchmarks/results/linux-matrix-v2/`.

## 5. Keep the evidence

```
tar czf casf-linux-results.tar.gz benchmarks/results/linux-matrix-v2 benchmarks/results/local-subset-v1-linux
```

Copy the archive back, or commit the results directories on a branch
and open a pull request. Keep every run, including failed or
interrupted ones; note interruptions in research/limitations.md.

## Not covered yet

The 25 ms configuration models one network class on loopback; a real
wide area deployment with separate machines and an uncontrolled
network is still open, so wide area numbers beyond the injected
delay model may not be quoted.
