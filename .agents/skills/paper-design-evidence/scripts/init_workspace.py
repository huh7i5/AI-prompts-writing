#!/usr/bin/env python3
"""Initialize and inspect the standardized end-to-end paper pipeline workspace.

Supports built-in paper presets grounded in real publishing standards:
  - general    : Default cross-disciplinary workspace
  - journal_en : Compact English journal/conference paper (IEEEtran/elsarticle ready)
  - journal_zh : Chinese core journal article (ctexart + GB/T 7714 ready)
  - thesis_zh  : Chinese Master/PhD thesis (GB/T 7713.1 front/body/backmatter + ctexbook/university adapters)
  - review     : Focused or systematic literature review (FOCUSED_REVIEW inclusion/exclusion & synthesis matrix)

Zero third-party dependencies (Python 3 standard library only).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PARADIGMS = ("QUANTITATIVE", "QUALITATIVE", "ARCHIVAL_TEXTUAL", "THEORETICAL", "FOCUSED_REVIEW")
TIME_STATES = ("PRE_STUDY", "IN_PROGRESS", "POST_RESULTS")

WORKSPACE_DIRS = (
    "01_literature",
    "02_evidence",
    "03_backbone",
    "04_drafts",
    "05_audit",
    "06_submission",
)

PRESET_SPECS: dict[str, dict[str, Any]] = {
    "general": {
        "label": "通用学术论文 / General Manuscript",
        "default_paradigm": "QUANTITATIVE",
        "outline_standard": "Problem-driven IMRaD / thematic sections",
        "recommended_tex_template": "ctexart",
        "chapter_plan": [
            "00_abstract.md",
            "01_introduction.md",
            "02_methods.md",
            "03_results.md",
            "04_discussion_conclusion.md",
        ],
        "sections": [
            ("第 1 节：引言与研究问题", "研究对象、现有缺口与本文边界内贡献", "引言草稿（缺依据标 [待补]）"),
            ("第 2 节：研究设计与材料方法", "资料来源、分析条件、样本与比较基线", "方法记录与参数说明"),
            ("第 3 节：核心结果与分析", "可核查的实证发现或论证推导（含不利/边界结果）", "表格、图注与原始来源位置"),
            ("第 4 节：讨论与结论", "与既有研究比较、解释限制、适用范围与结论收窄", "限制清单与文献对照"),
        ],
        "extra_checks": [
            "核对摘要、正文、表格与图注的样本量、单位及结论强度是否同步。",
        ],
    },
    "journal_en": {
        "label": "英文期刊/会议小论文 (Journal / Conference)",
        "default_paradigm": "QUANTITATIVE",
        "outline_standard": "Compact IEEEtran / Elsevier / Springer single-contribution structure",
        "recommended_tex_template": "ieee",
        "chapter_plan": [
            "00_abstract.md",
            "01_introduction.md",
            "02_related_work.md",
            "03_methodology.md",
            "04_results.md",
            "05_discussion_conclusion.md",
        ],
        "sections": [
            ("1. Abstract & Keywords", "Problem, gap, method, 1-2 headline findings with exact units/CI, and scope boundary (<=250 words)", "Title + Abstract"),
            ("2. Introduction", "Specific gap grounded in verified citations, research question, and evidence-backed contributions", "Intro draft (no broad slogans)"),
            ("3. Related Work", "Synthesis organized by methodological differences and unresolved tensions", "Verified refs with reading_depth"),
            ("4. Methodology & Experimental Setup", "Data split fairness, baselines, parameters, metrics, and ethics/disclosure notes", "Methods + reproducibility checks"),
            ("5. Results & Tables", "Headline outcomes, exact numbers/percentage points, variance/CI, and trade-offs", "Tables, SVG/PNG figures & captions"),
            ("6. Discussion, Limitations & Conclusion", "Mechanism separation (observed vs hypothesized), scope limits, and concise takeaway", "Adverse results retained"),
        ],
        "extra_checks": [
            "No \\chapter level in IEEEtran/elsarticle; verify top headings map to \\section / \\subsection.",
            "Keep baseline comparison conditions (budget, dataset split, period) strictly matched.",
        ],
    },
    "journal_zh": {
        "label": "中文期刊小论文 (Chinese Core Journal)",
        "default_paradigm": "QUANTITATIVE",
        "outline_standard": "Chinese journal IMRaD + GB/T 7714 sequential citation style",
        "recommended_tex_template": "ctexart",
        "chapter_plan": [
            "00_abstract_zh_en.md",
            "01_intro.md",
            "02_methods.md",
            "03_results.md",
            "04_discussion_conclusion.md",
        ],
        "sections": [
            ("前置：中英文题目、摘要与关键词", "研究目的、方法要点、核心实测指标与适用边界（中文约300字 + 对应英文摘要）", "中英文摘要一致"),
            ("1 引言", "直接切入科学/工程问题，按争议或不足评述已有工作并明确本文贡献", "避免宏大开场白"),
            ("2 材料与方法", "研究对象、数据口径、纳入排除规则、测量工具或模型参数设置", "缺失参数标 [待补]"),
            ("3 结果与分析", "先核心发现后展开细节；百分比变化与百分点分清，不利结果保留", "三线表、矢量图及完整图注"),
            ("4 讨论与结论", "与既有文献对比差异、明确限制对结论外推的影响、克制总结", "资助与作者声明标待确认"),
        ],
        "extra_checks": [
            "参考文献著录须核对 GB/T 7714-2015（`gbt7714` 宏包或顺序编码制）中英文题录要素齐全。",
        ],
    },
    "thesis_zh": {
        "label": "中文硕博学位大论文 (GB/T 7713.1 Thesis)",
        "default_paradigm": "QUANTITATIVE",
        "outline_standard": "GB/T 7713.1-2006/2025 Thesis Standard (前置 -> 主体多章 -> 文献 -> 附录 -> 致谢成果)",
        "recommended_tex_template": "ctexbook",
        "chapter_plan": [
            "00_abstract_zh_en.md",
            "01_ch1_introduction.md",
            "02_ch2_literature_review.md",
            "03_ch3_study_design.md",
            "04_ch4_empirical_results.md",
            "05_ch5_conclusion_outlook.md",
        ],
        "sections": [
            ("前置部分：中英文摘要、目录与符号表", "按 GB/T 7713.1 组织中英文摘要、主要符号/缩略语说明（独创性声明与封面由学校模板生成）", "摘要数字与第3–4章严格同步"),
            ("第 1 章 绪论", "研究背景与现实/理论问题、国内外研究综述概述、研究内容、技术路线与主要创新点（预告编号）", "第1章预告的创新点须在末章闭合"),
            ("第 2 章 文献综述与理论基础", "按学派/方法争议系统梳理既有工作与局限，界定核心概念、理论假设与本文分析框架", "所有引文标明读取深度与页码锚点"),
            ("第 3 章 研究设计与研究一", "总体研究设计、数据/样本获取（标注N与排除原因）、第一个核心子研究方法与验证", "保持各章样本量口径跨章可追溯"),
            ("第 4 章 核心实证 / 拓展研究与综合讨论", "第二个核心研究或稳健性/对比实验、跨模型或跨情景权衡分析、综合局限说明", "不利结果与替代解释紧挨发现保留"),
            ("第 5 章 总结与展望（及结尾部分）", "逐条回应第1章提出的问题与创新点、研究不足与未来工作建议；后接 GB/T 7714 参考文献、附录、致谢与科研成果清单", "末章不引入正文未出现的全新数据"),
        ],
        "extra_checks": [
            "【大论文跨章闭环自查】第1章提出的每一条研究问题/创新点，必须能映射到 `03_claim_ledger.json` 并在末章给出实证回应。",
            "【跨章口径同步】若第3章调整了样本量、阈值或指标口径，必须同步排查第1章摘要、第4章汇总与第5章结论。",
            "【高校模板对接】正式提交校盲审/终稿时，可配合 `export_manuscript.py --tex-template thuthesis|pkuthss|sjtuthesis|ustcthesis` 或 `--template-tex` 对接本校模板。",
        ],
    },
    "review": {
        "label": "文献综述 / 系统综述 (Focused / Systematic Review)",
        "default_paradigm": "FOCUSED_REVIEW",
        "outline_standard": "Search scope -> inclusion/exclusion -> appraisal matrix -> thematic synthesis & conflicts",
        "recommended_tex_template": "ctexart",
        "chapter_plan": [
            "00_abstract.md",
            "01_scope_and_search.md",
            "02_evidence_synthesis.md",
            "03_debates_and_gaps.md",
            "04_conclusion.md",
        ],
        "sections": [
            ("1. 综述范围与检索策略", "核心问题、检索数据库、起止时间、中英文关键词、纳入与排除标准（区分一般综述与系统综述）", "无完整筛选记录不宣称已完成系统综述"),
            ("2. 文献筛选结果与质量评价", "实际检出与纳入篇数、证据深度分层（题录/摘要/全文比例）、研究设计异质性评估", "全文页码锚点 `[file, p.X, para.Y]`"),
            ("3. 分主题对比综合与方法争论", "围绕共识、分歧条件与相互矛盾结论的证据对比矩阵（非逐篇摘要罗列）", "来源结论与作者解释明确分开"),
            ("4. 研究空白、局限与未来议程", "基于已纳入文献的实证缺口（不得凭未读到断言无人研究）与后续验证优先级", "综述本身检索语言与时间边界限制"),
        ],
        "extra_checks": [
            "严禁对未完成 PRISMA 全流程记录的叙事性综述使用“系统综述已完成”措辞。",
            "严禁向纯文献综述或质性综述强行套用随机对照试验或单一实验 p 值模板。",
        ],
    },
}

PRESET_NAMES = tuple(PRESET_SPECS.keys())


def _norm_enum(val: str, allowed: tuple[str, ...], flag_name: str) -> str:
    norm = val.strip().upper().replace("-", "_")
    if norm not in allowed:
        raise ValueError(f"Invalid {flag_name} '{val}'. Allowed: {allowed}")
    return norm


def _norm_preset(val: str) -> str:
    norm = val.strip().lower().replace("-", "_")
    if norm not in PRESET_SPECS:
        raise ValueError(f"Invalid --preset '{val}'. Allowed: {PRESET_NAMES}")
    return norm


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def render_preset_outline(
    preset: str,
    paradigm: str,
    time_state: str,
    title: str,
    discipline: str,
) -> str:
    spec = PRESET_SPECS[preset]
    lines = [
        f"# 论文分章大纲（预设：{spec['label']}）",
        "",
        f"- **暂定题目**：{title or '{{来自 01_topic_spec 或待拟定}}'}",
        f"- **学科与文体**：{discipline or '{{学科}}'} · `{spec['outline_standard']}`",
        f"- **研究方式与当前状态**：`{paradigm}` · `{time_state}`",
        "- **一句话论文主线**：`{{在什么条件下，用什么材料/方法回答什么具体问题，边界何在}}`",
        "",
        "---",
        "",
        "## 章节安排与证据绑定（缺失部分标 `[待补]`，计划态与已完成严格分开）",
        "",
    ]
    for sec_title, reader_q, evidence_note in spec["sections"]:
        status_tag = "研究计划态 - 尚无结果" if time_state == "PRE_STUDY" else "待核对材料后起草"
        lines.extend(
            [
                f"### {sec_title}",
                f"- **本节核心任务与读者问题**：{reader_q}",
                f"- **挂载证据与边界提示**：{evidence_note}",
                "- **对应 `03_claim_ledger.json` 主张编号**：`{{C01...}}`",
                f"- **当前状态**：`{status_tag}`",
                "",
            ]
        )

    lines.extend(["---", "", "## 本论文类型专项自查清单"])
    for chk in spec["extra_checks"]:
        lines.append(f"- {chk}")
    lines.extend(["", "## 待补齐缺口清单", "- `[待补 1]`：", "- `[待补 2]`：", ""])
    return "\n".join(lines)


def cmd_init(args: argparse.Namespace) -> int:
    preset = _norm_preset(args.preset)
    preset_cfg = PRESET_SPECS[preset]

    raw_paradigm = args.paradigm if args.paradigm else preset_cfg["default_paradigm"]
    paradigm = _norm_enum(raw_paradigm, PARADIGMS, "--paradigm")
    time_state = _norm_enum(args.time_state, TIME_STATES, "--time-state")

    ws = Path(args.workspace).resolve()
    ws.mkdir(parents=True, exist_ok=True)
    for sub in WORKSPACE_DIRS:
        (ws / sub).mkdir(parents=True, exist_ok=True)

    spec_path = ws / "00_project_spec.json"
    if not spec_path.exists() or args.overwrite:
        spec = {
            "schema_version": "1.0",
            "created_at": _utc_now_iso(),
            "title_working": args.title or "",
            "discipline": args.discipline or "",
            "research_paradigm": paradigm,
            "study_time_state": time_state,
            "paper_preset": preset,
            "target_venue_or_type": args.paper_type or preset_cfg["label"],
            "outline_standard": preset_cfg["outline_standard"],
            "recommended_tex_template": preset_cfg["recommended_tex_template"],
            "chapter_plan": preset_cfg["chapter_plan"],
        }
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    ledger_path = ws / "03_backbone" / "03_claim_ledger.json"
    if not ledger_path.exists() or args.overwrite:
        skeleton_ledger = {
            "schema_version": "1.0",
            "generated_at": _utc_now_iso(),
            "research_paradigm": paradigm,
            "study_time_state": time_state,
            "paper_preset": preset,
            "one_sentence_storyline": "",
            "evidence_items": [],
            "claims": [],
        }
        ledger_path.write_text(json.dumps(skeleton_ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    outline_path = ws / "03_backbone" / "04_outline.md"
    outline_written = False
    if preset != "general" and (not outline_path.exists() or args.overwrite):
        outline_path.write_text(
            render_preset_outline(preset, paradigm, time_state, args.title or "", args.discipline or ""),
            encoding="utf-8",
        )
        outline_written = True

    print(
        json.dumps(
            {
                "action": "init",
                "workspace": str(ws),
                "paper_preset": preset,
                "paradigm": paradigm,
                "study_time_state": time_state,
                "outline_scaffolded": outline_written,
                "recommended_tex_template": preset_cfg["recommended_tex_template"],
                "created_dirs": list(WORKSPACE_DIRS),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    if not ws.exists():
        print(json.dumps({"exists": False, "workspace": str(ws), "next_station": "01_topic_literature"}, indent=2))
        return 0

    spec_file = ws / "00_project_spec.json"
    spec: dict[str, Any] = json.loads(spec_file.read_text(encoding="utf-8")) if spec_file.exists() else {}
    lit_ledger = ws / "01_literature" / "02_literature_ledger.json"
    claim_ledger = ws / "03_backbone" / "03_claim_ledger.json"
    outline_md = ws / "03_backbone" / "04_outline.md"
    draft_files = sorted(p.name for p in (ws / "04_drafts").glob("*.md")) if (ws / "04_drafts").exists() else []
    audit_files = sorted(p.name for p in (ws / "05_audit").glob("*.json")) if (ws / "05_audit").exists() else []

    claim_count = 0
    if claim_ledger.exists():
        cdata = json.loads(claim_ledger.read_text(encoding="utf-8"))
        claim_count = len(cdata.get("claims") or [])

    time_state = (spec.get("study_time_state") or "").upper()
    preset = spec.get("paper_preset") or "general"
    if not lit_ledger.exists() and claim_count == 0:
        recommended_station = "Station 01 (paper-topic-literature) or Station 02 (paper-design-evidence)"
    elif claim_count == 0 or not outline_md.exists():
        recommended_station = "Station 02 (paper-design-evidence): populate 03_claim_ledger.json & 04_outline.md"
    elif not draft_files:
        if time_state == "PRE_STUDY":
            recommended_station = (
                "Station 03 (paper-draft-polish) [PRE_STUDY_LOCK]: may only draft proposal/intro/planned-methods "
                "with [待补] placeholders; NEVER draft completed Results or Conclusion until real data arrives."
            )
        else:
            recommended_station = "Station 03 (paper-draft-polish): draft sections from locked claim ledger"
    else:
        recommended_station = "Station 04 (paper-audit-submission): run cross-section numeric & citation audit"

    report = {
        "exists": True,
        "workspace": str(ws),
        "paper_preset": preset,
        "project_spec": spec,
        "artifacts": {
            "literature_ledger_present": lit_ledger.exists(),
            "claim_ledger_present": claim_ledger.exists(),
            "registered_claims_count": claim_count,
            "outline_present": outline_md.exists(),
            "draft_sections": draft_files,
            "audit_reports": audit_files,
        },
        "recommended_next_step": recommended_station,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize or inspect a paper pipeline workspace.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create standardized paper_workspace directory structure.")
    p_init.add_argument("--workspace", required=True, help="Target workspace directory path.")
    p_init.add_argument(
        "--preset",
        default="general",
        help="Built-in paper preset: general, journal_en, journal_zh, thesis_zh, review.",
    )
    p_init.add_argument("--paradigm", default="", help="Paradigm (defaults to preset recommendation if omitted).")
    p_init.add_argument("--time-state", default="PRE_STUDY", help="Timeline state (case/hyphen insensitive).")
    p_init.add_argument("--discipline", default="")
    p_init.add_argument("--paper-type", default="")
    p_init.add_argument("--title", default="")
    p_init.add_argument("--overwrite", action="store_true")

    p_status = sub.add_parser("status", help="Inspect existing artifacts and determine current pipeline stage.")
    p_status.add_argument("--workspace", required=True, help="Workspace directory path.")

    args = parser.parse_args()
    if args.command == "init":
        return cmd_init(args)
    return cmd_status(args)


if __name__ == "__main__":
    raise SystemExit(main())
