"""Attack harness for the detection experiment (SPEC §23).

Each case starts from a seeded valid history with a retained witness
anchor, makes a controlled copy, injects exactly one mutation, and
invokes one named verification mode. The expectation is declared in
CASES before any run, alongside who controls which keys and stores.
Cases that correctly remain undetectable are expected to PASS and are
reported as such; the harness never upgrades them to detections.
"""

import contextlib
import json
import shutil
import sqlite3
import threading
from pathlib import Path

from benchmarks import runner, workload
from casf import crypto
from casf.bundle import read_bundle
from casf.canonical.jcs import canonicalize, parse
from casf.online import query_latest
from casf.verifier import Mode, TrustPins, verify
from casf.witness import Witness
from casf.witness.http import WitnessService, make_server
from casf.writer import Writer

LOG_ID = workload.LOG_ID
TOKEN = "bench-witness-token"
RECORDS = 38   # witnessed through 32; 33 to 38 stay unwitnessed
BATCH = 8
TARGET = 512

CASES: list[dict] = [
    {"name": "tamper-beginning", "spec": "Section 23", "mutation": "tamper",
     "position": 2, "mode": "integrity", "allow_unwitnessed": False,
     "attacker": ["writer store"], "anchor": "manifest pin",
     "connectivity": "offline", "expected": "FAIL",
     "note": "content mutation at the beginning breaks the chain"},
    {"name": "tamper-middle", "spec": "Section 23", "mutation": "tamper",
     "position": 17, "mode": "integrity", "allow_unwitnessed": False,
     "attacker": ["writer store"], "anchor": "manifest pin",
     "connectivity": "offline", "expected": "FAIL",
     "note": "content mutation in the middle breaks the chain"},
    {"name": "tamper-last-witnessed", "spec": "Section 23",
     "mutation": "tamper", "position": 32, "mode": "integrity",
     "allow_unwitnessed": False,
     "attacker": ["writer store"], "anchor": "manifest pin",
     "connectivity": "offline", "expected": "FAIL",
     "note": "content mutation at the last witnessed record"},
    {"name": "tamper-tail", "spec": "Section 23", "mutation": "tamper",
     "position": 35, "mode": "integrity", "allow_unwitnessed": False,
     "attacker": ["writer store"], "anchor": "manifest pin",
     "connectivity": "offline", "expected": "FAIL",
     "note": "content mutation in the unwitnessed tail breaks the chain"},
    {"name": "truncate-tail-integrity", "spec": "T18", "mutation": "truncate",
     "position": 32, "mode": "integrity", "allow_unwitnessed": False,
     "attacker": ["writer store"], "anchor": "manifest pin",
     "connectivity": "offline", "expected": "PASS",
     "note": "T18: integrity may pass; no rollback protection is claimed"},
    {"name": "truncate-tail-anchored", "spec": "T18", "mutation": "truncate",
     "position": 32, "mode": "anchored", "allow_unwitnessed": True,
     "attacker": ["writer store"], "anchor": "witnessed checkpoint",
     "connectivity": "offline", "expected": "PASS",
     "note": "T18: truncation back to the anchor stays consistent; "
             "no rollback protection is claimed"},
    {"name": "stolen-key-prefix-anchored", "spec": "T20",
     "mutation": "rewrite", "position": 16, "mode": "anchored",
     "allow_unwitnessed": True,
     "attacker": ["writer store", "log key"],
     "anchor": "witnessed checkpoints and receipts",
     "connectivity": "offline", "expected": "FAIL",
     "note": "T20: rewriting inside the witnessed prefix diverges "
             "from the retained anchor"},
    {"name": "stolen-key-suffix", "spec": "T20", "mutation": "rewrite",
     "position": 32, "mode": "anchored", "allow_unwitnessed": True,
     "attacker": ["writer store", "log key"],
     "anchor": "witnessed checkpoints and receipts",
     "connectivity": "offline", "expected": "PASS",
     "note": "T20: a false suffix after the last witnessed record "
             "remains possible offline"},
    {"name": "witness-rollback-retained", "spec": "T21",
     "mutation": "rollback", "position": 24, "mode": "online",
     "allow_unwitnessed": False,
     "attacker": ["witness store"],
     "anchor": "retained checkpoint pin", "connectivity": "online",
     "expected": "FAIL",
     "note": "T21: a client holding the earlier pin sees the conflict"},
    {"name": "witness-rollback-isolated", "spec": "T21",
     "mutation": "rollback", "position": 24, "mode": "online",
     "allow_unwitnessed": False,
     "attacker": ["witness store", "writer store"],
     "anchor": "none beyond the served evidence",
     "connectivity": "online", "expected": "PASS",
     "note": "T21: conditional failure only; no unconditional "
             "detection is claimed for an isolated client"},
]


def _pins(manifest_hash: str) -> TrustPins:
    auth_pub = crypto.public_key_raw(workload.seeded_key("authority"))
    wit_pub = crypto.public_key_raw(workload.seeded_key("witness"))
    return TrustPins(
        authority_keys={crypto.key_id(auth_pub): auth_pub},
        witness_keys={crypto.key_id(wit_pub): wit_pub},
        log_id=LOG_ID, manifest_hash=manifest_hash)


