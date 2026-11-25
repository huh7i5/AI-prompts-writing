#!/usr/bin/env python3
"""Automated self-test suite for Station 03 (paper-draft-polish).

Verifies:
1. SKILL.md concise structure, frontmatter, and valid relative file links.
2. H01 anti-slop gate (blocks '万能钥匙', dense '总体优势：...处理效率：...', and '全面领先';
   passes clean revision that preserves 12 ms（毫秒） and 18 ms while citing bad phrases in Section 2 notes).
3. 6.5 anti-defensive & numeric fidelity gate (blocks hollow apology or dropped adverse numbers;
   passes revision preserving 12/20, 8/20, 3, 1).
4. 6.4 grammar-only strictness gate & PRE_STUDY Results drafting lock.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
GATE_SCRIPT = SKILL_DIR / "scripts" / "style_and_draft_gate.py"


class Station03SkillTests(unittest.TestCase):
    def test_01_skill_structure_and_links(self) -> None:
        skill_md = SKILL_DIR / "SKILL.md"
        self.assertTrue(skill_md.exists())
        text = skill_md.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 160)
        self.assertTrue(text.startswith("---\nname: paper-draft-polish\n"))
        self.assertIn("Do NOT use for", text)

        rel_links = re.findall(r"\]\((\./[^)]+)\)", text)
        self.assertGreaterEqual(len(rel_links), 4)
        for rel in rel_links:
            self.assertTrue((SKILL_DIR / rel).resolve().exists(), f"Broken link: {rel}")

        self.assertTrue((SKILL_DIR / "agents" / "openai.yaml").exists())
        self.assertTrue((SKILL_DIR / "templates" / "05_revision_worklog.md").exists())

    def test_02_h01_anti_slop_and_section2_explanation_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "h01_src.md"
            src.write_text(
                "总体优势：这个方案像一把“万能钥匙”，肯定能彻底解决资料管理问题（这下可省心了）。"
                "处理效率：方法A在本次单次测量中用时12 ms（毫秒），方法B用时18 ms（毫秒），因此已经证明A在所有任务上全面领先。",
                encoding="utf-8",
            )
            res_bad = subprocess.run(
                [sys.executable, str(GATE_SCRIPT), "--draft", str(src), "--mode", "anti-slop"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_bad.returncode, 2)
            codes = {f["code"] for f in json.loads(res_bad.stdout)["findings"]}
            self.assertIn("AI_CLICHE_METAPHOR", codes)
            self.assertIn("UNSUPPORTED_ABSOLUTE_OVERCLAIM", codes)
            self.assertIn("OUTLINE_COLON_PROSE_SLOP", codes)

            clean_h01 = Path(tmp) / "h01_clean.md"
            clean_h01.write_text(
                "## 一、 修订稿\n\n"
                "在本次单次测量中，方法 A 的处理用时为 12 ms（毫秒），低于方法 B 的 18 ms。由于目前仅有这一次测量结果，尚不能判断方法 A 在其他资料管理任务或重复测试中是否持续占优。\n\n"
                "## 二、 关键修改对照与理由\n\n"
                "- 删去了“万能钥匙”“这下可省心了”及“在所有任务上全面领先”，去除了“总体优势：”“处理效率：”等提纲式标签，保留了首次说明单位的“12 ms（毫秒）”。",
                encoding="utf-8",
            )
            res_good = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(clean_h01),
                    "--mode",
                    "anti-slop",
                    "--source-text",
                    str(src),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_good.returncode, 0, msg=res_good.stdout)
            self.assertEqual(json.loads(res_good.stdout)["status"], "PASS")

    def test_03_anti_defensive_and_numeric_fidelity_6_5(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src_65.md"
            src.write_text(
                "这只是一次粗浅的尝试，恳请读者包涵。同一班级单次作业中（学生自选开启提醒），开启组 12/20 按时提交（3 人迟交一周），未开启组 8/20 按时提交（1 人迟交一周）。",
                encoding="utf-8",
            )
            dropped_adverse = Path(tmp) / "dropped.md"
            dropped_adverse.write_text(
                "同一班级单次作业中（学生自选开启提醒），开启提醒组有 12/20 人按时提交，未开启组有 8/20 人按时提交。",
                encoding="utf-8",
            )
            res_drop = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(dropped_adverse),
                    "--mode",
                    "anti-defensive",
                    "--source-text",
                    str(src),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_drop.returncode, 2)
            self.assertIn("SOURCE_NUMBER_DROPPED_OR_ALTERED", {f["code"] for f in json.loads(res_drop.stdout)["findings"]})

            good_65 = Path(tmp) / "good_65.md"
            good_65.write_text(
                "在同一班级的单次作业记录中（学生自行选择是否开启提醒），开启提醒组有 12/20 人按时提交，未开启组为 8/20 人；"
                "但开启组有 3 人迟交至少一周，高于未开启组的 1 人。\n\n"
                "## 二、 修改说明\n删去“粗浅的尝试，恳请读者包涵”，保留全部正向与反向人数及自选条件。",
                encoding="utf-8",
            )
            res_ok = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(good_65),
                    "--mode",
                    "anti-defensive",
                    "--source-text",
                    str(src),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_ok.returncode, 0, msg=res_ok.stdout)

    def test_04_grammar_only_and_pre_study_draft_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_grammar = Path(tmp) / "bad_64.md"
            bad_grammar.write_text("我顺手把这段话润色得更流畅了：本研究探讨了缓存的延迟表现。", encoding="utf-8")
            res_g = subprocess.run(
                [sys.executable, str(GATE_SCRIPT), "--draft", str(bad_grammar), "--mode", "grammar-only"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_g.returncode, 2)

            good_grammar = Path(tmp) / "good_64.md"
            good_grammar.write_text("未发现语法、拼写或格式错误。", encoding="utf-8")
            res_g_ok = subprocess.run(
                [sys.executable, str(GATE_SCRIPT), "--draft", str(good_grammar), "--mode", "grammar-only"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_g_ok.returncode, 0)

            ledger = Path(tmp) / "pre_ledger.json"
            ledger.write_text(json.dumps({"study_time_state": "PRE_STUDY", "claims": []}), encoding="utf-8")
            res_pre = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(good_grammar),
                    "--mode",
                    "draft",
                    "--section",
                    "results",
                    "--claim-ledger",
                    str(ledger),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_pre.returncode, 2)
            self.assertIn("PRE_STUDY_SECTION_LOCK", {f["code"] for f in json.loads(res_pre.stdout)["findings"]})

            # Numbered subsections ### 2. inside Section 1 must still be scanned!
            subsec_bad = Path(tmp) / "subsec_bad.md"
            subsec_bad.write_text(
                "## 一、 方法初稿\n### 1. 研究设计\n正常叙述。\n### 2. 资料分析\n该多维协同机制全面领先。\n## 二、 关键修改说明\n无。",
                encoding="utf-8",
            )
            res_sub = subprocess.run(
                [sys.executable, str(GATE_SCRIPT), "--draft", str(subsec_bad), "--mode", "draft"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_sub.returncode, 2)
            sub_codes = {f["code"] for f in json.loads(res_sub.stdout)["findings"]}
            self.assertIn("AI_BUZZWORD_STACK", sub_codes)
            self.assertIn("UNSUPPORTED_ABSOLUTE_OVERCLAIM", sub_codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
