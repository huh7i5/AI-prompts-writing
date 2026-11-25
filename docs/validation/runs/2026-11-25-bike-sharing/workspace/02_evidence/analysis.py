"""Summarize observed Capital Bikeshare rentals in UCI's pinned daily file."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
INPUT_SHA256 = "a6bcf826782d3c0fbfdcbeead17cd0884185a0dafe8ff10cd48a874ee7ba18be"
COUNTS = ("casual", "registered", "cnt")
START, END = date(2011, 1, 1), date(2012, 12, 31)


def analyze(source):
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != INPUT_SHA256:
        raise ValueError(f"{source.name} differs from the archived UCI file: {digest}")

    rows = list(csv.DictReader(io.StringIO(raw.decode("ascii"), newline="")))
    dates = []
    groups = {}
    checks = Counter()
    for row in rows:
        day = date.fromisoformat(row["dteday"])
        dates.append(day)
        working = int(row["workingday"])
        holiday = int(row["holiday"])
        expected_working = day.weekday() < 5 and holiday == 0
        counts = {name: int(row[name]) for name in COUNTS}
        checks["year_code_mismatches"] += int(row["yr"]) != day.year - 2011
        checks["workingday_or_holiday_code_errors"] += (
            holiday not in (0, 1) or working not in (0, 1) or working != expected_working
        )
        checks["count_identity_mismatches"] += counts["cnt"] != counts["casual"] + counts["registered"]
        checks["negative_count_rows"] += min(counts.values()) < 0
        for period in (str(day.year), "pooled"):
            bucket = groups.setdefault((period, working), Counter())
            bucket.update(counts)
            bucket["n_days"] += 1

    calendar = {START + timedelta(days=i) for i in range((END - START).days + 1)}
    distinct = set(dates)
    checks["duplicate_dates"] = len(dates) - len(distinct)
    checks["missing_calendar_dates"] = len(calendar - distinct)
    checks["out_of_period_dates"] = len(distinct - calendar)
    if any(checks.values()):
        raise ValueError(f"Input checks failed: {dict(checks)}")

    summaries = []
    contrasts = []
    for period in ("2011", "2012", "pooled"):
        means = {}
        for working in (0, 1):
            bucket = groups[period, working]
            n = bucket["n_days"]
            means[working] = {name: Fraction(bucket[name], n) for name in COUNTS}
            summaries.append({
                "period": period,
                "workingday": working,
                "n_days": n,
                "rental_sums": {name: bucket[name] for name in COUNTS},
                "mean_rentals_per_day": {name: float(mean) for name, mean in means[working].items()},
            })
        contrasts.append({
            "period": period,
            "working_minus_nonworking_rentals_per_day": {
                name: float(means[1][name] - means[0][name]) for name in COUNTS
            },
        })

    return {
        "source_file": source.name,
        "sha256": digest,
        "calendar": {"first_date": min(dates).isoformat(), "last_date": max(dates).isoformat(),
                     "n_rows": len(rows), "n_unique_dates": len(distinct)},
        "checks": dict(checks),
        "groups": summaries,
        "contrasts": contrasts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare with the saved results.json")
    args = parser.parse_args()
    serialized = json.dumps(analyze(DIRECTORY / "day.csv"), indent=2) + "\n"
    output = DIRECTORY / "results.json"
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != serialized:
            raise SystemExit("results.json is missing or differs from recomputed results")
        print("Verified results.json against day.csv.")
    else:
        output.write_bytes(serialized.encode("utf-8"))
        print("Wrote results.json.")


if __name__ == "__main__":
    main()
