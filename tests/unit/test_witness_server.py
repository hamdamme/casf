"""R05, R06 and R10: admission, transport bounds and safe shutdown."""

import concurrent.futures
import http.client
import json
import socket
import threading
import time
from contextlib import contextmanager

import pytest

from casf import crypto
from casf.witness.http import WitnessService, make_server
from tests.unit.test_writer import AUTH_PUB, LOG_ID, WIT, _manifest_envelope

TOKEN = "synthetic-server-token"


@contextmanager
def running(tmp_path, **options):
    service = WitnessService(tmp_path / "witness.db", WIT, token=TOKEN,
                             authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
                             **options)
    service.witness.register_log(_manifest_envelope())
    server = make_server(service, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield service, server
    finally:
        server.shutdown()
        thread.join(5)
        assert not thread.is_alive()
        server.server_close()
        service.close()


def request(server, body=b"{}", *, token=TOKEN):
    conn = http.client.HTTPConnection(*server.server_address, timeout=5)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        conn.request("POST", f"/v1/logs/{LOG_ID}/latest", body, headers)
        response = conn.getresponse()
        return response.status, json.loads(response.read())
    finally:
        conn.close()


def headers(length, token=TOKEN):
    return (f"POST /v1/logs/{LOG_ID}/latest HTTP/1.1\r\nHost: localhost\r\n"
            f"Authorization: Bearer {token}\r\nContent-Length: {length}\r\n\r\n").encode()


def read_response(sock):
    response = http.client.HTTPResponse(sock)
    response.begin()
    return response.status, response.getheader("Content-Type"), response.read()


def test_slow_body_has_total_deadline(tmp_path):
    with (
        running(tmp_path, request_timeout=0.15) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as sock,
    ):
        sock.sendall(headers(100) + b"{")
        status, content_type, body = read_response(sock)
        assert status == 400
        assert content_type == "application/json"
        assert json.loads(body)["code"] == "BAD_REQUEST"
        assert request(server)[0] == 400


def test_large_body_rejected_before_upload(tmp_path):
    with (
        running(tmp_path, max_request_bytes=64) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as sock,
    ):
        sock.sendall(headers(100000))
        status, _, body = read_response(sock)
        assert status == 413
        assert json.loads(body)["code"] == "TOO_LARGE"


def test_auth_rejected_before_upload(tmp_path):
    with (
        running(tmp_path) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as sock,
    ):
        sock.sendall(headers(100, token="wrong"))
        status, _, body = read_response(sock)
        assert status == 403
        assert TOKEN.encode() not in body


def test_real_overload_is_json_429(tmp_path, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    with running(tmp_path, max_inflight=1) as (service, server):
        def blocked(*args):
            entered.set()
            assert release.wait(5)
            return {}
        monkeypatch.setattr(service.witness, "latest", blocked)
        body = json.dumps({"nonce": crypto.b64url_encode(b"x" * 32)}).encode()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(request, server, body)
            try:
                assert entered.wait(3)
                status, error = request(server, body)
                assert status == 429
                assert error == {"code": "THROTTLED",
                                 "message": "service at capacity; retry later",
                                 "retryable": True}
            finally:
                release.set()
            assert first.result()[0] == 200


def test_disconnect_releases_body_slot(tmp_path):
    with running(tmp_path, max_inflight=1) as (_, server):
        sock = socket.create_connection(server.server_address, timeout=3)
        sock.sendall(headers(100) + b"{")
        sock.close()
        deadline = time.monotonic() + 3
        while True:
            status, _ = request(server)
            if status != 429 or time.monotonic() >= deadline:
                break
            time.sleep(0.01)
        assert status == 400


def test_malformed_http_is_minimal_server_error(tmp_path, caplog):
    secret = b"synthetic-secret-marker"
    with (
        running(tmp_path) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as sock,
    ):
        sock.sendall(b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: "
                     + secret + b"\r\n\r\n")
        status, content_type, body = read_response(sock)
        assert status == 400
        assert content_type.startswith("text/plain")
        assert secret not in body
    assert secret.decode() not in caplog.text


def test_connection_limit_returns_minimal_503(tmp_path):
    with (
        running(tmp_path, max_connections=2) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as idle,
    ):
        idle.sendall(b"GET / HTTP/1.1\r\n")
        deadline = time.monotonic() + 3
        while len(server._server.server_state.connections) < 1:
            assert time.monotonic() < deadline
            time.sleep(0.01)
        with socket.create_connection(server.server_address, timeout=3) as sock:
            sock.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            status, content_type, body = read_response(sock)
            assert status == 503
            assert content_type.startswith("text/plain")
            assert b"Traceback" not in body


def test_shutdown_waits_for_active_work(tmp_path, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    with running(tmp_path) as (service, server):
        def blocked(*args):
            entered.set()
            assert release.wait(5)
            return {}
        monkeypatch.setattr(service.witness, "latest", blocked)
        body = json.dumps({"nonce": crypto.b64url_encode(b"x" * 32)}).encode()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            operation = pool.submit(request, server, body)
            assert entered.wait(3)
            stopped = pool.submit(server.shutdown)
            try:
                time.sleep(0.1)
                assert not stopped.done()
            finally:
                release.set()
            assert operation.result()[0] == 200
            stopped.result(timeout=5)
        server.server_close()
        assert server._socket.fileno() == -1
        assert not any(t.is_alive() for t in server._pool._threads)


def test_internal_exception_is_sanitized(tmp_path, monkeypatch, caplog):
    with running(tmp_path) as (service, server):
        def fail(*args):
            raise RuntimeError("synthetic-private-marker")
        monkeypatch.setattr(service.witness, "latest", fail)
        body = json.dumps({"nonce": crypto.b64url_encode(b"x" * 32)}).encode()
        status, error = request(server, body)
        assert status == 503
        assert error["retryable"] is True
        assert "synthetic-private-marker" not in json.dumps(error)
    assert "synthetic-private-marker" not in caplog.text


@pytest.mark.parametrize("option", [
    {"max_inflight": 0}, {"max_request_bytes": 0},
    {"request_timeout": 0}, {"request_timeout": float("nan")},
    {"max_connections": 1},
])
def test_invalid_limits_rejected_before_database_open(tmp_path, option):
    with pytest.raises(ValueError):
        WitnessService(tmp_path / "absent.db", WIT, token=TOKEN, **option)
    assert not (tmp_path / "absent.db").exists()


def test_cancelled_request_retains_worker_slot(tmp_path, monkeypatch):
    import asyncio

    service = WitnessService(tmp_path / "cancel.db", WIT, token=TOKEN, max_inflight=1)
    server = make_server(service, "127.0.0.1", 0)
    entered = threading.Event()
    release = threading.Event()

    def blocked(*args):
        entered.set()
        assert release.wait(5)
        return {}

    monkeypatch.setattr(service.witness, "latest", blocked)
    body = json.dumps({"nonce": crypto.b64url_encode(b"x" * 32)}).encode()
    scope = {"type": "http", "method": "POST", "path": f"/v1/logs/{LOG_ID}/latest",
             "headers": [(b"authorization", f"Bearer {TOKEN}".encode()),
                         (b"content-length", str(len(body)).encode())]}

    async def exercise():
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        task = asyncio.create_task(server._application(scope, receive, send))
        try:
            assert await asyncio.to_thread(entered.wait, 3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not service._inflight.acquire(blocking=False)
        finally:
            release.set()
            await asyncio.to_thread(server.server_close)
        assert service._inflight.acquire(blocking=False)
        service._inflight.release()

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        server.server_close()
        service.close()


def test_deep_json_rejected_without_internal_details(tmp_path):
    with running(tmp_path, max_request_bytes=20000) as (_, server):
        status, error = request(server, b"[" * 5000 + b"]" * 5000)
        assert status == 400
        assert error["code"] == "BAD_REQUEST"
        assert "RecursionError" not in json.dumps(error)


def test_duplicate_auth_header_is_rejected(tmp_path):
    with (
        running(tmp_path) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as sock,
    ):
        packet = headers(0).replace(b"Content-Length:", b"Authorization: Bearer extra\r\nContent-Length:")
        sock.sendall(packet)
        status, _, body = read_response(sock)
        assert status == 400
        assert json.loads(body)["code"] == "BAD_REQUEST"


def test_chunked_post_without_length_is_rejected(tmp_path):
    with (
        running(tmp_path) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as sock,
    ):
        sock.sendall((f"POST /v1/logs/{LOG_ID}/latest HTTP/1.1\r\nHost: localhost\r\n"
                      f"Authorization: Bearer {TOKEN}\r\nTransfer-Encoding: chunked\r\n\r\n").encode())
        status, _, body = read_response(sock)
        assert status == 400
        assert json.loads(body)["code"] == "BAD_REQUEST"


def test_close_before_start_releases_listener(tmp_path):
    service = WitnessService(tmp_path / "close.db", WIT, token=TOKEN)
    server = make_server(service, "127.0.0.1", 0)
    try:
        server.server_close()
        server.server_close()
        assert server._socket.fileno() == -1
        with pytest.raises(RuntimeError):
            server.serve_forever()
    finally:
        service.close()


def test_incomplete_headers_have_deadline(tmp_path):
    with (
        running(tmp_path, header_timeout=0.15) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as sock,
    ):
        sock.sendall(b"GET / HTTP/1.1\r\nHost: local")
        assert sock.recv(1) == b""
        assert request(server)[0] == 400


def test_silent_connections_are_bounded(tmp_path):
    with running(tmp_path, max_connections=2) as (_, server):
        sockets = []
        try:
            for _ in range(2):
                sockets.append(socket.create_connection(server.server_address, timeout=3))
            deadline = time.monotonic() + 3
            while len(server._server.server_state.connections) < 2:
                assert time.monotonic() < deadline
                time.sleep(0.01)
            with socket.create_connection(server.server_address, timeout=3) as extra:
                assert extra.recv(1) == b""
            assert len(server._server.server_state.connections) == 2
        finally:
            for sock in sockets:
                sock.close()


def test_next_request_headers_have_deadline(tmp_path):
    with (
        running(tmp_path, header_timeout=0.2) as (_, server),
        socket.create_connection(server.server_address, timeout=3) as sock,
    ):
        sock.sendall(headers(2) + b"{}")
        assert read_response(sock)[0] == 400
        sock.sendall(b"GET / HTTP/1.1\r\nHost: local")
        assert sock.recv(1) == b""


def test_long_operation_is_not_a_header_timeout(tmp_path, monkeypatch):
    with running(tmp_path, header_timeout=0.05) as (service, server):
        def delayed(*args):
            time.sleep(0.15)
            return {}
        monkeypatch.setattr(service.witness, "latest", delayed)
        body = json.dumps({"nonce": crypto.b64url_encode(b"x" * 32)}).encode()
        assert request(server, body)[0] == 200
