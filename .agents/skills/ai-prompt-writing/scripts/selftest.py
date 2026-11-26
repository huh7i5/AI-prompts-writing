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

    def test_03_run_gates_pipeline_integration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "pipe_ws"
            (ws / "01_literature").mkdir(parents=True)
            (ws / "03_backbone").mkdir(parents=True)
            (ws / "04_drafts").mkdir(parents=True)
            (ws / "00_project_spec.json").write_text(
                json.dumps({"research_paradigm": "QUANTITATIVE", "study_time_state": "POST_RESULTS"}),
                encoding="utf-8",
            )
            (ws / "01_literature" / "02_literature_ledger.json").write_text(
                json.dumps({"entries": [{"ref_id": "doe2024study", "title": "Study", "reading_depth": "FULLTEXT_READ"}]}),
                encoding="utf-8",
            )
            (ws / "03_backbone" / "03_claim_ledger.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "research_paradigm": "QUANTITATIVE",
                        "study_time_state": "POST_RESULTS",
                        "one_sentence_storyline": "AI hint raises score by 7 percentage points under controlled quiz.",
                        "evidence_items": [
                            {
                                "evidence_id": "E01",
                                "source_location": "raw_data.csv",
                                "recomputation_status": "RECOMPUTED_LOCAL",
                            }
                        ],
                        "claims": [
                            {
                                "claim_id": "C01",
                                "claim_text": "Mean score improved from 75% to 82% (+7 pp).",
                                "support_level": "SUPPORTED",
                                "bound_evidence_ids": ["E01"],
                                "has_adverse_or_counterexample": False,
                                "scope_and_limitations": "Single-course cohort.",
                                "target_sections": ["results"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (ws / "03_backbone" / "04_outline.md").write_text("# Outline", encoding="utf-8")
            (ws / "04_drafts" / "01_results.md").write_text(
                "## 一、 结果\n\n与既有基线一致 [@doe2024study]，实验组平均得分率 82%，对照组 75%，相差 7 个百分点。",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(DOCTOR_SCRIPT), "run-gates", "--workspace", str(ws)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out["overall_status"], "PASS")

    def test_04_install_skill_roundtrip(self) -> None:
        import tempfile
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        installer = repo_root / "scripts" / "install_skill.py"
        if not installer.exists():
            # When running `verify` inside an installed skill directory, the repo root installer is absent.
            return

        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            fake_home.mkdir()

            def run_inst(*cli_args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, "-B", str(installer), *cli_args],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=False,
                )

            r_inst = run_inst("install", "--host", "codex", "--home-root", str(fake_home), "--skip-selftest")
            self.assertEqual(r_inst.returncode, 0, msg=r_inst.stdout + r_inst.stderr)
            d_inst = json.loads(r_inst.stdout)
            self.assertTrue(d_inst["verified"])
            codex_dir = fake_home / ".codex" / "skills"
            self.assertTrue((codex_dir / "ai-prompt-writing" / "SKILL.md").exists())
            self.assertTrue((codex_dir / "paper-audit-submission" / "SKILL.md").exists())

            r_ver = run_inst("verify", "--host", "codex", "--home-root", str(fake_home), "--skip-selftest")
            self.assertEqual(r_ver.returncode, 0, msg=r_ver.stdout + r_ver.stderr)
            self.assertTrue(json.loads(r_ver.stdout)["verified"])

            r_dup = run_inst("install", "--host", "codex", "--home-root", str(fake_home), "--skip-selftest")
            self.assertEqual(r_dup.returncode, 2, msg=r_dup.stdout + r_dup.stderr)
            self.assertEqual(json.loads(r_dup.stdout)["status"], "BLOCKED_EXISTING")

            r_upd = run_inst("update", "--host", "codex", "--home-root", str(fake_home), "--backup-existing", "--skip-selftest")
            self.assertEqual(r_upd.returncode, 0, msg=r_upd.stdout + r_upd.stderr)
            d_upd = json.loads(r_upd.stdout)
            self.assertTrue(d_upd["verified"])
            self.assertTrue(Path(d_upd["backup_dir"]).exists())

            r_un = run_inst("uninstall", "--host", "codex", "--home-root", str(fake_home))
            self.assertEqual(r_un.returncode, 0, msg=r_un.stdout + r_un.stderr)
            self.assertFalse((codex_dir / "ai-prompt-writing").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
