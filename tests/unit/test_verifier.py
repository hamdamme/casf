"""R03 / R07 / T05/T12/T13 (SPEC §21): independent verifier, public trust only."""

from casf import crypto
from casf.verifier import (
    AnchorStatus,
    Mode,
    Result,
    TrustPins,
    TrustStatus,
    verify,
)

AUTH = crypto.generate_key()
LOG = crypto.generate_key()
WIT = crypto.generate_key()
AUTH_PUB = crypto.public_key_raw(AUTH)
LOG_PUB = crypto.public_key_raw(LOG)
WIT_PUB = crypto.public_key_raw(WIT)

LOG_ID = "123e4567-e89b-42d3-a456-426614174000"
TS = "2026-10-11T00:00:00.000000Z"
ZERO = "0" * 64


def _manifest_body():
    return {
        "version": 1, "type": "manifest", "log_id": LOG_ID,
        "issuer_id": crypto.key_id(AUTH_PUB),
        "log_key_id": crypto.key_id(LOG_PUB),
        "log_public_key": crypto.b64url_encode(LOG_PUB),
        "witness_id": crypto.key_id(WIT_PUB),
        "witness_public_key": crypto.b64url_encode(WIT_PUB),
        "created_at": TS, "predecessor": None,
    }

def _manifest_env():
    body = _manifest_body()
    return {
        "body": body,
        "manifest_hash": crypto.digest_manifest(body),
        "signature": crypto.sign_manifest(AUTH, body),
    }

def _record_body(seq, prev, mh, event_id="123e4567-e89b-42d3-a456-426614174001"):
    return {
        "version": 1, "type": "record", "log_id": LOG_ID,
        "manifest_hash": mh, "seq": seq, "event_id": event_id,
        "recorded_at": TS, "actor": "alice", "event_type": "login",
        "payload": {}, "attributes": {},
        "prev_hash": prev, "key_id": crypto.key_id(LOG_PUB),
    }

def _record_env(body, signer=LOG):
    return {
        "body": body,
        "record_hash": crypto.digest_record(body),
        "signature": crypto.sign_record(signer, body),
    }

def _chain(n):
    """n valid record envelopes with real linkage."""
    mh = _manifest_env()["manifest_hash"]
    prev = crypto.genesis_hash(mh)
    out = []
    for i in range(1, n + 1):
        body = _record_body(i, prev, mh,
                            event_id=f"123e4567-e89b-42d3-a456-4266{i:08d}")
        out.append(_record_env(body))
        prev = crypto.digest_record(body)
    return out

def _checkpoint_env(index, count, head, prev_cp, mh, final=False):
    body = {
        "version": 1, "type": "checkpoint", "log_id": LOG_ID,
        "manifest_hash": mh, "index": index, "count": count,
        "head_hash": head, "previous_checkpoint_hash": prev_cp,
        "key_id": crypto.key_id(LOG_PUB), "issued_at": TS, "final": final,
    }
    return {
        "body": body,
        "checkpoint_hash": crypto.digest_checkpoint(body),
        "signature": crypto.sign_checkpoint(LOG, body),
    }

def _receipt_env(cp_env, prev_rc=ZERO):
    cp = cp_env["body"]
    body = {
        "version": 1, "type": "receipt",
        "witness_id": crypto.key_id(WIT_PUB), "log_id": LOG_ID,
        "manifest_hash": cp["manifest_hash"],
        "checkpoint_hash": cp_env["checkpoint_hash"],
        "checkpoint_index": cp["index"], "count": cp["count"],
        "head_hash": cp["head_hash"], "previous_receipt_hash": prev_rc,
        "accepted_at": TS,
    }
    return {
        "body": body,
        "receipt_hash": crypto.digest_receipt(body),
        "signature": crypto.sign_receipt(WIT, body),
    }

def _status_env(mh, serial=1, status="active", signer=AUTH):
    body = {
        "version": 1, "type": "status", "issuer_id": crypto.key_id(AUTH_PUB),
        "serial": serial, "manifest_hash": mh, "status": status,
        "issued_at": TS, "reason": "",
    }
    return {"body": body, "signature": crypto.sign_status(signer, body)}

