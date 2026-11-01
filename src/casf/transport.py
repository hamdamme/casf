"""Bounded synchronous HTTP transport for witness requests.

The caller's time budget covers name resolution, connection setup, TLS,
request writing, and response parsing. Response bodies and headers are
bounded independently of the server's framing claims.
"""

from __future__ import annotations

import http.client
import ipaddress
import math
import socket
import ssl
import threading
import time
from concurrent.futures import Future
from typing import Any, cast
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 64 * 1024
_MAX_RESPONSE_LINE = 4096
_MAX_RESPONSE_HEADERS = 32
_RESOLVER_SLOTS = threading.BoundedSemaphore(4)


class ResponseLimitError(ValueError):
    """The peer exceeded the configured response bound."""


class _BoundedResponseReader:
    """Apply per response line and header count limits without globals."""

    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self._reading_headers = False
        self._header_lines = 0

    def start_status(self) -> None:
        self._reading_headers = False
        self._header_lines = 0

    def readline(self, size: int = -1) -> bytes:
        limit = _MAX_RESPONSE_LINE + 1
        line = self._stream.readline(limit if size < 0 else min(size, limit))
        if len(line) > _MAX_RESPONSE_LINE:
            raise http.client.LineTooLong("status or header line")
        status_line = line.startswith(b"HTTP/")
        if not self._reading_headers or status_line:
            self._header_lines = 0
            self._reading_headers = True
        elif line not in (b"\r\n", b"\n"):
            self._header_lines += 1
            if self._header_lines > _MAX_RESPONSE_HEADERS:
                raise http.client.HTTPException("too many response headers")
        return cast(bytes, line)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class _BoundedResponse(http.client.HTTPResponse):
    def begin(self) -> None:
        stream: Any = self.fp
        if not isinstance(stream, _BoundedResponseReader):
            stream = _BoundedResponseReader(stream)
            self.fp = cast(Any, stream)
        stream.start_status()
        super().begin()


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("witness request exceeded its total time budget")
    return remaining


def _interrupt(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass


def _addresses(host: str, port: int, deadline: float) -> list[tuple[Any, ...]]:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)

    if not _RESOLVER_SLOTS.acquire(blocking=False):
        raise TimeoutError("witness name resolution is at capacity")
    result: Future[list[tuple[Any, ...]]] = Future()

    def resolve() -> None:
        try:
            result.set_result(socket.getaddrinfo(
                host, port, type=socket.SOCK_STREAM))
        except OSError as exc:  # pass resolver failures to caller
            result.set_exception(exc)
        finally:
            _RESOLVER_SLOTS.release()

    threading.Thread(target=resolve, name="casf-dns", daemon=True).start()
    try:
        return result.result(timeout=_remaining(deadline))
    except TimeoutError:
        raise TimeoutError("witness name resolution exceeded its time budget") from None


def _connected_socket(host: str, port: int, *, https: bool,
                      deadline: float) -> socket.socket:
    last_error: OSError | None = None
    for family, socktype, proto, _canonname, address in _addresses(host, port, deadline):
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(_remaining(deadline))
            sock.connect(address)
            if not https:
                return sock
            wrapped = ssl.create_default_context().wrap_socket(
                sock, server_hostname=host, do_handshake_on_connect=False)
            wrapped.settimeout(_remaining(deadline))
            timer = threading.Timer(_remaining(deadline), _interrupt,
                                    args=(wrapped,))
            timer.daemon = True
            timer.start()
            try:
                wrapped.do_handshake()
                wrapped.settimeout(_remaining(deadline))
                return wrapped
            finally:
                timer.cancel()
        except OSError as exc:
            last_error = exc
            sock.close()
    if last_error is not None:
        raise last_error
    raise OSError("witness host resolved to no stream addresses")


def request(base_url: str, method: str, path: str, token: str, body: bytes,
            *, timeout: float) -> tuple[int, bytes]:
    """Perform one bounded witness request without following redirects."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    try:
        parts = urlsplit(base_url)
        host, port = parts.hostname, parts.port
    except ValueError as exc:
        raise ValueError("invalid witness URL") from exc
    if (not host or parts.scheme not in {"http", "https"}
            or parts.username is not None or parts.password is not None
            or port == 0):
        raise ValueError("witness URL requires a valid HTTP or HTTPS host")
    https = parts.scheme == "https"
    if not https:
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise ValueError("HTTP requires a literal loopback address; use HTTPS")

    port = port if port is not None else (443 if https else 80)
    deadline = time.monotonic() + timeout
    sock = _connected_socket(host, port, https=https, deadline=deadline)
    conn_type = http.client.HTTPSConnection if https else http.client.HTTPConnection
    conn = conn_type(host, port, timeout=_remaining(deadline))
    conn.response_class = _BoundedResponse
    conn.sock = sock
    timer = threading.Timer(_remaining(deadline), _interrupt, args=(sock,))
    timer.daemon = True
    timer.start()
    try:
        conn.request(method, path, body=body,
                     headers={"Content-Type": "application/json",
                              "Authorization": f"Bearer {token}",
                              "Connection": "close"})
        response = conn.getresponse()
        if response.getheader("Transfer-Encoding") is not None:
            raise http.client.HTTPException(
                "transfer-encoded witness responses are unsupported")
        length = response.getheader("Content-Length")
        if length is not None:
            if not length.isascii() or not length.isdecimal():
                raise http.client.HTTPException("invalid response Content-Length")
            if len(length) > 20 or int(length) > MAX_RESPONSE_BYTES:
                raise ResponseLimitError("witness response exceeds its byte limit")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ResponseLimitError("witness response exceeds its byte limit")
        _remaining(deadline)
        return response.status, payload
    finally:
        timer.cancel()
        conn.close()
