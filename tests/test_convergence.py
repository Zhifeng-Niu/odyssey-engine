"""Black-box tests for odyssey_helper.py convergence semantics.

Each test drives the real CLI in a throwaway directory — the same way the
stop hook invokes it. Fixtures build JSONL logs; assertions check verdicts.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HELPER = REPO / "scripts" / "odyssey_helper.py"


def run_cli(*args, cwd=None):
    proc = subprocess.run(
        [sys_executable(), str(HELPER), *args],
        capture_output=True, text=True, cwd=cwd,
    )
    return proc


def sys_executable():
    import sys
    return sys.executable or "python3"


class ConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.jsonl = str(Path(self.tmp.name) / "log.jsonl")
        run_cli("init", "--jsonl", self.jsonl, "--name", "t", "--direction", "lower")

    def log_keeps(self, metrics, start=1):
        for i, m in enumerate(metrics, start=start):
            run_cli("log", "--jsonl", self.jsonl, "--run", str(i),
                    "--metric", str(m), "--status", "keep")

    def check(self, tier="standard"):
        proc = run_cli("convergence-check", "--jsonl", self.jsonl, "--tier", tier)
        return json.loads(proc.stdout)

    def test_diminishing_returns_converges(self):
        self.log_keeps([100.0, 99.9, 99.85, 99.82, 99.80, 99.79])
        self.assertTrue(self.check()["converged"])

    def test_insufficient_data_does_not_converge(self):
        self.log_keeps([100.0, 90.0, 80.0])
        result = self.check()
        self.assertFalse(result["converged"])
        self.assertIn("insufficient data", result["reason"])

    def test_pivot_partitions_evidence(self):
        self.log_keeps([100.0, 99.9, 99.85, 99.82, 99.80, 99.79])
        self.assertTrue(self.check()["converged"])
        run_cli("log", "--jsonl", self.jsonl, "--run", "7", "--pivot",
                "--description", "new goal")
        self.log_keeps([900.0, 880.0, 860.0], start=8)
        result = self.check()
        self.assertFalse(result["converged"])
        self.assertEqual(result["pivots"], 1)
        self.assertIn("pivot", result["reason"])

    def test_stale_on_drift(self):
        self.log_keeps([100.0, 99.9, 99.85, 99.82, 99.80, 99.79])
        run_cli("log", "--jsonl", self.jsonl, "--run", "7",
                "--remeasure", "--metric", "105.0", "--was", "99.79")
        result = self.check()
        self.assertFalse(result["converged"])
        self.assertTrue(result["stale"])
        self.assertIn("environment drift", result["reason"])

    def test_stable_probe_restores_convergence(self):
        self.log_keeps([100.0, 99.9, 99.85, 99.82, 99.80, 99.79])
        run_cli("log", "--jsonl", self.jsonl, "--run", "7",
                "--remeasure", "--metric", "99.85", "--was", "99.79")
        result = self.check()
        self.assertTrue(result["converged"])
        self.assertFalse(result["stale"])

    def test_remeasures_do_not_consume_patience(self):
        self.log_keeps([100.0, 99.9, 99.85, 99.83, 99.82])
        run_cli("log", "--jsonl", self.jsonl, "--run", "9",
                "--remeasure", "--metric", "99.9", "--was", "99.82")
        result = self.check()
        patience = next(e for e in result["evidence"] if e["check"] == "patience_budget")
        self.assertEqual(patience["used"], 5)

    def test_stuck_is_not_convergence(self):
        self.log_keeps([100.0, 99.0, 98.0, 97.0, 96.0])
        for run in range(6, 9):
            run_cli("log", "--jsonl", self.jsonl, "--run", str(run), "--status", "discard")
        result = self.check()
        self.assertFalse(result["converged"])
        self.assertFalse(result["stale"])


class ArgValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.jsonl = str(Path(self.tmp.name) / "log.jsonl")
        run_cli("init", "--jsonl", self.jsonl, "--name", "t", "--direction", "lower")

    def test_pivot_rejects_status(self):
        proc = run_cli("log", "--jsonl", self.jsonl, "--run", "1",
                       "--pivot", "--status", "keep")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("cannot be combined", proc.stderr)

    def test_remeasure_requires_was(self):
        proc = run_cli("log", "--jsonl", self.jsonl, "--run", "1",
                       "--remeasure", "--metric", "5.0")
        self.assertNotEqual(proc.returncode, 0)

    def test_status_required(self):
        proc = run_cli("log", "--jsonl", self.jsonl, "--run", "1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--status is required", proc.stderr)


if __name__ == "__main__":
    unittest.main()
