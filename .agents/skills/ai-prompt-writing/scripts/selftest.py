#!/usr/bin/env python3
"""Self-test for the master router skill (ai-prompt-writing)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DOCTOR_SCRIPT = SKILL_DIR / "scripts" / "pipeline_doctor.py"


class RouterSkillTests(unittest.TestCase):
    def test_01_router_structure_and_station_links(self) -> None:
        skill_md = SKILL_DIR / "SKILL.md"
        self.assertTrue(skill_md.exists())
        text = skill_md.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 120)
        self.assertTrue(text.startswith("---\nname: ai-prompt-writing\n"))

        rel_links = re.findall(r"\]\(((?:\.\.?/)[^)]+)\)", text)
        self.assertGreaterEqual(len(rel_links), 5)
        for rel in rel_links:
            self.assertTrue((SKILL_DIR / rel).resolve().exists(), f"Broken router link: {rel}")

    def test_02_diagnose_progression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            res0 = subprocess.run(
                [sys.executable, str(DOCTOR_SCRIPT), "diagnose", "--workspace", str(ws)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res0.returncode, 0)
            d0 = json.loads(res0.stdout)
            self.assertEqual(d0["suite_mode"], "FULL_SUITE_MODE")
            self.assertFalse(d0["workspace_exists"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
