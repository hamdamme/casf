"""Command line interface (SPEC §19).

Exit codes: 0 requested policy passed; 1 invalid cryptographic
evidence or divergence; 2 usage or schema error; 3 unknown, revoked
or unsupported trust or profile; 4 inconclusive, pending or
unavailable; 5 local I/O or internal error. Every command supports
--json for stable structured output. Secrets come from named
environment variables, never from command line values, and no error
output ever prints a private key, passphrase or token (T17).
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import cast

from casf import crypto
from casf.bundle import read_bundle
from casf.errors import CasfError, InconclusiveError, SchemaError
from casf.keys import generate_key, load_key
from casf.online import query_latest
from casf.storage import Database
from casf.trust.state import locked_state
from casf.types import JsonObject, JsonValue
from casf.verifier import Mode, Result, TrustPins, TrustStatus, verify
from casf.writer import Writer

__all__ = ["main"]

PASS_ENV = "CASF_PASSPHRASE"
TOKEN_ENV = "CASF_WITNESS_TOKEN"


# ------------------------------------------------------------ helpers

def _secret(env_name: str) -> bytes:
    value = os.environ.get(env_name)
    if not value:
        raise SchemaError(
            f"environment variable {env_name} is not set; secrets come "
            "from named environment variables, never command line values")
    return value.encode()


def _writer(args: argparse.Namespace) -> Writer:
    key = load_key(args.key, passphrase=_secret(args.passphrase_env))
    return Writer(args.db, key)


def _sole_log_id(db_path: str) -> str:
    db = Database(db_path)
    try:
        rows = db.connection.execute(
            "SELECT log_id FROM manifests").fetchall()
        if len(rows) != 1:
            raise CasfError("expected exactly one log in the store")
        value = rows[0][0]
        if not isinstance(value, str):
            raise CasfError("stored manifest is corrupt")
        return value
    finally:
        db.close()


def _read_json_file(path: str) -> JsonObject:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise SchemaError(f"cannot read JSON from {path}") from e
    if not isinstance(data, dict):
        raise SchemaError(f"expected a JSON object in {path}")
    return data


def _print(args: argparse.Namespace, obj: JsonObject, human: str) -> None:
    if args.json:
        print(json.dumps(obj, sort_keys=True))
    else:
        print(human)


def _body_of(envelope: JsonObject) -> JsonObject:
    body = envelope["body"]
    if not isinstance(body, dict):
        raise SchemaError("envelope body is missing or not an object")
    return body


def _count_of(envelope: JsonObject) -> JsonValue:
    return _body_of(envelope).get("count", "unknown")


# ------------------------------------------------------------ commands

def _cmd_key_generate(args: argparse.Namespace) -> int:
    generate_key(args.role, args.out,
                 passphrase=_secret(args.passphrase_env))
    _print(args, {"created": args.out, "role": args.role},
           f"created {args.role} key at {args.out}")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    manifest = _read_json_file(args.manifest)
    writer = _writer(args)
    writer.create_log(manifest)
    log_id = _body_of(manifest).get("log_id", "unknown")
    _print(args, {"log_id": log_id, "count": 0},
           f"initialized log {log_id}")
    return 0


def _cmd_append(args: argparse.Namespace) -> int:
    event = _read_json_file(args.event)
    if set(event) != {"event_id", "actor", "event_type", "payload",
                      "attributes"}:
        raise SchemaError("event must be exactly event_id, actor, "
                          "event_type, payload, attributes")
    event_id = event["event_id"]
    actor = event["actor"]
    event_type = event["event_type"]
    payload = event["payload"]
    attributes = event["attributes"]
    if not isinstance(event_id, str) or not isinstance(actor, str) \
            or not isinstance(event_type, str) \
            or not isinstance(payload, dict) \
            or not isinstance(attributes, dict):
        raise SchemaError("event field types are wrong")
    writer = _writer(args)
    log_id = _sole_log_id(args.db)
    envelope = writer.append(
        log_id, event_id=event_id, actor=actor, event_type=event_type,
        payload=payload, attributes=attributes)
    seq = _body_of(envelope).get("seq", "unknown")
    _print(args, {"seq": seq, "event_id": event_id},
           f"appended record seq {seq}")
    return 0


def _cmd_checkpoint(args: argparse.Namespace) -> int:
    writer = _writer(args)
    log_id = _sole_log_id(args.db)
    pending = writer.pending_checkpoint(log_id)
    if pending is not None:
        count = _count_of(pending[0])
        _print(args, {"pending": True, "count": count},
               f"reusing pending checkpoint through count {count}")
        return 0
    envelope = writer.create_checkpoint(log_id)
    count = _count_of(envelope)
    _print(args, {"pending": True, "count": count},
           f"created pending checkpoint through count {count}")
    return 0


def _cmd_witness_submit(args: argparse.Namespace) -> int:
    writer = _writer(args)
    log_id = _sole_log_id(args.db)
    if writer.pending_checkpoint(log_id) is None:
        print("error: no pending checkpoint for this log", file=sys.stderr)
        return 4
    token = _secret(args.token_env).decode()
    try:
        receipt = writer.submit_pending(log_id, args.url, token)
    except CasfError as e:
        print(f"error: {e}", file=sys.stderr)
        return 4  # pending or unavailable; identical bytes await retry
    count = _count_of(receipt)
    _print(args, {"accepted": True, "count": count},
           f"receipt accepted through count {count}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    writer = _writer(args)
    log_id = _sole_log_id(args.db)
    dest = writer.export_bundle(log_id, args.out)
    _print(args, {"bundle": str(dest)}, f"exported bundle to {dest}")
    return 0


def _cmd_seal(args: argparse.Namespace) -> int:
    writer = _writer(args)
    log_id = _sole_log_id(args.db)
    try:
        envelope = writer.seal_log(log_id)
    except CasfError as e:
        if str(e).startswith("PENDING_DRAIN"):
            print(f"error: {e}", file=sys.stderr)
            return 4
        raise
    body = envelope["body"]
    count = body["count"] if isinstance(body, dict) else "unknown"
    _print(args, {"sealed": True, "count": count},
           f"sealed at count {count}; final checkpoint pending receipt")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    db = Database(args.db)
    try:
        rows = db.connection.execute(
            "SELECT log_id, count, sealed FROM heads").fetchall()
        if len(rows) != 1:
            raise CasfError("expected exactly one log in the store")
        log_id, count, sealed = rows[0]
        accepted = db.connection.execute(
            "SELECT MAX(count) FROM checkpoints WHERE log_id = ? "
            "AND state = 'accepted'", (log_id,)).fetchone()[0]
        witnessed = accepted if isinstance(accepted, int) else 0
        pending = db.connection.execute(
            "SELECT 1 FROM outbox WHERE log_id = ?",
            (log_id,)).fetchone() is not None
    finally:
        db.close()
    report: JsonObject = {
        "log_id": log_id, "count": count, "sealed": bool(sealed),
        "witnessed": witnessed, "backlog": count - witnessed,
        "pending_checkpoint": pending,
    }
    _print(args, report,
           f"count {count}, witnessed {witnessed}, "
           f"backlog {count - witnessed}"
           + (", sealed" if sealed else "")
           + (", checkpoint pending" if pending else ""))
    return 0


_TRUST_FIELDS = {"version", "authorities", "logs", "policy"}
_TRUST_LOG_FIELDS = {"manifest_hash", "witness_id", "witness_url",
                     "minimum_status_serial"}
_TRUST_POLICY_FIELDS = {"mode", "allow_unwitnessed",
                        "query_timeout_seconds", "max_chain_steps"}


def _load_trust(path: str, log_id: str) -> tuple[dict[str, bytes],
                                                 JsonObject, JsonObject]:
    trust = _read_json_file(path)
    if set(trust) != _TRUST_FIELDS:
        raise SchemaError("trust file must be exactly version, "
                          "authorities, logs, policy")
    authorities = trust["authorities"]
    logs = trust["logs"]
    policy = trust["policy"]
    if not isinstance(authorities, dict) or not isinstance(logs, dict) \
            or not isinstance(policy, dict):
        raise SchemaError("trust file field types are wrong")
    if set(policy) != _TRUST_POLICY_FIELDS:
        raise SchemaError("trust policy fields are wrong")
    keys: dict[str, bytes] = {}
    for issuer, encoded in authorities.items():
        if not isinstance(encoded, str):
            raise SchemaError("authority keys must be base64url strings")
        keys[issuer] = crypto.b64url_decode(encoded)
    entry = logs.get(log_id)
    if entry is None:
        raise CasfError("LOG_NOT_PROVISIONED: the trust file does not "
                        "provision this log")
    if not isinstance(entry, dict) or set(entry) != _TRUST_LOG_FIELDS:
        raise SchemaError("trust log entry fields are wrong")
    return keys, entry, policy


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        bundle = read_bundle(args.path, max_records=args.max_records,
                             max_evidence_objects=args.max_evidence_objects,
                             max_total_bytes=args.max_bundle_bytes)
    except CasfError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2  # hostile or malformed bundle, bounded rejection (T16)
    body = bundle.manifest["body"]
    if not isinstance(body, dict):
        print("error: manifest is corrupt", file=sys.stderr)
        return 2
    log_id = body["log_id"]
    if not isinstance(log_id, str):
        print("error: manifest is corrupt", file=sys.stderr)
        return 2
    try:
        authorities, entry, policy = _load_trust(args.trust, log_id)
    except CasfError as e:
        code = 3 if str(e).startswith("LOG_NOT_PROVISIONED") else 2
        print(f"error: {e}", file=sys.stderr)
        return code
    witness_key = body["witness_public_key"]
    witness_id = body["witness_id"]
    if not isinstance(witness_key, str) or not isinstance(witness_id, str):
        print("error: manifest is corrupt", file=sys.stderr)
        return 2
    witness_pub = crypto.b64url_decode(witness_key)
    minimum = entry["minimum_status_serial"]
    pins = TrustPins(
        authority_keys=authorities,
        witness_keys={witness_id: witness_pub},
        log_id=log_id, manifest_hash=str(entry["manifest_hash"]),
        minimum_status_serial=minimum if type(minimum) is int else 1)
    chain_budget = policy["max_chain_steps"]
    if type(chain_budget) is not int or chain_budget < 1:
        raise SchemaError("max_chain_steps must be a positive integer")
    if type(minimum) is not int or minimum < 1:
        raise SchemaError("minimum_status_serial must be a positive integer")
    mode_name = args.mode or str(policy["mode"])
    try:
        mode = Mode(mode_name)
    except ValueError:
        print(f"error: unknown mode {mode_name}", file=sys.stderr)
        return 2
    online_query = None
    if mode is Mode.ONLINE:
        url = str(entry["witness_url"])
        token = _secret(args.token_env).decode()
        timeout = policy["query_timeout_seconds"]
        budget = timeout if isinstance(timeout, (int, float)) else 10.0

        def online_query() -> object:
            return query_latest(url, log_id, token, witness_pub,
                                timeout=budget)

    state_path = Path(args.state).absolute()
    if state_path.resolve().is_relative_to(Path(args.path).resolve()):
        raise SchemaError("verifier state must be outside the evidence bundle")
    with locked_state(str(state_path), str(entry["manifest_hash"]),
                      initialize=args.initialize_state) as state:
        previous = state.previous
        if previous is not None:
            pins = TrustPins(
                authority_keys=pins.authority_keys, witness_keys=pins.witness_keys,
                log_id=pins.log_id, manifest_hash=pins.manifest_hash,
                minimum_status_serial=max(minimum, previous.status_serial))
        report = verify(
            bundle.manifest, bundle.records, pins, mode=mode,
            checkpoint_envelopes=bundle.checkpoints,
            receipt_envelopes=bundle.receipts,
            status_envelopes=bundle.statuses,
            max_chain_steps=chain_budget,
            max_records=args.max_records,
            allow_unwitnessed=bool(policy["allow_unwitnessed"]),
            online_query=online_query,
            retained_checkpoint=previous.checkpoint if previous else None)
        if report.result is Result.PASS:
            state.save(report.observed_status_serial, report.checkpoint)
            if previous is None:
                report.diagnostic_codes.append("VERIFIER_STATE_INITIALIZED")
            if report.checkpoint is not None and (previous is None or previous.checkpoint is None):
                report.diagnostic_codes.append("CHECKPOINT_FIRST_OBSERVATION")
    summary: JsonObject = {
        "mode": report.mode.value, "result": report.result.value,
        "verified_through": report.verified_through,
        "witnessed_through": report.witnessed_through,
        "unwitnessed_count": report.unwitnessed_count,
        "anchor_status": report.anchor_status.value,
        "freshness_status": report.freshness_status.value,
        "trust_status": report.trust_status.value,
        "diagnostic_codes": cast(list[JsonValue],
                                 report.diagnostic_codes),
    }
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"mode: {report.mode.value}  result: {report.result.value}")
        print(f"verified through: {report.verified_through}  "
              f"witnessed through: {report.witnessed_through}  "
              f"unwitnessed: {report.unwitnessed_count}")
        if report.diagnostic_codes:
            print("diagnostics: " + ", ".join(report.diagnostic_codes))
    if report.result is Result.PASS:
        return 0
    if report.result is Result.INCONCLUSIVE:
        return 4
    if report.trust_status in (TrustStatus.REVOKED, TrustStatus.UNTRUSTED,
                               TrustStatus.UNKNOWN):
        return 3
    return 1


# -------------------------------------------------------------- parser

def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("limit must be a positive integer")
    return number


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true",
                        help="stable structured output")
    parser = argparse.ArgumentParser(
        prog="casf", description="Cryptographic audit and signing "
                                 "framework commands (SPEC §19)")
    sub = parser.add_subparsers(dest="command", required=True)

    key = sub.add_parser("key", parents=[common])
    key_sub = key.add_subparsers(dest="key_command", required=True)
    gen = key_sub.add_parser("generate", parents=[common])
    gen.add_argument("--role", required=True,
                     choices=["authority", "log", "witness"])
    gen.add_argument("--out", required=True)
    gen.add_argument("--passphrase-env", default=PASS_ENV)
    gen.set_defaults(func=_cmd_key_generate)

    init = sub.add_parser("init", parents=[common])
    init.add_argument("--manifest", required=True)
    init.add_argument("--db", required=True)
    init.add_argument("--key", required=True)
    init.add_argument("--passphrase-env", default=PASS_ENV)
    init.set_defaults(func=_cmd_init)

    append = sub.add_parser("append", parents=[common])
    append.add_argument("--db", required=True)
    append.add_argument("--key", required=True)
    append.add_argument("--event", required=True,
                        help="request JSON file (use - for stdin)")
    append.add_argument("--passphrase-env", default=PASS_ENV)
    append.set_defaults(func=_cmd_append)

    checkpoint = sub.add_parser("checkpoint", parents=[common])
    checkpoint.add_argument("--db", required=True)
    checkpoint.add_argument("--key", required=True)
    checkpoint.add_argument("--passphrase-env", default=PASS_ENV)
    checkpoint.set_defaults(func=_cmd_checkpoint)

    witness = sub.add_parser("witness", parents=[common])
    wit_sub = witness.add_subparsers(dest="witness_command", required=True)
    submit = wit_sub.add_parser("submit", parents=[common])
    submit.add_argument("--db", required=True)
    submit.add_argument("--key", required=True)
    submit.add_argument("--url", required=True)
    submit.add_argument("--token-env", default=TOKEN_ENV)
    submit.add_argument("--passphrase-env", default=PASS_ENV)
    submit.set_defaults(func=_cmd_witness_submit)

    export = sub.add_parser("export", parents=[common])
    export.add_argument("--db", required=True)
    export.add_argument("--key", required=True)
    export.add_argument("--out", required=True)
    export.add_argument("--passphrase-env", default=PASS_ENV)
    export.set_defaults(func=_cmd_export)

    ver = sub.add_parser("verify", parents=[common])
    ver.add_argument("path")
    ver.add_argument("--trust", required=True)
    ver.add_argument("--state", required=True,
                     help="verifier state in a separate protected directory")
    ver.add_argument("--initialize-state", action="store_true",
                     help="explicitly initialize previously unobserved manifest state")
    ver.add_argument("--mode", choices=["integrity", "anchored", "online"])
    ver.add_argument("--token-env", default=TOKEN_ENV)
    ver.add_argument("--max-records", type=_positive_int, default=1_000_000)
    ver.add_argument("--max-evidence-objects", type=_positive_int, default=100_000)
    ver.add_argument("--max-bundle-bytes", type=_positive_int, default=256 * 1024 * 1024)
    ver.set_defaults(func=_cmd_verify)

    seal = sub.add_parser("seal", parents=[common])
    seal.add_argument("--db", required=True)
    seal.add_argument("--key", required=True)
    seal.add_argument("--passphrase-env", default=PASS_ENV)
    seal.set_defaults(func=_cmd_seal)

    status = sub.add_parser("status", parents=[common])
    status.add_argument("--db", required=True)
    status.set_defaults(func=_cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the SPEC §19 exit code."""
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:  # argparse usage errors map to exit 2
        return int(e.code) if isinstance(e.code, int) else 2
    try:
        result = args.func(args)
    except SchemaError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except InconclusiveError as e:
        print(f"error: {e}", file=sys.stderr)
        return 4
    except CasfError as e:
        print(f"error: {e}", file=sys.stderr)
        return 5
    except OSError as e:
        print(f"error: local I/O failure: {e.strerror or e}",
              file=sys.stderr)
        return 5
    return int(result)


if __name__ == "__main__":
    sys.exit(main())
