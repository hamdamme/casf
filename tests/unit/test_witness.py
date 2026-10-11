"""R05 (SPEC §13; T08, T09, T22): witness acceptance state machine.

The witness is a stateful verifier with its own storage. It accepts
only a valid extension of its retained state, replays a stored
receipt on an identical retry, and rejects conflicts without moving
its high water state. HTTP transport arrives in the next session.
"""

import sqlite3

import pytest

from casf import crypto
from casf.errors import CasfError
from casf.witness import ConflictError, Witness
from tests.unit.test_writer import (
    AUTH_PUB,
    LOG,
    LOG_ID,
    LOG_PUB,
    TS,
    WIT,
    WIT_PUB,
    ZERO,
    _append,
    _manifest_envelope,
    _writer,
)


def _witness(tmp_path, name="wit.db", **kw):
    wit = Witness(tmp_path / name, WIT,
                  authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB}, **kw)
    wit.register_log(_manifest_envelope())
    return wit


def _checkpoint(w, index, count, prev_cp=ZERO, final=False, head=None):
    mh = w.manifest_envelope(LOG_ID)["manifest_hash"]
    if head is None:
        records = list(w.records(LOG_ID))
        head = (records[count - 1]["record_hash"] if count
                else crypto.genesis_hash(mh))
    body = {
        "version": 1, "type": "checkpoint", "log_id": LOG_ID,
        "manifest_hash": mh, "index": index, "count": count,
        "head_hash": head, "previous_checkpoint_hash": prev_cp,
        "key_id": crypto.key_id(LOG_PUB), "issued_at": TS, "final": final,
    }
    return {"body": body, "checkpoint_hash": crypto.digest_checkpoint(body),
            "signature": crypto.sign_checkpoint(LOG, body)}


def _records(w, start, count):
    """Record envelopes for seq start through count inclusive."""
    return list(w.records(LOG_ID))[start - 1:count]


def _state(db_path):
    con = sqlite3.connect(db_path)
    try:
        return con.execute(
            "SELECT count, head_hash, checkpoint_index, checkpoint_hash, "
            "sealed FROM w_state WHERE log_id = ?", (LOG_ID,)).fetchone()
    finally:
        con.close()


# ---------------- acceptance (SPEC §13) ----------------

def test_accept_first_checkpoint(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    _append(w, 2)
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=2)
    receipt = wit.submit(LOG_ID, cp, _records(w, 1, 2))
    body = receipt["body"]
    assert set(body) == {"version", "type", "witness_id", "log_id",
                         "manifest_hash", "checkpoint_hash",
                         "checkpoint_index", "count", "head_hash",
                         "previous_receipt_hash", "accepted_at"}
    assert body["version"] == 1 and body["type"] == "receipt"
    assert body["witness_id"] == crypto.key_id(WIT_PUB)
    assert body["checkpoint_hash"] == cp["checkpoint_hash"]
    assert body["checkpoint_index"] == 0 and body["count"] == 2
    assert body["previous_receipt_hash"] == ZERO
    crypto.verify_receipt(WIT_PUB, body, receipt["signature"])
    assert _state(tmp_path / "wit.db")[:4] == (
        2, body["head_hash"], 0, cp["checkpoint_hash"])

def test_identical_retry_replays_same_receipt(tmp_path):
    """T22: a lost response retried returns the stored receipt."""
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=1)
    first = wit.submit(LOG_ID, cp, _records(w, 1, 1))
    again = wit.submit(LOG_ID, cp, _records(w, 1, 1))
    assert again == first
    assert _state(tmp_path / "wit.db")[2] == 0  # one state transition only

def test_extension_chain_of_checkpoints(tmp_path):
    w = _writer(tmp_path / "w.db")
    for n in range(1, 5):
        _append(w, n)
    wit = _witness(tmp_path)
    cp0 = _checkpoint(w, index=0, count=2)
    r0 = wit.submit(LOG_ID, cp0, _records(w, 1, 2))
    cp1 = _checkpoint(w, index=1, count=4, prev_cp=cp0["checkpoint_hash"])
    r1 = wit.submit(LOG_ID, cp1, _records(w, 3, 4))
    assert r1["body"]["checkpoint_index"] == 1
    assert r1["body"]["previous_receipt_hash"] == r0["receipt_hash"]
    assert _state(tmp_path / "wit.db")[0] == 4