def _pins(mh=None, minimum_status_serial=1):
    return TrustPins(
        authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB},
        witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
        log_id=LOG_ID,
        manifest_hash=mh,
        minimum_status_serial=minimum_status_serial,
    )

def _anchored(n=3, anchor_count=2):
    env = _manifest_env()
    mh = env["manifest_hash"]
    records = _chain(n)
    head = records[anchor_count - 1]["record_hash"]
    cp = _checkpoint_env(0, anchor_count, head, ZERO, mh)
    rc = _receipt_env(cp)
    return env, records, [cp], [rc]

# ---------------- T05: clean offline verification ----------------

def test_integrity_pass_reports_verified_range():
    env = _manifest_env()
    report = verify(env, _chain(3), _pins(env["manifest_hash"]))
    assert report.result == Result.PASS
    assert report.verified_from == 1
    assert report.verified_through == 3
    assert report.first_failure_seq is None

def test_empty_history_passes_at_genesis():
    env = _manifest_env()
    report = verify(env, [], _pins(env["manifest_hash"]))
    assert report.result == Result.PASS
    assert report.verified_through == 0

def test_first_failure_seq_and_verified_range():
    env = _manifest_env()
    records = _chain(3)
    records[1]["body"] = dict(records[1]["body"], actor="mallory")  # breaks digest+sig
    report = verify(env, records, _pins(env["manifest_hash"]))
    assert report.result == Result.FAIL
    assert report.first_failure_seq == 2
    assert report.verified_through == 1
    assert "RECORD_HASH_MISMATCH" in report.diagnostic_codes

def test_seq_gap_fails():
    env = _manifest_env()
    mh = env["manifest_hash"]
    records = _chain(1)
    records.append(_record_env(_record_body(3, records[0]["record_hash"], mh,
                                            event_id="123e4567-e89b-42d3-a456-426600000003")))
    report = verify(env, records, _pins(mh))
    assert report.result == Result.FAIL
    assert "SEQ_GAP" in report.diagnostic_codes

def test_chain_break_fails():
    env = _manifest_env()
    mh = env["manifest_hash"]
    records = _chain(1)
    bad = _record_body(2, "ab" * 32, mh, event_id="123e4567-e89b-42d3-a456-426600000002")
    records.append(_record_env(bad))
    report = verify(env, records, _pins(mh))
    assert report.result == Result.FAIL
    assert "CHAIN_BREAK" in report.diagnostic_codes

def test_record_signature_wrong_key_fails():
    env = _manifest_env()
    records = _chain(2)
    records[1] = _record_env(records[1]["body"], signer=WIT)
    report = verify(env, records, _pins(env["manifest_hash"]))
    assert report.result == Result.FAIL
    assert "RECORD_SIGNATURE" in report.diagnostic_codes

# ---------------- T12: versions, substitution, replacement ----------------

def test_unknown_version_never_falls_back():
    env = _manifest_env()
    mh = env["manifest_hash"]
    body = _record_body(1, crypto.genesis_hash(mh), mh)
    body["version"] = 2
    report = verify(env, [_record_env(body)], _pins(mh))
    assert report.result == Result.FAIL
    assert "VERSION_UNSUPPORTED" in report.diagnostic_codes

def test_untrusted_issuer_fails():
    env = _manifest_env()
    pins = TrustPins(authority_keys={}, witness_keys={crypto.key_id(WIT_PUB): WIT_PUB},
                     log_id=LOG_ID)
    report = verify(env, _chain(1), pins)
    assert report.result == Result.FAIL
    assert report.trust_status == TrustStatus.UNTRUSTED
    assert "ISSUER_UNTRUSTED" in report.diagnostic_codes

def test_manifest_replacement_fails():
    env = _manifest_env()
    report = verify(env, _chain(1), _pins("ff" * 32))
    assert report.result == Result.FAIL
    assert "MANIFEST_REPLACED" in report.diagnostic_codes

