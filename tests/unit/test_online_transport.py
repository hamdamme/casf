"""Online transport encrypts credentials and authenticates HTTPS peers."""

import contextlib
import datetime
import http.server
import ipaddress
import ssl
import threading

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from casf import online
from casf.errors import CasfError, InconclusiveError

TOKEN = "transport-test-token"
LOG_ID = "123e4567-e89b-42d3-a456-426614174000"


@pytest.fixture()
def certificate(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CASF transport test")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([
                x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .sign(key, hashes.SHA256()))
    cert_path = tmp_path / "certificate.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    return cert_path, key_path


@contextlib.contextmanager
def server(certificate=None, redirect=None):
    received = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.headers.get("Authorization"))
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(302 if redirect else 200)
            if redirect:
                self.send_header("Location", redirect)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):
            pass

    service = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    if certificate:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(*certificate)
        service.socket = context.wrap_socket(service.socket, server_side=True)
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    try:
        yield service.server_port, received
    finally:
        service.shutdown()
        service.server_close()
        thread.join(timeout=5)


def trust_certificate(monkeypatch, certificate):
    context = ssl.create_default_context(cafile=str(certificate[0]))
    monkeypatch.setattr(online.ssl, "create_default_context", lambda: context)


def test_https_accepts_trusted_certificate(certificate, monkeypatch):
    trust_certificate(monkeypatch, certificate)
    with server(certificate) as (port, received):
        response, nonce = online.fetch_latest(f"https://127.0.0.1:{port}", LOG_ID, TOKEN)
        assert response == {} and len(nonce) == 32
        assert received == [f"Bearer {TOKEN}"]


def test_https_rejects_untrusted_certificate(certificate):
    with server(certificate) as (port, received):
        with pytest.raises(InconclusiveError) as exc:
            online.fetch_latest(f"https://127.0.0.1:{port}", LOG_ID, TOKEN)
        assert isinstance(exc.value.__cause__, ssl.SSLCertVerificationError)
        assert received == []
        assert TOKEN not in str(exc.value)


def test_https_rejects_hostname_mismatch(certificate, monkeypatch):
    trust_certificate(monkeypatch, certificate)
    with server(certificate) as (port, received):
        with pytest.raises(InconclusiveError) as exc:
            online.fetch_latest(f"https://localhost:{port}", LOG_ID, TOKEN)
        assert isinstance(exc.value.__cause__, ssl.SSLCertVerificationError)
        assert received == []


def test_https_never_sends_token_to_plain_http():
    with server() as (port, received):
        with pytest.raises(InconclusiveError):
            online.fetch_latest(f"https://127.0.0.1:{port}", LOG_ID, TOKEN, timeout=2)
        assert received == []


def test_https_does_not_follow_plain_http_redirect(certificate, monkeypatch):
    trust_certificate(monkeypatch, certificate)
    with (
        server() as (plain_port, plain_received),
        server(certificate, f"http://127.0.0.1:{plain_port}") as (port, received),
    ):
        with pytest.raises(CasfError):
            online.fetch_latest(f"https://127.0.0.1:{port}", LOG_ID, TOKEN)
        assert received == [f"Bearer {TOKEN}"]
        assert plain_received == []


def test_http_loopback_still_works():
    with server() as (port, received):
        response, _ = online.fetch_latest(f"http://127.0.0.1:{port}", LOG_ID, TOKEN)
        assert response == {} and received == [f"Bearer {TOKEN}"]


@pytest.mark.parametrize("url", [
    "http://example.com", "http://192.168.1.2", "http://localhost",
    "http://127.0.0.1.example.com", "http://[::ffff:192.168.1.2]",
    "ftp://127.0.0.1", "//127.0.0.1", "https://user:password@example.com",
    "https://127.0.0.1:0", "https://127.0.0.1:invalid", "https://[broken",
])
def test_unsafe_url_rejected_before_connection(url, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("unsafe URL attempted a connection")

    monkeypatch.setattr(online.http.client, "HTTPConnection", unexpected)
    monkeypatch.setattr(online.http.client, "HTTPSConnection", unexpected)
    with pytest.raises(CasfError):
        online.fetch_latest(url, LOG_ID, TOKEN)