def test_heartbeat_checkpoint_same_count(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = _witness(tmp_path)
    cp0 = _checkpoint(w, index=0, count=1)
    wit.submit(LOG_ID, cp0, _records(w, 1, 1))
    cp1 = _checkpoint(w, index=1, count=1, prev_cp=cp0["checkpoint_hash"])
    receipt = wit.submit(LOG_ID, cp1, [])
    assert receipt["body"]["count"] == 1

def test_empty_first_checkpoint(tmp_path):
    w = _writer(tmp_path / "w.db")
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=0)
    receipt = wit.submit(LOG_ID, cp, [])
    assert receipt["body"]["count"] == 0
    assert receipt["body"]["head_hash"] == crypto.genesis_hash(
        w.manifest_envelope(LOG_ID)["manifest_hash"])

# ---------------- rejection keeps high water state (T08) ----------------

def test_bad_extension_rejected_state_unchanged(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    _append(w, 2)
    wit = _witness(tmp_path)
    records = _records(w, 1, 2)
    records[1]["body"]["payload"] = {"n": 999}  # breaks digest and chain
    cp = _checkpoint(w, index=0, count=2)
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, cp, records)
    assert _state(tmp_path / "wit.db")[0] == 0
    good = _checkpoint(w, index=0, count=2)
    wit.submit(LOG_ID, good, _records(w, 1, 2))  # state still acceptive

def test_head_hash_mismatch_rejected(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=1)
    cp["body"]["head_hash"] = "ff" * 32
    cp["checkpoint_hash"] = crypto.digest_checkpoint(cp["body"])
    cp["signature"] = crypto.sign_checkpoint(LOG, cp["body"])
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, cp, _records(w, 1, 1))
    assert _state(tmp_path / "wit.db")[0] == 0

def test_reused_index_new_digest_is_conflict(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    _append(w, 2)
    wit = _witness(tmp_path)
    cp0 = _checkpoint(w, index=0, count=1)
    wit.submit(LOG_ID, cp0, _records(w, 1, 1))
    fork = _checkpoint(w, index=0, count=2)  # same index, new digest
    with pytest.raises(ConflictError):
        wit.submit(LOG_ID, fork, _records(w, 2, 2))
    assert _state(tmp_path / "wit.db")[2] == 0  # high water unmoved

def test_wrong_previous_checkpoint_hash_rejected(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = _witness(tmp_path)
    cp0 = _checkpoint(w, index=0, count=1)
    wit.submit(LOG_ID, cp0, _records(w, 1, 1))
    cp1 = _checkpoint(w, index=1, count=1, prev_cp="ab" * 32)
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, cp1, [])

def test_count_decrease_rejected(tmp_path):
    w = _writer(tmp_path / "w.db")
    for n in range(1, 3):
        _append(w, n)
    wit = _witness(tmp_path)
    cp0 = _checkpoint(w, index=0, count=2)
    wit.submit(LOG_ID, cp0, _records(w, 1, 2))
    cp1 = _checkpoint(w, index=1, count=1, prev_cp=cp0["checkpoint_hash"])
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, cp1, [])

def test_too_many_records_rejected(tmp_path):
    w = _writer(tmp_path / "w.db")
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=129,  # over the 128 record limit
                     head="ab" * 32)
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, cp, [])
    assert _state(tmp_path / "wit.db")[0] == 0

def test_noncontiguous_records_rejected(tmp_path):
    w = _writer(tmp_path / "w.db")
    for n in range(1, 4):
        _append(w, n)
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=3)
    records = _records(w, 1, 3)
    del records[1]  # gap at seq 2
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, cp, records)

def test_checkpoint_signed_by_wrong_key_rejected(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=1)
    cp["signature"] = crypto.sign_checkpoint(WIT, cp["body"])  # wrong signer
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, cp, _records(w, 1, 1))

