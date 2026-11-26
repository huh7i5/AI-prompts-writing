#!/usr/bin/env python3
"""Cross-host installer for the AI-prompts-writing 1+4 Agent Skills Suite.

Installs, updates, verifies, or uninstalls all 5 skills under `.agents/skills/` into:
  - claude       -> <home-root>/.claude/skills
  - codex        -> <home-root>/.codex/skills
  - cursor       -> <home-root>/.cursor/skills
  - antigravity  -> <home-root>/.gemini/antigravity/skills
  - opencode     -> <home-root>/.config/opencode/skills
  - project      -> <project-root>/.agents/skills

Zero third-party dependencies (Python 3 standard library only).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_SRC = REPO_ROOT / ".agents" / "skills"
SKILL_NAMES = (
    "ai-prompt-writing",
    "paper-topic-literature",
    "paper-design-evidence",
    "paper-draft-polish",
    "paper-audit-submission",
)


def resolve_target_dir(host: str, home_root: Path, project_root: Path, target_dir: str) -> Path:
    if target_dir:
        return Path(target_dir).expanduser().resolve()
    mapping = {
        "claude": home_root / ".claude" / "skills",
        "codex": home_root / ".codex" / "skills",
        "cursor": home_root / ".cursor" / "skills",
        "antigravity": home_root / ".gemini" / "antigravity" / "skills",
        "opencode": home_root / ".config" / "opencode" / "skills",
        "project": project_root / ".agents" / "skills",
    }
    key = host.strip().lower()
    if key not in mapping:
        raise ValueError(f"Unsupported --host '{host}'. Supported: {sorted(mapping.keys())}")
    return mapping[key].resolve()


def _copy_skill_tree(src: Path, dst: Path) -> None:
    def _ignore(directory: str, names: list[str]) -> set[str]:
        return {n for n in names if n == "__pycache__" or n.endswith(".pyc")}

    shutil.copytree(src, dst, ignore=_ignore)


def run_verify(dest_root: Path, skip_selftest: bool = False) -> dict[str, Any]:
    missing = [s for s in SKILL_NAMES if not (dest_root / s / "SKILL.md").exists()]
    if missing:
        return {
            "verified": False,
            "target_dir": str(dest_root),
            "missing_skills": missing,
        }

    selftest_ok = True
    selftest_report: dict[str, Any] | None = None
    if not skip_selftest:
        doctor = dest_root / "ai-prompt-writing" / "scripts" / "pipeline_doctor.py"
        if not doctor.exists():
            return {"verified": False, "target_dir": str(dest_root), "error": "Missing installed pipeline_doctor.py"}
        proc = subprocess.run(
            [sys.executable, "-B", str(doctor), "selftest"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        selftest_ok = proc.returncode == 0
        try:
            selftest_report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            selftest_report = {"raw_stdout": proc.stdout, "raw_stderr": proc.stderr}

    return {
        "verified": selftest_ok,
        "target_dir": str(dest_root),
        "installed_skills": list(SKILL_NAMES),
        "selftest_ran": not skip_selftest,
        "selftest_report": selftest_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install, update, verify, or uninstall the 1+4 AI-prompts-writing skill suite.")
    parser.add_argument("action", nargs="?", default="install", choices=("install", "update", "verify", "uninstall"))
    parser.add_argument("--host", default="codex", choices=("claude", "codex", "cursor", "antigravity", "opencode", "project"))
    parser.add_argument("--home-root", default=str(Path.home()), help="Override home root directory (useful for isolated tests).")
    parser.add_argument("--project-root", default=".", help="Project root when --host project.")
    parser.add_argument("--target-dir", default="", help="Explicit skills destination directory (overrides --host mapping).")
    parser.add_argument("--backup", "--backup-existing", action="store_true", dest="backup_existing", help="Move existing suite directories into a timestamped backup folder on update.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing matching folders during update without backup.")
    parser.add_argument("--skip-selftest", action="store_true", help="Skip running pipeline_doctor.py selftest after copy/verify.")
    args = parser.parse_args()

    for s in SKILL_NAMES:
        if not (SKILLS_SRC / s / "SKILL.md").exists():
            raise SystemExit(f"Source skill missing under {SKILLS_SRC}: {s}")

    dest_root = resolve_target_dir(
        args.host,
        Path(args.home_root).expanduser().resolve(),
        Path(args.project_root).expanduser().resolve(),
        args.target_dir,
    )

    if args.action == "verify":
        rep = run_verify(dest_root, skip_selftest=args.skip_selftest)
        rep["action"] = "verify"
        rep["host"] = args.host
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep["verified"] else 2

    if args.action == "uninstall":
        removed: list[str] = []
        for s in SKILL_NAMES:
            target = dest_root / s
            if target.exists():
                shutil.rmtree(target)
                removed.append(s)
        print(json.dumps({"action": "uninstall", "host": args.host, "target_dir": str(dest_root), "removed": removed}, ensure_ascii=False, indent=2))
        return 0

    existing = [s for s in SKILL_NAMES if (dest_root / s).exists()]
    if existing and args.action == "install":
        print(
            json.dumps(
                {
                    "action": "install",
                    "status": "BLOCKED_EXISTING",
                    "host": args.host,
                    "target_dir": str(dest_root),
                    "existing_skills": existing,
                    "next_step": "Re-run with 'update --backup-existing' to preserve prior copies safely, or 'verify' to check existing install.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    if existing and args.action == "update" and not (args.backup_existing or args.force):
        print(
            json.dumps(
                {
                    "action": "update",
                    "status": "NEEDS_BACKUP_FLAG",
                    "host": args.host,
                    "target_dir": str(dest_root),
                    "existing_skills": existing,
                    "next_step": "Pass --backup-existing (recommended) to move existing folders aside before updating.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    dest_root.mkdir(parents=True, exist_ok=True)
    backup_dir: str | None = None
    if existing and args.action == "update":
        if args.backup_existing:
            ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            bdir = dest_root.parent / f"_backup_ai_prompts_writing_{ts}"
            bdir.mkdir(parents=True, exist_ok=True)
            for s in existing:
                shutil.move(str(dest_root / s), str(bdir / s))
            backup_dir = str(bdir)
        elif args.force:
            for s in existing:
                shutil.rmtree(dest_root / s)

    for s in SKILL_NAMES:
        _copy_skill_tree(SKILLS_SRC / s, dest_root / s)

    ver = run_verify(dest_root, skip_selftest=args.skip_selftest)
    out = {
        "action": args.action,
        "host": args.host,
        "target_dir": str(dest_root),
        "backup_dir": backup_dir,
        "installed_skills": list(SKILL_NAMES),
        "verified": ver["verified"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ver["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
