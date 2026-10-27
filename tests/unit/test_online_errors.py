"""Unsigned witness errors cannot establish conflicting signed history."""

import http.server
import json
import threading

import pytest

from casf.canonical.jcs import canonicalize
from casf.cli import main
from casf.errors import NoCheckpointError
from casf.online import query_latest
from casf.verifier import FreshnessStatus, Mode, Result, verify
from tests.status import active_status
from tests.unit.test_cli import _trust
from tests.unit.test_verify_online import TOKEN, _evidence, _pins, _service
from tests.unit.test_writer import AUTH, LOG_ID, WIT_PUB, _manifest_envelope


@pytest.fixture()
def evidence(tmp_path):
    svc, server = _service(tmp_path)
    w, mh, cps, rcs = _evidence(tmp_path, svc, records=2, witnessed=2)
    try:
        yield w, mh, cps, rcs, f"http://127.0.0.1:{server.server_port}"
    finally:
        w.close()
        server.shutdown()
        server.server_close()
        svc.close()


def check(evidence, query):
    w, mh, cps, rcs, _ = evidence
    return verify(
        w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
        mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
        status_envelopes=[active_status(AUTH, mh)], online_query=query)


def assert_inconclusive(report):
    assert report.result == Result.INCONCLUSIVE
    assert report.freshness_status == FreshnessStatus.INCONCLUSIVE
    assert "FRESHNESS_INCONCLUSIVE" in report.diagnostic_codes
    assert "WITNESS_STATE_CONFLICT" not in report.diagnostic_codes


def test_no_checkpoint_callback_is_not_proof_of_conflict(evidence):
    def no_checkpoint():
        raise NoCheckpointError("no accepted checkpoint")

    assert_inconclusive(check(evidence, no_checkpoint))


@pytest.mark.parametrize("http_status", [404, 503])
def test_unsigned_no_checkpoint_is_inconclusive_in_library_and_cli(
        evidence, tmp_path, monkeypatch, capsys, http_status):
    w, mh, _, _, real_url = evidence
    control = check(evidence, lambda: query_latest(real_url, LOG_ID, TOKEN, WIT_PUB))
    assert control.result == Result.PASS
    assert control.freshness_status == FreshnessStatus.FRESH_WITNESS_VIEW

    class UnsignedError(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            payload = b'{"code":"NO_CHECKPOINT"}'
            self.send_response(http_status)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), UnsignedError)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        fake_url = f"http://127.0.0.1:{server.server_port}"
        report = check(evidence, lambda: query_latest(fake_url, LOG_ID, TOKEN, WIT_PUB))
        assert_inconclusive(report)
        assert report.verified_through == control.verified_through == 2
        assert report.witnessed_through == control.witnessed_through == 2
        bundle = tmp_path / "bundle"
        w.export_bundle(LOG_ID, bundle)
        (bundle / "status.jsonl").write_bytes(canonicalize(active_status(AUTH, mh)) + b"\n")
        trust = _trust(tmp_path, _manifest_envelope(), mode="online", witness_url=fake_url)
        monkeypatch.setenv("CASF_WITNESS_TOKEN", TOKEN)
        code = main(["verify", str(bundle), "--trust", str(trust), "--json"])
        output = capsys.readouterr().out
        summary = json.loads(output)
        assert code == 4
        assert summary["result"] == "INCONCLUSIVE"
        assert summary["freshness_status"] == "INCONCLUSIVE"
        assert "FRESHNESS_INCONCLUSIVE" in summary["diagnostic_codes"]
        assert "WITNESS_STATE_CONFLICT" not in summary["diagnostic_codes"]
        assert TOKEN not in output
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
