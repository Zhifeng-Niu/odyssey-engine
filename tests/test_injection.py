"""Stop-hook output contract tests.

Runs the real stop hook against a fixture mission and asserts the strict
JSON contract Claude Code expects: valid parseable output, correct
decision, mission content delivered. Guards against regression of the
heredoc-JSON bug that made the loop run blind (fixed in v1.1.0).
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "hooks" / "stop-hook.sh"
HELPER = REPO / "scripts" / "odyssey_helper.py"

STATE = """---
active: true
iteration: {iteration}
session_id: test
completion_promise: ""
orientation: engineer
started_at: 2026-10-20T10:00:00Z
time_budget_seconds: 0
consecutive_discards: {discards}
delivery_tier: standard
patience_budget: 30
discard_threshold: 10
min_metric_delta_pct: 0.5
convergence_window: 5
auto_orient_switch: true
mission_file: MISSION.md
---
"""


class StopHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / ".claude").mkdir()
        self.write_state(iteration=3, discards=0)
        self.write_mission()
        subprocess.run(
            ["python3", str(HELPER), "init", "--jsonl", "odyssey.jsonl",
             "--name", "m", "--direction", "lower"],
            cwd=self.dir, capture_output=True,
        )

    def write_state(self, iteration, discards):
        (self.dir / ".claude" / "odyssey.local.md").write_text(
            STATE.format(iteration=iteration, discards=discards)
        )

    def write_mission(self):
        mission = (
            '# Mission: Optimize API Latency\n\n'
            '## Goal\nReduce p99 below 200ms. Target: "aggressive" per CEO.\n'
            'Unicode 中文 and emoji 🚀 must survive.\n\n'
            '## Metrics\n| p99_ms | lower |\n'
        )
        (self.dir / "MISSION.md").write_text(mission)

    def run_hook(self):
        return subprocess.run(
            ["bash", str(HOOK)], cwd=self.dir, capture_output=True,
            text=True, stdin=subprocess.DEVNULL, timeout=30,
        )

    def parse(self, proc):
        return json.loads(proc.stdout)

    def hook_log(self, entries):
        for run, metric in entries:
            subprocess.run(
                ["python3", str(HELPER), "log", "--jsonl", "odyssey.jsonl",
                 "--run", str(run), "--metric", str(metric), "--status", "keep"],
                cwd=self.dir, capture_output=True,
            )

    def test_waypoint_block_valid_json_with_content(self):
        self.hook_log([(1, 100.0), (2, 90.0)])  # not converged
        proc = self.run_hook()
        self.assertEqual(proc.returncode, 2)
        data = self.parse(proc)
        self.assertEqual(data["decision"], "block")
        self.assertIn("aggressive", data["systemMessage"])
        self.assertIn("🚀", data["systemMessage"])

    def test_convergence_allows_exit(self):
        self.hook_log([(1, 100.0), (2, 99.9), (3, 99.85), (4, 99.82), (5, 99.80), (6, 99.79)])
        proc = self.run_hook()
        self.assertEqual(proc.returncode, 0)
        data = self.parse(proc)
        self.assertEqual(data["decision"], "allow")
        state = (self.dir / ".claude" / "odyssey.local.md").read_text()
        self.assertIn("active: false", state)

    def test_stuck_auto_switches_orientation(self):
        self.write_state(iteration=20, discards=12)
        self.hook_log([(1, 100.0)])
        proc = self.run_hook()
        self.assertEqual(proc.returncode, 2)
        data = self.parse(proc)
        self.assertEqual(data["decision"], "block")
        state = (self.dir / ".claude" / "odyssey.local.md").read_text()
        self.assertIn("orientation: creative", state)


if __name__ == "__main__":
    unittest.main()