def _authority_keys() -> dict:
    auth_pub = crypto.public_key_raw(workload.seeded_key("authority"))
    return {crypto.key_id(auth_pub): auth_pub}


def _checkpoint_cycle(writer: Writer, witness: Witness,
                      appended: list[dict]) -> None:
    writer.create_checkpoint(LOG_ID)
    pending = writer.pending_checkpoint(LOG_ID)
    if pending is None:  # pragma: no cover
        raise RuntimeError("pending checkpoint missing")
    envelope, from_seq, to_seq = pending
    receipt = witness.submit(LOG_ID, envelope,
                             appended[from_seq - 1:to_seq])
    writer.record_receipt(LOG_ID, receipt)


def _open(root: Path) -> tuple[Writer, Witness]:
    writer = Writer(root / "writer.db", workload.seeded_key("log"))
    witness = Witness(root / "witness.db", workload.seeded_key("witness"),
                      authority_keys=_authority_keys())
    return writer, witness


def _build_history(root: Path, records: int = RECORDS) -> str:
    """Seeded history, checkpoints at batch multiples only; returns
    the manifest hash."""
    root.mkdir(parents=True, exist_ok=True)
    writer, witness = _open(root)
    try:
        manifest = runner._manifest()
        writer.create_log(manifest)
        witness.register_log(manifest)
        appended: list[dict] = []
        for i, event in enumerate(
                workload.generate(41, records, TARGET), start=1):
            appended.append(writer.append(LOG_ID, **event))
            if i % BATCH == 0:
                _checkpoint_cycle(writer, witness, appended)
        return str(manifest["manifest_hash"])
    finally:
        writer.close()
        witness.close()


def _extend_history(root: Path, count: int, seed: int) -> None:
    writer, witness = _open(root)
    try:
        appended = list(writer.records(LOG_ID))
        for event in workload.generate(seed, count, TARGET):
            appended.append(writer.append(LOG_ID, **event))
        _checkpoint_cycle(writer, witness, appended)
    finally:
        writer.close()
        witness.close()


def _attacker_connection(db_path: Path) -> sqlite3.Connection:
    """A store controlling attacker drops the append only triggers;
    they guard honest writers, not someone holding the file."""
    con = sqlite3.connect(db_path)
    con.execute("DROP TRIGGER IF EXISTS records_no_update")
    con.execute("DROP TRIGGER IF EXISTS records_no_delete")
    return con


def _mutate_tamper(db_path: Path, seq: int) -> None:
    con = _attacker_connection(db_path)
    try:
        row = con.execute(
            "SELECT envelope FROM records WHERE log_id = ? AND seq = ?",
            (LOG_ID, seq)).fetchone()
        envelope = parse(bytes(row[0]))
        body = envelope["body"]
        payload = body["payload"]
        data = payload["data"]
        payload["data"] = ("X" if data[0] != "X" else "Y") + data[1:]
        con.execute(
            "UPDATE records SET envelope = ? WHERE log_id = ? AND seq = ?",
            (sqlite3.Binary(canonicalize(envelope)), LOG_ID, seq))
        con.commit()
    finally:
        con.close()


def _reset_head(con: sqlite3.Connection, keep: int) -> None:
    head = con.execute(
        "SELECT record_hash FROM records WHERE log_id = ? AND seq = ?",
        (LOG_ID, keep)).fetchone()[0]
    con.execute("DELETE FROM records WHERE log_id = ? AND seq > ?",
                (LOG_ID, keep))
    con.execute("UPDATE heads SET count = ?, head_hash = ? "
                "WHERE log_id = ?", (keep, head, LOG_ID))
    con.commit()


def _mutate_truncate(db_path: Path, keep: int) -> None:
    con = _attacker_connection(db_path)
    try:
        _reset_head(con, keep)
    finally:
        con.close()


def _mutate_rewrite(db_path: Path, keep: int, total: int) -> None:
    con = _attacker_connection(db_path)
    try:
        _reset_head(con, keep)
    finally:
        con.close()
    writer = Writer(db_path, workload.seeded_key("log"))  # stolen key
    try:
        for event in workload.generate(1041, total - keep, TARGET):
            writer.append(LOG_ID, **event)
    finally:
        writer.close()


def _export(db_path: Path, dest: Path) -> Path:
    writer = Writer(db_path, workload.seeded_key("log"))
    try:
        return writer.export_bundle(LOG_ID, dest)
    finally:
        writer.close()


def _verify_bundle(bundle_dir: Path, manifest_hash: str, case: dict,
                   online_query=None, retained=None):
    bundle = read_bundle(bundle_dir)
    return verify(
        bundle.manifest, bundle.records, _pins(manifest_hash),
        mode=Mode(case["mode"]),
        status_envelopes=[workload.active_status(manifest_hash)],
        checkpoint_envelopes=bundle.checkpoints,
        receipt_envelopes=bundle.receipts,
        allow_unwitnessed=bool(case["allow_unwitnessed"]),
        online_query=online_query, retained_checkpoint=retained)


