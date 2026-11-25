#!/usr/bin/env python3
"""Deterministic compliance & boundary gate for Station 04 (paper-audit-submission).

Guards against classic high-severity audit, submission, revision, and proofreading errors:
1. Fabricated supplemental experiments in 9.2/9.3 when --no-new-experiments is active (T08/R08).
2. Full-manuscript / full-proof / already-submitted overclaims when --partial-scope is active (T06/T12).
3. Unconfirmed default declarations ("无利益冲突", "未受任何资助", fake repo DOIs, unconditional public
   release of private interviews) in 8.4 / 10.2 when --unconfirmed-declarations is active (T11).
4. Silent acceptance or dismissal of substantive proof changes in 10.1 (T12).
5. Cross-section sync broadcast via 03_claim_ledger.json (--claim-ledger + --modified-claims).

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
    r"(不|未|尚未|不能|不可|切勿|严禁|并非|没有|不声称|不能宣称|不能直接|不得|待确认|待作者确认|待核实|待补|"
    r"not|never|cannot|do not|unconfirmed|pending|yet to)"
)
NEGATION_WINDOW_REGEX = re.compile(NEGATION_CORE + r"[^。；！？!?\n]{0,22}$", re.IGNORECASE)
NEGATION_ANYWHERE_REGEX = re.compile(NEGATION_CORE, re.IGNORECASE)

FAKE_DOI_REGEX = re.compile(r"\b10\.(?:0000|1234|5555|9999)/[-._;()/:A-Za-z0-9]+|\b10\.5281/zenodo\.0+\b", re.IGNORECASE)

FABRICATED_EXP_REGEX = re.compile(
    r"(我们已补充(?:了)?实验|已完成补充实验|新增实验结果表明|补充的\s*\d+\s*人实验显示|"
    r"\bwe have conducted additional experiments\b|\bnew experiments with \d+ participants show\b)",
    re.IGNORECASE,
)

FULL_SCOPE_OVERCLAIM_REGEX = re.compile(
    r"(全文已核验无误|已完成全文核验|整篇校样已核对完成|已向(?:期刊|出版方|编辑部)正式提交|"
    r"已经联系编辑完成了?更正|\bfull manuscript has been verified\b|\bproofs have been submitted\b)",
    re.IGNORECASE,
)

UNCONFIRMED_DEFAULT_DECL_REGEX = re.compile(
    r"(本研究未受任何资助|全体作者均确认无利益冲突|The authors declare no competing interests|"
    r"本研究已获得伦理委员会正式批准|建议直接公开原始访谈(?:录音|记录|全文)|删除姓名即可确保完全匿名)",
    re.IGNORECASE,
)

PROOF_SILENT_DISMISSAL_REGEX = re.compile(
    r"(只是普通排版笔误已直接改好|已直接按校样的\s*300\s*人统一修改表格)",
    re.IGNORECASE,
)


def _is_inside_quotes_or_code(line: str, match_start: int, match_end: int) -> bool:
    before = line[:match_start]
    after = line[match_end:]
    if before.count("`") % 2 == 1 and "`" in after:
        return True
    for open_q, close_q in (("“", "”"), ("「", "」"), ("‘", "’"), ('"', '"'), ("'", "'"), ("[", "]")):
        if open_q in before and close_q in after:
            return True
    return False


def _is_negated(line: str, match_start: int, match_end: int) -> bool:
    same_clause = re.split(r"[。；！？!?\n]", line[:match_start])[-1]
    if NEGATION_WINDOW_REGEX.search(same_clause[-28:]):
        return True
    if _is_inside_quotes_or_code(line, match_start, match_end):
        if NEGATION_ANYWHERE_REGEX.search(same_clause) or "待" in line[match_end : match_end + 18]:
            return True
    return False


def run_audit_gate(
    text: str,
    tasks: set[str],
    no_new_experiments: bool,
    partial_scope: bool,
    unconfirmed_declarations: bool,
    claim_ledger: dict[str, Any] | None,
    modified_claims: set[str],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        # 1. Fake repository or citation DOI check
        for m_doi in FAKE_DOI_REGEX.finditer(line):
            if not _is_negated(line, m_doi.start(), m_doi.end()):
                findings.append(
                    {
                        "severity": "BLOCKER",
                        "code": "FAKE_OR_PLACEHOLDER_DOI",
                        "line": idx,
                        "detail": f"Detected fabricated/placeholder DOI '{m_doi.group(0)}'.",
                    }
                )

        # 2. Fabricated supplemental experiment check (9.2 / 9.3, T08/R08)
        if no_new_experiments or bool(tasks & {"9.2", "9.3"}):
            sev = "BLOCKER" if no_new_experiments else "WARN"
            for m_exp in FABRICATED_EXP_REGEX.finditer(line):
                if not _is_negated(line, m_exp.start(), m_exp.end()):
                    findings.append(
                        {
                            "severity": sev,
                            "code": "FABRICATED_SUPPLEMENTAL_EXPERIMENT",
                            "line": idx,
                            "detail": (
                                f"Claimed completed supplemental experiment ('{m_exp.group(0)}'). "
                                "Ensure real new experimental data was supplied; never turn a reviewer request into a fake completion."
                            ),
                        }
                    )

        # 3. Partial-scope overclaim check (7.1, 7.3, 10.1, 10.3)
        if partial_scope or bool(tasks & {"7.1", "10.1", "10.3"}):
            sev_scope = "BLOCKER" if partial_scope else "WARN"
            for m_full in FULL_SCOPE_OVERCLAIM_REGEX.finditer(line):
                if not _is_negated(line, m_full.start(), m_full.end()):
                    findings.append(
                        {
                            "severity": sev_scope,
                            "code": "PARTIAL_SCOPE_OVERCLAIM",
                            "line": idx,
                            "detail": (
                                f"Claimed full-manuscript check or submission completion ('{m_full.group(0)}')."
                            ),
                        }
                    )

        # 4. Unconfirmed declaration defaults & privacy violation check (8.4, 10.2, T11)
        if unconfirmed_declarations or bool(tasks & {"8.4", "10.2"}):
            sev_decl = "BLOCKER" if unconfirmed_declarations else "WARN"
            for m_decl in UNCONFIRMED_DEFAULT_DECL_REGEX.finditer(line):
                if not _is_negated(line, m_decl.start(), m_decl.end()):
                    findings.append(
                        {
                            "severity": sev_decl,
                            "code": "UNCONFIRMED_DECLARATION_OR_PRIVACY_BREACH",
                            "line": idx,
                            "detail": (
                                f"Defaulted declaration or unsafe privacy advice ('{m_decl.group(0)}'); "
                                "verify explicit author confirmation or use [待作者确认]."
                            ),
                        }
                    )

        # 5. Page proof substantive change silent dismissal check (10.1, T12)
        if "10.1" in tasks:
            for m_prf in PROOF_SILENT_DISMISSAL_REGEX.finditer(line):
                if not _is_negated(line, m_prf.start(), m_prf.end()):
                    findings.append(
                        {
                            "severity": "BLOCKER",
                            "code": "PROOF_SUBSTANTIVE_CHANGE_MISHANDLED",
                            "line": idx,
                            "detail": (
                                f"Substantive number change in proofs mishandled ('{m_prf.group(0)}'); "
                                "must flag for joint author & editor confirmation."
                            ),
                        }
                    )

    # 6. Impact propagation broadcast via 03_claim_ledger.json
    impacted_sections: list[str] = []
    if claim_ledger and modified_claims:
        for c in claim_ledger.get("claims") or []:
            if c.get("claim_id") in modified_claims:
                for sec in c.get("target_sections") or []:
                    if sec not in impacted_sections:
                        impacted_sections.append(sec)

    blockers = sum(1 for f in findings if f["severity"] == "BLOCKER")
    warns = sum(1 for f in findings if f["severity"] == "WARN")
    status = "BLOCKED" if blockers > 0 else ("WARN" if warns > 0 else "PASS")

    return {
        "station": "04_audit_submission",
        "tasks": sorted(tasks),
        "status": status,
        "blocker_count": blockers,
        "warn_count": warns,
        "impacted_target_sections_to_sync": impacted_sections,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Station 04 deterministic audit, declaration, revision & proof gate.")
    parser.add_argument("--draft", required=True, help="Path to Station 04 output Markdown.")
    parser.add_argument("--task", default="7.1", help="Comma-separated Station 04 sub-task(s), e.g. '7.1' or '9.2,9.3'.")
    parser.add_argument(
        "--no-new-experiments",
        action="store_true",
        help="Set when revising/responding without newly executed experimental results (T08/R08).",
    )
    parser.add_argument(
        "--partial-scope",
        action="store_true",
        help="Set when only snippets/selected pages were supplied (T06/T12).",
    )
    parser.add_argument(
        "--unconfirmed-declarations",
        action="store_true",
        help="Set when funding, COI, ethics, or public data consent were not explicitly confirmed (T11).",
    )
    parser.add_argument("--claim-ledger", default="", help="Optional path to 03_claim_ledger.json.")
    parser.add_argument("--modified-claims", default="", help="Comma-separated modified claim IDs (e.g. 'C01,C02').")
    parser.add_argument("--json-out", default="", help="Optional output JSON report path.")
    args = parser.parse_args()

    tasks = {t.strip() for t in args.task.split(",") if t.strip()}
    draft_text = Path(args.draft).read_text(encoding="utf-8")
    ledger = json.loads(Path(args.claim_ledger).read_text(encoding="utf-8")) if args.claim_ledger else None
    mod_claims = {c.strip() for c in args.modified_claims.split(",") if c.strip()}

    report = run_audit_gate(
        text=draft_text,
        tasks=tasks,
        no_new_experiments=args.no_new_experiments,
        partial_scope=args.partial_scope,
        unconfirmed_declarations=args.unconfirmed_declarations,
        claim_ledger=ledger,
        modified_claims=mod_claims,
    )
    if args.json_out:
        out_p = Path(args.json_out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
