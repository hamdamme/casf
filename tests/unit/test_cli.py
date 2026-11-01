"""R10 (SPEC §19; T16, T17): CLI contracts, exit codes, diagnostics.

Exit codes: 0 requested policy passed; 1 invalid evidence or
divergence; 2 usage or schema error; 3 unknown, revoked or
unsupported trust; 4 inconclusive, pending or unavailable; 5 local
I/O or internal error. Secrets never appear in output (T17) and
malicious input is rejected inside bounded resources (T16).
"""

import io
import json
import os
import stat
import threading

import pytest
from cryptography.hazmat.primitives import serialization

from casf import crypto
from casf.canonical.jcs import canonicalize
from casf.cli import main
from casf.keys import load_key
from casf.storage import Database
from casf.witness.http import WitnessService, make_server
from tests.status import active_status, register_active
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


def test_init_rejects_duplicate_json_before_opening_store(tmp_path, capsys):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"body":{},"body":{}}')
    db = tmp_path / "log.db"
    assert main(["init", "--manifest", str(manifest), "--db", str(db),
                 "--key", str(tmp_path / "unused.key")]) == 2
    assert not db.exists()
    assert "invalid CASF JSON" in capsys.readouterr().err


def test_admin_manifest_trust_and_status_commands(tmp_path, capsys):
    auth = tmp_path / "authority.pem"
    log = tmp_path / "log.pem"
    witness = tmp_path / "witness.pem"
    for role, path in (("authority", auth), ("log", log),
                       ("witness", witness)):
        assert main(["key", "generate", "--role", role,
                     "--out", str(path)]) == 0
        capsys.readouterr()
    for role, path in (("authority", auth), ("log", log),
                       ("witness", witness)):
        key = load_key(path, passphrase=PASS)
        public_path = tmp_path / f"{role}.pub.pem"
        public_path.write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
        if role == "authority":
            authority_pub_path = public_path
        elif role == "log":
            log_pub_path = public_path
        else:
            witness_pub_path = public_path

    manifest_path = tmp_path / "manifest.json"
    assert main(["admin", "manifest", "--authority-key", str(auth),
                 "--log-public-key", str(log_pub_path),
                 "--witness-public-key", str(witness_pub_path),
                 "--out", str(manifest_path)]) == 0
    manifest = json.loads(manifest_path.read_text())
    capsys.readouterr()
    auth_key = load_key(auth, passphrase=PASS)
    crypto.verify_manifest(crypto.public_key_raw(auth_key), manifest["body"],
                           manifest["signature"])

    trust_path = tmp_path / "trust.json"
    assert main(["admin", "trust", "--manifest", str(manifest_path),
                 "--authority-public-key", str(authority_pub_path),
                 "--mode", "anchored", "--out", str(trust_path)]) == 0
    trust = json.loads(trust_path.read_text())
    assert manifest["body"]["log_id"] in trust["logs"]
    capsys.readouterr()

    status_path = tmp_path / "status.json"
    assert main(["admin", "status", "sign", "--manifest", str(manifest_path),
                 "--authority-key", str(auth), "--serial", "1",
                 "--status", "active", "--reason", "initial setup",
                 "--out", str(status_path)]) == 0
    status = json.loads(status_path.read_text())
    crypto.verify_status(crypto.public_key_raw(auth_key), status["body"],
                         status["signature"])
    assert stat.S_IMODE(os.stat(status_path).st_mode) == 0o600
    capsys.readouterr()

    witness_db = tmp_path / "witness.db"
    assert main(["admin", "register", "--manifest", str(manifest_path),
                 "--status-file", str(status_path),
                 "--authority-public-key", str(authority_pub_path),
                 "--witness-key", str(witness), "--db", str(witness_db)]) == 0
    capsys.readouterr()
    revoked_path = tmp_path / "revoked.json"
    assert main(["admin", "status", "sign", "--manifest", str(manifest_path),
                 "--authority-key", str(auth), "--serial", "2",
                 "--status", "revoked", "--reason", "test revocation",
                 "--out", str(revoked_path)]) == 0
    capsys.readouterr()
    assert main(["admin", "status", "install", "--status-file",
                 str(revoked_path), "--log-id", manifest["body"]["log_id"],
                 "--authority-public-key", str(authority_pub_path),
                 "--witness-key", str(witness), "--db", str(witness_db)]) == 0
    capsys.readouterr()


def test_append_duplicate_json_from_stdin_rejected_before_signing(
        tmp_path, capsys, monkeypatch):
    key = _key(tmp_path, capsys)
    env = _manifest_for(key)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(env))
    db = tmp_path / "log.db"
    assert main(["init", "--manifest", str(manifest_path), "--db", str(db),
                 "--key", str(key)]) == 0
    capsys.readouterr()
    before = Database(db)
    try:
        count_before = before.connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    finally:
        before.close()
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(
        b'{"event_id":"one","event_id":"two","actor":"a",'
        b'"event_type":"x","payload":{},"attributes":{}}')))
    assert main(["append", "--db", str(db), "--key", str(key),
                 "--event", "-"]) == 2
    assert "invalid CASF JSON" in capsys.readouterr().err
    after = Database(db)
    try:
        assert after.connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] == count_before
    finally:
        after.close()

# ---------------- happy path through the commands ----------------

