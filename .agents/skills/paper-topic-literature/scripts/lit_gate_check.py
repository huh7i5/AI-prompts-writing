#!/usr/bin/env python3
"""Deterministic quality gate for Station 01 (Topic & Literature Grounding).

Scans drafts/outputs produced in tasks 1.1-2.3 for:
1. Offline mode hallucinated references / DOIs (when --mode search-offline).
2. Fake/injected test DOIs (e.g., 10.0000/fake.2099 from prompt injection).
3. Unregistered / orphan citations against 02_literature_ledger.json or --allowed-ids.
4. Unsupported absolute novelty or gap overclaims ("前人从未研究", "全面领先", "首次提出", etc.)
   with context-aware negation guards so legitimate cautious statements pass cleanly.
5. Unwarranted Systematic Review / PRISMA claims without screening logs.
6. Reading-depth boundary warnings when citing abstract-only or metadata-only sources.

Exit codes:
  0 -> PASS or WARN
  2 -> BLOCKED (must be fixed before delivering output or advancing pipeline)
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

FAKE_DOI_PREFIXES = ("10.0000/", "10.1234/", "10.5555/", "10.9999/")
DOI_REGEX = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
CITE_KEY_REGEX = re.compile(r"\[@([A-Za-z0-9_:-]+)\]")
BRACKET_SOURCE_REGEX = re.compile(r"\[(材料[A-Za-z0-9]+|来源[A-Za-z0-9]+|[A-Z])\]")
AUTHOR_YEAR_CITE_REGEX = re.compile(r"\(([A-Z][A-Za-z\s.&]+,\s*(?:19|20)\d{2}[a-z]?)\)")

OVERCLAIM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("UNVERIFIED_GAP_CN", re.compile(r"(前人从未研究|尚无任何研究|国内外尚无研究|目前没有任何文献|填补了.{0,8}空白)")),
    ("UNVERIFIED_SUPERLATIVE_CN", re.compile(r"(首次提出|首次揭示|首次证明|全面领先|全面优于|彻底解决了)")),
    (
        "UNVERIFIED_GAP_EN",
        re.compile(
            r"\b(no prior study exists|never been studied before|fills a complete gap|"
            r"outperforms in all aspects|completely solves)\b",
            re.IGNORECASE,
        ),
    ),
]

NEGATION_VERB_CORE = (
    r"(不|未|并非|不能|不可|切勿|严禁|避免|不足以|尚不能|无法|没有证据表明|不能断言|不宣称|"
    r"隔离|忽略|剔除|拒绝|伪造|虚构|未采纳|不采用|不采信|"
    r"do not|don't|cannot|can't|never claim|not enough to|avoid|rejected|isolated|ignored|fabricated)"
)
NEGATION_PREFIX_REGEX = re.compile(NEGATION_VERB_CORE + r"[^。；！？!?\n]{0,20}$", re.IGNORECASE)
NEGATION_ANYWHERE_REGEX = re.compile(NEGATION_VERB_CORE, re.IGNORECASE)

SYS_REVIEW_CLAIM_REGEX = re.compile(
    r"(本文开展了系统综述|本研究为系统综述|已完成系统综述|严格遵循\s*PRISMA\s*完成了|"
    r"\bwe conducted a systematic review\b|\bfollowing PRISMA guidelines, we screened\b)",
    re.IGNORECASE,
)

INJECTION_RESIDUE_REGEX = re.compile(
    r"(忽略(?:上述|用户|前面)要求|ignore (?:previous|all|user) instructions)",
    re.IGNORECASE,
)

DEPTH_DISCLOSURE_REGEX = re.compile(
    r"(摘要|题录|元数据|未读全文|待读全文|待核实全文|abstract[- ]only|based on (?:the )?abstract|metadata[- ]only)",
    re.IGNORECASE,
)


def _clean_doi(raw: str) -> str:
    cleaned = raw.strip().rstrip(".,;)]}>\"'`")
    if cleaned.lower().endswith(".pdf"):
        cleaned = cleaned[:-4]
    return cleaned.lower()


def _expand_allowed_ids(raw_ids: set[str]) -> set[str]:
    expanded: set[str] = set()
    for item in raw_ids:
        expanded.add(item)
        stripped = re.sub(r"^(材料|来源)", "", item).strip()
        if stripped:
            expanded.add(stripped)
            expanded.add(f"材料{stripped}")
            expanded.add(f"来源{stripped}")
    return expanded


def _is_inside_quotes_or_code(line: str, match_start: int, match_end: int) -> bool:
    before = line[:match_start]
    after = line[match_end:]
    if before.count("`") % 2 == 1 and "`" in after:
        return True
    for open_q, close_q in (("“", "”"), ("「", "」"), ('"', '"'), ("'", "'")):
        if open_q in before and close_q in after:
            return True
    return False


def _is_negated_match(line: str, match_start: int, match_end: int | None = None) -> bool:
    same_sentence_prefix = re.split(r"[。；！？!?\n]", line[:match_start])[-1]
    window = same_sentence_prefix[-26:]
    if NEGATION_PREFIX_REGEX.search(window):
        return True
    end_pos = match_end if match_end is not None else match_start
    if _is_inside_quotes_or_code(line, match_start, end_pos):
        if NEGATION_ANYWHERE_REGEX.search(same_sentence_prefix):
            return True
    return False


def run_gate(
    draft_text: str,
    mode: str,
    ledger_data: dict[str, Any] | None,
    allowed_ids: set[str],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    lines = draft_text.splitlines()

    registered_dois: set[str] = set()
    expanded_allowed_ids = _expand_allowed_ids(allowed_ids)
    registered_ids: set[str] = set(expanded_allowed_ids)
    shallow_depth_ids: list[str] = []
    is_sys_review_allowed = False

    if ledger_data:
        is_sys_review_allowed = bool(ledger_data.get("is_systematic_review", False))
        for entry in ledger_data.get("entries", []):
            rid = entry.get("ref_id")
            if rid:
                registered_ids.add(rid)
            doi = entry.get("doi")
            if doi:
                registered_dois.add(_clean_doi(doi))
            arxiv_id = entry.get("arxiv_id")
            if arxiv_id:
                bare_arxiv = re.sub(r"v\d+$", "", str(arxiv_id).strip(), flags=re.IGNORECASE).lower()
                registered_dois.add(f"10.48550/arxiv.{bare_arxiv}")
                registered_dois.add(f"10.48550/arxiv.{str(arxiv_id).strip().lower()}")
            if entry.get("verification_status") in ("NOT_FOUND", "REJECTED_FAKE_PREFIX"):
                findings.append(
                    {
                        "severity": "BLOCKER",
                        "code": "INVALID_LEDGER_ENTRY",
                        "line": None,
                        "detail": f"Ledger contains unverified/fake entry '{rid}' ({doi}). Remove before drafting.",
                    }
                )
            if entry.get("reading_depth") in ("METADATA_ONLY", "ABSTRACT_READ") and rid:
                shallow_depth_ids.append(rid)

    for idx, line in enumerate(lines, start=1):
        # 1. Check DOIs on this line
        for m_doi in DOI_REGEX.finditer(line):
            raw_doi = m_doi.group(1)
            doi = _clean_doi(raw_doi)
            if any(doi.startswith(p) for p in FAKE_DOI_PREFIXES) or "/fake" in doi:
                if not _is_negated_match(line, m_doi.start(), m_doi.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "FAKE_OR_INJECTED_DOI",
                            "line": idx,
                            "detail": f"Detected fake/test DOI '{doi}' (possible prompt injection or fabrication).",
                        }
                    )
                    continue
            elif any(doi.startswith(p) for p in FAKE_DOI_PREFIXES) or "/fake" in doi:
                continue
            if mode == "search-offline":
                findings.append(
                    {
                        "severity": "BLOCKER",
                        "code": "OFFLINE_HALLUCINATED_DOI",
                        "line": idx,
                        "detail": f"Offline search plan must not output specific DOIs ('{doi}').",
                    }
                )
            elif ledger_data is not None and doi not in registered_dois:
                if not _is_negated_match(line, m_doi.start(), m_doi.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "UNREGISTERED_DOI",
                            "line": idx,
                            "detail": f"DOI '{doi}' is not registered in the verified literature ledger.",
                        }
                    )

        # 2. Offline mode author-year reference check
        if mode == "search-offline":
            for ay in AUTHOR_YEAR_CITE_REGEX.findall(line):
                findings.append(
                    {
                        "severity": "BLOCKER",
                        "code": "OFFLINE_HALLUCINATED_CITATION",
                        "line": idx,
                        "detail": f"Offline search plan must not list memorized citations ('({ay})').",
                    }
                )

        # 3. Check [@ref_id] against ledger/allowed_ids; check [材料A]/[A] ONLY when --allowed-ids is given
        if registered_ids:
            for ckey in CITE_KEY_REGEX.findall(line):
                if ckey not in registered_ids:
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "ORPHAN_CITATION_KEY",
                            "line": idx,
                            "detail": f"Citation key '[@{ckey}]' is not in ledger or allowed source IDs.",
                        }
                    )
        if expanded_allowed_ids:
            for bkey in BRACKET_SOURCE_REGEX.findall(line):
                if bkey not in expanded_allowed_ids:
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "ORPHAN_SOURCE_LABEL",
                            "line": idx,
                            "detail": f"Source label '[{bkey}]' is not in declared allowed IDs {sorted(expanded_allowed_ids)}.",
                        }
                    )

        # 4. Unsupported absolute novelty / gap / superiority overclaims
        for code, pattern in OVERCLAIM_PATTERNS:
            for m in pattern.finditer(line):
                if not _is_negated_match(line, m.start(), m.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": code,
                            "line": idx,
                            "detail": (
                                f"Unsupported absolute claim '{m.group(0)}'. Narrow to actual search/material scope."
                            ),
                        }
                    )

        # 5. Unwarranted Systematic Review claim
        for m in SYS_REVIEW_CLAIM_REGEX.finditer(line):
            if not is_sys_review_allowed and not _is_negated_match(line, m.start(), m.end()):
                findings.append(
                    {
                        "severity": "BLOCKER",
                        "code": "SYSTEMATIC_REVIEW_OVERCLAIM",
                        "line": idx,
                        "detail": f"Claimed systematic review ('{m.group(0)}') without complete screening protocol.",
                    }
                )

        # 6. Prompt injection residue check
        if INJECTION_RESIDUE_REGEX.search(line) and not any(
            w in line for w in ("隔离", "忽略", "注入", "异常指令", "污染", "剔除", "ignored", "isolated")
        ):
            findings.append(
                {
                    "severity": "WARN",
                    "code": "POSSIBLE_INJECTION_TEXT",
                    "line": idx,
                    "detail": "Line contains raw instruction-override phrasing; verify material isolation.",
                }
            )

    # 7. Reading-depth disclosure check for Related Work mode (both ledger shallow entries & snippet --allowed-ids)
    if mode == "related-work":
        cited_shallow = [rid for rid in shallow_depth_ids if rid in draft_text]
        needs_disclosure = bool(cited_shallow) or (bool(expanded_allowed_ids) and ledger_data is None)
        if needs_disclosure and not DEPTH_DISCLOSURE_REGEX.search(draft_text):
            findings.append(
                {
                    "severity": "WARN",
                    "code": "MISSING_DEPTH_DISCLOSURE",
                    "line": None,
                    "detail": (
                        "Draft cites abstract/metadata/snippet sources without disclosing reading-depth "
                        "limitations (e.g., '基于摘要' / '待核对全文')."
                    ),
                }
            )

    blocker_count = sum(1 for f in findings if f["severity"] == "BLOCKER")
    warn_count = sum(1 for f in findings if f["severity"] == "WARN")
    if blocker_count > 0:
        status = "BLOCKED"
    elif warn_count > 0:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "mode": mode,
        "status": status,
        "blocker_count": blocker_count,
        "warn_count": warn_count,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Station 01 deterministic output quality gate.")
    parser.add_argument("--draft", required=True, help="Path to Markdown/text draft to inspect.")
    parser.add_argument(
        "--mode",
        choices=["topic", "search-offline", "matrix", "related-work"],
        default="related-work",
        help="Validation mode matching the active sub-task.",
    )
    parser.add_argument("--ledger", default="", help="Optional path to 02_literature_ledger.json.")
    parser.add_argument(
        "--allowed-ids",
        default="",
        help="Comma-separated allowed source labels when not using a JSON ledger (e.g. 'A,B,材料A,材料B').",
    )
    parser.add_argument("--json-out", default="", help="Optional path to write JSON gate report.")
    args = parser.parse_args()

    draft_text = Path(args.draft).read_text(encoding="utf-8")
    ledger_data = json.loads(Path(args.ledger).read_text(encoding="utf-8")) if args.ledger else None
    allowed_ids = {x.strip() for x in args.allowed_ids.split(",") if x.strip()}

    report = run_gate(draft_text=draft_text, mode=args.mode, ledger_data=ledger_data, allowed_ids=allowed_ids)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
