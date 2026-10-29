"""H1 writer rollback experiment (SPEC 001 Section 22).

Canonical H1: a signed chain with an external witness (C) detects
restoration below the witness retained state when the witness stays
honest and reachable; an isolated signed chain with only local
checkpoints (B) cannot distinguish the same old valid snapshot from its
original history without a newer independent reference.

This differs from T21: T21 rolls back witness state; here the witness
state is preserved and only the writer store is rolled back.

Arm B production note: the CASF writer accepts at most one unwitnessed
checkpoint (the outbox rule), so a local checkpoint only profile is not
a supported production configuration. B's local checkpoints are
therefore produced by the research-only adapter in this file as valid
signed protocol objects stored beside the writer database. Production
code, protocol bytes, trust rules, and cryptography are unchanged.

Expectations come from the predeclared manifest
(benchmarks/h1-writer-rollback.v1.json). Observed outcomes are preserved
and classified; INCONCLUSIVE is recorded as an outcome mismatch, never
upgraded to a detection. Unexpected acceptance of the restored snapshot
in the primary C case is evidence against H1.
"""

import argparse
import contextlib
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from benchmarks import analyze, runner, workload
from casf import crypto
from casf.bundle import read_bundle
from casf.errors import CasfError
from casf.model.schema import validate_protocol_body
from casf.online import query_latest
from casf.verifier import Mode, Result, TrustPins, verify
from casf.witness import Witness
from casf.witness.http import WitnessService, make_server
from casf.writer import Writer

LOG_ID = workload.LOG_ID
TOKEN = "bench-h1-witness-token"
ZERO = "0" * 64
MAX_CHECKPOINT_EXTENSION = 128  # SPEC §12

EXPECTED = {
    "b_current_control": "PASS",
    "c_current_control": "PASS",
    "b_restored_old": "PASS",
    "c_restored_old_primary": "FAIL",
    "c_restored_old_retained_pin": "FAIL",
    "c_recovered_control": "PASS",
}
DETECTION_CASES = {"c_restored_old_primary", "c_restored_old_retained_pin"}


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


def _witness_pub() -> bytes:
    return crypto.public_key_raw(workload.seeded_key("witness"))


def make_local_checkpoint(manifest_hash: str, index: int, count: int,
                          head_hash: str, prev_checkpoint_hash: str) -> dict:
    """Research-only adapter: one valid signed local checkpoint object.

    The writer cannot retain more than one unwitnessed checkpoint, so
    arm B's checkpoints are produced here. The object follows the same
    schema, domains, and log key as a writer created checkpoint, with a
    fixed benchmark timestamp. It is stored beside the writer database,
    never inside it.
    """
    log_key = workload.seeded_key("log")
    body = {
        "version": 1, "type": "checkpoint", "log_id": LOG_ID,
        "manifest_hash": manifest_hash, "index": index, "count": count,
        "head_hash": head_hash,
        "previous_checkpoint_hash": prev_checkpoint_hash,
        "key_id": crypto.key_id(crypto.public_key_raw(log_key)),
        "issued_at": workload.TS, "final": False,
    }
    validate_protocol_body("checkpoint", body)
    return {"body": body,
            "checkpoint_hash": crypto.digest_checkpoint(body),
            "signature": crypto.sign_checkpoint(log_key, body)}


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


