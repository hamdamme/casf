"""Online freshness client (SPEC §14).

The verifier generates a fresh random 32 byte nonce for every query
and never reuses one. The response must arrive inside the time
budget; a timeout or partition is INCONCLUSIVE, never evidence of
rollback. A replayed response fails the nonce echo check, so replay
never passes freshness. What a fresh response proves is bounded:
the witness signed this view during the query under its honesty
assumption; it does not prove the writer disclosed every committed
record.
"""

import http.client
import ipaddress
import json
import math
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from casf import crypto
from casf.canonical.jcs import parse
from casf.errors import CasfError, InconclusiveError, NoCheckpointError, SchemaError
from casf.transport import ResponseLimitError
from casf.transport import request as http_request
from casf.types import JsonObject

__all__ = [
    "InconclusiveError",
    "LatestView",
    "fetch_latest",
    "query_latest",
    "verify_latest_response",
]

_LATEST_FIELDS = {"version", "type", "nonce", "witness_id", "log_id",
                  "manifest_hash", "checkpoint_hash", "receipt_hash",
                  "checkpoint_index", "count", "head_hash", "final",
                  "responded_at"}


@dataclass
class LatestView:
    """A validated fresh witness view."""
    body: JsonObject
    checkpoint: JsonObject
    receipt: JsonObject


def fetch_latest(base_url: str, log_id: str, token: str, *,
                 timeout: float = 10.0) -> tuple[JsonObject, bytes]:
    """Query the witness; return the raw response and the nonce sent."""
    nonce = os.urandom(32)  # a fresh nonce per query, never reused
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) \
            or not math.isfinite(timeout):
        raise CasfError("timeout must be positive and finite")
    if timeout <= 0:
        raise InconclusiveError("witness query time budget is exhausted")
    request = json.dumps({"nonce": crypto.b64url_encode(nonce)}).encode()
    try:
        parts = urlsplit(base_url)
        host, port = parts.hostname, parts.port
    except ValueError as e:
        raise CasfError("invalid witness URL") from e
    if not host or parts.scheme not in {"http", "https"}:
        raise CasfError("witness URL requires an HTTP or HTTPS host")
    if parts.username is not None or parts.password is not None or port == 0:
        raise CasfError("witness URL must not contain credentials or port zero")
    if parts.scheme == "http":
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise CasfError("HTTP requires a literal loopback address; use HTTPS")
    try:
        status, payload = http_request(
            base_url, "POST", f"/v1/logs/{log_id}/latest", token,
            request, timeout=timeout)
    except (OSError, http.client.HTTPException, ResponseLimitError) as e:
        raise InconclusiveError(
            "witness unreachable within the time budget") from e
    try:
        parsed = parse(payload)
    except CasfError as e:
        raise InconclusiveError("witness answer was not valid JSON") from e
    if status != 200:
        code = parsed.get("code") if isinstance(parsed, dict) else None
        if code == "NO_CHECKPOINT":
            raise NoCheckpointError(
                "NO_CHECKPOINT: witness has no accepted checkpoint")
        raise CasfError(f"witness query rejected: {code or status}")
    if not isinstance(parsed, dict):
        raise CasfError("witness answer is not an object")
    return parsed, nonce


def _expect_envelope(env: JsonObject, hash_field: str
                     ) -> tuple[JsonObject, str, str]:
    if set(env) != {"body", hash_field, "signature"}:
        raise SchemaError(f"envelope must be exactly body, {hash_field}, "
                          "signature")
    body, digest_hex, sig = env["body"], env[hash_field], env["signature"]
    if not isinstance(body, dict) or not isinstance(digest_hex, str) \
            or not isinstance(sig, str):
        raise SchemaError("envelope field types are wrong")
    return body, digest_hex, sig


def verify_latest_response(response: JsonObject, nonce: bytes,
                           witness_pub: bytes, log_id: str) -> LatestView:
    """Validate a fresh response against the nonce just sent.

    The nonce echo is checked first: a response signed over any other
    nonce is a replay for this query and never passes freshness.
    This validates the checkpoint digest, witness receipt, and their
    bindings to the signed latest view. It does not independently verify
    the response checkpoint signature; the verifier checks supplied
    checkpoint evidence against the log key.
    """
    if set(response) != {"body", "signature", "checkpoint", "receipt"}:
        raise SchemaError("response must be exactly body, signature, "
                          "checkpoint, receipt")
    body = response["body"]
    signature = response["signature"]
    if not isinstance(body, dict) or not isinstance(signature, str):
        raise SchemaError("response field types are wrong")
    if set(body) != _LATEST_FIELDS:
        raise SchemaError("latest body fields are wrong")
    if body["version"] != 1 or body["type"] != "latest":
        raise SchemaError("unsupported latest response")
    if body["nonce"] != crypto.b64url_encode(nonce):
        raise CasfError("nonce mismatch; a replayed response never "
                        "passes freshness")
    if body["log_id"] != log_id:
        raise CasfError("response names a different log")
    if body["witness_id"] != crypto.key_id(witness_pub):
        raise CasfError("response names a different witness")
    crypto.verify_latest(witness_pub, body, signature)

    cp_body, cp_hash, _cp_sig = _expect_envelope(
        _as_object(response["checkpoint"]), "checkpoint_hash")
    rc_body, rc_hash, rc_sig = _expect_envelope(
        _as_object(response["receipt"]), "receipt_hash")
    if crypto.digest_checkpoint(cp_body) != cp_hash:
        raise CasfError("checkpoint_hash does not match the body")
    if crypto.digest_receipt(rc_body) != rc_hash:
        raise CasfError("receipt_hash does not match the body")
    crypto.verify_receipt(witness_pub, rc_body, rc_sig)
    if rc_body["checkpoint_hash"] != cp_hash:
        raise CasfError("receipt does not match the checkpoint")
    if body["checkpoint_hash"] != cp_hash or body["receipt_hash"] != rc_hash:
        raise CasfError("latest body does not match the evidence")
    if body["count"] != rc_body["count"] \
            or body["head_hash"] != rc_body["head_hash"] \
            or body["checkpoint_index"] != rc_body["checkpoint_index"]:
        raise CasfError("latest view disagrees with the receipt")
    return LatestView(body=body,
                      checkpoint=_as_object(response["checkpoint"]),
                      receipt=_as_object(response["receipt"]))


def _as_object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        raise SchemaError("expected an object")
    return value


def query_latest(base_url: str, log_id: str, token: str,
                 witness_pub: bytes, *,
                 timeout: float = 10.0) -> LatestView:
    """Fetch and validate a fresh witness view in one call."""
    response, nonce = fetch_latest(base_url, log_id, token,
                                   timeout=timeout)
    return verify_latest_response(response, nonce, witness_pub, log_id)
