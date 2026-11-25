"""Independently check the manuscript's nine table rows against UCI day.csv."""

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import sys
from contextlib import closing
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "workspace/02_evidence/day.csv"
DEFAULT_DRAFT = ROOT / "workspace/04_drafts/manuscript.md"
SHA256 = "a6bcf826782d3c0fbfdcbeead17cd0884185a0dafe8ff10cd48a874ee7ba18be"
HEADER = ["年份", "用户类别", "工作日日均", "非工作日日均", "差值"]
CATEGORIES = {"临时": "casual", "临时用户": "casual", "注册": "registered", "注册用户": "registered", "合计": "cnt"}
PERIODS = {"2011": "2011", "2012": "2012", "合并": "pooled", "两年合并": "pooled"}
DISPLAY_NUMBER = re.compile(r"[+−-]?(?:\d+|\d{1,3}(?:,\d{3})+)\.\d")


def reference_values():
    raw = DATA.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError("day.csv failed the archive member SHA-256 check")
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE days (day TEXT PRIMARY KEY, yr TEXT, work INT, casual INT, registered INT, cnt INT)")
        for row in csv.DictReader(io.StringIO(raw.decode("ascii"))):
            day = date.fromisoformat(row["dteday"])
            holiday, working, year_code = (int(row[k]) for k in ("holiday", "workingday", "yr"))
            counts = [int(row[k]) for k in ("casual", "registered", "cnt")]
            calendar_workday = holiday == 0 and day.weekday() < 5
            if day.year != 2011 + year_code or holiday not in (0, 1) or working != calendar_workday:
                raise ValueError(f"Calendar code mismatch at {day}")
            if min(counts) < 0 or sum(counts[:2]) != counts[2]:
                raise ValueError(f"Rental count mismatch at {day}")
            db.execute("INSERT INTO days VALUES(?,?,?,?,?,?)", (day.isoformat(), str(day.year), working, *counts))
        calendar = db.execute("SELECT MIN(day), MAX(day), COUNT(*) FROM days").fetchone()
        if calendar != ("2011-01-01", "2012-12-31", 731):
            raise ValueError(f"Incomplete calendar: {calendar}")
        summaries = db.execute("""
            SELECT yr, work, COUNT(*), SUM(casual), SUM(registered), SUM(cnt) FROM days GROUP BY yr, work
            UNION ALL
            SELECT 'pooled', work, COUNT(*), SUM(casual), SUM(registered), SUM(cnt) FROM days GROUP BY work
        """).fetchall()
    means = {}
    day_counts = {}
    for period, working, n, casual, registered, total in summaries:
        day_counts.setdefault(period, {})[str(working)] = n
        for category, count in zip(("casual", "registered", "cnt"), (casual, registered, total)):
            means.setdefault((period, category), {})[working] = Decimal(count) / Decimal(n)
    expected = {}
    for key, averages in means.items():
        values = (averages[1], averages[0], averages[1] - averages[0])
        expected[key] = [x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) for x in values]
    return expected, day_counts


def table_rows(markdown):
    """Yield (line number, parsed cells) from the uniquely titled table."""
    lines = markdown.splitlines()
    def split(line):
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    starts = [i for i, line in enumerate(lines) if split(line) == HEADER]
    if len(starts) != 1:
        raise ValueError(f"Expected one table with headers {HEADER}, found {len(starts)}")
    header = starts[0]
    delimiters = split(lines[header + 1]) if header + 1 < len(lines) else []
    if len(delimiters) != len(HEADER) or not all(re.fullmatch(r":?-{3,}:?", c) for c in delimiters):
        raise ValueError("Malformed Markdown table delimiter")
    for i in range(header + 2, len(lines)):
        if "|" not in lines[i]:
            break
        cells = split(lines[i])
        if len(cells) != len(HEADER):
            raise ValueError(f"Expected five cells on line {i + 1}")
        yield i + 1, cells


def check(draft):
    expected, day_counts = reference_values()
    issues = []
    seen = set()
    cells_checked = 0
    for line, (year, label, *values) in table_rows(draft.read_text(encoding="utf-8")):
        key = (PERIODS.get(year), CATEGORIES.get(label))
        if key not in expected or key in seen:
            raise ValueError(f"Unknown or duplicate year/category on line {line}: {year} / {label}")
        seen.add(key)
        for column, value, target in zip(HEADER[2:], values, expected[key]):
            cells_checked += 1
            normalized = value.replace(",", "").replace("−", "-")
            if not DISPLAY_NUMBER.fullmatch(value) or Decimal(normalized) != target:
                issues.append({"line": line, "year": year, "category": label, "column": column,
                               "observed": value, "expected": str(target)})
    if seen != set(expected):
        raise ValueError(f"Missing year/category rows: {sorted(set(expected) - seen)}")
    return {
        "status": "BLOCKED" if issues else "PASS",
        "data_sha256": SHA256,
        "days_by_period_and_workingday": day_counts,
        "unique_dates": sum(day_counts["pooled"].values()),
        "table_rows_checked": len(seen),
        "numeric_cells_checked": cells_checked,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--json-out", type=Path, help="also save this report as UTF-8 JSON")
    args = parser.parse_args()
    try:
        report = check(args.draft)
    except (ValueError, OSError, sqlite3.Error) as error:
        report = {"status": "BLOCKED", "error": str(error)}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_bytes(output.encode("utf-8"))
    sys.stdout.buffer.write(output.encode("utf-8"))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
