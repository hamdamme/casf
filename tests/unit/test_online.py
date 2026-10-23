"""R06 / SPEC §14 online freshness: nonce queries and T11.

A fresh response proves the witness signed this view during the
query. Replay never passes freshness, a timeout or partition is
inconclusive rather than evidence of rollback, and a response to a
different nonce is rejected.
"""

import http.server
import os
import threading
import time

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.online import (
    InconclusiveError,
    query_latest,
    verify_latest_response,
)
from casf.witness import NoCheckpointError
from casf.witness.http import WitnessService, make_server
from tests.unit.test_witness import _checkpoint, _records
from tests.unit.test_writer import (
    AUTH_PUB,
    LOG_ID,
    WIT,
    WIT_PUB,
    ZERO,
    _append,
    _manifest_envelope,
    _writer,
)

TOKEN = "test-bearer-token"  # loopback test credential, never a real one


@pytest.fixture()
def running(tmp_path):
    svc = WitnessService(tmp_path / "wit.db", WIT, token=TOKEN,
                         authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    svc.witness.register_log(_manifest_envelope())
    server = make_server(svc, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    yield svc, url, tmp_path
    server.shutdown()
    server.server_close()
    svc.close()


def _accept(running, count=2, index=0, prev_cp=None):
    svc, _, tmp_path = running
    w = _writer(tmp_path / f"w{index}.db")
    for n in range(1, count + 1):
        _append(w, n)
    cp = _checkpoint(w, index=index, count=count,
                     prev_cp=prev_cp or ZERO)
    svc.witness.submit(LOG_ID, cp, _records(w, 1, count))
    return cp


# ---------------- happy path ----------------

def test_latest_roundtrip(running):
    _accept(running, 2)
    _, url, _ = running
    view = query_latest(url, LOG_ID, TOKEN, WIT_PUB)
    assert view.body["type"] == "latest"
    assert view.body["count"] == 2
    assert view.body["checkpoint_index"] == 0
    assert view.body["final"] is False
    assert len(crypto.b64url_decode(view.body["nonce"])) == 32

def test_latest_reflects_new_checkpoints(running):
    svc, url, tmp_path = running
    cp0 = _accept(running, 1, index=0)
    w2 = _writer(tmp_path / "ext.db")
    _append(w2, 1)
    cp1 = _checkpoint(w2, index=1, count=1,
                      prev_cp=cp0["checkpoint_hash"],
                      head=cp0["body"]["head_hash"])  # heartbeat, same head
    svc.witness.submit(LOG_ID, cp1, [])
    view = query_latest(url, LOG_ID, TOKEN, WIT_PUB)
    assert view.body["checkpoint_index"] == 1

def test_latest_final_flag_after_seal(running):
    svc, url, tmp_path = running
    w = _writer(tmp_path / "wf.db")
    _append(w, 1)
    cp = _checkpoint(w, index=0, count=1, final=True)
    svc.witness.submit(LOG_ID, cp, _records(w, 1, 1))
    view = query_latest(url, LOG_ID, TOKEN, WIT_PUB)
    assert view.body["final"] is True

def test_no_checkpoint_yet(running):
    _, url, _ = running
    with pytest.raises(NoCheckpointError, match="NO_CHECKPOINT"):
        query_latest(url, LOG_ID, TOKEN, WIT_PUB)

def test_unknown_log_rejected(running):
    _, url, _ = running
    other = "123e4567-e89b-42d3-a456-426614174999"
    with pytest.raises(CasfError):
        query_latest(url, other, TOKEN, WIT_PUB)

# ---------------- T11: replay, wrong nonce, timeout ----------------

def _raw_latest(url, log_id, token):
    """One query returning the raw response and the nonce sent."""
    from casf.online import fetch_latest
    return fetch_latest(url, log_id, token)


def test_replay_never_passes_freshness(running):
    _accept(running, 1)
    _, url, _ = running
    response, nonce1 = _raw_latest(url, LOG_ID, TOKEN)
    verify_latest_response(response, nonce1, WIT_PUB, LOG_ID)  # valid once
    with pytest.raises(CasfError, match="nonce"):
        verify_latest_response(response, os.urandom(32), WIT_PUB, LOG_ID)


def test_wrong_nonce_rejected(running):
    _accept(running, 1)
    _, url, _ = running
    response, _ = _raw_latest(url, LOG_ID, TOKEN)
    forged = dict(response)
    body = dict(response["body"])
    body["nonce"] = crypto.b64url_encode(os.urandom(32))
    forged["body"] = body
    with pytest.raises(CasfError):
        verify_latest_response(forged, os.urandom(32), WIT_PUB, LOG_ID)


def test_wrong_witness_key_rejected(running):
    _accept(running, 1)
    _, url, _ = running
    response, nonce = _raw_latest(url, LOG_ID, TOKEN)
    from tests.unit.test_writer import LOG_PUB
    with pytest.raises(CasfError):
        verify_latest_response(response, nonce, LOG_PUB, LOG_ID)


def test_timeout_is_inconclusive(running):
    _accept(running, 1)
    _, url, _ = running
    with pytest.raises(InconclusiveError):
        query_latest(url, LOG_ID, TOKEN, WIT_PUB, timeout=0.0)


def test_partition_is_inconclusive():
    # nothing listens on this port: a partition, not rollback evidence
    with pytest.raises(InconclusiveError):
        query_latest("http://127.0.0.1:9", LOG_ID, TOKEN, WIT_PUB,
                     timeout=0.5)


def test_slow_server_is_inconclusive():
    class Sleepy(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            time.sleep(1.0)
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Sleepy)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        with pytest.raises(InconclusiveError):
            query_latest(url, LOG_ID, TOKEN, WIT_PUB, timeout=0.2)
    finally:
        server.shutdown()
        server.server_close()


def test_nonce_never_reused(running):
    _accept(running, 1)
    _, url, _ = running
    _, nonce1 = _raw_latest(url, LOG_ID, TOKEN)
    _, nonce2 = _raw_latest(url, LOG_ID, TOKEN)
    assert nonce1 != nonce2
    assert len(nonce1) == 32
