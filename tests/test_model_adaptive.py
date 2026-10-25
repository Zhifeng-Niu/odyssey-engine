"""Model-adaptive harness tests: prompt density scales with model class."""

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
iteration: 3
session_id: x
completion_promise: ""
orientation: engineer
started_at: 2026-10-20T10:00:00Z
time_budget_seconds: 0
consecutive_discards: 0
delivery_tier: standard
patience_budget: 30
discard_threshold: 10
min_metric_delta_pct: 0.5
convergence_window: 5
auto_orient_switch: true
mission_file: MISSION.md
model_class: {mc}
---
"""


class ModelAdaptiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / ".claude").mkdir()
        (self.dir / "MISSION.md").write_text('# Mission: T\n\n## Goal\nCut p99 "strict"\n')
        subprocess.run(
            ["python3", str(HELPER), "init", "--jsonl", "odyssey.jsonl",
             "--name", "t", "--direction", "lower"],
            cwd=self.dir, capture_output=True,
        )

    def run_hook(self, model_class):
        (self.dir / ".claude" / "odyssey.local.md").write_text(
            STATE.format(mc=model_class))
        proc = subprocess.run(
            ["bash", str(HOOK)], cwd=self.dir, capture_output=True,
            text=True, stdin=subprocess.DEVNULL, timeout=30,
        )
        self.assertEqual(proc.returncode, 2)
        return json.loads(proc.stdout)["systemMessage"]

    def test_flagship_gets_terse_brief(self):
        msg = self.run_hook("flagship")
        self.assertLess(len(msg), 600)
        self.assertIn("Next hypothesis from MISSION.md backlog", msg)
        self.assertNotIn("Follow these steps in order", msg)

    def test_standard_gets_full_procedure(self):
        msg = self.run_hook("standard")
        self.assertIn("Follow these steps in order", msg)
        self.assertIn("GOODHART GUARD", msg)

    def test_compact_gets_micro_discipline(self):
        msg = self.run_hook("compact")
        self.assertIn("SMALLEST possible step", msg)
        self.assertIn("fails twice", msg)
        self.assertIn("MISSION CONTEXT", msg)

    def test_missing_class_defaults_to_standard(self):
        state = STATE.format(mc="standard").replace("model_class: standard\n", "")
        (self.dir / ".claude" / "odyssey.local.md").write_text(state)
        proc = subprocess.run(
            ["bash", str(HOOK)], cwd=self.dir, capture_output=True,
            text=True, stdin=subprocess.DEVNULL, timeout=30,
        )
        msg = json.loads(proc.stdout)["systemMessage"]
        self.assertIn("Follow these steps in order", msg)


if __name__ == "__main__":
    unittest.main()