@contextlib.contextmanager
def _serve(db_path: Path):
    service = WitnessService(db_path, workload.seeded_key("witness"),
                             token=TOKEN, authority_keys=_authority_keys())
    server = make_server(service, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        service.close()


def _run_rollback(case: dict, work: Path) -> tuple[str, list[str]]:
    base = work / "base"
    manifest_hash = _build_history(base, records=24)
    snapshot = work / "witness-snapshot.db"
    shutil.copy(base / "witness.db", snapshot)
    _extend_history(base, BATCH, seed=1042)  # witnessed through 32
    full = _export(base / "writer.db", work / "bundle-full")

    wit_pub = crypto.public_key_raw(workload.seeded_key("witness"))

    def _query(url: str):
        return lambda: query_latest(url, LOG_ID, TOKEN, wit_pub,
                                    timeout=5.0)

    if case["name"] == "witness-rollback-retained":
        bundle = read_bundle(full)
        anchor = bundle.checkpoints[-1]
        retained = (int(anchor["body"]["index"]),
                    str(anchor["checkpoint_hash"]))
        with _serve(base / "witness.db"):
            pass  # healthy state reached the client earlier
        shutil.copy(snapshot, base / "witness.db")  # the rollback
        with _serve(base / "witness.db") as url:
            report = _verify_bundle(full, manifest_hash, case,
                                    online_query=_query(url),
                                    retained=retained)
        return report.result.value, list(report.diagnostic_codes)

    # isolated client: evidence is truncated to the rolled back state,
    # so the served bundle and the witness agree with each other
    shutil.copy(snapshot, base / "witness.db")
    _mutate_truncate(base / "writer.db", keep=24)
    con = _attacker_connection(base / "writer.db")
    try:
        stale = con.execute(
            "SELECT checkpoint_hash FROM checkpoints WHERE log_id = ? "
            "AND count > ?", (LOG_ID, 24)).fetchall()
        for (checkpoint_hash,) in stale:
            con.execute("DELETE FROM receipts WHERE checkpoint_hash = ?",
                        (checkpoint_hash,))
        con.execute("DELETE FROM checkpoints WHERE log_id = ? "
                    "AND count > ?", (LOG_ID, 24))
        con.commit()
    finally:
        con.close()
    truncated = _export(base / "writer.db", work / "bundle-truncated")
    with _serve(base / "witness.db") as url:
        report = _verify_bundle(truncated, manifest_hash, case,
                                online_query=_query(url))
    return report.result.value, list(report.diagnostic_codes)


def run_case(case: dict, work_dir: Path) -> dict:
    """Run one predeclared case and compare with its expectation."""
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    if case["mutation"] == "rollback":
        observed, codes = _run_rollback(case, work)
    else:
        base = work / "base"
        manifest_hash = _build_history(base)
        db_path = base / "writer.db"
        if case["mutation"] == "tamper":
            _mutate_tamper(db_path, int(case["position"]))
        elif case["mutation"] == "truncate":
            _mutate_truncate(db_path, int(case["position"]))
        elif case["mutation"] == "rewrite":
            _mutate_rewrite(db_path, int(case["position"]), RECORDS)
        else:  # pragma: no cover
            raise ValueError(f"unknown mutation {case['mutation']}")
        bundle = _export(db_path, work / "bundle")
        report = _verify_bundle(bundle, manifest_hash, case)
        observed, codes = report.result.value, list(report.diagnostic_codes)
    row = {k: case[k] for k in ("name", "spec", "mutation", "mode",
                                "attacker", "anchor", "connectivity",
                                "expected", "note")}
    row["observed"] = observed
    row["codes"] = codes
    row["match"] = observed == case["expected"]
    return row


def run_matrix(out_dir: Path) -> list[dict]:
    """Run every case and write the raw matrix artifact.

    Working databases and bundles live in a temporary directory; the
    committed output is the matrix JSON only.
    """
    import tempfile

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        rows = [run_case(case, Path(work) / case["name"])
                for case in CASES]
    artifact = {
        "experiment": "detection matrix (SPEC Section 23)",
        "history": {"records": RECORDS, "checkpoint_batch": BATCH,
                    "target_bytes": TARGET, "seed": 41,
                    "witnessed_through": RECORDS - RECORDS % BATCH},
        "environment": runner._environment(),
        "rows": rows,
    }
    (out / "attacks.v1.json").write_text(json.dumps(artifact, indent=2))
    lines = [
        "# Detection matrix (SPEC Section 23)", "",
        (f"history: {RECORDS} records, checkpoint batch {BATCH}, "
        f"witnessed through {RECORDS - RECORDS % BATCH}, seed 41"), "",
        ("| case | spec | mode | attacker controls | expected | "
        "observed | match |"),
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['name']} | {row['spec']} | {row['mode']} | "
            f"{', '.join(row['attacker'])} | {row['expected']} | "
            f"{row['observed']} | {row['match']} |")
    lines += ["",
              ("Notes per case are in attacks.v1.json; cases expected "
              "to PASS are documented non detections, not failures "
              "of the harness.")]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return rows
