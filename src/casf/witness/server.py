"""Optional ASGI transport with bounded admission and safe witness shutdown.

R05, R06 and R10: network cancellation must not interrupt a witness commit.
Only authenticated requests with a complete bounded body enter the worker pool.
"""

from __future__ import annotations

import asyncio
import socket
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future, ThreadPoolExecutor
from io import BytesIO
from typing import Any

from casf.errors import CasfError
from casf.witness.http import WitnessService, _dispatch, _error, _Request

Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class WitnessServer:
    """Serve one witness; close the service only after server_close returns."""

    def __init__(self, service: WitnessService, host: str, port: int) -> None:
        try:
            import uvicorn
        except ImportError as exc:
            raise CasfError("install casf[witness] to run the HTTP witness") from exc

        from casf.witness.protocol import bounded_protocol

        self.service = service
        self._pool = ThreadPoolExecutor(max_workers=service.max_inflight,
                                        thread_name_prefix="casf-witness")
        self._finished = threading.Event()
        self._lifecycle = threading.Lock()
        self._running = False
        self._closed = False
        self._thread_id: int | None = None
        self._socket = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET,
                                     socket.SOCK_STREAM)
        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((host, port))
            self._socket.listen(service.max_connections)
            self._socket.setblocking(False)
            address = self._socket.getsockname()
            self.server_address = (str(address[0]), int(address[1]))
            self.server_port = self.server_address[1]
            config = uvicorn.Config(
                self._application, interface="asgi3", loop="asyncio", ws="none",
                http=bounded_protocol(service.max_connections, service.header_timeout),
                lifespan="off", access_log=False, log_config=None,
                proxy_headers=False, server_header=False,
                limit_concurrency=service.max_connections,
                backlog=service.max_connections, timeout_keep_alive=5,
                h11_max_incomplete_event_size=16384,
                timeout_graceful_shutdown=None,
            )
            self._server = uvicorn.Server(config)
        except BaseException:
            self._socket.close()
            self._pool.shutdown(wait=True)
            raise

    async def _respond(self, request: _Request, send: Send) -> None:
        headers = [(b"content-type", b"application/json"),
                   (b"content-length", str(len(request.data)).encode())]
        if request.close_connection:
            headers.append((b"connection", b"close"))
        await send({"type": "http.response.start", "status": request.status,
                    "headers": headers})
        await send({"type": "http.response.body", "body": request.data})

    async def _reject(self, request: _Request, send: Send, status: int,
                      code: str, message: str, *, retryable: bool = False) -> None:
        # Discard unread bodies by closing the connection, not by blocking a worker.
        request.close_connection = True
        _error(request, status, code, message, retryable=retryable)
        await self._respond(request, send)

    async def _application(self, scope: dict[str, Any], receive: Receive,
                           send: Send) -> None:
        request = _Request("", {})
        try:
            await self._handle(scope, receive, send, request)
        except (OSError, asyncio.CancelledError):
            # A disconnected caller can retry the exact bytes to recover a receipt.
            raise
        except Exception:  # noqa: BLE001 — sanitize errors at the transport boundary
            # No exception text, request target, or body enters an error response.
            await self._reject(request, send, 503, "UNAVAILABLE",
                               "transient service failure", retryable=True)

    async def _handle(self, scope: dict[str, Any], receive: Receive,
                      send: Send, request: _Request) -> None:
        if scope["type"] != "http":
            raise RuntimeError("unsupported ASGI scope")
        for name, value in scope["headers"]:
            key = name.decode("ascii").lower()
            if key in request.headers and key in ("authorization", "content-length"):
                await self._reject(request, send, 400, "BAD_REQUEST", "duplicate request header")
                return
            request.headers[key] = value.decode("latin1")
        auth = self.service.check_auth(request.headers.get("authorization"))
        if auth:
            await self._reject(request, send, auth,
                               "UNAUTHENTICATED" if auth == 401 else "FORBIDDEN",
                               "bearer credential required" if auth == 401 else "credential rejected")
            return
        if not self.service._inflight.acquire(blocking=False):
            await self._reject(request, send, 429, "THROTTLED",
                               "service at capacity; retry later", retryable=True)
            return
        worker: Future[None] | None = None
        try:
            length = request.headers.get("content-length")
            if scope["method"] == "POST" and (length is None or not length.isascii()
                                               or not length.isdecimal()):
                await self._reject(request, send, 400, "BAD_REQUEST", "content length is required")
                return
            if length is not None:
                if not length.isascii() or not length.isdecimal() or len(length) > 20:
                    await self._reject(request, send, 400, "BAD_REQUEST", "invalid content length")
                    return
                if int(length) > self.service.max_request_bytes:
                    await self._reject(request, send, 413, "TOO_LARGE",
                                       "request over the configured byte limit")
                    return
            body = bytearray()
            try:
                async with asyncio.timeout(self.service.request_timeout):
                    while True:
                        event = await receive()
                        if event["type"] == "http.disconnect":
                            return
                        chunk = event.get("body", b"")
                        if len(body) + len(chunk) > self.service.max_request_bytes:
                            await self._reject(request, send, 413, "TOO_LARGE",
                                               "request over the configured byte limit")
                            return
                        body.extend(chunk)
                        if not event.get("more_body", False):
                            break
            except TimeoutError:
                await self._reject(request, send, 400, "BAD_REQUEST", "request body deadline exceeded")
                return
            if length is not None and len(body) != int(length):
                await self._reject(request, send, 400, "BAD_REQUEST", "incomplete request body")
                return
            request.path = scope.get("raw_path", scope["path"].encode()).decode("ascii")
            if scope.get("query_string"):
                request.path += "?" + scope["query_string"].decode("ascii")
            request.headers = {key.title(): value for key, value in request.headers.items()}
            request.rfile = BytesIO(body)
            worker = self._pool.submit(_dispatch, self.service, request, scope["method"])
            # The slot belongs to the worker until completion, even if ASGI is cancelled.
            worker.add_done_callback(lambda _: self.service._inflight.release())
            await asyncio.shield(asyncio.wrap_future(worker))
            await self._respond(request, send)
        finally:
            if worker is None:
                self.service._inflight.release()

    def serve_forever(self) -> None:
        with self._lifecycle:
            if self._closed or self._running:
                raise RuntimeError("server cannot be started twice")
            self._running = True
            self._thread_id = threading.get_ident()
        try:
            self._server.run(sockets=[self._socket])
        finally:
            # Do not close SQLite while an accepted operation can still commit.
            self._pool.shutdown(wait=True)
            self._socket.close()
            with self._lifecycle:
                self._closed = True
            self._finished.set()

    def shutdown(self) -> None:
        """Stop admission and wait for accepted work; call from another thread."""
        with self._lifecycle:
            if self._thread_id == threading.get_ident() and not self._finished.is_set():
                raise RuntimeError("shutdown must run outside the serving thread")
            self._server.should_exit = True
            running = self._running
        if running:
            self._finished.wait()

    def server_close(self) -> None:
        """Release sockets and workers before the caller closes its witness."""
        with self._lifecycle:
            self._closed = True
        self.shutdown()
        self._socket.close()
        self._pool.shutdown(wait=True)
