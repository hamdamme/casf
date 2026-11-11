"""Run a synthetic verified CLI workflow against an ephemeral loopback witness.

Usage: PYTHONPATH=src .venv/bin/python -m examples.verified_workflow NEW_DIRECTORY
Only public synthetic evidence survives; keys, databases and retained state are
temporary. This is a functional demonstration, not a deployment or benchmark.
"""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import tempfile
import threading
from contextlib import closing, contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from casf import crypto
from casf.bundle import read_bundle
from casf.canonical.jcs import canonicalize
from casf.cli import main as cli
from casf.keys import load_key
from casf.witness.http import WitnessService, make_server
from casf.writer import Writer


@contextmanager
def demo_secrets():
    values = {"CASF_PASSPHRASE": secrets.token_urlsafe(32),
              "CASF_WITNESS_TOKEN": secrets.token_urlsafe(32)}
    previous = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield values
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def run(output: Path) -> dict:
    output = output.absolute()
    output.mkdir(mode=0o700)  # never reuse an existing demonstration
    steps = []

    def command(label, *args, expected=0):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli([str(arg) for arg in args] + ["--json"])
        value = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else {}
        steps.append({"step": label, "exit_code": code, "expected_exit_code": expected})
        if code != expected:
            raise RuntimeError(f"{label}: expected exit {expected}, got {code}: {stderr.getvalue()}")
        return value

    try:
        with tempfile.TemporaryDirectory(prefix="casf-demo-") as directory, demo_secrets() as secret:
            work = Path(directory)
            keys = {}
            for role in ("authority", "log", "witness"):
                command(f"create {role} key", "key", "generate", "--role", role,
                        "--out", work / f"{role}.pem")
                keys[role] = load_key(work / f"{role}.pem",
                                      passphrase=secret["CASF_PASSPHRASE"].encode())
                (work / f"{role}.pub.pem").write_bytes(keys[role].public_key().public_bytes(
                    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            manifest, status, trust = work / "manifest.json", work / "status.json", output / "trust.json"
            command("create manifest", "admin", "manifest", "--authority-key", work / "authority.pem",
                    "--log-public-key", work / "log.pub.pem", "--witness-public-key",
                    work / "witness.pub.pem", "--out", manifest)
            command("sign active status", "admin", "status", "sign", "--manifest", manifest,
                    "--authority-key", work / "authority.pem", "--serial", "1", "--status", "active",
                    "--reason", "synthetic demonstration", "--out", status)
            command("register witness", "admin", "register", "--manifest", manifest,
                    "--status-file", status, "--authority-public-key", work / "authority.pub.pem",
                    "--witness-key", work / "witness.pem", "--db", work / "witness.db")
            authority = crypto.public_key_raw(keys["authority"])
            service = WitnessService(work / "witness.db", keys["witness"],
                                     token=secret["CASF_WITNESS_TOKEN"],
                                     authority_keys={crypto.key_id(authority): authority})
            server = make_server(service, "127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}"
                command("provision trust", "admin", "trust", "--manifest", manifest,
                        "--authority-public-key", work / "authority.pub.pem", "--witness-url", url,
                        "--mode", "anchored", "--out", trust)
                common = ["--db", work / "writer.db", "--key", work / "log.pem", "--trust", trust,
                          "--status-file", status, "--state", work / "writer-state.json"]
                initialized = command("verified initialization", "init", *common,
                                      "--manifest", manifest, "--initialize-state")
                if initialized.get("startup_verified") is not True:
                    raise RuntimeError("initialization did not verify startup")
                document = output / "synthetic-document.txt"
                document.write_text("Synthetic demonstration document. No personal data.\n")
                fingerprint = hashlib.sha256(document.read_bytes()).hexdigest()
                event = work / "event.json"
                event.write_text(json.dumps({"event_id": "123e4567-e89b-42d3-a456-426614174001",
                    "actor": "synthetic-demo", "event_type": "document-recorded",
                    "payload": {"sha256": fingerprint}, "attributes": {}}))
                command("append document fingerprint", "append", *common, "--event", event)
                command("retry identical event", "append", *common, "--event", event)
                worker = command("witness pending record", "witness", "work", *common, "--once")
                if (worker.get("committed"), worker.get("witnessed"), worker.get("backlog")) != (1, 1, 0):
                    raise RuntimeError("worker did not witness exactly one idempotent record")
                bundle = output / "bundle"
                command("export public evidence", "export", "--db", work / "writer.db",
                        "--trust", trust, "--out", bundle)
                (bundle / "status.jsonl").write_bytes(canonicalize(json.loads(status.read_text())) + b"\n")
                evidence = read_bundle(bundle)
                if evidence.records[0]["body"]["payload"]["sha256"] != fingerprint:
                    raise RuntimeError("recorded fingerprint does not match the demonstration file")
                verify = ["--trust", trust, "--state", work / "verifier-state.json"]
                reports = {}
                for mode in ("integrity", "anchored", "online"):
                    reports[mode] = command(f"verify {mode}", "verify", bundle, *verify, "--mode", mode,
                                           *(["--initialize-state"] if mode == "integrity" else []))
                state_before = (work / "verifier-state.json").read_bytes()
                tampered = work / "tampered"
                shutil.copytree(bundle, tampered)
                record = evidence.records[0]
                record["body"]["payload"]["sha256"] = "0" * 64
                (tampered / "records.jsonl").write_bytes(canonicalize(record) + b"\n")
                bad = command("reject modified record", "verify", tampered, *verify,
                              "--mode", "integrity", expected=1)
                if bad.get("result") != "FAIL" or (work / "verifier-state.json").read_bytes() != state_before:
                    raise RuntimeError("modified evidence was accepted or replaced retained state")
                with closing(Writer(work / "writer.db")) as reader:
                    reader.backup(work / "backup.db")
                backup = command("inspect backup", "status", "--db", work / "backup.db")
                if backup.get("count") != 1:
                    raise RuntimeError("backup did not retain the committed record")
                checkpoint, receipt = work / "anchor-checkpoint.json", work / "anchor-receipt.json"
                checkpoint.write_bytes(canonicalize(evidence.checkpoints[-1]))
                receipt.write_bytes(canonicalize(evidence.receipts[-1]))
                restored = command("authenticate restored bundle", "restore", bundle,
                    "--db", work / "restored.db", "--key", work / "log.pem", "--trust", trust,
                    "--anchor-checkpoint", checkpoint, "--anchor-receipt", receipt)
                if restored.get("freshness_checked") is not False:
                    raise RuntimeError("offline restore claimed a fresh witness check")
                restored_common = [*common]
                restored_common[1] = work / "restored.db"
                command("promote and seal restored writer", "seal", *restored_common)
                final = command("witness final seal", "witness", "work", *restored_common, "--once")
                if final.get("state") != "sealed":
                    raise RuntimeError("restored writer did not retain its witnessed final seal")
            finally:
                server.shutdown()
                thread.join()
                server.server_close()
                service.close()
            unavailable = command("report unavailable witness", "verify", bundle, *verify,
                                  "--mode", "online", expected=4)
            if "FRESHNESS_INCONCLUSIVE" not in unavailable.get("diagnostic_codes", []):
                raise RuntimeError("unavailable witness was not reported as inconclusive")
            summary = {"status": "complete", "synthetic": True, "single_host": True,
                       "document_sha256": fingerprint, "steps": steps,
                       "verification": reports, "tamper_result": bad["result"],
                       "unavailable_witness_result": unavailable["result"],
                       "worker": worker, "restored_final_state": final["state"],
                       "private_state_retained": False}
    except Exception:
        (output / "summary.json").write_text(json.dumps({"status": "incomplete", "steps": steps}, indent=2) + "\n")
        raise
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = run(args.output)
    print(f"Completed {len(result['steps'])} checks; public synthetic evidence: {args.output}")


if __name__ == "__main__":
    main()
