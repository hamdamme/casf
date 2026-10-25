"""Create synthetic public evidence for installed package checks."""

import json
import sys
import tempfile
from pathlib import Path

from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.lifecycle import sign_status
from casf.writer import Writer


def main():
    destination = Path(sys.argv[1])
    authority, log, witness = (crypto.generate_key() for _ in range(3))
    authority_pub = crypto.public_key_raw(authority)
    witness_pub = crypto.public_key_raw(witness)
    log_pub = crypto.public_key_raw(log)
    log_id = '123e4567-e89b-42d3-a456-426614174000'
    timestamp = '2026-10-25T00:00:00.000000Z'
    body = {
        'version': 1, 'type': 'manifest', 'log_id': log_id,
        'issuer_id': crypto.key_id(authority_pub), 'log_key_id': crypto.key_id(log_pub),
        'log_public_key': crypto.b64url_encode(log_pub),
        'witness_id': crypto.key_id(witness_pub),
        'witness_public_key': crypto.b64url_encode(witness_pub),
        'created_at': timestamp, 'predecessor': None,
    }
    manifest_hash = crypto.digest_manifest(body)
    envelope = {'body': body, 'manifest_hash': manifest_hash,
                'signature': crypto.sign_manifest(authority, body)}
    with tempfile.TemporaryDirectory() as private_work:
        writer = Writer(Path(private_work) / 'writer.db', log)
        try:
            writer.create_log(envelope)
            for n in (1, 2):
                writer.append(log_id, event_id=f'123e4567-e89b-42d3-a456-4266{n:08d}',
                              actor='synthetic', event_type='check', payload={'n': n}, attributes={})
            writer.export_bundle(log_id, destination)
        finally:
            writer.close()
    status = sign_status(authority, serial=1, manifest_hash=manifest_hash,
                         status='active', issued_at=timestamp, reason='')
    (destination / 'status.jsonl').write_bytes(canonicalize(status) + b'\n')
    trust = {
        'authority': crypto.b64url_encode(authority_pub),
        'witness': crypto.b64url_encode(witness_pub),
        'log_id': log_id, 'manifest_hash': manifest_hash,
    }
    destination.with_name(destination.name + '-trust.json').write_text(json.dumps(trust))
    print('Synthetic public bundle created; no private key files exported.')


if __name__ == '__main__':
    main()
