#!/usr/bin/env python3
"""Cross-section & cross-version numeric and sample-size consistency scanner (Station 04).

Extracts sample sizes (N/n, 纳入X人, 样本量X, X participants) and unit-bearing quantities
(ms, %, 万元, 元, 万吨, etc.) across multiple files or labeled blocks inside a single file
(e.g., 摘要 / 方法 / 表1 / 接收稿 / 校样), flagging potential cross-location discrepancies
such as T06 (102 vs 120 vs 200) and T12 (30 vs 300).

Zero third-party dependencies (Python 3 standard library only).
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

BLOCK_HEADER_REGEX = re.compile(
    r"^\s*(?:#+\s*|\*\*)?((?:待查|原稿|修订)?(?:接收稿|校样|摘要|引言|方法|结果|讨论|结论|正文|评审意见|意见|反馈|表\s*\d+|图\s*\d+|图注\s*[A-Za-z0-9]*|"
    r"R\d+|Abstract|Methods?|Results?|Discussion|Conclusion|Table\s*\d+|Figure\s*\d+|Proof|Accepted)[^：:写\n]{0,16})(?:[：:]|写[‘“\"])",
    re.IGNORECASE,
)

SAMPLE_SIZE_PATTERNS = [
    re.compile(r"(?:纳入|招募|访谈了?|调查了?|收集了?|共|对|也是|仍是|仍为)\s*(\d+)\s*(?:名|位|例|人|个样本|份)"),
    re.compile(r"(\d+)\s*个(?:厂区|班级|小组|社区|站点|中心|受试组)"),
    re.compile(r"样本量(?:为|是|:|：)?\s*(\d+)"),
    re.compile(r"\b([Nn])\s*=\s*(\d+)\b"),
    re.compile(r"\b(\d+)\s+(?:participants|subjects|patients|students|respondents|sites)\b", re.IGNORECASE),
]

CJK_AND_SYMBOL_UNIT_REGEX = re.compile(
    r"(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)\s*(个百分点|%|万元|亿元|元/吨|元每吨|万吨|元|吨|毫秒|秒)"
)
ASCII_UNIT_REGEX = re.compile(
    r"(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)\s*(ms|s|kg|Hz)(?![A-Za-z])",
    re.IGNORECASE,
)
PER_TON_PREFIX_REGEX = re.compile(r"每吨(?:补助|成本|费用|价格)?(?:为|按)?\s*(\d+(?:\.\d+)?)\s*元")


def _normalize_unit(u: str) -> str:
    low = u.lower()
    if low == "毫秒":
        return "ms"
    if low == "秒":
        return "s"
    if low == "元每吨":
        return "元/吨"
    return u


def parse_blocks_from_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    blocks: list[dict[str, Any]] = []
    current_label = path.stem

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        # Split inline multi-sentence labeled snippets like "结果：...。摘要：...。" or "方法第1段：纳入102人。表1：样本量120。"
        segments = re.split(
            r"(?<=[。！？；;])\s*(?=(?:待查|原稿|修订)?(?:接收稿|校样|摘要|方法|结果|讨论|结论|正文|评审意见|R\d+|表\s*\d+|图注)[^：:写\n]{0,12}(?:[：:]|写[‘“\"]))",
            line,
        )
        for seg in segments:
            m = BLOCK_HEADER_REGEX.match(seg)
            if m:
                current_label = f"{path.name}:{m.group(1).strip()}"
            blocks.append({"location": current_label, "line": line_no, "text": seg})
    return blocks


def analyze_blocks(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    sample_mentions: list[dict[str, Any]] = []
    unit_groups: dict[str, list[dict[str, Any]]] = {}

    for blk in blocks:
        seg = blk["text"]
        loc = blk["location"]
        lno = blk["line"]

        for pat in SAMPLE_SIZE_PATTERNS:
            for m in pat.finditer(seg):
                val_str = m.group(2) if m.lastindex == 2 else m.group(1)
                sample_mentions.append(
                    {
                        "value": int(val_str),
                        "location": loc,
                        "line": lno,
                        "snippet": m.group(0),
                    }
                )

        per_ton_spans: list[tuple[int, int]] = []
        for pm in PER_TON_PREFIX_REGEX.finditer(seg):
            per_ton_spans.append(pm.span())
            unit_groups.setdefault("元/吨", []).append(
                {"value": float(pm.group(1)), "raw": pm.group(0), "location": loc, "line": lno}
            )

        for um in CJK_AND_SYMBOL_UNIT_REGEX.finditer(seg):
            if any(s <= um.start() and um.end() <= e for s, e in per_ton_spans):
                continue
            val = float(um.group(1))
            unit = _normalize_unit(um.group(2))
            unit_groups.setdefault(unit, []).append(
                {"value": val, "raw": um.group(0), "location": loc, "line": lno}
            )

        for am in ASCII_UNIT_REGEX.finditer(seg):
            val = float(am.group(1))
            unit = _normalize_unit(am.group(2))
            unit_groups.setdefault(unit, []).append(
                {"value": val, "raw": am.group(0), "location": loc, "line": lno}
            )

    distinct_samples = sorted({item["value"] for item in sample_mentions})
    alerts: list[dict[str, Any]] = []
    if len(distinct_samples) > 1:
        alerts.append(
            {
                "code": "POTENTIAL_SAMPLE_SIZE_DISCREPANCY",
                "distinct_values": distinct_samples,
                "message": (
                    f"Detected multiple sample-size numbers across locations: {distinct_samples}. "
                    "Verify whether these represent total vs subgroup vs conflicting versions; never average or pick one silently."
                ),
                "occurrences": sample_mentions,
            }
        )

    unit_variations: dict[str, Any] = {}
    for unit, items in unit_groups.items():
        vals = sorted({x["value"] for x in items})
        unit_variations[unit] = {"distinct_values": vals, "occurrences": items}

    return {
        "total_blocks_scanned": len(blocks),
        "sample_size_mentions": sample_mentions,
        "distinct_sample_sizes": distinct_samples,
        "has_sample_size_variation": len(distinct_samples) > 1,
        "unit_bearing_values": unit_variations,
        "alerts": alerts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract and cross-check sample sizes and unit-bearing numbers.")
    parser.add_argument("--inputs", nargs="+", required=True, help="One or more Markdown/text files to scan.")
    parser.add_argument("--out-json", default="", help="Optional path to save JSON scan report.")
    args = parser.parse_args()

    all_blocks: list[dict[str, Any]] = []
    for p_str in args.inputs:
        all_blocks.extend(parse_blocks_from_file(Path(p_str)))

    report = analyze_blocks(all_blocks)
    if args.out_json:
        out_p = Path(args.out_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
