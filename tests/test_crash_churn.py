"""Crash/churn protocol and test-incentive tests (autodev parity)."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HELPER = REPO / "scripts" / "odyssey_helper.py"


def run_cli(*args):
    return subprocess.run(
        ["python3", str(HELPER), *args], capture_output=True, text=True
    )


class ChurnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.jsonl = str(Path(self.tmp.name) / "log.jsonl")
        run_cli("init", "--jsonl", self.jsonl, "--name", "t", "--direction", "lower")

    def test_five_consecutive_crashes_stop_the_loop(self):
        run_cli("log", "--jsonl", self.jsonl, "--run", "1",
                "--metric", "100", "--status", "keep")
        for run in range(2, 7):
            run_cli("log", "--jsonl", self.jsonl, "--run", str(run), "--status", "crash")
        result = json.loads(run_cli(
            "convergence-check", "--jsonl", self.jsonl, "--tier", "standard").stdout)
        self.assertTrue(result["converged"])
        self.assertIn("churn", result["reason"])

    def test_fewer_crashes_do_not_stop(self):
        run_cli("log", "--jsonl", self.jsonl, "--run", "1",
                "--metric", "100", "--status", "keep")
        for run in range(2, 6):
            run_cli("log", "--jsonl", self.jsonl, "--run", str(run), "--status", "crash")
        result = json.loads(run_cli(
            "convergence-check", "--jsonl", self.jsonl, "--tier", "standard").stdout)
        self.assertFalse(result["converged"])

    def test_crash_streak_broken_by_keep(self):
        for run in range(1, 6):
            run_cli("log", "--jsonl", self.jsonl, "--run", str(run), "--status", "crash")
        run_cli("log", "--jsonl", self.jsonl, "--run", "6",
                "--metric", "100", "--status", "keep")
        result = json.loads(run_cli(
            "convergence-check", "--jsonl", self.jsonl, "--tier", "standard").stdout)
        self.assertFalse(result["converged"])


class TestIncentiveTests(unittest.TestCase):
    def score(self, *extra):
        return json.loads(run_cli(
            "score", "--l1", "8", "--l2", "7.5", "--l3", "7.5", "--l4", "8",
            "--lines", "10", "--baseline", "7.0", *extra
        ).stdout)

    def test_added_tests_bonus_breaks_cap(self):
        plain = self.score()
        rewarded = self.score("--tests-added", "1")
        # l1 8->9, l4 8->9 lifts composite by 0.3+0.2
        self.assertEqual(rewarded["composite"], round(plain["composite"] + 0.5, 2))

    def test_removed_tests_penalize_l1(self):
        penalized = self.score("--tests-removed", "1")
        self.assertEqual(penalized["layers"]["l1"], 7.0)


if __name__ == "__main__":
    unittest.main()