def _build_arm(root: Path, manifest: dict, events_old: list[dict],
               events_new: list[dict], batch: int, with_witness: bool,
               prefix: str) -> None:
    """Build one arm's history and save the old and current snapshots.

    Snapshots use the writer's SQLite backup, never a copy of a live
    database file. Arm B additionally snapshots its local checkpoint
    file, which lives beside the writer database and rolls back with it.
    """
    manifest_hash = str(manifest["manifest_hash"])
    checkpoints_path = root / f"{prefix}-local-checkpoints.json"
    writer = Writer(root / f"{prefix}.db", workload.seeded_key("log"))
    witness = None
    if with_witness:
        witness = Witness(root / "witness.db", workload.seeded_key("witness"),
                          authority_keys=_authority_keys())
    local_checkpoints: list[dict] = []
    try:
        writer.create_log(manifest)
        if witness is not None:
            witness.register_log(manifest)
        appended: list[dict] = []
        prev_cp = ZERO
        for i, event in enumerate(events_old, start=1):
            appended.append(writer.append(LOG_ID, **event))
            if i % batch == 0:
                if witness is not None:
                    _checkpoint_cycle(writer, witness, appended)
                else:
                    checkpoint = make_local_checkpoint(
                        manifest_hash, len(local_checkpoints), i,
                        str(appended[-1]["record_hash"]), prev_cp)
                    prev_cp = str(checkpoint["checkpoint_hash"])
                    local_checkpoints.append(checkpoint)
        writer.backup(root / f"{prefix}-old-snapshot.db")
        if not with_witness:
            (root / f"{prefix}-old-checkpoints.json").write_text(
                json.dumps(local_checkpoints))
        for event in events_new:
            appended.append(writer.append(LOG_ID, **event))
        if witness is not None:
            _checkpoint_cycle(writer, witness, appended)
        else:
            checkpoint = make_local_checkpoint(
                manifest_hash, len(local_checkpoints),
                len(appended), str(appended[-1]["record_hash"]), prev_cp)
            local_checkpoints.append(checkpoint)
        writer.backup(root / f"{prefix}-current-snapshot.db")
    finally:
        writer.close()
        if witness is not None:
            witness.close()
    if not with_witness:
        checkpoints_path.write_text(json.dumps(local_checkpoints))


def local_checkpoint_check(bundle_dir: Path, checkpoints_path: Path,
                           manifest_hash: str) -> dict:
    """Research-only local checkpoint consistency check for arm B.

    Scope: integrity verification of the record stream, then a check
    that every local checkpoint envelope is well formed, signed by the
    log key, consistently indexed and chained, and that its head matches
    the recomputed record digest at its count. No witness is contacted
    and no receipts are consulted. This check cannot establish
    currentness; a PASS says nothing about whether newer history exists.
    """
    bundle = read_bundle(bundle_dir)
    report = verify(
        bundle.manifest, bundle.records, _pins(manifest_hash),
        mode=Mode.INTEGRITY,
        status_envelopes=[workload.active_status(manifest_hash)])
    if report.result is not Result.PASS:
        return {"result": report.result.value, "stage": "integrity",
                "codes": list(report.diagnostic_codes)}
    digests = {}
    for seq, env in enumerate(bundle.records, start=1):
        digests[seq] = crypto.digest_record(env["body"])
    checkpoints = json.loads(Path(checkpoints_path).read_text())
    mbody = bundle.manifest["body"]
    log_raw = crypto.b64url_decode(mbody["log_public_key"])
    genesis = crypto.genesis_hash(manifest_hash)
    prev_cp, prev_count = ZERO, 0
    validated = 0
    for index, env in enumerate(checkpoints):
        try:
            if set(env) != {"body", "checkpoint_hash", "signature"}:
                raise CasfError("envelope shape")
            cbody = env["body"]
            validate_protocol_body("checkpoint", cbody)
            if cbody["log_id"] != LOG_ID \
                    or cbody["manifest_hash"] != manifest_hash \
                    or cbody["key_id"] != mbody["log_key_id"]:
                raise CasfError("binding")
            if cbody["index"] != index:
                raise CasfError("index gap")
            if cbody["previous_checkpoint_hash"] != prev_cp:
                raise CasfError("chain break")
            count = cbody["count"]
            if type(count) is not int or count < prev_count \
                    or count - prev_count > MAX_CHECKPOINT_EXTENSION:
                raise CasfError("count rule")
            if crypto.digest_checkpoint(cbody) != env["checkpoint_hash"]:
                raise CasfError("hash mismatch")
            crypto.verify_checkpoint(log_raw, cbody, env["signature"])
            expected_head = genesis if count == 0 else digests.get(count)
            if expected_head is None:
                raise CasfError("count beyond records")
            if cbody["head_hash"] != expected_head:
                raise CasfError("head mismatch")
        except (CasfError, KeyError, TypeError) as e:
            return {"result": "FAIL", "stage": f"checkpoint {index}",
                    "codes": [f"LOCAL_CHECKPOINT_{e}"]}
        prev_cp, prev_count = str(env["checkpoint_hash"]), count
        validated += 1
    return {"result": "PASS", "stage": "local", "codes": [],
            "checkpoints_validated": validated,
            "currentness": "not established: no newer independent "
                           "reference exists"}


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


