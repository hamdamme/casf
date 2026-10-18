"""Standalone benchmark witness server for the wide area matrix.

Runs on the second machine (for example a cloud instance in another
region). It serves the real witness HTTP API with the deterministic
benchmark keys and pre registers one log id per planned run, so each
run of a remote configuration gets a fresh log on a witness that
keeps its state between runs (SPEC §22). Synthetic keys and token
only; never point a production writer at this server.

Usage:
    CASF_BENCH_TOKEN=... python -m benchmarks.witness_server \
        --host 0.0.0.0 --port 8080 --token-env CASF_BENCH_TOKEN \
        --seeds 7,8,9,10,11,12,13,14,15,16 --runs 10
"""

import argparse
import os
import tempfile
from pathlib import Path

from benchmarks import workload
from casf.witness.http import WitnessService, make_server


def _authority_keys() -> dict:
    from casf import crypto
    auth_pub = crypto.public_key_raw(workload.seeded_key("authority"))
    return {crypto.key_id(auth_pub): auth_pub}


def build_server(host: str, port: int, *, token: str, seeds: list[int],
                 runs: int, db_path: Path) -> tuple:
    """Witness service with every planned run log pre registered."""
    service = WitnessService(db_path, workload.seeded_key("witness"),
                             token=token,
                             authority_keys=_authority_keys())
    for i in range(runs):
        log_id = workload.run_log_id(seeds[i % len(seeds)], i)
        service.witness.register_log(workload.manifest(log_id))
    server = make_server(service, host, port)
    return service, server


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="benchmarks.witness_server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token-env", required=True,
                        help="environment variable holding the bearer token")
    parser.add_argument("--seeds", required=True,
                        help="comma separated run seeds, as in the manifest")
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--db", default="",
                        help="witness database path; default is temporary")
    args = parser.parse_args(argv)

    token = os.environ.get(args.token_env, "")
    if not token:
        parser.error(f"environment variable {args.token_env} is not set; "
                     "the bearer token comes from the environment only")
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    if not seeds or args.runs < 1:
        parser.error("seeds and runs must match the benchmark manifest")

    db_path = (Path(args.db) if args.db
               else Path(tempfile.mkdtemp(prefix="casf-bench-witness-"))
               / "witness.db")
    service, server = build_server(args.host, args.port, token=token,
                                   seeds=seeds, runs=args.runs,
                                   db_path=db_path)
    print(f"benchmark witness on {args.host}:{server.server_address[1]} "
          f"with {args.runs} pre registered logs; ctrl+c to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close()
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
