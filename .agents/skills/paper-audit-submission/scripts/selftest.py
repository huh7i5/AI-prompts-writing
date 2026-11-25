#!/usr/bin/env python3
"""Automated self-test suite for Station 04 (paper-audit-submission).

Verifies:
1. SKILL.md concise structure, frontmatter, and valid relative file links.
2. check_numbers.py discrepancy detection on T06 (102 vs 120 vs 200) and T12 (30 vs 300).
3. T08/R08 revision gate (blocks fabricated supplemental 30-person experiment; passes honest R1 fix + R2 pending).
4. T11 declaration & privacy gate (blocks default no-COI / no-funding / public interview release / fake Zenodo DOI).
5. T12 proof gate & claim_ledger impact propagation broadcast.
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
NUM_SCRIPT = SKILL_DIR / "scripts" / "check_numbers.py"
GATE_SCRIPT = SKILL_DIR / "scripts" / "audit_submission_gate.py"


class Station04SkillTests(unittest.TestCase):
    def test_01_skill_structure_and_links(self) -> None:
        skill_md = SKILL_DIR / "SKILL.md"
        self.assertTrue(skill_md.exists())
        text = skill_md.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 160)
        self.assertTrue(text.startswith("---\nname: paper-audit-submission\n"))
        self.assertIn("Do NOT use for", text)

        rel_links = re.findall(r"\]\((\./[^)]+)\)", text)
        self.assertGreaterEqual(len(rel_links), 5)
        for rel in rel_links:
            self.assertTrue((SKILL_DIR / rel).resolve().exists(), f"Broken link: {rel}")

        self.assertTrue((SKILL_DIR / "agents" / "openai.yaml").exists())

    def test_02_check_numbers_t06_and_t12(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            t06_input = Path(tmp) / "t06.md"
            t06_input.write_text(
                "方法第1段：纳入102人。表1：样本量120。\n摘要：我们对200人进行分析，证明干预能改善学习。",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(NUM_SCRIPT), "--inputs", str(t06_input)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            data = json.loads(res.stdout)
            self.assertTrue(data["has_sample_size_variation"])
            self.assertEqual(data["distinct_sample_sizes"], [102, 120, 200])

            t12_input = Path(tmp) / "t12.md"
            t12_input.write_text(
                "接收稿结果段：纳入30人，均值12 ms。表1：样本量30。\n校样结果段：纳入300人，均值12 ms。表1：样本量30。",
                encoding="utf-8",
            )
            res12 = subprocess.run(
                [sys.executable, str(NUM_SCRIPT), "--inputs", str(t12_input)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            d12 = json.loads(res12.stdout)
            self.assertEqual(d12["distinct_sample_sizes"], [30, 300])

            h03_input = Path(tmp) / "h03.md"
            h03_input.write_text(
                "正文P1：方案计划每年处理12万吨，补助按15元每吨估算，年度补助为180万元。\n"
                "表1：年度处理量12万吨；每吨补助15元；年度补助180万元。\n"
                "摘要A1：补助每年180万元，可使内部收益率达到12%。",
                encoding="utf-8",
            )
            res_h03 = subprocess.run(
                [sys.executable, str(NUM_SCRIPT), "--inputs", str(h03_input)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            dh03 = json.loads(res_h03.stdout)
            self.assertEqual(dh03["unit_bearing_values"]["%"]["distinct_values"], [12.0])
            self.assertEqual(dh03["unit_bearing_values"]["元/吨"]["distinct_values"], [15.0])
            self.assertEqual(len(dh03["unit_bearing_values"]["元/吨"]["occurrences"]), 2)

    def test_03_t08_reviewer_revision_no_fake_experiments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_t08 = Path(tmp) / "bad_t08.md"
            bad_t08.write_text(
                "针对 R2，我们已补充了实验，补充的 30 人实验显示显著差异（p = 0.01），全文已核验无误。",
                encoding="utf-8",
            )
            res_bad = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(bad_t08),
                    "--task",
                    "9.2,9.3",
                    "--no-new-experiments",
                    "--partial-scope",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_bad.returncode, 2)
            codes = {f["code"] for f in json.loads(res_bad.stdout)["findings"]}
            self.assertIn("FABRICATED_SUPPLEMENTAL_EXPERIMENT", codes)
            self.assertIn("PARTIAL_SCOPE_OVERCLAIM", codes)

            good_t08 = Path(tmp) / "good_t08.md"
            good_t08.write_text(
                "修订后摘要：在本测试中，方法 A 的准确率为 89%，低于方法 B 的 90%。\n"
                "改动对照：R1 已修正摘要方向矛盾；R2（增加 30 人重复实验并报告显著性）实验尚未开展，列为仍待处理，不能写“我们已补充实验”；其他未提供章节待核对。",
                encoding="utf-8",
            )
            res_ok = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(good_t08),
                    "--task",
                    "9.2,9.3",
                    "--no-new-experiments",
                    "--partial-scope",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_ok.returncode, 0, msg=res_ok.stdout)

    def test_04_t11_declarations_and_t12_proofs_with_impact_broadcast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_t11 = Path(tmp) / "bad_t11.md"
            bad_t11.write_text(
                "资助声明：本研究未受任何资助。利益冲突：The authors declare no competing interests。\n"
                "数据可用性：建议直接公开原始访谈记录，仓库 DOI 为 10.5281/zenodo.000000。",
                encoding="utf-8",
            )
            res_bad = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(bad_t11),
                    "--task",
                    "8.4",
                    "--unconfirmed-declarations",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_bad.returncode, 2)
            codes = {f["code"] for f in json.loads(res_bad.stdout)["findings"]}
            self.assertIn("UNCONFIRMED_DECLARATION_OR_PRIVACY_BREACH", codes)
            self.assertIn("FAKE_OR_PLACEHOLDER_DOI", codes)

            ledger = Path(tmp) / "ledger.json"
            ledger.write_text(
                json.dumps(
                    {
                        "claims": [
                            {
                                "claim_id": "C01",
                                "target_sections": ["abstract", "table_1", "caption_1", "conclusion"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            good_t12 = Path(tmp) / "good_t12.md"
            good_t12.write_text(
                "仅对所提供的接收稿结果段、校样结果段及表1进行比对（其他页未提供，未完成整篇校样）：\n"
                "发现实质性数字差异：接收稿与表1均为纳入30人，校样结果段变为纳入300人且与表1冲突。请作者核查原始记录并与编辑确认，不能当普通排版笔误自行定夺。",
                encoding="utf-8",
            )
            res_12 = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(good_t12),
                    "--task",
                    "10.1",
                    "--partial-scope",
                    "--claim-ledger",
                    str(ledger),
                    "--modified-claims",
                    "C01",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_12.returncode, 0, msg=res_12.stdout)
            out_json = json.loads(res_12.stdout)
            self.assertEqual(
                out_json["impacted_target_sections_to_sync"],
                ["abstract", "table_1", "caption_1", "conclusion"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