def test_full_command_flow(tmp_path, capsys, monkeypatch):
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
    monkeypatch.delenv("CASF_PASSPHRASE")
    assert main(["export", "--db", str(db), "--out", str(bundle)]) == 0
    (bundle / "status.jsonl").write_bytes(
        canonicalize(active_status(AUTH, env["manifest_hash"])) + b"\n")
    trust = _trust(tmp_path, env)
    assert main(["verify", str(bundle), "--state", str(tmp_path / "state.json"),
                 "--initialize-state", "--trust", str(trust),
                 "--mode", "integrity"]) == 0
    out = capsys.readouterr().out
    assert "integrity" in out  # human output names the mode
    assert main(["status", "--db", str(db)]) == 0
    assert "count" in capsys.readouterr().out


def test_append_reads_strict_json_from_stdin(tmp_path, capsys, monkeypatch):
    key = _key(tmp_path, capsys)
    env = _manifest_for(key)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(env))
    db = tmp_path / "stdin.db"
    assert main(["init", "--manifest", str(manifest), "--db", str(db),
                 "--key", str(key)]) == 0
    capsys.readouterr()
    raw = json.dumps({
        "event_id": "123e4567-e89b-42d3-a456-426600000011",
        "actor": "alice", "event_type": "login", "payload": {},
        "attributes": {},
    }).encode()
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(raw)))
    assert main(["append", "--db", str(db), "--key", str(key),
                 "--event", "-"]) == 0
    check = Database(db)
    try:
        assert check.connection.execute(
            "SELECT COUNT(*) FROM records WHERE log_id = ?", (LOG_ID,)
        ).fetchone() == (1,)
    finally:
        check.close()

def test_witness_submit_then_status(tmp_path, capsys):
    key = _key(tmp_path, capsys)
    env = _manifest_for(key)
    svc = WitnessService(tmp_path / "wit.db", WIT, token=TOKEN,
                         authority_keys={crypto.key_id(AUTH_PUB): AUTH_PUB})
    register_active(svc.witness, env, AUTH)
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
    register_active(wit, _manifest_envelope(), AUTH)
    cp = w.create_checkpoint(LOG_ID)  # anchor the full history
    _, from_seq, to_seq = w.pending_checkpoint(LOG_ID)
    extension = list(w.records(LOG_ID))[from_seq - 1:to_seq]
    receipt = wit.submit(LOG_ID, cp, extension)
    w.record_receipt(LOG_ID, receipt)
    dest = tmp_path / "bundle"
    w.export_bundle(LOG_ID, dest)
    (dest / "status.jsonl").write_bytes(
        canonicalize(active_status(AUTH, w.manifest_envelope(LOG_ID)["manifest_hash"])) + b"\n")
    return w, dest


def test_verify_tampered_bundle_exit_1(tmp_path, capsys):
    _w, bundle = _exported(tmp_path, capsys)
    lines = (bundle / "records.jsonl").read_bytes().split(b"\n")
    lines[0] = lines[0].replace(b"alice", b"carol")
    (bundle / "records.jsonl").write_bytes(b"\n".join(lines))
    trust = _trust(tmp_path, _manifest_envelope())
    assert main(["verify", str(bundle), "--state", str(tmp_path / "state.json"),
                 "--initialize-state", "--trust", str(trust),
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
    assert main(["verify", str(bundle), "--state", str(tmp_path / "state.json"),
                 "--initialize-state", "--trust", str(trust),
                 "--mode", "integrity"]) == 3

def test_verify_online_unreachable_exit_4(tmp_path, capsys):
    _w, bundle = _exported(tmp_path, capsys)
    trust = _trust(tmp_path, _manifest_envelope(), mode="online",
                   witness_url="http://127.0.0.1:9")  # nothing listens
    assert main(["verify", str(bundle), "--state", str(tmp_path / "state.json"),
                 "--initialize-state", "--trust", str(trust),
                 "--mode", "online"]) == 4

def test_verify_unknown_log_trust_exit_3(tmp_path, capsys):
    _w, bundle = _exported(tmp_path, capsys)
    env = _manifest_envelope()
    trust_path = _trust(tmp_path, env)
    trust = json.loads(trust_path.read_text())
    trust["logs"] = {}  # log is not provisioned
    trust_path.write_text(json.dumps(trust))
    assert main(["verify", str(bundle), "--state", str(tmp_path / "state.json"),
                 "--initialize-state", "--trust", str(trust_path),
                 "--mode", "integrity"]) == 3

def test_verify_mismatched_provisioned_witness_id_exit_3(tmp_path, capsys):
    _w, bundle = _exported(tmp_path, capsys)
    env = _manifest_envelope()
    trust_path = _trust(tmp_path, env)
    trust = json.loads(trust_path.read_text())
    wrong_witness_id = crypto.key_id(AUTH_PUB)
    assert wrong_witness_id != env["body"]["witness_id"]
    trust["logs"][LOG_ID]["witness_id"] = wrong_witness_id
    trust_path.write_text(json.dumps(trust))

    state = tmp_path / "state.json"
    result = main(["verify", str(bundle), "--state", str(state),
                   "--initialize-state", "--trust", str(trust_path),
                   "--mode", "integrity"])

    assert result == 3
    assert "WITNESS_ID_MISMATCH" in capsys.readouterr().err
    assert not state.exists()

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
    assert main(["verify", str(bundle), "--state", str(tmp_path / "state.json"),
                 "--initialize-state", "--trust", str(trust),
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
    register_active(svc.witness, env, AUTH)
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
