#!/usr/bin/env python3
"""Initialize and inspect the standardized end-to-end paper pipeline workspace.

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


def _norm_enum(val: str, allowed: tuple[str, ...], flag_name: str) -> str:
    norm = val.strip().upper().replace("-", "_")
    if norm not in allowed:
        raise ValueError(f"Invalid {flag_name} '{val}'. Allowed: {allowed}")
    return norm


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def cmd_init(args: argparse.Namespace) -> int:
    paradigm = _norm_enum(args.paradigm, PARADIGMS, "--paradigm")
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
            "target_venue_or_type": args.paper_type or "",
        }
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    ledger_path = ws / "03_backbone" / "03_claim_ledger.json"
    if not ledger_path.exists():
        skeleton_ledger = {
            "schema_version": "1.0",
            "generated_at": _utc_now_iso(),
            "research_paradigm": paradigm,
            "study_time_state": time_state,
            "one_sentence_storyline": "",
            "evidence_items": [],
            "claims": [],
        }
        ledger_path.write_text(json.dumps(skeleton_ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "action": "init",
                "workspace": str(ws),
                "paradigm": paradigm,
                "study_time_state": time_state,
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
    p_init.add_argument("--paradigm", default="QUANTITATIVE", help="Paradigm (case/hyphen insensitive).")
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
