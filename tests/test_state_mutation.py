"""State-mutation regression: multibyte state file under C locale.

Real-world failure (v1.5.1): the state file embeds the mission prompt
(multibyte by design), and the hook's `sed -i` mutations died with
"RE error: illegal byte sequence" — reported as a non-blocking stop-hook
error in the user's session. All state mutations now run through python.
This test pins that contract: hook paths must work with Chinese content
in the state file even when the parent environment forces a C locale.
"""

import json
import os
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
session_id: x
completion_promise: ""
orientation: {orientation}
started_at: 2026-10-26T10:00:00Z
time_budget_seconds: 0
consecutive_discards: {discards}
delivery_tier: standard
patience_budget: 30
discard_threshold: 10
min_metric_delta_pct: 0.5
convergence_window: 5
auto_orient_switch: true
mission_file: MISSION.md
model_class: standard
---

# Odyssey Mission Active

## Mission Prompt

优化 DMD Stage Two 工厂布局方案：厂型组合、竞标价阶梯 🚀 "引号" 与 | 竖线
"""


class StateMutationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / ".claude").mkdir()
        (self.dir / "MISSION.md").write_text(
            '# Mission: 工厂布局 🚀\n\n## Goal\n| 竞标 |\n', encoding="utf-8")
        subprocess.run(
            ["python3", str(HELPER), "init", "--jsonl", "odyssey.jsonl",
             "--name", "t", "--direction", "lower"],
            cwd=self.dir, capture_output=True,
        )

    def write_state(self, iteration=3, discards=0, orientation="engineer"):
        (self.dir / ".claude" / "odyssey.local.md").write_text(
            STATE.format(iteration=iteration, discards=discards,
                         orientation=orientation), encoding="utf-8")

    def run_hook_c_locale(self):
        env = os.environ.copy()
        env["LC_ALL"] = "C"   # hostile parent locale, like the reported session
        env["LANG"] = "C"
        return subprocess.run(
            ["bash", str(HOOK)], cwd=self.dir, capture_output=True,
            text=True, stdin=subprocess.DEVNULL, timeout=30, env=env,
        )

    def hook_log(self, entries):
        for run, metric in entries:
            subprocess.run(
                ["python3", str(HELPER), "log", "--jsonl", "odyssey.jsonl",
                 "--run", str(run), "--metric", str(metric), "--status", "keep"],
                cwd=self.dir, capture_output=True,
            )

    def test_increment_path_no_sed_error(self):
        self.write_state(iteration=3, discards=0)
        self.hook_log([(1, 100.0), (2, 90.0)])
        proc = self.run_hook_c_locale()
        self.assertNotIn("illegal byte sequence", proc.stderr)
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertEqual(data["decision"], "block")
        state = (self.dir / ".claude" / "odyssey.local.md").read_text(encoding="utf-8")
        self.assertIn("iteration: 4", state)
        self.assertIn("工厂布局", state)  # embedded mission survived the rewrite

    def test_deactivate_path_no_sed_error(self):
        self.write_state(iteration=3, discards=0)
        self.hook_log([(1, 100.0), (2, 99.9), (3, 99.85), (4, 99.82), (5, 99.80), (6, 99.79)])
        proc = self.run_hook_c_locale()
        self.assertNotIn("illegal byte sequence", proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["decision"], "allow")
        state = (self.dir / ".claude" / "odyssey.local.md").read_text(encoding="utf-8")
        self.assertIn("active: false", state)
        self.assertIn("completed_at:", state)

    def test_auto_switch_path_no_sed_error(self):
        self.write_state(iteration=20, discards=12)
        self.hook_log([(1, 100.0)])
        proc = self.run_hook_c_locale()
        self.assertNotIn("illegal byte sequence", proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["decision"], "block")
        state = (self.dir / ".claude" / "odyssey.local.md").read_text(encoding="utf-8")
        self.assertIn("orientation: creative", state)
        self.assertIn("consecutive_discards: 0", state)


    def test_gbk_state_file_survives(self):
        """Real-world v1.5.4 case: state file containing GBK-encoded bytes
        (from a broken-locale session or GBK editor) crashed set_state with
        UnicodeDecodeError. Decode chain must survive and normalize."""
        self.write_state(iteration=3, discards=0)
        self.hook_log([(1, 100.0), (2, 90.0)])
        state_path = self.dir / ".claude" / "odyssey.local.md"
        text = state_path.read_text(encoding="utf-8")
        # inject GBK-encoded Chinese into the mission prompt section
        gbk_bytes = "工厂布局：竞标价阶梯".encode("gbk")
        raw = state_path.read_bytes()
        state_path.write_bytes(raw + b"\n" + gbk_bytes)
        proc = self.run_hook_c_locale()
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("UnicodeDecodeError", proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["decision"], "block")
        # state was normalized back to valid UTF-8
        state_path.read_text(encoding="utf-8")
        self.assertIn("iteration: 4", state_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()