def test_unknown_log_rejected(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = Witness(tmp_path / "wit.db", WIT,
                  authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    cp = _checkpoint(w, index=0, count=1)
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, cp, _records(w, 1, 1))

def test_manifest_for_another_witness_rejected(tmp_path):
    env = _manifest_envelope()
    env["body"]["witness_id"] = crypto.key_id(LOG_PUB)  # not this witness
    env["manifest_hash"] = crypto.digest_manifest(env["body"])
    wit = Witness(tmp_path / "wit.db", WIT,
                  authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    with pytest.raises(CasfError):
        wit.register_log(env)

# ---------------- sealing (SPEC §12, §13) ----------------

def test_final_checkpoint_seals_the_log(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=1, final=True)
    wit.submit(LOG_ID, cp, _records(w, 1, 1))
    assert _state(tmp_path / "wit.db")[4] == 1
    later = _checkpoint(w, index=1, count=1, prev_cp=cp["checkpoint_hash"])
    with pytest.raises(CasfError):
        wit.submit(LOG_ID, later, [])
    same = wit.submit(LOG_ID, cp, _records(w, 1, 1))  # retrieval still ok
    assert same["body"]["checkpoint_hash"] == cp["checkpoint_hash"]

# ---------------- receipt retrieval (SPEC §14 lookup) ----------------

def test_receipt_lookup_roundtrip(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=1)
    wit.submit(LOG_ID, cp, _records(w, 1, 1))
    checkpoint, receipt = wit.receipt(cp["checkpoint_hash"])
    assert checkpoint == cp
    assert receipt["body"]["checkpoint_hash"] == cp["checkpoint_hash"]

def test_receipt_lookup_missing(tmp_path):
    wit = _witness(tmp_path)
    with pytest.raises(CasfError):
        wit.receipt("ab" * 32)

# ---------------- record digest retention (SPEC §13) ----------------

def test_record_digests_retained_bodies_discarded(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    _append(w, 2)
    wit = _witness(tmp_path)
    cp = _checkpoint(w, index=0, count=2)
    wit.submit(LOG_ID, cp, _records(w, 1, 2))
    records = list(w.records(LOG_ID))
    con = sqlite3.connect(tmp_path / "wit.db")
    try:
        rows = con.execute(
            "SELECT seq, record_hash FROM w_record_digests "
            "WHERE log_id = ? ORDER BY seq", (LOG_ID,)).fetchall()
    finally:
        con.close()
    assert rows == [(1, records[0]["record_hash"]),
                    (2, records[1]["record_hash"])]

# ---------------- T22: crash after commit, before the response ----------------

class _CrashWitness(Witness):
    def _debug_hook(self, stage):
        if stage == "after_commit":
            raise RuntimeError("simulated crash")


def test_crash_after_commit_replays_same_receipt(tmp_path):
    w = _writer(tmp_path / "w.db")
    _append(w, 1)
    wit = _CrashWitness(tmp_path / "wit.db", WIT,
                        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    wit.register_log(_manifest_envelope())
    cp = _checkpoint(w, index=0, count=1)
    with pytest.raises(RuntimeError):
        wit.submit(LOG_ID, cp, _records(w, 1, 1))
    wit2 = Witness(tmp_path / "wit.db", WIT,  # recover, already registered
                   authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    retry = wit2.submit(LOG_ID, cp, _records(w, 1, 1))
    _, stored = wit2.receipt(cp["checkpoint_hash"])
    assert retry == stored
    assert _state(tmp_path / "wit.db")[2] == 0  # one state transition only

# ---------------- T09: two valid forks, one winner ----------------

def _mp_fork_child(db_path, checkpoint, records):
    import sys

    from casf.errors import CasfError
    from casf.witness import Witness
    from tests.unit.test_writer import AUTH_PUB, LOG_ID, WIT
    wit = Witness(db_path, WIT,
                  authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    try:
        wit.submit(LOG_ID, checkpoint, records)
    except CasfError:
        sys.exit(3)
    sys.exit(0)


def test_concurrent_forks_single_winner(tmp_path):
    from tests.unit.test_writer import MP

    w1 = _writer(tmp_path / "w1.db")
    _append(w1, 1)
    w2 = _writer(tmp_path / "w2.db")
    _append(w2, 1)  # identical first record on both forks
    _append(w1, 2)
    w2.append(LOG_ID, event_id="123e4567-e89b-42d3-a456-426600000777",
              actor="bob", event_type="logout",
              payload={"n": 777}, attributes={})  # divergent second record
    wit = _witness(tmp_path)  # register the log before spawning children
    wit.close()
    cp1 = _checkpoint(w1, index=0, count=2)
    cp2 = _checkpoint(w2, index=0, count=2)
    assert cp1["checkpoint_hash"] != cp2["checkpoint_hash"]
    db = tmp_path / "wit.db"
    procs = [
        MP.Process(target=_mp_fork_child,
                   args=(db, cp1, _records(w1, 1, 2))),
        MP.Process(target=_mp_fork_child,
                   args=(db, cp2, _records(w2, 1, 2))),
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    codes = sorted(p.exitcode for p in procs)
    assert codes == [0, 3]  # at most one extension accepted
    assert _state(db)[2] == 0  # exactly one checkpoint index retained
