"""Synthetic two-host acceptance helpers. Never use these fixtures for real records.

Prepare private role directories, serve only on loopback behind a TLS proxy,
and exercise the public verified-writer API against the remote witness.
The runner refuses to replace an existing fixture directory.
"""

import argparse
import ipaddress
import json
import os
import secrets
import signal
import socket
import ssl
import subprocess
import threading
import time
import uuid
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from casf import crypto
from casf.bundle import read_bundle
from casf.canonical.jcs import canonicalize
from casf.errors import CasfError, InconclusiveError, TrustError
from casf.keys import generate_key, load_key
from casf.lifecycle import sign_status
from casf.online import query_latest
from casf.transport import request
from casf.verifier import Mode, Result, TrustPins, verify
from casf.witness.http import WitnessService, make_server
from casf.writer import StartupPolicy, Writer


def private(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
        stream.write(data)


def read_json(path):
    return json.loads(path.read_text())


def prepare(root, address):
    root.mkdir(mode=0o700)
    roles = {}
    keys = {}
    for role in ('authority', 'writer', 'witness', 'public', 'tls'):
        path = root / role
        path.mkdir(mode=0o700)
        roles[role] = path
    for role, key_role in [('authority', 'authority'), ('writer', 'log'), ('witness', 'witness')]:
        password = secrets.token_urlsafe(32).encode()
        private(roles[role] / 'passphrase', password)
        generate_key(key_role, roles[role] / 'key.pem', passphrase=password)
        keys[role] = load_key(roles[role] / 'key.pem', passphrase=password)
    pubs = {role: crypto.public_key_raw(key) for role, key in keys.items()}
    now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S.000000Z')
    body = {'version': 1, 'type': 'manifest', 'log_id': str(uuid.uuid4()),
            'issuer_id': crypto.key_id(pubs['authority']),
            'log_key_id': crypto.key_id(pubs['writer']),
            'log_public_key': crypto.b64url_encode(pubs['writer']),
            'witness_id': crypto.key_id(pubs['witness']),
            'witness_public_key': crypto.b64url_encode(pubs['witness']),
            'created_at': now, 'predecessor': None}
    manifest = {'body': body, 'manifest_hash': crypto.digest_manifest(body),
                'signature': crypto.sign_manifest(keys['authority'], body)}
    status = sign_status(keys['authority'], serial=1, manifest_hash=manifest['manifest_hash'],
                         status='active', issued_at=now, reason='synthetic rehearsal')
    revoked = sign_status(keys['authority'], serial=2, manifest_hash=manifest['manifest_hash'],
                          status='revoked', issued_at=now, reason='synthetic revocation drill')
    token = secrets.token_urlsafe(32).encode()
    for role in ('writer', 'witness'):
        private(roles[role] / 'token', token)
        private(roles[role] / 'manifest.json', canonicalize(manifest))
        private(roles[role] / 'status.json', canonicalize(status))
        private(roles[role] / 'authority.pub', pubs['authority'])
    private(roles['authority'] / 'revoked.json', canonicalize(revoked))
    private(roles['public'] / 'manifest.json', canonicalize(manifest))
    make_certificates(roles['tls'], address)
    return {'log_id': body['log_id'], 'manifest_hash': manifest['manifest_hash']}


def make_certificates(root, address):
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'CASF synthetic rehearsal CA')])
    now = datetime.now(UTC)
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=7))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False,
              key_encipherment=False, data_encipherment=False, key_agreement=False,
              key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False),
              critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
                         critical=False)
          .sign(ca_key, hashes.SHA256()))
    private(root / 'ca.pem', ca.public_bytes(serialization.Encoding.PEM))
    for label in ('valid', 'rotated', 'expired', 'wrong-host'):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        host = ipaddress.ip_address('192.0.2.123' if label == 'wrong-host' else address)
        cert = (x509.CertificateBuilder().subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, 'CASF synthetic witness')]))
            .issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=2))
            .not_valid_after(now - timedelta(days=1) if label == 'expired'
                             else now + timedelta(days=2))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                           critical=False)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(host)]), critical=False)
            .sign(ca_key, hashes.SHA256()))
        private(root / (label + '.pem'), cert.public_bytes(serialization.Encoding.PEM))
        private(root / (label + '.key'), key.private_bytes(serialization.Encoding.PEM,
                  serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


def configuration(root):
    manifest = read_json(root / 'manifest.json')
    authority = (root / 'authority.pub').read_bytes()
    body = manifest['body']
    pins = TrustPins(authority_keys={crypto.key_id(authority): authority},
                     witness_keys={body['witness_id']: crypto.b64url_decode(body['witness_public_key'])},
                     log_id=body['log_id'], manifest_hash=manifest['manifest_hash'])
    key = load_key(root / 'key.pem', passphrase=(root / 'passphrase').read_bytes())
    return manifest, pins, key


def serve(root, port):
    manifest, pins, key = configuration(root)
    fresh = not (root / 'witness.db').exists()
    with closing(WitnessService(root / 'witness.db', key,
                               token=(root / 'token').read_text(),
                               authority_keys=dict(pins.authority_keys), max_inflight=4,
                               max_connections=16, header_timeout=2, request_timeout=2)) as service:
        if fresh:
            service.witness.register_log(manifest, read_json(root / 'status.json'))
        server = make_server(service, '127.0.0.1', port)
        def stop(_signum, _frame):
            threading.Thread(target=server.shutdown, daemon=True).start()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        try:
            server.serve_forever()
        finally:
            server.server_close()


def exercise(root, url, ssh_host, ssh_key, remote_root, output):
    """Control only named synthetic user services; never reboot the machine."""
    output.mkdir(mode=0o700)
    writer_root = root / 'writer'
    manifest, pins, key = configuration(writer_root)
    log_id = pins.log_id
    token = (writer_root / 'token').read_text()
    status = read_json(writer_root / 'status.json')
    old_ca = os.environ.get('SSL_CERT_FILE')
    os.environ['SSL_CERT_FILE'] = str(root / 'tls' / 'ca.pem')
    steps = []
    ssh = ['ssh', '-i', str(ssh_key), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
           '-o', 'StrictHostKeyChecking=yes', ssh_host]

    def control(action, unit):
        if action not in ('stop', 'start', 'restart', 'kill') or unit not in ('witness', 'proxy'):
            raise ValueError('unsupported rehearsal control')
        operation = ['kill', '--signal=KILL', '--kill-whom=main'] if action == 'kill' else [action]
        subprocess.run([*ssh, 'systemctl', '--user', *operation, f'casf-rehearsal-{unit}.service'],
                       check=True, capture_output=True)

    def copy_file(source, name):
        if name not in ('tls.pem', 'tls.key', 'witness/token'):
            raise ValueError('unsupported rehearsal file')
        subprocess.run(['scp', '-q', '-i', str(ssh_key), '-o', 'IdentitiesOnly=yes',
                        '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', str(source),
                        f'{ssh_host}:{remote_root}/{name}'], check=True, capture_output=True)

    def note(name):
        steps.append({'check': name, 'result': 'PASS'})
        (output / 'checks.json').write_text(json.dumps(steps, indent=2) + '\n')

    def latest(current_token=None):
        return query_latest(url, log_id, token if current_token is None else current_token,
                            crypto.b64url_decode(manifest['body']['witness_public_key']), timeout=3)

    def wait_ready():
        deadline = time.monotonic() + 15
        while True:
            try:
                return latest()
            except CasfError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)

    def rejected_tls(label):
        try:
            latest()
        except InconclusiveError as exc:
            assert isinstance(exc.__cause__, ssl.SSLCertVerificationError)
            note(label)
        else:
            raise RuntimeError('invalid TLS certificate was accepted')

    startup = StartupPolicy(state_path=writer_root / 'retained.json', status_envelopes=(status,),
                            witness_url=url, token=token, initialize_state=True)
    try:
        with closing(Writer.initialize_verified(writer_root / 'writer.db', key, manifest,
                     trust_pins={log_id: pins}, startup=startup)) as writer:
            note('verified startup over cross-host TLS')
            def append_pending():
                writer.append(log_id, event_id=str(uuid.uuid4()), actor='synthetic operator',
                              event_type='rehearsal', payload={'synthetic': True}, attributes={})
                return canonicalize(writer.create_checkpoint(log_id))
            before = append_pending()
            try:
                writer.submit_pending(log_id, url, 'synthetic-wrong-token')
            except TrustError:
                assert canonicalize(writer.pending_checkpoint(log_id)[0]) == before
                note('wrong token rejected without changing pending bytes')
            else:
                raise RuntimeError('wrong token accepted')
            writer.submit_pending(log_id, url, token)
            note('corrected-token retry accepted')
            control('restart', 'witness')
            wait_ready()
            note('supervised witness restart retains accepted history')
            control('kill', 'witness')
            time.sleep(1.25)
            wait_ready()
            note('service supervisor restarts killed witness without losing history')
            before = append_pending()
            control('stop', 'proxy')
            try:
                writer.submit_pending(log_id, url, token, timeout=1)
            except InconclusiveError:
                assert canonicalize(writer.pending_checkpoint(log_id)[0]) == before
                note('proxy outage remains inconclusive and preserves pending bytes')
            else:
                raise RuntimeError('offline proxy accepted submission')
            control('start', 'proxy')
            wait_ready()
            writer.submit_pending(log_id, url, token)
            note('pending retry recovers after proxy restart')
            cp_bytes = append_pending()
            cp, start, end = writer.pending_checkpoint(log_id)
            records = list(writer.records(log_id))[start - 1:end]
            code, _ = request(url, 'POST', f'/v1/logs/{log_id}/checkpoints', token,
                              canonicalize({'checkpoint': cp, 'records': records}), timeout=3)
            assert code in (200, 201)
            assert canonicalize(writer.pending_checkpoint(log_id)[0]) == cp_bytes
            writer.recover_pending_receipt(log_id, url, token)
            assert writer.pending_checkpoint(log_id) is None
            note('accepted-but-unrecorded reply recovers exact pending receipt')
            bundle = read_bundle(writer.export_bundle(log_id, output / 'bundle'))
            report = verify(manifest, bundle.records, pins, mode=Mode.ONLINE,
                            checkpoint_envelopes=bundle.checkpoints,
                            receipt_envelopes=bundle.receipts, status_envelopes=[status],
                            online_query=latest)
            assert report.result is Result.PASS
            note('online public verification authenticates complete history')
            code, _ = request(url, 'GET', f'/v1/logs/{log_id}/receipts/{cp["checkpoint_hash"]}',
                              'synthetic-wrong-token', b'', timeout=3)
            assert code == 403
            note('receipt reads require authentication')
            address = urlsplit(url)
            context = ssl.create_default_context()
            def raw_connection():
                plain = socket.create_connection((address.hostname, address.port), timeout=4)
                try:
                    return context.wrap_socket(plain, server_hostname=address.hostname)
                except BaseException:
                    plain.close()
                    raise
            headers = (f'POST /v1/logs/{log_id}/latest HTTP/1.1\r\n'
                       f'Host: {address.netloc}\r\nAuthorization: Bearer {token}\r\n')
            with raw_connection() as connection:
                connection.sendall((headers + 'Content-Length: 16777217\r\n\r\n').encode())
                assert b' 413 ' in connection.recv(4096).split(b'\r\n')[0]
            note('oversized body rejected from headers before upload')
            held = []
            try:
                for _ in range(4):
                    connection = raw_connection()
                    held.append(connection)
                    connection.sendall((headers + 'Content-Length: 100\r\n\r\n{').encode())
                time.sleep(0.35)
                code, _ = request(url, 'POST', f'/v1/logs/{log_id}/latest', token,
                                  canonicalize({'nonce': crypto.b64url_encode(bytes(32))}), timeout=3)
                assert code == 429
                note('bounded inflight requests reject excess work')
                assert b' 400 ' in held[0].recv(4096).split(b'\r\n')[0]
                note('partial request body expires within configured deadline')
            finally:
                for connection in held:
                    connection.close()
            wait_ready()
        for label in ('wrong-host', 'expired', 'rotated'):
            control('stop', 'proxy')
            copy_file(root / 'tls' / (label + '.pem'), 'tls.pem')
            copy_file(root / 'tls' / (label + '.key'), 'tls.key')
            control('start', 'proxy')
            time.sleep(0.5)
            if label == 'rotated':
                wait_ready()
                note('replacement valid certificate accepted')
            else:
                rejected_tls(label + ' certificate rejected')
        os.environ.pop('SSL_CERT_FILE', None)
        rejected_tls('untrusted private CA rejected')
        os.environ['SSL_CERT_FILE'] = str(root / 'tls' / 'ca.pem')
        control('stop', 'witness')
        replacement = root / 'writer' / 'next-token'
        private(replacement, secrets.token_urlsafe(32).encode())
        copy_file(replacement, 'witness/token')
        control('start', 'witness')
        time.sleep(0.5)
        old_token = token
        token = replacement.read_text()
        wait_ready()
        code, _ = request(url, 'POST', f'/v1/logs/{log_id}/latest', old_token,
                          canonicalize({'nonce': crypto.b64url_encode(bytes(32))}), timeout=3)
        assert code == 403
        note('old token rejected after rotation')
        note('new token authenticates reads after rotation')
        revoked = read_json(root / 'authority' / 'revoked.json')
        revoked_startup = StartupPolicy(state_path=writer_root / 'retained.json',
            status_envelopes=(revoked,), witness_url=url, token=token)
        try:
            Writer.open_verified(writer_root / 'writer.db', key, trust_pins={log_id: pins},
                                 startup=revoked_startup).close()
        except TrustError:
            note('signed revocation blocks verified writer startup')
        else:
            raise RuntimeError('revoked writer started')
        stale_startup = StartupPolicy(state_path=writer_root / 'retained.json',
            status_envelopes=(status,), witness_url=url, token=token)
        try:
            Writer.open_verified(writer_root / 'writer.db', key, trust_pins={log_id: pins},
                                 startup=stale_startup).close()
        except TrustError:
            state = read_json(writer_root / 'retained.json')
            assert state['manifests'][manifest['manifest_hash']]['revoked'] is True
            note('stale active status cannot erase retained revocation')
        else:
            raise RuntimeError('stale active status reauthorized revoked writer')
        journal = subprocess.check_output([*ssh, 'journalctl', '--user', '--no-pager',
            '-u', 'casf-rehearsal-witness.service', '-u', 'casf-rehearsal-proxy.service',
            '-o', 'cat'], text=True)
        markers = [old_token, token, 'synthetic-wrong-token']
        markers += [(root / role / 'passphrase').read_text()
                    for role in ('authority', 'writer', 'witness')]
        if any(marker in journal for marker in markers):
            raise RuntimeError('rehearsal journal contains a synthetic secret')
        note('service journals contain no synthetic credential markers')
        return {'synthetic': True, 'checks': steps, 'log_id': log_id,
                'same_administrator': True, 'physical_power_loss_tested': False}
    finally:
        if old_ca is None:
            os.environ.pop('SSL_CERT_FILE', None)
        else:
            os.environ['SSL_CERT_FILE'] = old_ca


def main():
    if not __debug__:
        raise RuntimeError('Rehearsal checks require Python without optimization')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('root', type=Path)
    prep.add_argument('--address', required=True)
    server = sub.add_parser('serve')
    server.add_argument('root', type=Path)
    server.add_argument('--port', type=int, default=8131)
    run = sub.add_parser('exercise')
    run.add_argument('root', type=Path)
    run.add_argument('--url', required=True)
    run.add_argument('--ssh-host', required=True)
    run.add_argument('--ssh-key', type=Path, required=True)
    run.add_argument('--remote-root', required=True)
    run.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        print(json.dumps(prepare(args.root.absolute(), args.address)))
    elif args.command == 'serve':
        serve(args.root.absolute(), args.port)
    else:
        result = exercise(args.root.absolute(), args.url, args.ssh_host, args.ssh_key,
                          args.remote_root, args.output.absolute())
        (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        print(f"Completed {len(result['checks'])} cross-host checks")


if __name__ == '__main__':
    main()
