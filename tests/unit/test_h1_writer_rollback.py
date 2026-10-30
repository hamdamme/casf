"""Focused tests for the H1 writer rollback harness.

These tests establish the harness properties the experiment brief
requires; they do not assert the H1 outcome itself. The hypothesis
verdict belongs to the experiment report, computed from observed runs.
"""

import json
import tempfile
import unittest
from pathlib import Path

from benchmarks import h1_writer_rollback as h1
from benchmarks import runner, workload

OLD, NEW, BATCH, TARGET = 24, 32, 8, 512
SEED, OFFSET = 7301, 50000


def _built_run(tmp: Path) -> dict:
    """Build one run's arm state and return paths and the manifest hash."""
    manifest = runner._manifest()
    manifest_hash = str(manifest["manifest_hash"])
    events_old = workload.generate(SEED, OLD, TARGET)
    events_new = workload.generate(SEED + OFFSET, NEW - OLD, TARGET)
    h1._build_arm(tmp, manifest, events_old, events_new, BATCH,
                  with_witness=False, prefix="b")
    h1._build_arm(tmp, manifest, events_old, events_new, BATCH,
                  with_witness=True, prefix="c")
    return {"manifest_hash": manifest_hash}


class HarnessTest(unittest.TestCase):
    def test_healthy_controls_succeed(self):
        with tempfile.TemporaryDirectory() as d:
            row = h1.run_one(SEED, 0, Path(d) / "run", OLD, NEW, BATCH,
                             TARGET, OFFSET)
        cases = row["cases"]
        self.assertEqual(cases["b_current_control"]["observed"], "PASS")
        self.assertEqual(cases["c_current_control"]["observed"], "PASS")
        self.assertEqual(cases["c_recovered_control"]["observed"], "PASS")

    def test_rollback_restores_old_writer_state_only(self):
        with tempfile.TemporaryDirectory() as d:
            row = h1.run_one(SEED, 0, Path(d) / "run", OLD, NEW, BATCH,
                             TARGET, OFFSET)
        counts = row["counts"]
        self.assertEqual(counts["restored_b"], OLD)
        self.assertEqual(counts["restored_c"], OLD)
        # the witness was not rolled back: during the primary query it
        # reported the newer state through an authenticated fresh view
        view = row["cases"]["c_restored_old_primary"]["witness_view"]
        self.assertIsNotNone(view)
        self.assertEqual(view["count"], NEW)

    def test_primary_case_uses_no_retained_newer_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            row = h1.run_one(SEED, 0, Path(d) / "run", OLD, NEW, BATCH,
                             TARGET, OFFSET)
        # the pin captured in the healthy phase is used only by the
        # supplementary case; the primary case passes no retained state
        self.assertEqual(row["retained_pin_checkpoint_index"], 3)
        primary = row["cases"]["c_restored_old_primary"]
        self.assertIn("witness_view", primary)

    def test_b_validates_restored_local_history(self):
        with tempfile.TemporaryDirectory() as d:
            row = h1.run_one(SEED, 0, Path(d) / "run", OLD, NEW, BATCH,
                             TARGET, OFFSET)
        case = row["cases"]["b_restored_old"]
        self.assertEqual(case["observed"], "PASS")
        self.assertEqual(case["checkpoints_validated"], OLD // BATCH)
        self.assertIn("not established", case["currentness"])

    def test_restored_old_snapshot_is_not_accepted_as_current(self):
        # The H1 relevant invariant for arm C: verification of the
        # restored snapshot must not PASS while the honest witness
        # retains newer state. The exact non PASS result and its
        # diagnostic codes are recorded for the report.
        with tempfile.TemporaryDirectory() as d:
            row = h1.run_one(SEED, 0, Path(d) / "run", OLD, NEW, BATCH,
                             TARGET, OFFSET)
        primary = row["cases"]["c_restored_old_primary"]
        self.assertNotEqual(primary["observed"], "PASS")
        self.assertTrue(primary["codes"])

    def test_retained_pin_yields_conflict_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            row = h1.run_one(SEED, 0, Path(d) / "run", OLD, NEW, BATCH,
                             TARGET, OFFSET)
        case = row["cases"]["c_restored_old_retained_pin"]
        self.assertEqual(case["observed"], "FAIL")
        self.assertIn("WITNESS_STATE_CONFLICT", case["codes"])

    def test_local_checkpoint_check_detects_tampered_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            info = _built_run(tmp)
            bundle = h1._export(tmp / "b.db", tmp / "bundle")
            path = tmp / "b-local-checkpoints.json"
            data = json.loads(path.read_text())
            data[0]["body"]["count"] += 1  # now inconsistent
            path.write_text(json.dumps(data))
            out = h1.local_checkpoint_check(bundle, path,
                                            info["manifest_hash"])
            self.assertEqual(out["result"], "FAIL")

    def test_classification_is_honest(self):
        # A witness outage or any non PASS that is not the predeclared
        # FAIL must be recorded as a mismatch or invalid trial, never
        # upgraded to a detection; acceptance of the old snapshot is
        # evidence against H1.
        self.assertEqual(
            h1._classify("c_restored_old_primary", "INCONCLUSIVE", None),
            "outcome_mismatch")
        self.assertEqual(
            h1._classify("c_restored_old_primary", "PASS", None),
            "evidence_against")
        self.assertEqual(
            h1._classify("c_restored_old_primary", None, "TimeoutError"),
            "invalid_trial")
        self.assertEqual(
            h1._classify("c_restored_old_primary", "FAIL", None),
            "detection")
        self.assertEqual(h1._classify("b_current_control", "PASS", None),
                         "as_expected")

    def test_refuses_to_overwrite_results(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "results"
            out.mkdir()
            with self.assertRaises(SystemExit):
                h1.run_experiment(
                    Path("benchmarks/h1-writer-rollback.v1.json"), out)


if __name__ == "__main__":
    unittest.main()
