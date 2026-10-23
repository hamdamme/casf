"""Reference HTTP transport for the witness (SPEC §14).

Endpoints: POST /v1/logs/{log_id}/checkpoints accepts a submission
of exactly {checkpoint, records} and returns 201 on first acceptance
or 200 on an identical retry; GET /v1/logs/{log_id}/receipts/
{checkpoint_hash} returns the stored checkpoint and receipt with
distinct 404 codes for a missing log and a missing receipt.

Errors are JSON objects of exactly {code, message, retryable}; no
stack traces, payloads, keys or tokens leave the service. Requests
are bounded by size and concurrency. Authentication is a configured
bearer credential, acceptable for this reference service over
loopback in tests and only over HTTPS in any wider deployment
(SPEC §14); the credential never appears in a URL or log line.
"""

import hmac
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from casf import crypto
from casf.canonical.limits import MAX_WITNESS_REQUEST_BYTES
from casf.errors import CasfError, SchemaError
from casf.witness import (
    ConflictError,
    NoCheckpointError,
    UnknownLogError,
    Witness,
)

__all__ = ["WitnessService", "make_server"]

_SUBMIT_RE = re.compile(r"^/v1/logs/([^/]+)/checkpoints$")
_RECEIPT_RE = re.compile(r"^/v1/logs/([^/]+)/receipts/([0-9a-f]{64})$")
_LATEST_RE = re.compile(r"^/v1/logs/([^/]+)/latest$")


class WitnessService:
    """Witness plus the transport configuration for one HTTP server."""

    def __init__(self, db_path: str | Path,
                 witness_priv: Ed25519PrivateKey, *, token: str,
                 authority_keys: dict[str, bytes] | None = None,
                 max_request_bytes: int = MAX_WITNESS_REQUEST_BYTES,
                 max_inflight: int = 64,
                 busy_timeout_ms: int = 5000) -> None:
        if not token:
            raise CasfError("a bearer credential is required")
        self.witness = Witness(db_path, witness_priv,
                               authority_keys=authority_keys,
                               busy_timeout_ms=busy_timeout_ms)
        self._token = token
        self.max_request_bytes = max_request_bytes
        self._inflight = threading.BoundedSemaphore(max_inflight)

    def close(self) -> None:
        self.witness.close()

    def check_auth(self, header: str | None) -> int:
        """0 when authorized, 401 when missing, 403 when rejected."""
        if header is None:
            return 401
        parts = header.split(None, 1)
        if len(parts) != 2 or parts[0] != "Bearer":
            return 401
        if not hmac.compare_digest(parts[1], self._token):
            return 403
        return 0


def _send(handler: BaseHTTPRequestHandler, status: int, obj: Any) -> None:
    data = json.dumps(obj).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _error(handler: BaseHTTPRequestHandler, status: int, code: str,
           message: str, *, retryable: bool = False) -> None:
    _send(handler, status,
          {"code": code, "message": message, "retryable": retryable})


def _submit(service: WitnessService, handler: BaseHTTPRequestHandler,
            log_id: str) -> None:
    length = handler.headers.get("Content-Length")
    if length is None or not length.isdigit():
        _error(handler, 400, "BAD_REQUEST", "content length is required")
        return
    if int(length) > service.max_request_bytes:
        handler.close_connection = True  # the unread body is discarded
        _error(handler, 413, "TOO_LARGE",
               "request over the configured byte limit")
        return
    raw = handler.rfile.read(int(length))
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        _error(handler, 400, "BAD_REQUEST", "request body is not valid JSON")
        return
    if not isinstance(payload, dict) \
            or set(payload) != {"checkpoint", "records"} \
            or not isinstance(payload["checkpoint"], dict) \
            or not isinstance(payload["records"], list):
        _error(handler, 400, "BAD_REQUEST",
               "submission must be exactly checkpoint and records")
        return
    try:
        receipt, accepted = service.witness._submit(
            log_id, payload["checkpoint"], payload["records"])
    except UnknownLogError:
        _error(handler, 404, "LOG_NOT_FOUND", "log is not registered")
    except ConflictError as e:
        detail = f" (stored {e.existing}, proposed {e.proposed})" \
            if e.existing else ""
        _error(handler, 409, "CONFLICT", f"{e}{detail}")
    except (SchemaError, CasfError) as e:
        _error(handler, 400, "BAD_REQUEST", str(e))
    except Exception:  # noqa: BLE001 — nothing internal may leak (§14)
        _error(handler, 503, "UNAVAILABLE", "transient service failure",
               retryable=True)
    else:
        _send(handler, 201 if accepted else 200, {"receipt": receipt})


