"""R10 (SPEC §19; T16, T17): CLI contracts, exit codes, diagnostics.

Exit codes: 0 requested policy passed; 1 invalid evidence or
divergence; 2 usage or schema error; 3 unknown, revoked or
unsupported trust; 4 inconclusive, pending or unavailable; 5 local
I/O or internal error. Secrets never appear in output (T17) and
malicious input is rejected inside bounded resources (T16).
"""

import json
import os
import stat
import threading

import pytest

from casf import crypto
from casf.cli import main
from casf.keys import load_key
from casf.witness.http import WitnessService, make_server
from tests.unit.test_writer import (
    AUTH,
    AUTH_PUB,
    LOG_ID,
    TS,
    WIT,
    WIT_PUB,
    _append,
    _manifest_envelope,
    _writer,
)

PASS = b"cli-test-passphrase"  # test only, never a real secret
TOKEN = "cli-test-token"       # test only, never a real secret


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("CASF_PASSPHRASE", PASS.decode())
    monkeypatch.setenv("CASF_WITNESS_TOKEN", TOKEN)


def _key(tmp_path, capsys, name="log.key"):
    path = tmp_path / name
    assert main(["key", "generate", "--role", "log",
                 "--out", str(path)]) == 0
    capsys.readouterr()
    return path


def _manifest_for(key_path, log_id=LOG_ID):
    key = load_key(key_path, passphrase=PASS)
    pub = crypto.public_key_raw(key)
    body = {
        "version": 1, "type": "manifest", "log_id": log_id,
        "issuer_id": crypto.key_id(AUTH_PUB),
        "log_key_id": crypto.key_id(pub),
        "log_public_key": crypto.b64url_encode(pub),
        "witness_id": crypto.key_id(WIT_PUB),
        "witness_public_key": crypto.b64url_encode(WIT_PUB),
        "created_at": TS, "predecessor": None,
    }
    return {"body": body, "manifest_hash": crypto.digest_manifest(body),
            "signature": crypto.sign_manifest(AUTH, body)}


def _event(tmp_path, n=1):
    path = tmp_path / f"event{n}.json"
    path.write_text(json.dumps({
        "event_id": f"123e4567-e89b-42d3-a456-4266{n:08d}",
        "actor": "alice", "event_type": "login",
        "payload": {"n": n}, "attributes": {}}))
    return path


def _trust(tmp_path, env, mode="integrity", witness_url=""):
    body = env["body"]
    logs = {body["log_id"]: {
        "manifest_hash": env["manifest_hash"],
        "witness_id": body["witness_id"],
        "witness_url": witness_url,
        "minimum_status_serial": 1,
    }}
    trust = {
        "version": 1,
        "authorities": {body["issuer_id"]: crypto.b64url_encode(AUTH_PUB)},
        "logs": logs,
        "policy": {"mode": mode, "allow_unwitnessed": False,
                   "query_timeout_seconds": 10, "max_chain_steps": 10000},
    }
    path = tmp_path / "trust.json"
    path.write_text(json.dumps(trust))
    return path


# ---------------- key generate ----------------

def test_key_generate_and_refuse_overwrite(tmp_path, capsys):
    path = _key(tmp_path, capsys)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert main(["key", "generate", "--role", "log",
                 "--out", str(path)]) == 5  # local error, never overwrites
    out = capsys.readouterr()
    assert PASS.decode() not in out.out + out.err  # T17

# ---------------- happy path through the commands ----------------

def test_full_command_flow(tmp_path, capsys):
    key = _key(tmp_path, capsys)
    env = _manifest_for(key)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(env))
    db = tmp_path / "log.db"
    assert main(["init", "--manifest", str(manifest), "--db", str(db),
                 "--key", str(key)]) == 0
    assert main(["append", "--db", str(db), "--key", str(key),
                 "--event", str(_event(tmp_path))]) == 0
    assert main(["checkpoint", "--db", str(db), "--key", str(key)]) == 0
    assert main(["checkpoint", "--db", str(db), "--key", str(key)]) == 0
    # second call reuses the pending checkpoint, no new one is invented
    bundle = tmp_path / "bundle"
    assert main(["export", "--db", str(db), "--key", str(key),
                 "--out", str(bundle)]) == 0
    trust = _trust(tmp_path, env)
    assert main(["verify", str(bundle), "--trust", str(trust),
                 "--mode", "integrity"]) == 0
    out = capsys.readouterr().out
    assert "integrity" in out  # human output names the mode
    assert main(["status", "--db", str(db)]) == 0
    assert "count" in capsys.readouterr().out