def _export(db_path: Path, dest: Path) -> Path:
    writer = Writer(db_path, workload.seeded_key("log"))
    try:
        return writer.export_bundle(LOG_ID, dest)
    finally:
        writer.close()


def _record_count(db_path: Path) -> int:
    writer = Writer(db_path, workload.seeded_key("log"))
    try:
        return sum(1 for _ in writer.records(LOG_ID))
    finally:
        writer.close()


def _verify_online(bundle_dir: Path, manifest_hash: str, url: str,
                   retained: tuple[int, str] | None,
                   captured: dict) -> tuple[object, float]:
    """One online verification; returns (report, elapsed milliseconds).

    The measurement boundary is the verify call, including the witness
    round trip. The captured view records that the witness was reachable
    and which authenticated state it reported during the query.
    """
    def query():
        view = query_latest(url, LOG_ID, TOKEN, _witness_pub(), timeout=5.0)
        captured["view"] = {
            "checkpoint_index": view.body["checkpoint_index"],
            "checkpoint_hash": view.body["checkpoint_hash"],
            "count": view.body["count"],
            "head_hash": view.body["head_hash"],
        }
        return view

    bundle = read_bundle(bundle_dir)
    start = time.perf_counter()
    report = verify(
        bundle.manifest, bundle.records, _pins(manifest_hash),
        mode=Mode.ONLINE,
        status_envelopes=[workload.active_status(manifest_hash)],
        checkpoint_envelopes=bundle.checkpoints,
        receipt_envelopes=bundle.receipts,
        allow_unwitnessed=False,
        online_query=query, retained_checkpoint=retained)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return report, elapsed_ms


def _classify(case: str, observed: str | None, error: str | None) -> str:
    if error is not None:
        return "invalid_trial"
    expected = EXPECTED[case]
    if observed == expected:
        if case in DETECTION_CASES and expected == "FAIL":
            return "detection"
        return "as_expected"
    if observed == "PASS" and expected != "PASS":
        return "evidence_against"
    return "outcome_mismatch"


def _case_row(case: str, observed: str | None, codes: list[str],
              error: str | None, elapsed_ms: float | None) -> dict:
    row = {"expected": EXPECTED[case], "observed": observed,
           "codes": codes,
           "classification": _classify(case, observed, error)}
    if elapsed_ms is not None:
        row["verification_ms"] = round(elapsed_ms, 3)
    if error is not None:
        row["error"] = error
    return row


