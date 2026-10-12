"""SPEC §15 online mode and T18: freshness in the verdict.

Online mode fetches a fresh witness view and compares it to both the
supplied evidence and any locally retained high water state. A
lower or different witness view is WITNESS_STATE_CONFLICT, a newer
view needs more evidence before advancing, and a partition is
inconclusive. A locally committed but unwitnessed record is never
described as witnessed (T18).
"""

import threading

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.online import InconclusiveError, LatestView, query_latest
from casf.verifier import (
    AnchorStatus,
    FreshnessStatus,
    Mode,
    Result,
    TrustPins,
    verify,
)
from casf.witness.http import WitnessService, make_server
from tests.unit.test_writer import (
    AUTH_PUB,
    LOG_ID,
    WIT,
    WIT_PUB,
    _append,
    _manifest_envelope,
    _writer,
)

TOKEN = "test-bearer-token"  # loopback test credential, never a real one


def _pins(mh):
    return TrustPins(
        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
        witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
        log_id=LOG_ID, manifest_hash=mh)


def _service(tmp_path):
    svc = WitnessService(tmp_path / "wit.db", WIT, token=TOKEN,
                         authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    svc.witness.register_log(_manifest_envelope())
    server = make_server(svc, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return svc, server


def _evidence(tmp_path, svc, records=3, witnessed=2):
    """Writer history with the witnessed prefix anchored."""
    w = _writer(tmp_path / "w.db")
    for n in range(1, witnessed + 1):
        _append(w, n)
    cp = w.create_checkpoint(LOG_ID)
    _env, from_seq, to_seq = w.pending_checkpoint(LOG_ID)
    extension = list(w.records(LOG_ID))[from_seq - 1:to_seq]
    receipt = svc.witness.submit(LOG_ID, cp, extension)
    w.record_receipt(LOG_ID, receipt)
    for n in range(witnessed + 1, records + 1):  # unwitnessed suffix
        _append(w, n)
    mh = w.manifest_envelope(LOG_ID)["manifest_hash"]
    return w, mh, [cp], [receipt]


def test_online_pass_with_fresh_view(tmp_path):
    svc, server = _service(tmp_path)
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=2, witnessed=2)
        report = verify(
            w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
            mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
            online_query=lambda: query_latest(url, LOG_ID, TOKEN, WIT_PUB))
        assert report.result == Result.PASS
        assert report.freshness_status == FreshnessStatus.FRESH_WITNESS_VIEW
        assert report.witnessed_through == 2
    finally:
        server.shutdown()
        server.server_close()
        svc.close()


def _fake_view(index, checkpoint_hash, count=2):
    return LatestView(body={
        "checkpoint_index": index, "checkpoint_hash": checkpoint_hash,
        "count": count, "head_hash": "ab" * 32,
    }, checkpoint={}, receipt={})


def test_online_timeout_is_inconclusive(tmp_path):
    svc, server = _service(tmp_path)
    try:
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=2, witnessed=2)

        def offline():
            raise InconclusiveError("partition")

        report = verify(
            w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
            mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
            online_query=offline)
        assert report.result == Result.INCONCLUSIVE
        assert report.freshness_status == FreshnessStatus.INCONCLUSIVE
        assert "FRESHNESS_INCONCLUSIVE" in report.diagnostic_codes
    finally:
        server.shutdown()
        server.server_close()
        svc.close()


def test_witness_behind_evidence_is_conflict(tmp_path):
    svc, server = _service(tmp_path)
    try:
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=2, witnessed=2)
        cps[0]
        behind = _fake_view(-1, "ab" * 32)  # witness lost the checkpoint
        report = verify(
            w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
            mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
            online_query=lambda: behind)
        assert report.result == Result.FAIL
        assert report.freshness_status == FreshnessStatus.CONFLICT
        assert "WITNESS_STATE_CONFLICT" in report.diagnostic_codes
    finally:
        server.shutdown()
        server.server_close()
        svc.close()


def test_different_digest_at_same_index_is_conflict(tmp_path):
    svc, server = _service(tmp_path)
    try:
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=2, witnessed=2)
        forged = _fake_view(0, "ff" * 32)  # same index, other digest
        report = verify(
            w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
            mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
            online_query=lambda: forged)
        assert report.freshness_status == FreshnessStatus.CONFLICT
        assert "WITNESS_STATE_CONFLICT" in report.diagnostic_codes
    finally:
        server.shutdown()
        server.server_close()
        svc.close()


def test_witness_ahead_needs_more_evidence(tmp_path):
    svc, server = _service(tmp_path)
    try:
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=2, witnessed=2)
        ahead = _fake_view(7, "ab" * 32)  # newer index, no chain supplied
        report = verify(
            w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
            mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
            online_query=lambda: ahead)
        assert report.result == Result.INCONCLUSIVE
        assert "WITNESS_AHEAD" in report.diagnostic_codes
    finally:
        server.shutdown()
        server.server_close()
        svc.close()


def test_retained_high_water_conflict(tmp_path):
    svc, server = _service(tmp_path)
    try:
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=2, witnessed=2)
        anchor = cps[0]
        view = _fake_view(0, anchor["checkpoint_hash"])
        report = verify(
            w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
            mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
            online_query=lambda: view,
            retained_checkpoint=(3, "ab" * 32))  # pin ahead of the answer
        assert report.freshness_status == FreshnessStatus.CONFLICT
        assert "WITNESS_STATE_CONFLICT" in report.diagnostic_codes
    finally:
        server.shutdown()
        server.server_close()
        svc.close()


# ---------------- T18: unwitnessed suffix is never witnessed ----------------

def test_unwitnessed_suffix_rejected_online(tmp_path):
    svc, server = _service(tmp_path)
    try:
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=3, witnessed=2)
        anchor = cps[0]
        view = _fake_view(0, anchor["checkpoint_hash"])
        report = verify(
            w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
            mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
            online_query=lambda: view)
        assert report.result == Result.FAIL
        assert "UNWITNESSED_SUFFIX" in report.diagnostic_codes
        assert report.witnessed_through == 2
        assert report.unwitnessed_count == 1
    finally:
        server.shutdown()
        server.server_close()
        svc.close()


def test_unwitnessed_suffix_visible_when_allowed(tmp_path):
    svc, server = _service(tmp_path)
    try:
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=3, witnessed=2)
        anchor = cps[0]
        view = _fake_view(0, anchor["checkpoint_hash"])
        report = verify(
            w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)), _pins(mh),
            mode=Mode.ONLINE, checkpoint_envelopes=cps, receipt_envelopes=rcs,
            online_query=lambda: view, allow_unwitnessed=True)
        assert report.result == Result.PASS
        assert report.anchor_status == AnchorStatus.PARTIAL_ANCHOR
        assert report.freshness_status == FreshnessStatus.FRESH_WITNESS_VIEW
        assert report.unwitnessed_count == 1  # never described as witnessed
    finally:
        server.shutdown()
        server.server_close()
        svc.close()


def test_online_requires_query(tmp_path):
    svc, server = _service(tmp_path)
    try:
        w, mh, cps, rcs = _evidence(tmp_path, svc, records=2, witnessed=2)
        with pytest.raises(CasfError):
            verify(w.manifest_envelope(LOG_ID), list(w.records(LOG_ID)),
                   _pins(mh), mode=Mode.ONLINE, checkpoint_envelopes=cps,
                   receipt_envelopes=rcs)
    finally:
        server.shutdown()
        server.server_close()
        svc.close()
