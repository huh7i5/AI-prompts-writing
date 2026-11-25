#!/usr/bin/env python3
"""Deterministic quality & boundary gate for Station 02 (paper-design-evidence).

Validates both:
A) Structured 03_claim_ledger.json contracts:
   - SUPPORTED claims must bind >=1 evidence_id.
   - PRE_STUDY workspaces must not contain SUPPORTED empirical findings.
   - Claims flagged has_adverse_or_counterexample=true must specify scope_and_limitations.
   - Every claim must list target_sections for downstream sync tracking.
B) Markdown drafts/outputs for tasks 3.1-4.3:
   - Paradigm mismatch guard (blocks demanding p-values / RCTs / sample sizes on theoretical or archival studies, e.g. T10).
   - Pre-study fabricated completion guard (blocks claiming experiments/approvals are completed when --time-state pre-study).
   - Formal-verification overclaim guard in task 4.2 (blocks claiming full formal machine proof without prover logs).
   - Fake figure-generation claim guard & caption completeness warnings in task 4.3.

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

ALLOWED_PARADIGMS = {"QUANTITATIVE", "QUALITATIVE", "ARCHIVAL_TEXTUAL", "THEORETICAL", "FOCUSED_REVIEW"}
ALLOWED_TIME_STATES = {"PRE_STUDY", "IN_PROGRESS", "POST_RESULTS"}
ALLOWED_TASKS = {"3.1", "3.2", "3.3", "3.4", "3.5", "4.1", "4.2", "4.3"}
ALLOWED_SUPPORT_LEVELS = {
    "SUPPORTED",
    "CONSISTENT_WITH",
    "HYPOTHESIS_UNTESTED",
    "INSUFFICIENT_EVIDENCE",
    "REFUTED_OR_COUNTEREXAMPLE",
}

NEGATION_CORE = (
    r"(不|未|无需|不需要|不必|不适用|并非|不能|不可|切勿|严禁|不要求|不强求|尚未|"
    r"拒绝|拦截|删去|剔除|不得|不能按|原话|"
    r"not required|unnecessary|not applicable|do not|cannot|without claiming|haven't|rejected|refused)"
)
NEGATION_WINDOW_REGEX = re.compile(NEGATION_CORE + r"[^。；！？!?\n]{0,20}$", re.IGNORECASE)
NEGATION_ANYWHERE_REGEX = re.compile(NEGATION_CORE, re.IGNORECASE)

# Demands that are invalid when imposed on pure theoretical proofs or archival close reading (e.g. T10)
STAT_EXPERIMENT_DEMAND_REGEX = re.compile(
    r"(需补充样本量|请提供样本量|建议增加随机对照|必须报告\s*p\s*值|计算统计显著性|样本量不足|"
    r"\bprovide sample size\b|\brun a randomized controlled trial\b|\breport p-values\b)",
    re.IGNORECASE,
)

FORMAL_VERIFICATION_OVERCLAIM_REGEX = re.compile(
    r"(已完成完整形式化验证|已通过形式化机器证明|完成了形式化证明核验|"
    r"\bcompleted full formal verification\b|\bformally verified in Coq/Lean\b)",
    re.IGNORECASE,
)

PRE_STUDY_COMPLETED_CLAIM_REGEX = re.compile(
    r"(实验结果表明|我们的实验证明了|数据分析显示显著|已获得伦理委员会批准|"
    r"\bour experiments demonstrate\b|\bdata analysis reveals significant\b)",
    re.IGNORECASE,
)

FAKE_PLOT_RENDERED_REGEX = re.compile(
    r"(已为您生成高清图表文件|图像文件已绘制完成|见已生成的图片|"
    r"\bfigure image has been generated\b|\bplot file rendered successfully\b)",
    re.IGNORECASE,
)

CAPTION_UNIT_REGEX = re.compile(r"(单位|unit|%|ms|kg|Hz|°C|分|秒|米|元)", re.IGNORECASE)
CAPTION_SAMPLE_REGEX = re.compile(r"(样本量|人数|\bN\s*=|\bn\s*=|\bn_\d+\s*=|待补.*样本|待补.*人数)", re.IGNORECASE)
CAPTION_ERROR_REGEX = re.compile(
    r"(误差|标准差|标准误|置信区间|四分位|\bSD\b|\bSE\b|\bCI\b|\bIQR\b|待补.*误差)", re.IGNORECASE
)


def _is_inside_quotes_or_code(line: str, match_start: int, match_end: int) -> bool:
    before = line[:match_start]
    after = line[match_end:]
    if before.count("`") % 2 == 1 and "`" in after:
        return True
    for open_q, close_q in (("“", "”"), ("「", "」"), ("‘", "’"), ('"', '"'), ("'", "'")):
        if open_q in before and close_q in after:
            return True
    return False


def _is_negated(line: str, match_start: int, match_end: int | None = None) -> bool:
    same_sentence_prefix = re.split(r"[。；！？!?\n]", line[:match_start])[-1]
    prefix = same_sentence_prefix[-26:]
    if NEGATION_WINDOW_REGEX.search(prefix):
        return True
    end_pos = match_end if match_end is not None else match_start
    if _is_inside_quotes_or_code(line, match_start, end_pos):
        if NEGATION_ANYWHERE_REGEX.search(same_sentence_prefix):
            return True
    return False


def validate_claim_ledger(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    time_state = (ledger.get("study_time_state") or "").strip().upper().replace("-", "_")
    paradigm = (ledger.get("research_paradigm") or "").strip().upper().replace("-", "_")
    storyline = (ledger.get("one_sentence_storyline") or "").strip()

    if time_state not in ALLOWED_TIME_STATES:
        findings.append(
            {
                "severity": "BLOCKER",
                "code": "INVALID_LEDGER_TIME_STATE",
                "line": None,
                "detail": f"Invalid study_time_state '{ledger.get('study_time_state')}'; expected {sorted(ALLOWED_TIME_STATES)}.",
            }
        )
    if paradigm not in ALLOWED_PARADIGMS:
        findings.append(
            {
                "severity": "BLOCKER",
                "code": "INVALID_LEDGER_PARADIGM",
                "line": None,
                "detail": f"Invalid research_paradigm '{ledger.get('research_paradigm')}'; expected {sorted(ALLOWED_PARADIGMS)}.",
            }
        )

    evidence_ids: set[str] = set()
    for e_idx, ev in enumerate(ledger.get("evidence_items") or [], start=1):
        if not isinstance(ev, dict) or not ev.get("evidence_id") or not ev.get("source_location"):
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "INVALID_EVIDENCE_ITEM",
                    "line": None,
                    "detail": f"evidence_items[{e_idx}] must include non-empty 'evidence_id' and 'source_location'.",
                }
            )
            continue
        evidence_ids.add(ev["evidence_id"])

    claims = ledger.get("claims")
    if not isinstance(claims, list) or len(claims) == 0:
        findings.append(
            {
                "severity": "WARN",
                "code": "EMPTY_CLAIM_LEDGER",
                "line": None,
                "detail": "Claim ledger currently has 0 claims registered.",
            }
        )
        return findings

    if not storyline:
        findings.append(
            {
                "severity": "WARN",
                "code": "EMPTY_STORYLINE",
                "line": None,
                "detail": "Claim ledger has claims but 'one_sentence_storyline' is empty.",
            }
        )

    seen_ids: set[str] = set()
    for idx, c in enumerate(claims, start=1):
        cid = c.get("claim_id") or f"index_{idx}"
        if cid in seen_ids:
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "DUPLICATE_CLAIM_ID",
                    "line": None,
                    "detail": f"Duplicate claim_id '{cid}' in 03_claim_ledger.json.",
                }
            )
        seen_ids.add(cid)

        level = c.get("support_level")
        if level not in ALLOWED_SUPPORT_LEVELS:
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "INVALID_SUPPORT_LEVEL",
                    "line": None,
                    "detail": f"Claim '{cid}' has invalid support_level '{level}'; allowed: {sorted(ALLOWED_SUPPORT_LEVELS)}.",
                }
            )
        bound_ev = c.get("bound_evidence_ids") or []
        scope = (c.get("scope_and_limitations") or "").strip()
        targets = c.get("target_sections") or []
        has_adverse = bool(c.get("has_adverse_or_counterexample", False))

        if level == "SUPPORTED" and not bound_ev:
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "UNGROUNDED_SUPPORTED_CLAIM",
                    "line": None,
                    "detail": f"Claim '{cid}' is marked SUPPORTED but binds zero evidence_ids.",
                }
            )

        if time_state == "PRE_STUDY" and level == "SUPPORTED" and paradigm != "THEORETICAL":
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "PRE_STUDY_FABRICATED_SUPPORT",
                    "line": None,
                    "detail": (
                        f"Workspace is in PRE_STUDY state, so empirical claim '{cid}' cannot be marked SUPPORTED "
                        "(use HYPOTHESIS_UNTESTED)."
                    ),
                }
            )

        if evidence_ids:
            missing_ev = [eid for eid in bound_ev if eid not in evidence_ids]
            if missing_ev:
                findings.append(
                    {
                        "severity": "BLOCKER",
                        "code": "UNKNOWN_EVIDENCE_ID_REF",
                        "line": None,
                        "detail": f"Claim '{cid}' references unregistered evidence_ids: {missing_ev}.",
                    }
                )

        if has_adverse and len(scope) < 5:
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "UNDISCLOSED_COUNTEREXAMPLE_OR_TRADEOFF",
                    "line": None,
                    "detail": (
                        f"Claim '{cid}' has_adverse_or_counterexample=true but 'scope_and_limitations' is empty."
                    ),
                }
            )

        if not targets:
            findings.append(
                {
                    "severity": "WARN",
                    "code": "MISSING_TARGET_SECTIONS",
                    "line": None,
                    "detail": f"Claim '{cid}' has empty target_sections; cross-section sync tracking needs anchors.",
                }
            )

    return findings


def validate_draft_text(
    text: str,
    tasks: set[str],
    paradigm: str,
    time_state: str,
    prover_verified: bool = False,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lines = text.splitlines()
    norm_paradigm = paradigm.upper().replace("-", "_")
    norm_time = time_state.upper().replace("-", "_")

    for idx, line in enumerate(lines, start=1):
        # 1. Paradigm mismatch check (e.g. T10 theoretical proof or archival close reading)
        if norm_paradigm in ("THEORETICAL", "ARCHIVAL_TEXTUAL"):
            for m in STAT_EXPERIMENT_DEMAND_REGEX.finditer(line):
                if not _is_negated(line, m.start(), m.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "PARADIGM_MISMATCH_REQUIREMENT",
                            "line": idx,
                            "detail": (
                                f"Imposed statistical/RCT requirement '{m.group(0)}' on a {norm_paradigm} study."
                            ),
                        }
                    )

        # 2. Formal verification overclaim check (Task 4.2 / T10)
        if not prover_verified:
            for m in FORMAL_VERIFICATION_OVERCLAIM_REGEX.finditer(line):
                if not _is_negated(line, m.start(), m.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "UNVERIFIED_FORMAL_PROOF_CLAIM",
                            "line": idx,
                            "detail": (
                                f"Claimed full formal verification ('{m.group(0)}') without machine prover execution."
                            ),
                        }
                    )

        # 3. Pre-study fabricated results check (Tasks 3.1 / 3.2 / 3.4 / 3.5 / 4.3)
        if norm_time == "PRE_STUDY":
            for m in PRE_STUDY_COMPLETED_CLAIM_REGEX.finditer(line):
                if not _is_negated(line, m.start(), m.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "PRE_STUDY_FABRICATED_COMPLETION",
                            "line": idx,
                            "detail": (
                                f"Pre-study plan/outline contains completed-finding phrasing ('{m.group(0)}')."
                            ),
                        }
                    )

        # 4. Task 4.3 fake rendered plot claim
        if "4.3" in tasks:
            for m in FAKE_PLOT_RENDERED_REGEX.finditer(line):
                if not _is_negated(line, m.start(), m.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "FAKE_PLOT_RENDER_CLAIM",
                            "line": idx,
                            "detail": f"Claimed image file was rendered ('{m.group(0)}') during caption/layout planning.",
                        }
                    )

    if "4.3" in tasks and text.strip():
        missing_parts: list[str] = []
        if not CAPTION_UNIT_REGEX.search(text):
            missing_parts.append("unit (单位)")
        if not CAPTION_SAMPLE_REGEX.search(text):
            missing_parts.append("sample size (N/n/样本量)")
        if not CAPTION_ERROR_REGEX.search(text):
            missing_parts.append("error definition (SD/SE/CI/误差含义)")
        if missing_parts:
            findings.append(
                {
                    "severity": "WARN",
                    "code": "CAPTION_MISSING_SCOPE_ELEMENTS",
                    "line": None,
                    "detail": f"Task 4.3 caption output is missing scope elements: {', '.join(missing_parts)}.",
                }
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Station 02 deterministic design & evidence quality gate.")
    parser.add_argument("--draft", default="", help="Optional Markdown output file for tasks 3.1-4.3.")
    parser.add_argument(
        "--task",
        default="4.2",
        help="Active Station 02 sub-task(s), comma-separated (e.g. '4.2' or '3.4,4.3').",
    )
    parser.add_argument(
        "--paradigm",
        default="QUANTITATIVE",
        help="Study paradigm (case/hyphen insensitive: QUANTITATIVE, QUALITATIVE, ARCHIVAL_TEXTUAL, THEORETICAL, FOCUSED_REVIEW).",
    )
    parser.add_argument(
        "--time-state",
        default="POST_RESULTS",
        help="Timeline state (case/hyphen insensitive: PRE_STUDY, IN_PROGRESS, POST_RESULTS).",
    )
    parser.add_argument("--claim-ledger", default="", help="Optional path to 03_claim_ledger.json to validate.")
    parser.add_argument("--prover-verified", action="store_true", help="Set only if an interactive theorem prover ran.")
    parser.add_argument("--json-out", default="", help="Optional path to save JSON gate report.")
    args = parser.parse_args()

    tasks = {t.strip() for t in args.task.split(",") if t.strip()}
    unknown_tasks = tasks - ALLOWED_TASKS
    if unknown_tasks:
        raise SystemExit(f"Unknown --task value(s): {sorted(unknown_tasks)}. Allowed: {sorted(ALLOWED_TASKS)}")

    norm_paradigm = args.paradigm.strip().upper().replace("-", "_")
    if norm_paradigm not in ALLOWED_PARADIGMS:
        raise SystemExit(f"Unknown --paradigm '{args.paradigm}'. Allowed: {sorted(ALLOWED_PARADIGMS)}")

    norm_time = args.time_state.strip().upper().replace("-", "_")
    if norm_time not in ALLOWED_TIME_STATES:
        raise SystemExit(f"Unknown --time-state '{args.time_state}'. Allowed: {sorted(ALLOWED_TIME_STATES)}")

    findings: list[dict[str, Any]] = []
    if args.claim_ledger:
        ledger_data = json.loads(Path(args.claim_ledger).read_text(encoding="utf-8"))
        findings.extend(validate_claim_ledger(ledger_data))

    if args.draft:
        draft_text = Path(args.draft).read_text(encoding="utf-8")
        findings.extend(
            validate_draft_text(
                text=draft_text,
                tasks=tasks,
                paradigm=norm_paradigm,
                time_state=norm_time,
                prover_verified=args.prover_verified,
            )
        )

    blocker_count = sum(1 for f in findings if f["severity"] == "BLOCKER")
    warn_count = sum(1 for f in findings if f["severity"] == "WARN")
    status = "BLOCKED" if blocker_count > 0 else ("WARN" if warn_count > 0 else "PASS")

    report = {
        "station": "02_design_evidence",
        "tasks": sorted(tasks),
        "paradigm": norm_paradigm,
        "time_state": norm_time,
        "status": status,
        "blocker_count": blocker_count,
        "warn_count": warn_count,
        "findings": findings,
    }
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if status == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
