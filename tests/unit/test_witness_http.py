"""SPEC §14 transport: HTTP submission and receipt retrieval.

Covers the reference HTTP service over loopback: authenticated
submit with 201 on first acceptance and 200 on an identical retry,
distinct 404 codes for missing logs and missing receipts, 400
validation, 409 conflict, 413 oversized, 429 throttling, and the
{code, message, retryable} error shape without internal details.
"""

import http.client
import json
import threading

import pytest

from casf import crypto
from casf.witness.http import WitnessService, make_server
from tests.status import register_active
from tests.unit.test_witness import _checkpoint, _records
from tests.unit.test_writer import (
    AUTH,
    AUTH_PUB,
    LOG_ID,
    WIT,
    _append,
    _manifest_envelope,
    _writer,
)

TOKEN = "test-bearer-token"  # loopback test credential, never a real one


@pytest.fixture()
def service(tmp_path):
    svc = WitnessService(tmp_path / "wit.db", WIT, token=TOKEN,
                         authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
                         max_request_bytes=4096, max_inflight=8)
    register_active(svc.witness, _manifest_envelope(), AUTH)
    yield svc
    svc.close()


@pytest.fixture()
def conn(service):
    server = make_server(service, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    c = http.client.HTTPConnection("127.0.0.1", server.server_port,
                                   timeout=10)
    yield c
    c.close()
    server.shutdown()
    server.server_close()


def _post(conn, path, obj, token=TOKEN, raw=None):
    body = raw if raw is not None else json.dumps(obj).encode()
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    conn.request("POST", path, body=body, headers=headers)
    resp = conn.getresponse()
    payload = resp.read()
    return resp.status, json.loads(payload) if payload else {}


def _get(conn, path, token=TOKEN):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    conn.request("GET", path, headers=headers)
    resp = conn.getresponse()
    payload = resp.read()
    return resp.status, json.loads(payload) if payload else {}


def _submission(tmp_path, count=2):
    w = _writer(tmp_path / "w.db")
    for n in range(1, count + 1):
        _append(w, n)
    cp = _checkpoint(w, index=0, count=count)
    return w, {"checkpoint": cp, "records": _records(w, 1, count)}


# ---------------- submit (POST checkpoints) ----------------

def test_submit_created_then_ok_on_retry(tmp_path, conn):
    _, body = _submission(tmp_path)
    status, data = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
    assert status == 201
    assert data["receipt"]["body"]["count"] == 2
    status, again = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
    assert status == 200  # identical retry, same stored receipt
    assert again["receipt"] == data["receipt"]

def test_submit_requires_auth(tmp_path, conn):
    _, body = _submission(tmp_path, 1)
    status, err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body,
                        token=None)
    assert status == 401
    status, err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body,
                        token="wrong-token")
    assert status == 403
    assert set(err) == {"code", "message", "retryable"}

def test_submit_bad_json_is_400(conn):
    status, err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", None,
                        raw=b"{not json")
    assert status == 400
    assert err["code"] == "BAD_REQUEST"
    assert err["retryable"] is False


def test_submit_duplicate_json_key_is_rejected_before_acceptance(tmp_path, conn):
    _writer_db, body = _submission(tmp_path, 1)
    checkpoint = json.dumps(body["checkpoint"], separators=(",", ":"))
    records = json.dumps(body["records"], separators=(",", ":"))
    raw = (f'{{"checkpoint":{checkpoint},"checkpoint":{checkpoint},'
           f'"records":{records}}}').encode()
    status, err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", None, raw=raw)
    assert status == 400
    assert err["code"] == "BAD_REQUEST"
    checkpoint_hash = body["checkpoint"]["checkpoint_hash"]
    status, missing = _get(
        conn, f"/v1/logs/{LOG_ID}/receipts/{checkpoint_hash}")
    assert status == 404
    assert missing["code"] == "RECEIPT_NOT_FOUND"


def test_latest_duplicate_nonce_is_rejected_before_signing(tmp_path, conn):
    _writer_db, body = _submission(tmp_path, 1)
    status, _ = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
    assert status == 201
    nonce = crypto.b64url_encode(b"n" * 32)
    raw = f'{{"nonce":"{nonce}","nonce":"{nonce}"}}'.encode()
    status, err = _post(conn, f"/v1/logs/{LOG_ID}/latest", None, raw=raw)
    assert status == 400
    assert err["code"] == "BAD_REQUEST"

