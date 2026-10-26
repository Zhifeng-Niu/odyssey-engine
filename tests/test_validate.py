"""Mission-grammar validation tests: MISSION.md as a checked language."""

import json
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HELPER = REPO / "scripts" / "odyssey_helper.py"
TEMPLATE = REPO / "templates" / "MISSION.md.template"


def validate(path):
    proc = subprocess.run(
        ["python3", str(HELPER), "validate", "--mission", str(path)],
        capture_output=True, text=True,
    )
    return json.loads(proc.stdout)


class ValidateTests(unittest.TestCase):
    def test_template_is_valid(self):
        result = validate(TEMPLATE)
        self.assertTrue(result["valid"], result["errors"])
        self.assertGreaterEqual(result["sections"], 8)

    def test_missing_sections_flagged(self):
        with tempfile_tmp() as p:
            p.write_text("# Mission: X\n\n## Goal\nonly a goal\n")
            result = validate(p)
            self.assertFalse(result["valid"])
            joined = " ".join(result["errors"])
            for section in ("Metrics", "Guard", "Termination", "Ideas Backlog"):
                self.assertIn(section, joined)

    def test_guard_requires_fenced_block(self):
        with tempfile_tmp() as p:
            p.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "```bash\n{{GUARD_CMD}}\n```", "no fenced block"))
            result = validate(p)
            self.assertFalse(result["valid"])
            self.assertIn("Guard", " ".join(result["errors"]))

    def test_strategy_field_warns_on_missing_board(self):
        with tempfile_tmp() as p:
            text = TEMPLATE.read_text(encoding="utf-8")
            text = text.replace("---\norientation:", "---\nfield: strategy\norientation:")
            text = text.replace("## Board\n", "")  # strip board if present
            p.write_text(text)
            result = validate(p)
            self.assertTrue(any("Board" in w for w in result["warnings"]))


def tempfile_tmp():
    import tempfile
    return _Ctx(tempfile.NamedTemporaryFile(suffix=".md", delete=False))


class _Ctx:
    def __init__(self, ntf):
        self.ntf = ntf

    def __enter__(self):
        self.ntf.close()
        return Path(self.ntf.name)

    def __exit__(self, *a):
        Path(self.ntf.name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
