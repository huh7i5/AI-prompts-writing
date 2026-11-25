"""Swap two pooled category labels in a temporary manuscript and run both checks."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

sys.dont_write_bytecode = True
from check_sample import CATEGORIES, DATA, DEFAULT_DRAFT, PERIODS, ROOT, SHA256, table_rows


def swap_pooled_labels(source):
    positions = {}
    lines = source.splitlines(keepends=True)
    for line, (year, label, *_) in table_rows(source):
        category = CATEGORIES.get(label)
        if PERIODS.get(year) == "pooled" and category in ("casual", "registered"):
            if category in positions:
                raise ValueError(f"Duplicate pooled category: {label}")
            positions[category] = (line - 1, label)
    if set(positions) != {"casual", "registered"}:
        raise ValueError("The original needs two labeled pooled rows")
    for category, partner in (("casual", "registered"), ("registered", "casual")):
        index, old = positions[category]
        parts = lines[index].split("|")
        label_index = 2 if not parts[0].strip() else 1
        if parts[label_index].strip() != old:
            raise ValueError("Category cell is ambiguous")
        parts[label_index] = parts[label_index].replace(old, positions[partner][1])
        lines[index] = "|".join(parts)
    return "".join(lines)


def run_check(script, *arguments):
    result = subprocess.run([sys.executable, str(script), *map(str, arguments)], capture_output=True)
    if result.returncode not in (0, 2):
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    report = json.loads(result.stdout.decode("utf-8"))
    if report["status"] not in ("PASS", "WARN", "BLOCKED"):
        raise ValueError("Unexpected status from " + script.name)
    return result.returncode, report


def experiment(draft):
    native = ROOT.parents[3] / ".agents/skills/paper-draft-polish/scripts/style_and_draft_gate.py"
    additional = ROOT / "check_sample.py"
    source_bytes = draft.read_bytes()
    source = source_bytes.decode("utf-8")
    modified = swap_pooled_labels(source)
    pattern = r"[+−-]?\d+(?:\.\d+)?"
    numeric_tokens_unchanged = Counter(re.findall(pattern, source)) == Counter(re.findall(pattern, modified))
    with TemporaryDirectory(prefix="bike-sharing-control-") as temp:
        mutation = Path(temp) / "swapped.md"
        mutation.write_bytes(modified.encode("utf-8"))
        results = {}
        for label, path in (("original", draft), ("swapped", mutation)):
            native_code, gate = run_check(native, "--mode", "polish", "--source-text", draft, "--draft", path)
            check_code, audit = run_check(additional, "--draft", path)
            results[label] = {
                "native_gate": {"exit_code": native_code, "status": gate["status"], "findings": gate["findings"]},
                "additional_check": {"exit_code": check_code, "status": audit["status"],
                                     "numeric_cells_checked": audit.get("numeric_cells_checked"),
                                     "issues": audit.get("issues", []), **({"error": audit["error"]} if "error" in audit else {})},
            }
    data_hash = hashlib.sha256(DATA.read_bytes()).hexdigest()
    original_unchanged = draft.read_bytes() == source_bytes
    original, swapped = results["original"], results["swapped"]
    issues = swapped["additional_check"]["issues"]
    affected = {(CATEGORIES.get(f["category"]), f["column"]) for f in issues if PERIODS.get(f["year"]) == "pooled"}
    expected_affected = {(category, col) for category in ("casual", "registered") for col in ("工作日日均", "非工作日日均", "差值")}
    reproduced = (original_unchanged and data_hash == SHA256 and numeric_tokens_unchanged
                  and original["native_gate"]["status"] == swapped["native_gate"]["status"] == "PASS"
                  and original["additional_check"]["status"] == "PASS" and swapped["additional_check"]["status"] == "BLOCKED"
                  and len(issues) == 6 and affected == expected_affected)
    return {
        "result": "REPRODUCED" if reproduced else "UNEXPECTED",
        "change": "Only the two pooled casual and registered category labels were exchanged in a temporary copy.",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_unchanged": original_unchanged,
        "data_sha256": data_hash, "data_matches_pinned_snapshot": data_hash == SHA256,
        "numeric_token_multiset_unchanged": numeric_tokens_unchanged,
        **results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--json-out", type=Path, help="also save this report as UTF-8 JSON")
    args = parser.parse_args()
    report = experiment(args.draft.resolve())
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_bytes(output.encode("utf-8"))
    sys.stdout.buffer.write(output.encode("utf-8"))
    return 0 if report["result"] == "REPRODUCED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