def test_submit_wrong_shape_is_400(conn):
    status, _err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints",
                        {"checkpoint": {}, "records": [], "extra": 1})
    assert status == 400

def test_submit_validation_failure_is_400(tmp_path, conn):
    _w, body = _submission(tmp_path, 1)
    body["records"][0]["body"]["payload"] = {"n": 999}  # breaks digest
    status, _err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
    assert status == 400

def test_submit_conflict_is_409(tmp_path, conn):
    w, body = _submission(tmp_path, 2)
    _post(conn, f"/v1/logs/{LOG_ID}/checkpoints",
          {"checkpoint": _checkpoint(w, index=0, count=1),
           "records": _records(w, 1, 1)})
    status, err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
    assert status == 409
    assert err["code"] == "CONFLICT"
    assert err["retryable"] is False

def test_submit_unknown_log_is_404(tmp_path, conn):
    _, body = _submission(tmp_path, 1)
    other = "123e4567-e89b-42d3-a456-426614174999"
    status, err = _post(conn, f"/v1/logs/{other}/checkpoints", body)
    assert status == 404
    assert err["code"] == "LOG_NOT_FOUND"

def test_submit_oversized_is_413(conn):
    status, err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", None,
                        raw=b" " * 5000)  # over the 4096 byte test limit
    assert status == 413
    assert err["code"] == "TOO_LARGE"
    assert err["retryable"] is False

def test_submit_throttled_is_429(tmp_path, conn, service):
    _, body = _submission(tmp_path, 1)
    service._inflight.acquire()  # saturate all eight slots by hand
    for _ in range(7):
        service._inflight.acquire()
    try:
        status, err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
        assert status == 429
        assert err["code"] == "THROTTLED"
        assert err["retryable"] is True
    finally:
        for _ in range(8):
            service._inflight.release()

def test_error_shape_never_leaks_internals(conn):
    status, err = _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", None,
                        raw=b"\x00\xff broken")
    assert status == 400
    assert set(err) == {"code", "message", "retryable"}
    assert "Traceback" not in err["message"]
    assert TOKEN not in json.dumps(err)

# ---------------- retrieval (GET receipts) ----------------

def test_receipt_roundtrip(tmp_path, conn):
    _, body = _submission(tmp_path, 2)
    _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
    cp_hash = body["checkpoint"]["checkpoint_hash"]
    status, data = _get(
        conn, f"/v1/logs/{LOG_ID}/receipts/{cp_hash}")
    assert status == 200
    assert data["checkpoint"] == body["checkpoint"]
    assert data["receipt"]["body"]["checkpoint_hash"] == cp_hash
    crypto.verify_receipt(
        crypto.public_key_raw(WIT), data["receipt"]["body"],
        data["receipt"]["signature"])

def test_receipt_missing_is_distinct_404(tmp_path, conn):
    _, body = _submission(tmp_path, 1)
    _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
    status, err = _get(conn, f"/v1/logs/{LOG_ID}/receipts/{'ab' * 32}")
    assert status == 404
    assert err["code"] == "RECEIPT_NOT_FOUND"

def test_receipt_unknown_log_is_distinct_404(conn):
    other = "123e4567-e89b-42d3-a456-426614174999"
    status, err = _get(conn, f"/v1/logs/{other}/receipts/{'ab' * 32}")
    assert status == 404
    assert err["code"] == "LOG_NOT_FOUND"

def test_receipt_requires_auth(tmp_path, conn):
    _, body = _submission(tmp_path, 1)
    _post(conn, f"/v1/logs/{LOG_ID}/checkpoints", body)
    cp_hash = body["checkpoint"]["checkpoint_hash"]
    status, _ = _get(conn, f"/v1/logs/{LOG_ID}/receipts/{cp_hash}",
                     token=None)
    assert status == 401

def test_unknown_path_is_404(conn):
    status, err = _get(conn, "/v1/nope")
    assert status == 404
    assert err["code"] == "NOT_FOUND"
