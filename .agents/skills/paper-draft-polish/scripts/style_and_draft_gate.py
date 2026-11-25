#!/usr/bin/env python3
"""Deterministic quality, style, and numeric-fidelity gate for Station 03 (paper-draft-polish).

Checks:
1. AI-slop & outline-colon templating linter (blocks childish clichés like '万能钥匙', '赋能...跃升',
   colloquial asides, dense '短标签：' bullet-prose, mechanical '首先...其次...最后' chains).
2. Defensive apology & unsupported absolute overclaim guard (blocks hollow apologies like '粗浅的尝试/请读者包涵'
   and ungrounded '全面领先/彻底解决', with same-clause negation & quotation safety).
3. Source-text numeric fidelity guard (--source-text): verifies all numbers/units in the original paragraph
   are preserved during polishing/editing/translation (6.2, 6.3, 6.5, 6.6).
4. Pipeline ledger locks (--claim-ledger / --lit-ledger): blocks drafting completed Results/Conclusion
   when study_time_state == PRE_STUDY, and blocks orphan [@cite_key] citations.
5. Grammar-only strictness guard (--mode grammar-only): flags full-paragraph rewrites when no error table
   or standard '未发现语法、拼写或格式错误' verdict is present.

Exit codes:
  0 -> PASS or WARN
  2 -> BLOCKED
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

NEGATION_CORE = (
    r"(不|未|并非|不能|不可|切勿|严禁|避免|删去|删除|去掉|去除|剔除|原句|原文|改为|替换为|"
    r"不足以|尚不能|无法|未采纳|不采用|不保留|"
    r"removed|deleted|avoid|do not|cannot|instead of|original)"
)
NEGATION_WINDOW_REGEX = re.compile(NEGATION_CORE + r"[^。；！？!?\n]{0,22}$", re.IGNORECASE)
NEGATION_ANYWHERE_REGEX = re.compile(NEGATION_CORE, re.IGNORECASE)

AI_SLOP_BLOCKERS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "AI_CLICHE_METAPHOR",
        re.compile(r"(万能钥匙|定海神针|这下可省心了|插上了腾飞的翅膀)"),
        "Remove colloquial/childish cliché or aside.",
    ),
    (
        "AI_BUZZWORD_STACK",
        re.compile(r"(赋能.{0,10}跃升|构建了?多维协同|多维协同(?:机制|优化|赋能|体系|框架)|全方位多层次赋能|实现了?质的飞跃)"),
        "Replace hollow buzzword stacking with concrete operational description.",
    ),
    (
        "DEFENSIVE_HOLLOW_APOLOGY",
        re.compile(r"(粗浅的尝试|恳请读者包涵|请读者批评指正|由于(?:作者|笔者|本人)水平有限|抛砖引玉)"),
        "Remove hollow defensive apology; keep only substantive methodological limitations.",
    ),
    (
        "UNSUPPORTED_ABSOLUTE_OVERCLAIM",
        re.compile(
            r"(在所有任务上全面领先|全面领先|彻底解决了?所有|彻底解决.{0,8}问题|填补了.{0,8}空白|"
            r"\boutperforms in all tasks\b|\bcompletely solves all\b)",
            re.IGNORECASE,
        ),
        "Narrow absolute superiority/completion claim to actual measured conditions.",
    ),
]

AI_SLOP_WARNINGS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "BOILERPLATE_OPENING_CLOSING",
        re.compile(r"(在当今.{0,16}(?:飞速发展|日新月异)的背景下|综上所述，总而言之|具有很重要的重要意义)"),
        "Trim empty transitional boilerplate or redundant repetition.",
    ),
    (
        "RIGID_FIRST_SECOND_FINALLY",
        re.compile(r"首先[，,].{4,120}其次[，,].{4,120}(?:最后|再次)[，,]"),
        "Avoid mechanical '首先—其次—最后' triad within a single paragraph; connect via real logic.",
    ),
]

DENSE_LABEL_COLON_REGEX = re.compile(r"(?:^|[。；！\n])\s*[\u4e00-\u9fff]{2,5}：")
CITE_KEY_REGEX = re.compile(r"\[@([A-Za-z0-9_:-]+)\]")
NUMBER_TOKEN_REGEX = re.compile(r"(?<![A-Za-z0-9_])(\d+(?:\.\d+)?(?:\s*(?:%|ms|s|kg|Hz|万元|元|人|封|个百分点))?)")

PROSE_SECTION_STOP_HEADERS = re.compile(
    r"^(?:#{1,3}|\*\*)\s*(?:(?:[二三四234][、.\s]|第[二三四]部分[：:\s])\s*)?"
    r"(?:关键修改|修改对照|修改说明|主要修改|关键写作判断|所用证据|来源与|待作者|待核实|术语与歧义|"
    r"Key Changes|Revision Notes|Verification|Items to Confirm)",
    re.IGNORECASE,
)


def _extract_primary_prose_zone(full_text: str) -> list[tuple[int, str]]:
    """Separate Section 1 (deliverable prose/revision) from Section 2+ (audit/explanation notes)
    so quoted original errors in '原句 -> 改句' tables never trigger false positives on clean revisions.
    """
    zone: list[tuple[int, str]] = []
    for idx, line in enumerate(full_text.splitlines(), start=1):
        if idx > 1 and PROSE_SECTION_STOP_HEADERS.search(line.strip()):
            break
        zone.append((idx, line))
    return zone


def _is_inside_quotes_or_code(line: str, match_start: int, match_end: int) -> bool:
    before = line[:match_start]
    after = line[match_end:]
    if before.count("`") % 2 == 1 and "`" in after:
        return True
    for open_q, close_q in (("“", "”"), ("「", "」"), ("‘", "’"), ('"', '"'), ("'", "'")):
        if open_q in before and close_q in after:
            return True
    return False


def _is_negated_or_meta(line: str, match_start: int, match_end: int) -> bool:
    # Skip markdown table rows comparing 原句 | 改句 when cell 1 quotes the bad original
    if line.lstrip().startswith("|") and ("原句" in line or line.count("|") >= 3):
        first_pipe = line.find("|")
        second_pipe = line.find("|", first_pipe + 1)
        if 0 <= first_pipe < match_start < second_pipe:
            return True
    if re.match(r"^\s*[-*]?\s*\**(?:原句|原文|问题|Original)\**[:：]", line):
        return True
    same_clause = re.split(r"[。；！？!?\n]", line[:match_start])[-1]
    if NEGATION_WINDOW_REGEX.search(same_clause[-28:]):
        return True
    if _is_inside_quotes_or_code(line, match_start, match_end):
        if NEGATION_ANYWHERE_REGEX.search(same_clause):
            return True
    return False


def _extract_core_numbers(text: str) -> set[str]:
    nums: set[str] = set()
    # Strip markdown headers/numbering like "1. " or "## 1" at line starts first
    cleaned_lines = [re.sub(r"^\s*(?:#+\s*)?\d+[.)、]\s*", "", ln) for ln in text.splitlines()]
    body = "\n".join(cleaned_lines)
    for raw in re.findall(r"(?<![A-Za-z0-9_.\-])\d+(?:\.\d+)?%?", body):
        nums.add(raw)
    return nums


def run_style_and_draft_gate(
    draft_text: str,
    mode: str,
    section: str,
    source_text: str | None,
    claim_ledger: dict[str, Any] | None,
    lit_ledger: dict[str, Any] | None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    prose_lines = _extract_primary_prose_zone(draft_text)
    prose_only_text = "\n".join(ln for _, ln in prose_lines)

    # Mode 6.4 grammar-only check
    if mode == "grammar-only":
        no_err_phrase = "未发现语法、拼写或格式错误" in draft_text or "No grammar, spelling, or formatting errors" in draft_text
        has_err_columns = ("修正句" in draft_text and "错误类型" in draft_text) or ("Correction" in draft_text and "Error" in draft_text)
        if not no_err_phrase and not has_err_columns:
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "GRAMMAR_ONLY_SCOPE_VIOLATION",
                    "line": 1,
                    "detail": (
                        "Task 6.4 (grammar-only) must either reply '未发现语法、拼写或格式错误' or list "
                        "'原句 | 修正句 | 错误类型 | 说明' without stylistic rewriting."
                    ),
                }
            )
        return _finalize(mode, findings)

    # 1. Pipeline Claim Ledger lock check
    if claim_ledger is not None:
        t_state = (claim_ledger.get("study_time_state") or "").upper().replace("-", "_")
        if t_state == "PRE_STUDY" and section.lower() in ("results", "discussion", "conclusion"):
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "PRE_STUDY_SECTION_LOCK",
                    "line": None,
                    "detail": (
                        f"Workspace is in PRE_STUDY state; drafting completed '{section}' prose is blocked "
                        "until empirical results exist."
                    ),
                }
            )

    # 2. Pipeline Literature Ledger citation whitelist check
    if lit_ledger is not None:
        valid_refs = {
            e.get("ref_id") for e in (lit_ledger.get("entries") or []) if isinstance(e, dict) and e.get("ref_id")
        }
        for line_no, line in prose_lines:
            for ckey in CITE_KEY_REGEX.findall(line):
                if ckey not in valid_refs:
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "UNREGISTERED_DRAFT_CITATION",
                            "line": line_no,
                            "detail": f"Citation '[@{ckey}]' in prose is not in 02_literature_ledger.json.",
                        }
                    )

    # 3. Scan primary deliverable prose zone for AI-slop, defensive apologies, and absolute overclaims
    dense_colon_hits = 0
    for line_no, line in prose_lines:
        for code, pattern, hint in AI_SLOP_BLOCKERS:
            for m in pattern.finditer(line):
                if not _is_negated_or_meta(line, m.start(), m.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": code,
                            "line": line_no,
                            "detail": f"Found '{m.group(0)}' in deliverable prose. {hint}",
                        }
                    )
        for code, pattern, hint in AI_SLOP_WARNINGS:
            for m in pattern.finditer(line):
                if not _is_negated_or_meta(line, m.start(), m.end()):
                    findings.append(
                        {
                            "severity": "WARN",
                            "code": code,
                            "line": line_no,
                            "detail": f"Found '{m.group(0)}'. {hint}",
                        }
                    )
        if not line.lstrip().startswith(("#", "-", "*", "|")):
            dense_colon_hits += len(DENSE_LABEL_COLON_REGEX.findall(line))

    if mode in ("polish", "anti-slop", "anti-defensive") and dense_colon_hits >= 2:
        findings.append(
            {
                "severity": "BLOCKER",
                "code": "OUTLINE_COLON_PROSE_SLOP",
                "line": None,
                "detail": (
                    f"Detected {dense_colon_hits} '短标签：' outline-style headers inside body prose; "
                    "rewrite into connected sentences with explicit logical relations."
                ),
            }
        )

    # 4. Source numeric fidelity check for revision/translation modes (6.2, 6.3, 6.5, 6.6)
    if source_text and mode in ("polish", "anti-slop", "anti-defensive", "translate"):
        src_nums = _extract_core_numbers(source_text)
        dst_nums = _extract_core_numbers(prose_only_text)
        missing_nums = sorted(src_nums - dst_nums)
        if missing_nums:
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "SOURCE_NUMBER_DROPPED_OR_ALTERED",
                    "line": None,
                    "detail": (
                        f"Original numbers {missing_nums} from source text are missing in revised prose; "
                        "never silently alter or drop empirical numbers during revision/translation."
                    ),
                }
            )

    return _finalize(mode, findings)


def _finalize(mode: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = sum(1 for f in findings if f["severity"] == "BLOCKER")
    warns = sum(1 for f in findings if f["severity"] == "WARN")
    status = "BLOCKED" if blockers > 0 else ("WARN" if warns > 0 else "PASS")
    return {
        "station": "03_draft_polish",
        "mode": mode,
        "status": status,
        "blocker_count": blockers,
        "warn_count": warns,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Station 03 deterministic style, anti-slop & numeric fidelity gate.")
    parser.add_argument("--draft", required=True, help="Path to drafted/revised Markdown output.")
    parser.add_argument(
        "--mode",
        default="polish",
        choices=["draft", "structure", "polish", "anti-slop", "grammar-only", "anti-defensive", "translate", "worklog"],
    )
    parser.add_argument(
        "--section",
        default="general",
        help="Target manuscript section when --mode draft (e.g., intro, methods, results, discussion, conclusion, abstract).",
    )
    parser.add_argument("--source-text", default="", help="Optional path to original unedited text to verify number preservation.")
    parser.add_argument("--source-inline", default="", help="Optional inline original text string to verify number preservation.")
    parser.add_argument("--claim-ledger", default="", help="Optional path to 03_claim_ledger.json.")
    parser.add_argument("--lit-ledger", default="", help="Optional path to 02_literature_ledger.json.")
    parser.add_argument("--json-out", default="", help="Optional JSON report path.")
    args = parser.parse_args()

    draft_text = Path(args.draft).read_text(encoding="utf-8")
    source_text = (
        Path(args.source_text).read_text(encoding="utf-8")
        if args.source_text
        else (args.source_inline if args.source_inline else None)
    )
    claim_ledger = json.loads(Path(args.claim_ledger).read_text(encoding="utf-8")) if args.claim_ledger else None
    lit_ledger = json.loads(Path(args.lit_ledger).read_text(encoding="utf-8")) if args.lit_ledger else None

    report = run_style_and_draft_gate(
        draft_text=draft_text,
        mode=args.mode.lower(),
        section=args.section.lower(),
        source_text=source_text,
        claim_ledger=claim_ledger,
        lit_ledger=lit_ledger,
    )
    if args.json_out:
        out_p = Path(args.json_out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
