"""Composite quality-gate scoring tests (the autodev-dominance layer)."""

import json
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HELPER = REPO / "scripts" / "odyssey_helper.py"


def score(*args):
    proc = subprocess.run(
        ["python3", str(HELPER), "score", *args],
        capture_output=True, text=True,
    )
    return proc


class ScoreTests(unittest.TestCase):
    def test_improvement_keeps(self):
        proc = score("--l1", "9", "--l2", "8", "--l3", "8", "--l4", "9",
                     "--lines", "23", "--baseline", "7.5")
        data = json.loads(proc.stdout)
        expected = round(9 * .3 + 8 * .25 + 8 * .25 + 9 * .2, 2)
        self.assertEqual(data["composite"], expected)
        self.assertEqual(data["verdict"], "keep")

    def test_regression_discards(self):
        proc = score("--l1", "5", "--l2", "5", "--l3", "5", "--l4", "5",
                     "--lines", "-2", "--baseline", "7.5")
        self.assertEqual(json.loads(proc.stdout)["verdict"], "discard")

    def test_equal_score_fewer_lines_is_simplification_win(self):
        proc = score("--l1", "7.5", "--l2", "7.5", "--l3", "7.5", "--l4", "7.5",
                     "--lines", "-14", "--baseline", "7.5")
        data = json.loads(proc.stdout)
        self.assertEqual(data["composite"], 7.5)
        self.assertEqual(data["verdict"], "keep")
        self.assertIn("simplification", data["reason"])

    def test_equal_score_more_lines_discards(self):
        proc = score("--l1", "7.5", "--l2", "7.5", "--l3", "7.5", "--l4", "7.5",
                     "--lines", "45", "--baseline", "7.5")
        self.assertEqual(json.loads(proc.stdout)["verdict"], "discard")

    def test_hard_fail_overrides(self):
        proc = score("--l1", "10", "--l2", "10", "--l3", "10", "--l4", "10",
                     "--lines", "0", "--baseline", "0", "--hard-fail")
        data = json.loads(proc.stdout)
        self.assertEqual(data["verdict"], "hard-fail")
        self.assertEqual(data["composite"], 0.0)

    def test_custom_weights(self):
        proc = score("--l1", "10", "--l2", "0", "--l3", "0", "--l4", "0",
                     "--lines", "1", "--baseline", "0", "--weights", "1.0,0,0,0")
        self.assertEqual(json.loads(proc.stdout)["composite"], 10.0)

    def test_weights_must_sum_to_one(self):
        proc = score("--l1", "5", "--l2", "5", "--l3", "5", "--l4", "5",
                     "--lines", "0", "--baseline", "0", "--weights", "0.5,0.5,0.5,0.5")
        self.assertNotEqual(proc.returncode, 0)

    def test_layers_bounded(self):
        proc = score("--l1", "11", "--l2", "5", "--l3", "5", "--l4", "5",
                     "--lines", "0", "--baseline", "0")
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