def test_witness_submit_then_status(tmp_path, capsys):
    key = _key(tmp_path, capsys)
    env = _manifest_for(key)
    svc = WitnessService(tmp_path / "wit.db", WIT, token=TOKEN,
                         authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    svc.witness.register_log(env)
    server = make_server(svc, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps(env))
        db = tmp_path / "log.db"
        assert main(["init", "--manifest", str(manifest), "--db", str(db),
                     "--key", str(key)]) == 0
        assert main(["append", "--db", str(db), "--key", str(key),
                     "--event", str(_event(tmp_path))]) == 0
        assert main(["checkpoint", "--db", str(db), "--key", str(key)]) == 0
        assert main(["witness", "submit", "--db", str(db), "--key", str(key),
                     "--url", url]) == 0
        capsys.readouterr()  # drain earlier human output
        assert main(["status", "--db", str(db), "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["count"] == 1
        assert report["backlog"] == 0
    finally:
        server.shutdown()
        server.server_close()
        svc.close()

# ---------------- verify exit codes ----------------

def _exported(tmp_path, capsys, records=2):
    from casf.witness import Witness
    w = _writer(tmp_path / "w.db")
    for n in range(1, records + 1):
        _append(w, n)
    wit = Witness(tmp_path / "wit.db", WIT,
                  authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    wit.register_log(_manifest_envelope())
    cp = w.create_checkpoint(LOG_ID)  # anchor the full history
    _, from_seq, to_seq = w.pending_checkpoint(LOG_ID)
    extension = list(w.records(LOG_ID))[from_seq - 1:to_seq]
    receipt = wit.submit(LOG_ID, cp, extension)
    w.record_receipt(LOG_ID, receipt)
    dest = tmp_path / "bundle"
    w.export_bundle(LOG_ID, dest)
    return w, dest


def test_verify_tampered_bundle_exit_1(tmp_path, capsys):
    _w, bundle = _exported(tmp_path, capsys)
    lines = (bundle / "records.jsonl").read_bytes().split(b"\n")
    lines[0] = lines[0].replace(b"alice", b"carol")
    (bundle / "records.jsonl").write_bytes(b"\n".join(lines))
    trust = _trust(tmp_path, _manifest_envelope())
    assert main(["verify", str(bundle), "--trust", str(trust),
                 "--mode", "integrity"]) == 1

def test_verify_revoked_trust_exit_3(tmp_path, capsys):
    from casf.lifecycle import sign_status
    w, bundle = _exported(tmp_path, capsys)
    mh = w.manifest_envelope(LOG_ID)["manifest_hash"]
    revoked = sign_status(AUTH, serial=2, manifest_hash=mh,
                          status="revoked", issued_at=TS,
                          reason="key compromise")
    from casf.canonical.jcs import canonicalize
    (bundle / "status.jsonl").write_bytes(canonicalize(revoked) + b"\n")
    trust = _trust(tmp_path, _manifest_envelope())
    assert main(["verify", str(bundle), "--trust", str(trust),
                 "--mode", "integrity"]) == 3

def test_verify_online_unreachable_exit_4(tmp_path, capsys):
    _w, bundle = _exported(tmp_path, capsys)
    trust = _trust(tmp_path, _manifest_envelope(), mode="online",
                   witness_url="http://127.0.0.1:9")  # nothing listens
    assert main(["verify", str(bundle), "--trust", str(trust),
                 "--mode", "online"]) == 4

def test_verify_unknown_log_trust_exit_3(tmp_path, capsys):
    _w, bundle = _exported(tmp_path, capsys)
    env = _manifest_envelope()
    trust_path = _trust(tmp_path, env)
    trust = json.loads(trust_path.read_text())
    trust["logs"] = {}  # log is not provisioned
    trust_path.write_text(json.dumps(trust))
    assert main(["verify", str(bundle), "--trust", str(trust_path),
                 "--mode", "integrity"]) == 3

# ---------------- usage and schema errors ----------------

def test_append_bad_event_exit_2(tmp_path, capsys):
    key = _key(tmp_path, capsys)
    env = _manifest_for(key)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(env))
    db = tmp_path / "log.db"
    main(["init", "--manifest", str(manifest), "--db", str(db),
          "--key", str(key)])
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    capsys.readouterr()
    assert main(["append", "--db", str(db), "--key", str(key),
                 "--event", str(bad)]) == 2

def test_oversized_bundle_line_bounded_exit_2(tmp_path, capsys):
    """T16: a hostile bundle is rejected inside bounded resources."""
    _w, bundle = _exported(tmp_path, capsys)
    with open(bundle / "records.jsonl", "ab") as f:
        f.write(b'{"body":' + b" " * 1_000_000 + b"}\n")
    trust = _trust(tmp_path, _manifest_envelope())
    assert main(["verify", str(bundle), "--trust", str(trust),
                 "--mode", "integrity"]) == 2
    err = capsys.readouterr().err
    assert "limit" in err

# ---------------- secret handling (T17) ----------------

def test_wrong_passphrase_never_printed(tmp_path, capsys, monkeypatch):
    key = _key(tmp_path, capsys)
    env = _manifest_for(key)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(env))
    db = tmp_path / "log.db"
    main(["init", "--manifest", str(manifest), "--db", str(db),
          "--key", str(key)])
    monkeypatch.setenv("CASF_PASSPHRASE", "wrong-passphrase")
    code = main(["append", "--db", str(db), "--key", str(key),
                 "--event", str(_event(tmp_path))])
    out = capsys.readouterr()
    assert code != 0
    assert "wrong-passphrase" not in out.out + out.err
    assert PASS.decode() not in out.out + out.err

def test_token_never_printed(tmp_path, capsys, monkeypatch):
    key = _key(tmp_path, capsys)
    env = _manifest_for(key)
    svc = WitnessService(tmp_path / "wit.db", WIT, token=TOKEN,
                         authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    svc.witness.register_log(env)
    server = make_server(svc, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps(env))
        db = tmp_path / "log.db"
        main(["init", "--manifest", str(manifest), "--db", str(db),
              "--key", str(key)])
        main(["append", "--db", str(db), "--key", str(key),
              "--event", str(_event(tmp_path))])
        main(["checkpoint", "--db", str(db), "--key", str(key)])
        monkeypatch.setenv("CASF_WITNESS_TOKEN", "wrong-token")
        code = main(["witness", "submit", "--db", str(db), "--key", str(key),
                     "--url", url])
        out = capsys.readouterr()
        assert code != 0
        assert "wrong-token" not in out.out + out.err
        assert TOKEN not in out.out + out.err
    finally:
        server.shutdown()
        server.server_close()
        svc.close()
