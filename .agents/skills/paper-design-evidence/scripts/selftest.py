#!/usr/bin/env python3
"""Automated self-test suite for Station 02 (paper-design-evidence).

Verifies:
1. SKILL.md concise structure, frontmatter, and valid relative file links.
2. init_workspace.py standard workspace scaffolding and stage status detection.
3. T10 theoretical proof boundary (blocks demanding p-values/sample sizes or claiming full formal verification;
   passes clean counterexample + domain-narrowing audit).
4. Claim-Evidence Ledger contract (blocks ungrounded SUPPORTED claims, pre-study fabricated findings,
   and undisclosed counterexamples/trade-offs; passes properly grounded ledger).
5. Task 4.3 figure caption gate (blocks fake rendered-plot claims).
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
SCRIPTS_DIR = SKILL_DIR / "scripts"
INIT_SCRIPT = SCRIPTS_DIR / "init_workspace.py"
GATE_SCRIPT = SCRIPTS_DIR / "design_evidence_gate.py"


class Station02SkillTests(unittest.TestCase):
    def test_01_skill_structure_and_links(self) -> None:
        skill_md = SKILL_DIR / "SKILL.md"
        self.assertTrue(skill_md.exists())
        text = skill_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertLessEqual(len(lines), 160, f"SKILL.md should stay concise (got {len(lines)} lines)")
        self.assertTrue(text.startswith("---\nname: paper-design-evidence\n"))
        self.assertIn("Do NOT use for", text)

        rel_links = re.findall(r"\]\((\./[^)]+)\)", text)
        self.assertGreaterEqual(len(rel_links), 5)
        for rel in rel_links:
            target = (SKILL_DIR / rel).resolve()
            self.assertTrue(target.exists(), f"Broken link in SKILL.md: {rel} -> {target}")

        self.assertTrue((SKILL_DIR / "agents" / "openai.yaml").exists())
        self.assertTrue((SKILL_DIR / "templates" / "03_claim_ledger.schema.json").exists())
        self.assertTrue((SKILL_DIR / "templates" / "04_outline_template.md").exists())

    def test_02_workspace_init_and_status_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "demo_paper_ws"
            res_init = subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "init",
                    "--workspace",
                    str(ws),
                    "--paradigm",
                    "THEORETICAL",
                    "--time-state",
                    "POST_RESULTS",
                    "--discipline",
                    "Mathematics",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_init.returncode, 0, msg=res_init.stderr)
            self.assertTrue((ws / "00_project_spec.json").exists())
            self.assertTrue((ws / "03_backbone" / "03_claim_ledger.json").exists())

            res_status = subprocess.run(
                [sys.executable, str(INIT_SCRIPT), "status", "--workspace", str(ws)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_status.returncode, 0)
            s_json = json.loads(res_status.stdout)
            self.assertTrue(s_json["exists"])
            self.assertEqual(s_json["artifacts"]["registered_claims_count"], 0)

    def test_03_t10_theoretical_counterexample_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_t10 = Path(tmp) / "bad_t10.md"
            bad_t10.write_text(
                "该推导样本量不足，必须报告 p 值并建议增加随机对照实验。此外我们已完成完整形式化验证。",
                encoding="utf-8",
            )
            res_bad = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(bad_t10),
                    "--task",
                    "4.2",
                    "--paradigm",
                    "theoretical",
                    "--time-state",
                    "post-results",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_bad.returncode, 2)
            codes = {f["code"] for f in json.loads(res_bad.stdout)["findings"]}
            self.assertIn("PARADIGM_MISMATCH_REQUIREMENT", codes)
            self.assertIn("UNVERIFIED_FORMAL_PROOF_CLAIM", codes)

            good_t10 = Path(tmp) / "good_t10.md"
            good_t10.write_text(
                "1. 已能支持与需收窄的主张：原主张“f(x)=x² 在整个实数域严格递增”不成立；若将定义域收窄至非负实数 [0, +∞)，则严格递增成立。\n"
                "2. 具体依据（反例）：推导中“若 a < b 则 a² < b²”隐含了非负条件。取反例 a = -2, b = -1，满足 -2 < -1，但 a² = 4 > b² = 1。\n"
                "3. 仍不能判断的部分：未提供论文其余引理是否依赖全实数域单调性（本研究属纯数学推导，无需统计检验或样本量，本次亦未运行机器形式化证明器）。\n"
                "4. 下一步：在命题前提中显式加入 a, b ≥ 0（或分 (-∞, 0] 严格递减讨论），并同步检查后续引用该命题的段落。",
                encoding="utf-8",
            )
            res_good = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(good_t10),
                    "--task",
                    "4.2",
                    "--paradigm",
                    "theoretical",
                    "--time-state",
                    "post-results",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_good.returncode, 0, msg=res_good.stdout)
            self.assertEqual(json.loads(res_good.stdout)["status"], "PASS")

    def test_04_claim_ledger_and_pre_study_guards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_ledger = Path(tmp) / "bad_ledger.json"
            bad_ledger.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "generated_at": "2026-11-25T00:00:00+00:00",
                        "research_paradigm": "QUANTITATIVE",
                        "study_time_state": "PRE_STUDY",
                        "one_sentence_storyline": "Test",
                        "evidence_items": [{"evidence_id": "E01", "source_location": "plan", "recomputation_status": "NOT_RECOMPUTED_TEXT_AUDIT_ONLY"}],
                        "claims": [
                            {
                                "claim_id": "C01",
                                "claim_text": "Intervention improves scores.",
                                "support_level": "SUPPORTED",
                                "bound_evidence_ids": [],
                                "has_adverse_or_counterexample": True,
                                "scope_and_limitations": "",
                                "target_sections": ["abstract"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            res_bad = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--claim-ledger",
                    str(bad_ledger),
                    "--task",
                    "3.4",
                    "--paradigm",
                    "quantitative",
                    "--time-state",
                    "pre-study",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_bad.returncode, 2)
            codes = {f["code"] for f in json.loads(res_bad.stdout)["findings"]}
            self.assertIn("UNGROUNDED_SUPPORTED_CLAIM", codes)
            self.assertIn("PRE_STUDY_FABRICATED_SUPPORT", codes)
            self.assertIn("UNDISCLOSED_COUNTEREXAMPLE_OR_TRADEOFF", codes)

            good_ledger = Path(tmp) / "good_ledger.json"
            good_ledger.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "generated_at": "2026-11-25T00:00:00+00:00",
                        "research_paradigm": "THEORETICAL",
                        "study_time_state": "POST_RESULTS",
                        "one_sentence_storyline": "f(x)=x^2 is strictly increasing on non-negative reals.",
                        "evidence_items": [
                            {
                                "evidence_id": "E01_AlgebraicStep",
                                "source_location": "User proof snippet line 1",
                                "recomputation_status": "RECOMPUTED_LOCAL",
                            }
                        ],
                        "claims": [
                            {
                                "claim_id": "C01",
                                "claim_text": "f(x)=x^2 is strictly increasing on [0, +inf).",
                                "support_level": "SUPPORTED",
                                "bound_evidence_ids": ["E01_AlgebraicStep"],
                                "has_adverse_or_counterexample": True,
                                "scope_and_limitations": "Restricted to non-negative real numbers; fails on negative reals (e.g. -2 < -1 gives 4 > 1).",
                                "target_sections": ["abstract", "main_theorem", "conclusion"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            res_good = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--claim-ledger",
                    str(good_ledger),
                    "--task",
                    "3.4",
                    "--paradigm",
                    "theoretical",
                    "--time-state",
                    "post-results",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_good.returncode, 0, msg=res_good.stdout)
            self.assertEqual(json.loads(res_good.stdout)["status"], "PASS")

    def test_05_figure_caption_and_composite_task_guards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_fig = Path(tmp) / "bad_43.md"
            bad_fig.write_text("已为您生成高清图表文件，图1展示了A和B的差异（±SD）。", encoding="utf-8")
            res = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(bad_fig),
                    "--task",
                    "3.4,4.3",
                    "--paradigm",
                    "quantitative",
                    "--time-state",
                    "pre-study",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 2)
            findings = json.loads(res.stdout)["findings"]
            codes = {f["code"] for f in findings}
            self.assertIn("FAKE_PLOT_RENDER_CLAIM", codes)
            self.assertIn("CAPTION_MISSING_SCOPE_ELEMENTS", codes)

            # Long quoted refusal explanation in PRE_STUDY must NOT false-positive
            refusal_doc = Path(tmp) / "refusal_43.md"
            refusal_doc.write_text(
                "图1（计划态）：期末得分率（单位：%，计划样本量 N = 120，[待补误差标记含义]）。\n"
                "拦截说明：由于实验下月才启动，不能按您原话在图注中写“实验结果表明 AI 提示显著提高了期末成绩”。",
                encoding="utf-8",
            )
            res_ok = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(refusal_doc),
                    "--task",
                    "3.4,4.3",
                    "--paradigm",
                    "QUANTITATIVE",
                    "--time-state",
                    "PRE_STUDY",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_ok.returncode, 0, msg=res_ok.stdout)
            self.assertEqual(json.loads(res_ok.stdout)["status"], "PASS")

    def test_06_stats_and_svg_plotter_end_to_end(self) -> None:
        stats_script = SCRIPTS_DIR / "stats_and_plot.py"
        self.assertTrue(stats_script.exists())
        sys.path.insert(0, str(SCRIPTS_DIR))
        import stats_and_plot as sap

        # Verify numerical accuracy of exact Student's t two-sided p-value (df=1, t=12.7062 -> p ~ 0.05)
        self.assertAlmostEqual(sap.student_t_two_sided_p(12.706205, 1.0), 0.05, places=4)

        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            csv_path = tpath / "raw_data.csv"
            csv_path.write_text(
                "group,score\n"
                "Control,74\nControl,76\nControl,75\nControl,75\nControl,NA\n"
                "AI_Hint,81\nAI_Hint,83\nAI_Hint,82\nAI_Hint,82\n",
                encoding="utf-8",
            )
            ledger_path = tpath / "03_claim_ledger.json"
            ledger_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "generated_at": "2026-11-25T00:00:00+00:00",
                        "research_paradigm": "QUANTITATIVE",
                        "study_time_state": "POST_RESULTS",
                        "one_sentence_storyline": "AI hint increased score by 7 percentage points.",
                        "evidence_items": [],
                        "claims": [],
                    }
                ),
                encoding="utf-8",
            )
            svg_out = tpath / "fig1.svg"
            cap_out = tpath / "fig1_caption.md"
            res = subprocess.run(
                [
                    sys.executable,
                    str(stats_script),
                    "analyze",
                    "--csv",
                    str(csv_path),
                    "--group-col",
                    "group",
                    "--baseline-group",
                    "Control",
                    "--value-col",
                    "score",
                    "--unit",
                    "%",
                    "--title",
                    "Final Test Score Comparison",
                    "--error-bar",
                    "ci95",
                    "--out-svg",
                    str(svg_out),
                    "--out-caption",
                    str(cap_out),
                    "--update-claim-ledger",
                    str(ledger_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out["total_valid_n"], 8)
            self.assertEqual(out["total_missing_n"], 1)
            self.assertAlmostEqual(out["groups"]["Control"]["mean"], 75.0, places=4)
            self.assertAlmostEqual(out["groups"]["AI_Hint"]["mean"], 82.0, places=4)
            self.assertAlmostEqual(out["pairwise_welch_comparison"]["diff_absolute"], 7.0, places=4)
            self.assertEqual(out["pairwise_welch_comparison"]["diff_unit_label"], "percentage points")
            self.assertLess(out["pairwise_welch_comparison"]["p_value"], 0.001)
            self.assertTrue(svg_out.exists() and "<svg" in svg_out.read_text(encoding="utf-8"))
            self.assertIn("个百分点", cap_out.read_text(encoding="utf-8"))

            # Verify generated caption passes Station 02 task 4.3 gate cleanly
            gate_cap = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(cap_out),
                    "--task",
                    "4.3",
                    "--paradigm",
                    "QUANTITATIVE",
                    "--time-state",
                    "POST_RESULTS",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(gate_cap.returncode, 0, msg=gate_cap.stdout)
            updated_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(updated_ledger["evidence_items"][0]["recomputation_status"], "RECOMPUTED_LOCAL")

    def test_07_paper_presets_thesis_and_review(self) -> None:
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        doctor_script = Path(__file__).resolve().parents[2] / "ai-prompt-writing" / "scripts" / "pipeline_doctor.py"
        with tempfile.TemporaryDirectory() as tmp:
            ws_thesis = Path(tmp) / "thesis_ws"
            res_t = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(INIT_SCRIPT),
                    "init",
                    "--workspace",
                    str(ws_thesis),
                    "--preset",
                    "thesis_zh",
                    "--discipline",
                    "计算机科学与技术",
                    "--title",
                    "基于可验证工作流的学术写作系统研究",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_t.returncode, 0, msg=res_t.stdout + res_t.stderr)
            out_t = json.loads(res_t.stdout)
            self.assertEqual(out_t["paper_preset"], "thesis_zh")
            self.assertTrue(out_t["outline_scaffolded"])
            self.assertEqual(out_t["recommended_tex_template"], "ctexbook")

            outline_text = (ws_thesis / "03_backbone" / "04_outline.md").read_text(encoding="utf-8")
            self.assertIn("GB/T 7713.1", outline_text)
            self.assertIn("第 1 章 绪论", outline_text)
            self.assertIn("thuthesis|pkuthss|sjtuthesis|ustcthesis", outline_text)

            diag_t = subprocess.run(
                [sys.executable, "-B", str(doctor_script), "diagnose", "--workspace", str(ws_thesis)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(diag_t.returncode, 0, msg=diag_t.stdout + diag_t.stderr)
            diag_data = json.loads(diag_t.stdout)
            self.assertEqual(diag_data["paper_preset"], "thesis_zh")
            self.assertIn("GB/T 7713.1", diag_data["reason"])

            ws_rev = Path(tmp) / "review_ws"
            res_r = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(INIT_SCRIPT),
                    "init",
                    "--workspace",
                    str(ws_rev),
                    "--preset",
                    "review",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_r.returncode, 0, msg=res_r.stdout + res_r.stderr)
            out_r = json.loads(res_r.stdout)
            self.assertEqual(out_r["paper_preset"], "review")
            self.assertEqual(out_r["paradigm"], "FOCUSED_REVIEW")
            self.assertTrue(out_r["outline_scaffolded"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
