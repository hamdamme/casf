"""Synthetic streaming comparison. Generate files before measuring in fresh processes."""
import argparse
import gc
import hashlib
import json
import platform
import resource
import sys
import time
import tracemalloc
from contextlib import nullcontext
from pathlib import Path

from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.verifier import Mode, Result, TrustPins, verify


def generate(destination, count, anchor_records=None):
    from tests.unit.test_verifier import (
        AUTH_PUB,
        LOG_ID,
        TS,
        WIT_PUB,
        ZERO,
        _checkpoint_env,
        _manifest_env,
        _receipt_env,
        _record_body,
        _record_env,
        _status_env,
    )
    destination.mkdir(parents=True)
    manifest = _manifest_env()
    mh = manifest['manifest_hash']
    (destination / 'manifest.json').write_bytes(canonicalize(manifest))
    prev = crypto.genesis_hash(mh)
    prev_cp = prev_rc = ZERO
    cp_index = 0
    anchor_records = count if anchor_records is None else min(count, anchor_records)
    with (destination / 'records.jsonl').open('wb') as records, \
            (destination / 'checkpoints.jsonl').open('wb') as cps, \
            (destination / 'receipts.jsonl').open('wb') as receipts:
        for seq in range(count + 1):
            if seq:
                body = _record_body(seq, prev, mh,
                                    event_id=f'123e4567-e89b-42d3-a456-{seq:012d}')
                body['payload'] = {'synthetic': 'x' * 1024}
                record = _record_env(body)
                prev = record['record_hash']
                records.write(canonicalize(record) + b'\n')
            if (seq and seq <= anchor_records and (seq % 128 == 0 or seq == anchor_records)) \
                    or (count == 0 and seq == 0):
                cp = _checkpoint_env(cp_index, seq, prev, prev_cp, mh)
                rc = _receipt_env(cp, prev_rc)
                prev_cp, prev_rc = cp['checkpoint_hash'], rc['receipt_hash']
                cps.write(canonicalize(cp) + b'\n')
                receipts.write(canonicalize(rc) + b'\n')
                cp_index += 1
    (destination / 'status.jsonl').write_bytes(canonicalize(_status_env(mh)) + b'\n')
    (destination / 'export.json').write_bytes(canonicalize(
        {'version': 1, 'type': 'export', 'log_id': LOG_ID, 'manifest_hash': mh,
         'through': count, 'record_count': count, 'generated_at': TS}))
    destination.with_suffix('.trust.json').write_text(json.dumps(
        {'authority': crypto.b64url_encode(AUTH_PUB), 'witness': crypto.b64url_encode(WIT_PUB),
         'manifest_hash': mh, 'log_id': LOG_ID}))


def measure(directory, reader, mode, trace=True):
    from casf import bundle as bundle_module
    trust = json.loads(directory.with_suffix('.trust.json').read_text())
    ap, wp = [crypto.b64url_decode(trust[k]) for k in ('authority', 'witness')]
    pins = TrustPins({crypto.key_id(ap): ap}, {crypto.key_id(wp): wp},
                     trust['log_id'], trust['manifest_hash'])
    gc.collect()
    if trace:
        tracemalloc.start()
    start = time.perf_counter()
    context = (bundle_module.open_bundle(directory) if reader == 'stream'
               else nullcontext(bundle_module.read_bundle(directory)))
    with context as bundle:
        report = verify(bundle.manifest, bundle.records, pins, mode=Mode(mode),
                        checkpoint_envelopes=bundle.checkpoints,
                        receipt_envelopes=bundle.receipts, status_envelopes=bundle.statuses,
                        allow_unwitnessed=True)
        if reader == 'stream':
            for _ in bundle.records:
                pass
    elapsed = time.perf_counter() - start
    peak = tracemalloc.get_traced_memory()[1] if trace else None
    if trace:
        tracemalloc.stop()
    if report.result is not Result.PASS:
        raise RuntimeError(report)
    print(json.dumps({'reader': reader, 'mode': mode, 'records': report.verified_through,
                      'result': report.result.value, 'seconds': elapsed,
                      'traced_peak_bytes': peak, 'maxrss': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      'maxrss_unit': 'bytes' if sys.platform == 'darwin' else 'KiB',
                      'python': sys.version, 'platform': platform.platform(),
                      'source': str(Path(bundle_module.__file__).resolve()),
                      'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(directory.iterdir())}}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    gen = sub.add_parser('generate')
    gen.add_argument('directory', type=Path)
    gen.add_argument('--count', type=int, required=True)
    gen.add_argument('--anchor-records', type=int)
    run = sub.add_parser('measure')
    run.add_argument('directory', type=Path)
    run.add_argument('--reader', choices=['eager', 'stream'], required=True)
    run.add_argument('--mode', choices=['integrity', 'anchored'], required=True)
    run.add_argument('--no-trace', action='store_true')
    args = parser.parse_args()
    if args.action == 'generate':
        generate(args.directory, args.count, args.anchor_records)
    else:
        measure(args.directory, args.reader, args.mode, not args.no_trace)
