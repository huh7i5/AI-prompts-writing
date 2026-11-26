#!/usr/bin/env python3
"""Master health checker and workspace stage coordinator for the AI-prompts-writing Skills Suite.

Subcommands:
  selftest   -> Discovers and executes selftest.py across all installed skills (router + 4 stations).
  diagnose   -> Inspects a paper workspace directory and outputs current pipeline stage,
                unlocked/missing artifacts, and exact recommended station skill to invoke next.
  run-gates  -> Executes all deterministic quality & compliance gates across a paper workspace
                (claim ledger contract, style/slop/citation checks per draft, and cross-file numbers).

Zero third-party dependencies (Python 3 standard library only).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROUTER_DIR = Path(__file__).resolve().parent.parent
SKILLS_ROOT = ROUTER_DIR.parent

EXPECTED_STATIONS = (
    "paper-topic-literature",
    "paper-design-evidence",
    "paper-draft-polish",
    "paper-audit-submission",
)


def cmd_selftest() -> int:
    station_results: list[dict[str, Any]] = []
    overall_ok = True

    all_skill_dirs = [ROUTER_DIR] + [SKILLS_ROOT / name for name in EXPECTED_STATIONS]
    for sdir in all_skill_dirs:
        sname = sdir.name
        skill_md = sdir / "SKILL.md"
        selftest_py = sdir / "scripts" / "selftest.py"
        if not skill_md.exists():
            overall_ok = False
            station_results.append({"skill": sname, "installed": False, "status": "MISSING_SKILL_MD"})
            continue

        if selftest_py.exists():
            proc = subprocess.run(
                [sys.executable, str(selftest_py)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            passed = proc.returncode == 0
            if not passed:
                overall_ok = False
            station_results.append(
                {
                    "skill": sname,
                    "installed": True,
                    "selftest_passed": passed,
                    "exit_code": proc.returncode,
                    "summary": (proc.stderr or proc.stdout).strip().splitlines()[-1] if (proc.stderr or proc.stdout) else "",
                }
            )
        else:
            station_results.append({"skill": sname, "installed": True, "selftest_passed": True, "note": "No selftest.py"})

    report = {
        "suite": "AI-prompts-writing 1+4 Pipeline Suite",
        "skills_root": str(SKILLS_ROOT),
        "all_passed": overall_ok,
        "results": station_results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if overall_ok else 2


def cmd_diagnose(workspace: Path) -> int:
    ws = workspace.resolve()
    installed_stations = [name for name in EXPECTED_STATIONS if (SKILLS_ROOT / name / "SKILL.md").exists()]
    mode = "FULL_SUITE_MODE" if len(installed_stations) == len(EXPECTED_STATIONS) else "STANDALONE_OR_PARTIAL_MODE"

    if not ws.exists():
        print(
            json.dumps(
                {
                    "suite_mode": mode,
                    "installed_stations": installed_stations,
                    "workspace_exists": False,
                    "workspace": str(ws),
                    "recommended_station": "paper-topic-literature (if starting from topic/literature) or paper-design-evidence (init_workspace.py)",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    spec_path = ws / "00_project_spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else {}
    time_state = (spec.get("study_time_state") or "UNKNOWN").upper()
    paper_preset = spec.get("paper_preset") or "general"

    topic_yaml = (ws / "01_literature" / "01_topic_spec.yaml").exists() or (ws / "01_topic_spec.yaml").exists()
    lit_json_path = ws / "01_literature" / "02_literature_ledger.json"
    if not lit_json_path.exists() and (ws / "02_literature_ledger.json").exists():
        lit_json_path = ws / "02_literature_ledger.json"

    claim_path = ws / "03_backbone" / "03_claim_ledger.json"
    outline_path = ws / "03_backbone" / "04_outline.md"
    drafts = sorted(p.name for p in (ws / "04_drafts").glob("*.md")) if (ws / "04_drafts").exists() else []
    audits = sorted(p.name for p in (ws / "05_audit").glob("*.json")) if (ws / "05_audit").exists() else []

    claims_count = 0
    if claim_path.exists():
        claims_count = len(json.loads(claim_path.read_text(encoding="utf-8")).get("claims") or [])

    if not lit_json_path.exists() and claims_count == 0:
        next_station = "paper-topic-literature"
        reason = "No verified literature ledger or locked claim ledger found yet; ground topic and literature first."
    elif claims_count == 0 or not outline_path.exists():
        next_station = "paper-design-evidence"
        reason = "Populate 03_claim_ledger.json and 04_outline.md before drafting prose chapters."
    elif not drafts:
        next_station = "paper-draft-polish"
        if time_state == "PRE_STUDY":
            reason = "PRE_STUDY lock active: may draft proposal/intro/planned-methods with [待补], NOT completed Results."
        else:
            reason = "Claim ledger & outline ready; proceed to section drafting and anti-slop polishing."
    else:
        next_station = "paper-audit-submission"
        reason = "Draft sections exist; run check_numbers.py and pre-submission / peer-review audit gates."

    preset_hints = {
        "thesis_zh": " [thesis_zh: enforce GB/T 7713.1 ch1->final closure & cross-chapter number sync]",
        "journal_en": " [journal_en: keep compact single-contribution scope & matched baseline comparisons]",
        "journal_zh": " [journal_zh: enforce GB/T 7714 sequential refs & bilingual abstract parity]",
        "review": " [review: state search databases/date window & inclusion/exclusion without claiming unrun PRISMA]",
    }
    if paper_preset in preset_hints:
        reason += preset_hints[paper_preset]

    print(
        json.dumps(
            {
                "suite_mode": mode,
                "installed_stations": installed_stations,
                "workspace_exists": True,
                "workspace": str(ws),
                "paper_preset": paper_preset,
                "study_time_state": time_state,
                "state_summary": {
                    "topic_spec_found": topic_yaml,
                    "literature_ledger_found": lit_json_path.exists(),
                    "claim_ledger_claims": claims_count,
                    "outline_found": outline_path.exists(),
                    "draft_files": drafts,
                    "audit_reports": audits,
                },
                "recommended_station": next_station,
                "reason": reason,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_run_gates(workspace: Path) -> int:
    ws = workspace.resolve()
    if not ws.exists():
        print(json.dumps({"overall_status": "BLOCKED", "error": f"Workspace not found: {ws}"}, indent=2))
        return 2

    spec_path = ws / "00_project_spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else {}
    paradigm = spec.get("research_paradigm") or "QUANTITATIVE"
    time_state = spec.get("study_time_state") or "POST_RESULTS"

    lit_path = ws / "01_literature" / "02_literature_ledger.json"
    claim_path = ws / "03_backbone" / "03_claim_ledger.json"
    drafts = sorted((ws / "04_drafts").glob("*.md")) if (ws / "04_drafts").exists() else []

    gate_reports: list[dict[str, Any]] = []
    has_blocker = False
    has_warn = False

    # 1. Station 02 Claim Ledger Gate
    s2_gate = SKILLS_ROOT / "paper-design-evidence" / "scripts" / "design_evidence_gate.py"
    if claim_path.exists() and s2_gate.exists():
        cmd = [
            sys.executable,
            str(s2_gate),
            "--task",
            "3.4",
            "--paradigm",
            paradigm,
            "--time-state",
            time_state,
            "--claim-ledger",
            str(claim_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
        rep = json.loads(proc.stdout)
        gate_reports.append({"check": "station02_claim_ledger", "report": rep})
        if rep["status"] == "BLOCKED":
            has_blocker = True
        elif rep["status"] == "WARN":
            has_warn = True

    # 2. Station 03 Style & Citation Gate across all draft chapters
    s3_gate = SKILLS_ROOT / "paper-draft-polish" / "scripts" / "style_and_draft_gate.py"
    if drafts and s3_gate.exists():
        for dfile in drafts:
            sec_low = dfile.stem.lower()
            sec = "general"
            for cand in ("abstract", "intro", "methods", "results", "discussion", "conclusion"):
                if cand in sec_low:
                    sec = cand
                    break
            cmd = [sys.executable, str(s3_gate), "--draft", str(dfile), "--mode", "draft", "--section", sec]
            if claim_path.exists():
                cmd.extend(["--claim-ledger", str(claim_path)])
            if lit_path.exists():
                cmd.extend(["--lit-ledger", str(lit_path)])
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
            rep = json.loads(proc.stdout)
            gate_reports.append({"check": f"station03_draft:{dfile.name}", "report": rep})
            if rep["status"] == "BLOCKED":
                has_blocker = True
            elif rep["status"] == "WARN":
                has_warn = True

    # 3. Station 04 Cross-Section Number & Sample-Size Scanner across all drafts
    s4_num = SKILLS_ROOT / "paper-audit-submission" / "scripts" / "check_numbers.py"
    if drafts and s4_num.exists():
        cmd = [sys.executable, str(s4_num), "--inputs"] + [str(d) for d in drafts]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
        num_rep = json.loads(proc.stdout)
        gate_reports.append(
            {
                "check": "station04_cross_draft_numbers",
                "has_sample_size_variation": num_rep.get("has_sample_size_variation", False),
                "distinct_sample_sizes": num_rep.get("distinct_sample_sizes", []),
                "alerts_count": len(num_rep.get("alerts") or []),
            }
        )

    overall = "BLOCKED" if has_blocker else ("WARN" if has_warn else "PASS")
    summary = {
        "workspace": str(ws),
        "overall_status": overall,
        "drafts_checked": [d.name for d in drafts],
        "gates": gate_reports,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if has_blocker else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI-prompts-writing Skills Suite doctor & stage router.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest", help="Run self-tests across router and all 4 station skills.")
    p_diag = sub.add_parser("diagnose", help="Inspect workspace state and recommend next station.")
    p_diag.add_argument("--workspace", required=True, help="Path to paper workspace directory.")
    p_gates = sub.add_parser("run-gates", help="Run all Station 02/03/04 deterministic gates across a workspace.")
    p_gates.add_argument("--workspace", required=True, help="Path to paper workspace directory.")

    args = parser.parse_args()
    if args.command == "selftest":
        return cmd_selftest()
    if args.command == "diagnose":
        return cmd_diagnose(Path(args.workspace))
    return cmd_run_gates(Path(args.workspace))


if __name__ == "__main__":
    raise SystemExit(main())
