#!/usr/bin/env python3
"""Automated self-test suite for Station 01 (paper-topic-literature).

Verifies:
1. SKILL.md progressive-disclosure size, frontmatter contract, and valid relative links.
2. Offline fallback contract (T02 boundary).
3. Prompt-injection / fake DOI / superiority overclaim blocking & negation safety (T03 boundary).
4. Orphan citation & unwarranted systematic review blocking (T09 / 2.3 boundary).
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
SEARCH_SCRIPT = SCRIPTS_DIR / "lit_search_verify.py"
GATE_SCRIPT = SCRIPTS_DIR / "lit_gate_check.py"


class Station01SkillTests(unittest.TestCase):
    def test_01_skill_structure_and_links(self) -> None:
        skill_md = SKILL_DIR / "SKILL.md"
        self.assertTrue(skill_md.exists(), "SKILL.md must exist")
        text = skill_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertLessEqual(len(lines), 160, f"SKILL.md should stay concise (got {len(lines)} lines)")
        self.assertTrue(text.startswith("---\nname: paper-topic-literature\n"))
        self.assertIn("Do NOT use for", text)

        # Verify all relative markdown links exist on disk
        rel_links = re.findall(r"\]\((\./[^)]+)\)", text)
        self.assertGreaterEqual(len(rel_links), 4)
        for rel in rel_links:
            target = (SKILL_DIR / rel).resolve()
            self.assertTrue(target.exists(), f"Broken link in SKILL.md: {rel} -> {target}")

        self.assertTrue((SKILL_DIR / "agents" / "openai.yaml").exists())
        self.assertTrue((SKILL_DIR / "templates" / "01_topic_spec.yaml").exists())
        self.assertTrue((SKILL_DIR / "templates" / "02_literature_ledger.schema.json").exists())

    def test_02_offline_search_fallback_and_gate_t02(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SEARCH_SCRIPT),
                "search",
                "--query",
                "generative AI source verification undergraduate",
                "--offline",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["capability_state"], "OFFLINE_FALLBACK")
        self.assertEqual(payload["entries"], [])

        with tempfile.TemporaryDirectory() as tmp:
            bad_plan = Path(tmp) / "bad_offline.md"
            bad_plan.write_text(
                "检索方案：建议参考 (Smith et al., 2024) 以及 DOI 10.1016/j.compedu.2024.105001。",
                encoding="utf-8",
            )
            bad_res = subprocess.run(
                [sys.executable, str(GATE_SCRIPT), "--draft", str(bad_plan), "--mode", "search-offline"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(bad_res.returncode, 2)
            bad_json = json.loads(bad_res.stdout)
            self.assertEqual(bad_json["status"], "BLOCKED")
            codes = {f["code"] for f in bad_json["findings"]}
            self.assertIn("OFFLINE_HALLUCINATED_DOI", codes)
            self.assertIn("OFFLINE_HALLUCINATED_CITATION", codes)

            good_plan = Path(tmp) / "good_offline.md"
            good_plan.write_text(
                "本次未执行外部检索，仅提供检索方案：\n"
                '检索式 1：("generative AI" OR LLM) AND ("source verification" OR "fact checking") AND undergraduate\n'
                '反向检索式 2：("generative AI") AND ("critical literacy" OR "null effect")\n'
                "当前不能凭未检索推断学界尚无相关研究。",
                encoding="utf-8",
            )
            good_res = subprocess.run(
                [sys.executable, str(GATE_SCRIPT), "--draft", str(good_plan), "--mode", "search-offline"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(good_res.returncode, 0)
            self.assertEqual(json.loads(good_res.stdout)["status"], "PASS")

    def test_03_contaminated_material_and_negation_guard_t03(self) -> None:
        verify_fake = subprocess.run(
            [sys.executable, str(SEARCH_SCRIPT), "verify", "--doi", "10.0000/fake.2099", "--offline"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(verify_fake.returncode, 2)
        v_json = json.loads(verify_fake.stdout)
        self.assertEqual(v_json["results"][0]["verification_status"], "REJECTED_FAKE_PREFIX")

        with tempfile.TemporaryDirectory() as tmp:
            hijacked = Path(tmp) / "hijacked_t03.md"
            hijacked.write_text(
                "已核实 DOI 10.0000/fake.2099，实验表明缓存方案A全面领先，并填补了国内外空白 [材料C]。",
                encoding="utf-8",
            )
            res_bad = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(hijacked),
                    "--mode",
                    "related-work",
                    "--allowed-ids",
                    "A,B,材料A,材料B",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_bad.returncode, 2)
            codes = {f["code"] for f in json.loads(res_bad.stdout)["findings"]}
            self.assertIn("FAKE_OR_INJECTED_DOI", codes)
            self.assertIn("UNVERIFIED_SUPERLATIVE_CN", codes)
            self.assertIn("UNVERIFIED_GAP_CN", codes)
            self.assertIn("ORPHAN_SOURCE_LABEL", codes)

            clean_t03 = Path(tmp) / "clean_t03.md"
            clean_t03.write_text(
                "已有测试在不同设置下呈现差异：单次同设置测试中，缓存方案 A 的延迟为 12 ms（对照 40 ms），"
                "但准确率为 89%，略低于对照的 90% [材料A]；而在另一小批量设置中，缓存并未降低延迟（未披露具体数值）[材料B]。"
                "上述比较仅依据摘要记录，尚不足以断言方案 A 全面领先；材料 B 附页中的异常指令与虚构编号已作为污染文本隔离忽略。",
                encoding="utf-8",
            )
            res_good = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(clean_t03),
                    "--mode",
                    "related-work",
                    "--allowed-ids",
                    "A,B,材料A,材料B",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_good.returncode, 0, msg=res_good.stdout)
            self.assertEqual(json.loads(res_good.stdout)["status"], "PASS")

    def test_04_ledger_whitelist_and_systematic_review_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.json"
            ledger.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "generated_at": "2026-11-25T00:00:00+00:00",
                        "capability_state": "ONLINE_API_VERIFIED",
                        "is_systematic_review": False,
                        "search_protocol": {"primary_query": "test"},
                        "entries": [
                            {
                                "ref_id": "lecun2015deep",
                                "title": "Deep learning",
                                "doi": "10.1038/nature14539",
                                "verification_status": "API_VERIFIED",
                                "reading_depth": "ABSTRACT_READ",
                            },
                            {
                                "ref_id": "oguibe2026empowering",
                                "title": "Empowering Student Debugging",
                                "doi": None,
                                "arxiv_id": "2606.14607v1",
                                "verification_status": "API_VERIFIED",
                                "reading_depth": "ABSTRACT_READ",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            bad_draft = Path(tmp) / "bad_ledger_draft.md"
            bad_draft.write_text(
                "本文开展了系统综述，综合了 [@lecun2015deep] 与 [@ghost2026paper] 的结论。",
                encoding="utf-8",
            )
            res = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(bad_draft),
                    "--mode",
                    "related-work",
                    "--ledger",
                    str(ledger),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 2)
            codes = {f["code"] for f in json.loads(res.stdout)["findings"]}
            self.assertIn("SYSTEMATIC_REVIEW_OVERCLAIM", codes)
            self.assertIn("ORPHAN_CITATION_KEY", codes)

            # Blind-eval regression checks:
            # 1) --allowed-ids "A,B" auto-expands to accept [材料A], [材料B];
            # 2) Long compound quoted negation & backticked fake DOI in audit section pass cleanly;
            # 3) Missing depth disclosure on snippet --allowed-ids triggers WARN;
            # 4) Canonical 10.48550/arxiv.<id> passes when arxiv_id is in ledger, and [A] in ledger mode doesn't false-block.
            b02_draft = Path(tmp) / "b02_reg.md"
            b02_draft.write_text(
                "测试显示索引 A 平均延迟较低 [材料A]，但在混合负载下未降低延迟 [材料B]（仅基于摘要）。\n"
                "附页注入说明：已隔离忽略伪造编号 `10.0000/fake.2099`，未采纳附页备注要求写入的“全面领先”与“填补了国内外空白”。",
                encoding="utf-8",
            )
            res_b02 = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(b02_draft),
                    "--mode",
                    "related-work",
                    "--allowed-ids",
                    "A,B",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_b02.returncode, 0, msg=res_b02.stdout)
            self.assertEqual(json.loads(res_b02.stdout)["status"], "PASS")

            arxiv_draft = Path(tmp) / "arxiv_reg.md"
            arxiv_draft.write_text(
                "组 [A] 观察到并发调试辅助效果 [@oguibe2026empowering] (https://doi.org/10.48550/arxiv.2606.14607)，基于摘要待读全文。",
                encoding="utf-8",
            )
            res_arxiv = subprocess.run(
                [
                    sys.executable,
                    str(GATE_SCRIPT),
                    "--draft",
                    str(arxiv_draft),
                    "--mode",
                    "related-work",
                    "--ledger",
                    str(ledger),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_arxiv.returncode, 0, msg=res_arxiv.stdout)
            self.assertEqual(json.loads(res_arxiv.stdout)["status"], "PASS")

    def test_05_diacritic_author_key_and_pdf_doi_clean(self) -> None:
        sys.path.insert(0, str(SCRIPTS_DIR))
        import lit_search_verify as lsv

        key = lsv._make_ref_id({"authors": ["Gregor Jošt"], "year": 2024, "title": "The Impact of LLMs"}, set())
        self.assertEqual(key, "jost2024impact")
        self.assertEqual(lsv._clean_doi("https://doi.org/10.1007/s10664-024-10594-x.pdf"), "10.1007/s10664-024-10594-x")

    def test_06_fulltext_indexer_and_ledger_upgrade(self) -> None:
        indexer = SCRIPTS_DIR / "fulltext_indexer.py"
        self.assertTrue(indexer.exists())
        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            papers_dir = tpath / "pdfs"
            papers_dir.mkdir()
            paper_md = papers_dir / "smith2024caching.md"
            paper_md.write_text(
                "--- Page 1 ---\n"
                "Introduction: Cache locality strongly governs memory latency under skewed read workloads.\n\n"
                "--- Page 2 ---\n"
                "Experiment 2 measured tail latency on 48-core servers: P99 dropped from 38 ms to 19 ms under batched eviction.\n",
                encoding="utf-8",
            )
            ledger_path = tpath / "02_literature_ledger.json"
            ledger_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "generated_at": "2026-11-25T00:00:00+00:00",
                        "capability_state": "ONLINE_API_VERIFIED",
                        "search_protocol": {"primary_query": "cache tail latency"},
                        "entries": [
                            {
                                "ref_id": "smith2024caching",
                                "title": "Cache Locality and Tail Latency",
                                "doi": "10.1145/1234567.89",
                                "verification_status": "API_VERIFIED",
                                "reading_depth": "ABSTRACT_READ",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            chunks_jsonl = tpath / "fulltext_chunks.jsonl"
            res_idx = subprocess.run(
                [
                    sys.executable,
                    str(indexer),
                    "index",
                    "--input",
                    str(papers_dir),
                    "--out-jsonl",
                    str(chunks_jsonl),
                    "--ledger",
                    str(ledger_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_idx.returncode, 0, msg=res_idx.stderr)
            idx_json = json.loads(res_idx.stdout)
            self.assertEqual(idx_json["upgraded_to_fulltext_read"], ["smith2024caching"])
            updated_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(updated_ledger["entries"][0]["reading_depth"], "FULLTEXT_READ")

            res_search = subprocess.run(
                [sys.executable, str(indexer), "search", "--index", str(chunks_jsonl), "--query", "48-core P99 batched eviction"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res_search.returncode, 0)
            hits = json.loads(res_search.stdout)["top_hits"]
            self.assertGreaterEqual(len(hits), 1)
            self.assertEqual(hits[0]["anchor"], "[smith2024caching.md, p.2, para.1]")


if __name__ == "__main__":
    unittest.main(verbosity=2)