def run_one(seed: int, run_index: int, work: Path, old_count: int,
            new_count: int, batch: int, target: int,
            seed_offset: int) -> dict:
    """One independent run: build, snapshot, roll back the writer only,
    and evaluate both arms against their predeclared expectations."""
    work.mkdir(parents=True, exist_ok=True)
    events_old = workload.generate(seed, old_count, target)
    events_new = workload.generate(seed + seed_offset, new_count - old_count,
                                   target)
    manifest = runner._manifest()
    manifest_hash = str(manifest["manifest_hash"])

    _build_arm(work, manifest, events_old, events_new, batch,
               with_witness=False, prefix="b")
    _build_arm(work, manifest, events_old, events_new, batch,
               with_witness=True, prefix="c")

    cases: dict[str, dict] = {}
    captured: dict = {}

    def guard(case, fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 -- the harness must record
            # any infrastructure failure as an invalid trial, never hide it
            cases[case] = _case_row(case, None, [], f"{type(e).__name__}: {e}",
                                    None)
            return None

    # D. healthy controls
    def b_current():
        bundle = _export(work / "b.db", work / "bundle-b-current")
        out = local_checkpoint_check(
            bundle, work / "b-local-checkpoints.json", manifest_hash)
        cases["b_current_control"] = _case_row(
            "b_current_control", out["result"], out["codes"], None, None)
    guard("b_current_control", b_current)

    retained_pin: tuple[int, str] | None = None

    def c_current():
        nonlocal retained_pin
        bundle_dir = _export(work / "c.db", work / "bundle-c-current")
        anchor = read_bundle(bundle_dir).checkpoints[-1]
        retained_pin = (int(anchor["body"]["index"]),
                        str(anchor["checkpoint_hash"]))
        with _serve(work / "witness.db") as url:
            report, ms = _verify_online(bundle_dir, manifest_hash, url,
                                        None, captured)
        cases["c_current_control"] = _case_row(
            "c_current_control", report.result.value,
            list(report.diagnostic_codes), None, ms)
    guard("c_current_control", c_current)

    # E. restore only the writer snapshots; the witness is untouched
    shutil.copyfile(work / "b-old-snapshot.db", work / "b.db")
    shutil.copyfile(work / "c-old-snapshot.db", work / "c.db")
    shutil.copyfile(work / "b-old-checkpoints.json",
                    work / "b-local-checkpoints.json")
    restored_b = _record_count(work / "b.db")
    restored_c = _record_count(work / "c.db")

    # F. primary comparison on the restored old snapshots
    def b_old():
        bundle = _export(work / "b.db", work / "bundle-b-old")
        out = local_checkpoint_check(
            bundle, work / "b-local-checkpoints.json", manifest_hash)
        row = _case_row("b_restored_old", out["result"], out["codes"],
                        None, None)
        row["checkpoints_validated"] = out.get("checkpoints_validated")
        row["currentness"] = out.get("currentness")
        cases["b_restored_old"] = row
    guard("b_restored_old", b_old)

    bundle_c_old = _export(work / "c.db", work / "bundle-c-old")
    with _serve(work / "witness.db") as url:
        # primary: no retained newer client checkpoint
        captured.clear()

        def c_primary():
            report, ms = _verify_online(bundle_c_old, manifest_hash, url,
                                        None, captured)
            row = _case_row("c_restored_old_primary", report.result.value,
                            list(report.diagnostic_codes), None, ms)
            row["witness_view"] = captured.get("view")
            row["freshness"] = report.freshness_status.value
            cases["c_restored_old_primary"] = row
        guard("c_restored_old_primary", c_primary)

        # G. supplementary: client retained the checkpoint at 32
        captured.clear()

        def c_retained():
            report, ms = _verify_online(bundle_c_old, manifest_hash, url,
                                        retained_pin, captured)
            row = _case_row("c_restored_old_retained_pin",
                            report.result.value,
                            list(report.diagnostic_codes), None, ms)
            row["witness_view"] = captured.get("view")
            row["freshness"] = report.freshness_status.value
            cases["c_restored_old_retained_pin"] = row
        guard("c_restored_old_retained_pin", c_retained)

    # H. restore the current writer snapshot; verification recovers
    def c_recovered():
        shutil.copyfile(work / "c-current-snapshot.db", work / "c.db")
        bundle_dir = _export(work / "c.db", work / "bundle-c-recovered")
        with _serve(work / "witness.db") as url:
            report, ms = _verify_online(bundle_dir, manifest_hash, url,
                                        None, captured)
        cases["c_recovered_control"] = _case_row(
            "c_recovered_control", report.result.value,
            list(report.diagnostic_codes), None, ms)
    guard("c_recovered_control", c_recovered)

    return {
        "run_id": f"run-{run_index:02d}", "seed": seed,
        "counts": {"old": old_count, "new": new_count,
                   "restored_b": restored_b, "restored_c": restored_c},
        "retained_pin_checkpoint_index": (retained_pin[0]
                                          if retained_pin else None),
        "cases": cases,
    }


def _environment() -> dict:
    env = runner._environment()
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True,
            check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        status = "unknown"
    env["working_tree_status"] = status if status else "clean"
    env["machine"] = platform.machine()
    env["cpu_count"] = os.cpu_count()
    try:
        env["ram_bytes"] = int(subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True,
            check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError):
        env["ram_bytes"] = None
    lock = Path("uv.lock")
    env["dependency_lock_sha256"] = (
        hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists()
        else None)
    harness = Path(__file__)
    env["harness_sha256"] = hashlib.sha256(harness.read_bytes()).hexdigest()
    import casf
    casf_path = Path(casf.__file__).resolve()
    env["casf_module_path"] = str(casf_path)
    tree = hashlib.sha256()
    for f in sorted(casf_path.parent.rglob("*.py")):
        tree.update(f.relative_to(casf_path.parent).as_posix().encode())
        tree.update(hashlib.sha256(f.read_bytes()).digest())
    env["casf_source_tree_sha256"] = tree.hexdigest()
    return env


def run_experiment(manifest_path: Path, out_dir: Path) -> dict:
    """Execute the predeclared manifest and write the raw artifact."""
    out = Path(out_dir)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing directory: {out}")
    cfg = json.loads(Path(manifest_path).read_text())
    c = cfg["configuration"]
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, seed in enumerate(c["seeds"]):
            rows.append(run_one(seed, i, Path(tmp) / f"run-{i:02d}",
                                c["old_count"], c["new_count"],
                                c["checkpoint_batch"], c["target_bytes"],
                                c["extension_seed_offset"]))
    artifact = {
        "experiment": cfg["experiment"],
        "hypothesis": cfg["hypothesis_text"],
        "hypothesis_source": cfg["hypothesis_source"],
        "manifest_sha256": hashlib.sha256(
            Path(manifest_path).read_bytes()).hexdigest(),
        "configuration": c,
        "expected": EXPECTED,
        "classification_rules": cfg["classification_rules"],
        "environment": _environment(),
        "runs": rows,
    }
    out.mkdir(parents=True)
    (out / "runs.v1.json").write_text(json.dumps(artifact, indent=2))
    (out / "report.md").write_text(_render_report(artifact))
    return artifact


def _render_report(artifact: dict) -> str:
    runs = artifact["runs"]
    lines = [
        "# H1 writer rollback experiment (SPEC Section 22)", "",
        f"hypothesis source: {artifact['hypothesis_source']}",
        f"manifest sha256: {artifact['manifest_sha256']}", "",
        ("configuration: old snapshot {old_count} records, current "
         "{new_count} records, checkpoint batch {checkpoint_batch}, "
         "{runs} runs, fixed seeds").format(**artifact["configuration"]),
        "",
        ("| case | expected | observed values | as declared | mismatch | "
         "against | invalid |"),
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for case, expected in EXPECTED.items():
        observed = [r["cases"][case]["observed"] for r in runs]
        classes = [r["cases"][case]["classification"] for r in runs]
        values = sorted({str(o) for o in observed})
        lines.append(
            f"| {case} | {expected} | {', '.join(values)} | "
            f"{classes.count('as_expected') + classes.count('detection')} | "
            f"{classes.count('outcome_mismatch')} | "
            f"{classes.count('evidence_against')} | "
            f"{classes.count('invalid_trial')} |")
    # run level timing summary with the SPEC across run interval method
    per_case_timings: dict[str, list[float]] = {}
    for r in runs:
        for case, payload in r["cases"].items():
            if "verification_ms" in payload:
                per_case_timings.setdefault(case, []).append(
                    payload["verification_ms"])
    if per_case_timings:
        lines += ["", "## Verification timing (decisive call, milliseconds)",
                  ""]
        for case, timings in per_case_timings.items():
            summary = analyze.summarize([{case: v} for v in timings],
                                        seed=41)
            s = summary[case]
            lines.append(
                f"- {case}: mean {s['mean']:.2f} ms, 95 percent interval "
                f"[{s['ci_low']:.2f}, {s['ci_high']:.2f}] over "
                f"{s['n_runs']} runs")
    lines += ["", "## Diagnostic codes observed", ""]
    codes_seen: dict[str, set[str]] = {}
    for r in runs:
        for case, payload in r["cases"].items():
            codes_seen.setdefault(case, set()).update(payload["codes"])
    for case, codes in codes_seen.items():
        lines.append(f"- {case}: {sorted(codes) if codes else 'none'}")
    env = artifact["environment"]
    lines += ["", "## Environment", ""]
    for key in sorted(env):
        lines.append(f"- {key}: {env[key]}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv)
    artifact = run_experiment(args.manifest, args.out_dir)
    runs = artifact["runs"]
    tally: dict[str, int] = {}
    for r in runs:
        for payload in r["cases"].values():
            tally[payload["classification"]] = \
                tally.get(payload["classification"], 0) + 1
    print(f"runs: {len(runs)}  classifications: {tally}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
