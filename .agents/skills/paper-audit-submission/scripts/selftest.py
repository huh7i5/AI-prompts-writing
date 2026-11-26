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

    def test_05_manuscript_export_docx_and_tex(self) -> None:
        import zipfile

        exp_script = SKILL_DIR / "scripts" / "export_manuscript.py"
        self.assertTrue(exp_script.exists())
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            (ws / "01_literature").mkdir(parents=True)
            (ws / "04_drafts").mkdir(parents=True)
            (ws / "00_project_spec.json").write_text(
                json.dumps({"title_working": "测试论文题目：AI辅助研究"}), encoding="utf-8"
            )
            (ws / "01_literature" / "02_literature_ledger.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "ref_id": "smith2024study",
                                "authors": ["Alice Smith", "Bob Lee"],
                                "year": 2024,
                                "title": "Controlled Trial of Hints",
                                "venue": "Journal of Testing",
                                "doi": "10.1000/test.2024",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (ws / "04_drafts" / "01_intro.md").write_text(
                "# 1. 引言\n\n已有研究表明支架设计影响学习表现 [@smith2024study]。\n\n"
                "| 组别 | 均值 |\n| --- | --- |\n| 对照 | 75% |\n| 实验 | 82% |\n",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(exp_script), "--workspace", str(ws), "--authors", "张三, 李四"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out["status"], "PASS")
            self.assertEqual(out["resolved_citations_count"], 1)

            docx_path = ws / "06_submission" / "manuscript.docx"
            tex_path = ws / "06_submission" / "manuscript.tex"
            self.assertTrue(docx_path.exists())
            self.assertTrue(tex_path.exists())

            tex_txt = tex_path.read_text(encoding="utf-8")
            self.assertIn(r"\documentclass[11pt,a4paper]{ctexart}", tex_txt)
            self.assertIn(r"\bibitem{ref1}", tex_txt)

            with zipfile.ZipFile(docx_path, "r") as zf:
                names = set(zf.namelist())
                self.assertIn("word/document.xml", names)
                self.assertIn("word/styles.xml", names)
                doc_xml = zf.read("word/document.xml").decode("utf-8")
                self.assertIn("Controlled Trial of Hints", doc_xml)

            try:
                import docx  # type: ignore

                d = docx.Document(str(docx_path))
                full_para_text = "\n".join(p.text for p in d.paragraphs)
                self.assertIn("引言", full_para_text)
                self.assertGreaterEqual(len(d.tables), 1)
            except ImportError:
                pass

    def test_06_docx_embedded_image_three_line_table_and_footer(self) -> None:
        import json
        import struct
        import subprocess
        import sys
        import tempfile
        import zipfile
        import zlib
        from pathlib import Path

        def make_tiny_png(w: int = 4, h: int = 4) -> bytes:
            raw_rows = b"".join(b"\x00" + b"\x1f\x4e\x78" * w for _ in range(h))

            def chunk(tag: bytes, payload: bytes) -> bytes:
                return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

            ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
            return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw_rows)) + chunk(b"IEND", b"")

        exp_script = SKILL_DIR / "scripts" / "export_manuscript.py"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            (ws / "01_literature").mkdir(parents=True)
            (ws / "02_evidence").mkdir(parents=True)
            (ws / "04_drafts").mkdir(parents=True)
            (ws / "06_submission").mkdir(parents=True)

            (ws / "00_project_spec.json").write_text(
                json.dumps({"title_working": "三线表与插图导出测试", "paper_preset": "thesis_zh"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (ws / "02_evidence" / "fig1.png").write_bytes(make_tiny_png())
            (ws / "01_literature" / "02_literature_ledger.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "ref_id": "Wang2024",
                                "authors": ["Wang, L."],
                                "year": 2024,
                                "title": "Structured Scholarly Formatting",
                                "venue": "J. Doc.",
                                "verification_status": "VERIFIED",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (ws / "04_drafts" / "01_ch1.md").write_text(
                "# 第 1 章 绪论\n\n前期研究表明排版一致性很重要 [@Wang2024]。\n\n![实验结果图](fig1.png)\n",
                encoding="utf-8",
            )
            (ws / "04_drafts" / "02_ch2.md").write_text(
                "# 第 2 章 对比实验\n\n| 模型 | 样本量 | 准确率 (%) |\n| --- | --- | --- |\n| 基线 | 120 | 78.4 |\n| 本文 | 120 | 84.2 |\n",
                encoding="utf-8",
            )

            docx_path = ws / "06_submission" / "thesis.docx"
            tex_path = ws / "06_submission" / "main.tex"
            res = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(exp_script),
                    "--workspace",
                    str(ws),
                    "--out-docx",
                    str(docx_path),
                    "--out-tex",
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
            summary = json.loads(res.stdout)
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(summary["resolved_citations_count"], 1)
            self.assertEqual(summary["docx_embedded_images"], ["fig1.png"])

            with zipfile.ZipFile(docx_path, "r") as zf:
                names = set(zf.namelist())
                self.assertIn("word/media/image1.png", names)
                self.assertIn("word/footer1.xml", names)
                doc_xml = zf.read("word/document.xml").decode("utf-8")
                self.assertIn("<w:drawing>", doc_xml)
                self.assertIn('w:sz="12"', doc_xml)
                self.assertIn("<w:pageBreakBefore/>", doc_xml)

            try:
                import docx  # type: ignore

                d = docx.Document(str(docx_path))
                self.assertGreaterEqual(len(d.tables), 1)
                self.assertGreaterEqual(len(d.inline_shapes), 1)
            except ImportError:
                pass

    def test_07_latex_registry_multifile_and_byo_template(self) -> None:
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        exp_script = SKILL_DIR / "scripts" / "export_manuscript.py"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            (ws / "01_literature").mkdir(parents=True)
            (ws / "04_drafts").mkdir(parents=True)
            (ws / "01_literature" / "02_literature_ledger.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "ref_id": "Smith2023",
                                "authors": ["Smith, A."],
                                "year": 2023,
                                "title": "Verified Benchmark Evaluation",
                                "venue": "IEEE Trans.",
                                "doi": "10.1109/test.2023.1",
                                "verification_status": "VERIFIED",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (ws / "04_drafts" / "01_intro.md").write_text(
                "# Introduction\n\nPrior benchmarks remain fragmented [@Smith2023].\n",
                encoding="utf-8",
            )
            (ws / "04_drafts" / "02_method.md").write_text(
                "# Methodology\n\nWe evaluate unified pipelines.\n",
                encoding="utf-8",
            )

            # 1) Verified registry adapter: ieee
            ieee_dir = Path(tmp) / "out_ieee"
            res_ieee = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(exp_script),
                    "--workspace",
                    str(ws),
                    "--tex-template",
                    "ieee",
                    "--out-tex",
                    str(ieee_dir / "paper.tex"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_ieee.returncode, 0, msg=res_ieee.stdout + res_ieee.stderr)
            ieee_tex = (ieee_dir / "paper.tex").read_text(encoding="utf-8")
            self.assertIn(r"\documentclass[conference]{IEEEtran}", ieee_tex)
            self.assertIn(r"\cite{Smith2023}", ieee_tex)
            self.assertTrue((ieee_dir / "refs.bib").exists())

            # 2) Verified university adapter: thuthesis multi-chapter layout
            thu_dir = Path(tmp) / "out_thu"
            res_thu = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(exp_script),
                    "--workspace",
                    str(ws),
                    "--tex-template",
                    "thuthesis",
                    "--out-tex",
                    str(thu_dir / "thuthesis_main.tex"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_thu.returncode, 0, msg=res_thu.stdout + res_thu.stderr)
            thu_main = (thu_dir / "thuthesis_main.tex").read_text(encoding="utf-8")
            self.assertIn(r"\documentclass[degree=master]{thuthesis}", thu_main)
            self.assertTrue((thu_dir / "data" / "chap01.tex").exists())
            self.assertTrue((thu_dir / "ref" / "refs.bib").exists())
            self.assertIn(r"\chapter{", (thu_dir / "data" / "chap01.tex").read_text(encoding="utf-8"))

            # 3) BYO inspect-tex + safe marker-block injection
            byo_tpl = Path(tmp) / "my_school_tpl.tex"
            original_tpl = (
                "\\documentclass{pkuthss}\n"
                "\\begin{document}\n"
                "% AI_PROMPTS_BODY_START\n"
                "OLD_PLACEHOLDER\n"
                "% AI_PROMPTS_BODY_END\n"
                "\\end{document}\n"
            )
            byo_tpl.write_text(original_tpl, encoding="utf-8")

            res_insp = subprocess.run(
                [sys.executable, "-B", str(exp_script), "--inspect-tex", str(byo_tpl)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_insp.returncode, 0, msg=res_insp.stdout + res_insp.stderr)
            insp_info = json.loads(res_insp.stdout)
            self.assertEqual(insp_info["documentclass"], "pkuthss")
            self.assertEqual(insp_info["top_section_cmd"], "chapter")
            self.assertTrue(insp_info["has_body_markers"])

            byo_out = Path(tmp) / "out_byo" / "adapted.tex"
            res_byo = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(exp_script),
                    "--workspace",
                    str(ws),
                    "--template-tex",
                    str(byo_tpl),
                    "--out-tex",
                    str(byo_out),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_byo.returncode, 0, msg=res_byo.stdout + res_byo.stderr)
            byo_summary = json.loads(res_byo.stdout)
            self.assertEqual(byo_summary["tex_details"]["injection_mode"], "marker-block")
            adapted_txt = byo_out.read_text(encoding="utf-8")
            self.assertIn(r"\chapter{Introduction}", adapted_txt)
            self.assertNotIn("OLD_PLACEHOLDER", adapted_txt)
            self.assertEqual(byo_tpl.read_text(encoding="utf-8"), original_tpl)


if __name__ == "__main__":
    unittest.main(verbosity=2)
