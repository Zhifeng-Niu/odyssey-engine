"""Setup script tests: multibyte prompts, hostile characters, C locale.

Regression for the v1.5.1 bug: BSD sed under a C locale died with
"RE error: illegal byte sequence" on Chinese mission prompts, and any
'|' in user content would break sed delimiter syntax. Template
substitution now runs through python; locale is pinned in the scripts.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SETUP = REPO / "scripts" / "setup-odyssey.sh"

PROMPT = '优化 DMD Stage Two 工厂布局方案 | 竞标价阶梯 🚀 "quoted" & $ (paren)'


class SetupTests(unittest.TestCase):
    def run_setup(self, cwd, *extra_args, c_locale=True):
        env = os.environ.copy()
        if c_locale:
            env["LC_ALL"] = "C"
            env["LANG"] = "C"
        return subprocess.run(
            ["bash", str(SETUP), PROMPT, *extra_args],
            cwd=cwd, capture_output=True, text=True, env=env, timeout=60,
        )

    def test_multibyte_prompt_c_locale_non_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_setup(tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            mission = (Path(tmp) / "MISSION.md").read_text(encoding="utf-8")
            self.assertIn("优化 DMD Stage Two", mission)
            self.assertIn("| 竞标价阶梯 🚀", mission)  # pipe survives too
            self.assertIn("🚀", mission)
            state_text = (Path(tmp) / ".claude" / "odyssey.local.md").read_text()
            self.assertIn("active: true", state_text)
            self.assertIn("field: code", state_text)
            self.assertIn("model_class: standard", state_text)

    def test_git_repo_gets_branch_and_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, capture_output=True)
            proc = self.run_setup(tmp, "--field", "strategy",
                                  "--model-class", "compact")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            mission = (Path(tmp) / "MISSION.md").read_text(encoding="utf-8")
            self.assertIn("Anticipation ladder", mission)  # strategy contract
            self.assertRegex(mission, r"expedition_branch: odyssey/\d{8}-\d{6}")
            state_text = (Path(tmp) / ".claude" / "odyssey.local.md").read_text()
            self.assertIn("field: strategy", state_text)
            self.assertIn("model_class: compact", state_text)

    def test_rejects_bad_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_setup(tmp, "--field", "ontology")
            self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