def _read_json(service: WitnessService,
               handler: BaseHTTPRequestHandler) -> Any | None:
    """Read a bounded JSON request body; None means an error was sent."""
    length = handler.headers.get("Content-Length")
    if length is None or not length.isdigit():
        _error(handler, 400, "BAD_REQUEST", "content length is required")
        return None
    if int(length) > service.max_request_bytes:
        handler.close_connection = True  # the unread body is discarded
        _error(handler, 413, "TOO_LARGE",
               "request over the configured byte limit")
        return None
    raw = handler.rfile.read(int(length))
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        _error(handler, 400, "BAD_REQUEST", "request body is not valid JSON")
        return None


def _latest(service: WitnessService, handler: BaseHTTPRequestHandler,
            log_id: str) -> None:
    payload = _read_json(service, handler)
    if payload is None:
        return
    if not isinstance(payload, dict) or set(payload) != {"nonce"} \
            or not isinstance(payload["nonce"], str):
        _error(handler, 400, "BAD_REQUEST",
               "latest query must be exactly nonce")
        return
    try:
        nonce = crypto.b64url_decode(payload["nonce"])
        response = service.witness.latest(log_id, nonce)
    except UnknownLogError:
        _error(handler, 404, "LOG_NOT_FOUND", "log is not registered")
    except NoCheckpointError as e:
        _error(handler, 404, "NO_CHECKPOINT", str(e), retryable=True)
    except (SchemaError, CasfError) as e:
        _error(handler, 400, "BAD_REQUEST", str(e))
    except Exception:  # noqa: BLE001 — nothing internal may leak (§14)
        _error(handler, 503, "UNAVAILABLE", "transient service failure",
               retryable=True)
    else:
        _send(handler, 200, response)


def _receipt(service: WitnessService, handler: BaseHTTPRequestHandler,
             log_id: str, checkpoint_hash: str) -> None:
    try:
        if not service.witness.log_registered(log_id):
            _error(handler, 404, "LOG_NOT_FOUND", "log is not registered")
            return
        checkpoint, receipt = service.witness.receipt(checkpoint_hash)
    except CasfError:
        _error(handler, 404, "RECEIPT_NOT_FOUND",
               "no stored receipt for this checkpoint digest")
    except Exception:  # noqa: BLE001 — nothing internal may leak (§14)
        _error(handler, 503, "UNAVAILABLE", "transient service failure",
               retryable=True)
    else:
        _send(handler, 200, {"checkpoint": checkpoint, "receipt": receipt})


def _drain(service: WitnessService, handler: BaseHTTPRequestHandler) -> None:
    """Discard an unread request body so keep-alive stays clean."""
    length = handler.headers.get("Content-Length")
    if length is None or not length.isdigit():
        return
    if int(length) > service.max_request_bytes:
        handler.close_connection = True
        return
    handler.rfile.read(int(length))


def _dispatch(service: WitnessService, handler: BaseHTTPRequestHandler,
              method: str) -> None:
    auth = service.check_auth(handler.headers.get("Authorization"))
    if auth != 0:
        _drain(service, handler)
    if auth == 401:
        _error(handler, 401, "UNAUTHENTICATED",
               "bearer credential required")
        return
    if auth != 0:
        _error(handler, 403, "FORBIDDEN", "credential rejected")
        return
    if not service._inflight.acquire(blocking=False):
        _error(handler, 429, "THROTTLED", "service at capacity; retry later",
               retryable=True)
        return
    try:
        submit = _SUBMIT_RE.match(handler.path)
        receipt = _RECEIPT_RE.match(handler.path)
        latest = _LATEST_RE.match(handler.path)
        if method == "POST" and submit:
            _submit(service, handler, submit.group(1))
        elif method == "POST" and latest:
            _latest(service, handler, latest.group(1))
        elif method == "GET" and receipt:
            _receipt(service, handler, receipt.group(1), receipt.group(2))
        else:
            _error(handler, 404, "NOT_FOUND", "unknown endpoint")
    finally:
        service._inflight.release()


def make_server(service: WitnessService, host: str,
                port: int) -> ThreadingHTTPServer:
    """Build the threaded HTTP server for one witness service."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            """Never log request lines or bodies by default (SPEC §13)."""

        def do_POST(self) -> None:
            _dispatch(service, self, "POST")

        def do_GET(self) -> None:
            _dispatch(service, self, "GET")

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server