def test_log_id_mismatch_fails():
    env = _manifest_env()
    pins = _pins(env["manifest_hash"])
    pins = TrustPins(authority_keys=pins.authority_keys, witness_keys=pins.witness_keys,
                     log_id="123e4567-e89b-42d3-a456-426614179999",
                     manifest_hash=env["manifest_hash"])
    report = verify(env, _chain(1), pins)
    assert report.result == Result.FAIL
    assert "LOG_ID_MISMATCH" in report.diagnostic_codes

# ---------------- T13: status and trust ----------------

def test_revoked_status_fails_trust():
    env = _manifest_env()
    mh = env["manifest_hash"]
    report = verify(env, _chain(1), _pins(mh),
                    status_envelopes=[_status_env(mh, serial=2, status="revoked")])
    assert report.result == Result.FAIL
    assert report.trust_status == TrustStatus.REVOKED
    assert "STATUS_REVOKED" in report.diagnostic_codes

def test_status_serial_below_minimum_fails():
    env = _manifest_env()
    mh = env["manifest_hash"]
    report = verify(env, _chain(1), _pins(mh, minimum_status_serial=5),
                    status_envelopes=[_status_env(mh, serial=2)])
    assert report.result == Result.FAIL
    assert "STATUS_SERIAL_LOW" in report.diagnostic_codes

def test_bad_status_signature_fails():
    env = _manifest_env()
    mh = env["manifest_hash"]
    report = verify(env, _chain(1), _pins(mh),
                    status_envelopes=[_status_env(mh, signer=WIT)])
    assert report.result == Result.FAIL
    assert "STATUS_SIGNATURE" in report.diagnostic_codes

# ---------------- anchored mode ----------------

def test_anchored_pass():
    env, records, cps, rcs = _anchored(3, 2)
    report = verify(env, records, _pins(env["manifest_hash"]), mode=Mode.ANCHORED,
                    checkpoint_envelopes=cps, receipt_envelopes=rcs,
                    allow_unwitnessed=True)
    assert report.result == Result.PASS
    assert report.anchor_status == AnchorStatus.PARTIAL_ANCHOR
    assert report.unwitnessed_count == 1

def test_anchored_incomplete_history_fails():
    env, records, cps, rcs = _anchored(3, 2)
    report = verify(env, records[:1], _pins(env["manifest_hash"]), mode=Mode.ANCHORED,
                    checkpoint_envelopes=cps, receipt_envelopes=rcs)
    assert report.result == Result.FAIL
    assert report.anchor_status == AnchorStatus.INCOMPLETE

def test_anchored_divergent_head_fails():
    env, records, cps, rcs = _anchored(3, 2)
    records[1]["body"] = dict(records[1]["body"], actor="mallory")
    records[1]["record_hash"] = crypto.digest_record(records[1]["body"])
    records[1]["signature"] = crypto.sign_record(LOG, records[1]["body"])
    # chain now breaks at 3; keep only records 1-2 so anchor compares a changed head
    report = verify(env, records[:2], _pins(env["manifest_hash"]), mode=Mode.ANCHORED,
                    checkpoint_envelopes=cps, receipt_envelopes=rcs)
    assert report.result == Result.FAIL
    assert report.anchor_status == AnchorStatus.DIVERGENT

def test_anchored_unwitnessed_suffix_rejected_by_default():
    env, records, cps, rcs = _anchored(3, 2)
    report = verify(env, records, _pins(env["manifest_hash"]), mode=Mode.ANCHORED,
                    checkpoint_envelopes=cps, receipt_envelopes=rcs)
    assert report.result == Result.FAIL
    assert "UNWITNESSED_SUFFIX" in report.diagnostic_codes

def test_anchored_bad_receipt_signature_fails():
    env, records, cps, rcs = _anchored(3, 2)
    sig = rcs[0]["signature"]
    mangled = ("B" if sig[0] == "A" else "A") + sig[1:]
    bad_rc = dict(rcs[0], signature=mangled)
    report = verify(env, records, _pins(env["manifest_hash"]), mode=Mode.ANCHORED,
                    checkpoint_envelopes=cps, receipt_envelopes=[bad_rc],
                    allow_unwitnessed=True)
    assert report.result == Result.FAIL
    assert "RECEIPT_SIGNATURE" in report.diagnostic_codes
