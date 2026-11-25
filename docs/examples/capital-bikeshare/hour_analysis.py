"""Summarize fixed clock-hour windows in the UCI Capital Bikeshare data."""

import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DAY_FILE = ROOT.parents[1] / "validation/runs/2026-11-25-bike-sharing/workspace/02_evidence/day.csv"
HOUR_FILE = ROOT / "hour.csv.gz"
OUTPUT = ROOT / "hour-results.json"

DAY_HASH = "a6bcf826782d3c0fbfdcbeead17cd0884185a0dafe8ff10cd48a874ee7ba18be"
HOUR_HASH = "e03de4ee4ef4dc376ac6e04bf829673c6269e8eba5c60fa121640fa2f829504f"
CATEGORIES = ("casual", "registered", "cnt")
MORNING = (7, 8, 9)
AFTERNOON = (16, 17, 18)
WINDOWS = MORNING + AFTERNOON
ALL_HOURS = tuple(range(24))


def read_records(content, expected_hash):
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError("Input differs from the pinned UCI archive member")
    return csv.DictReader(io.StringIO(content.decode("ascii")))


def load_inputs():
    """Check hourly keys and totals against the independently archived daily table."""
    days = {r["dteday"]: r for r in read_records(DAY_FILE.read_bytes(), DAY_HASH)}
    hourly = defaultdict(dict)
    for row in read_records(gzip.decompress(HOUR_FILE.read_bytes()), HOUR_HASH):
        day, hour = row["dteday"], int(row["hr"])
        if day not in days or hour not in ALL_HOURS or hour in hourly[day]:
            raise ValueError(f"Unexpected or duplicate hourly key: {day} {hour}")
        if any(row[k] != days[day][k] for k in ("workingday", "holiday", "weekday", "yr", "mnth")):
            raise ValueError(f"Calendar fields differ from the day table: {day} {hour}")
        counts = {k: int(row[k]) for k in CATEGORIES}
        if min(counts.values()) < 0 or counts["cnt"] != counts["casual"] + counts["registered"]:
            raise ValueError(f"Inconsistent hourly rentals: {day} {hour}")
        hourly[day][hour] = counts
    if days.keys() != hourly.keys():
        raise ValueError("Day and hour files cover different dates")
    for day, row in days.items():
        for k in CATEGORIES:
            if sum(counts[k] for counts in hourly[day].values()) != int(row[k]):
                raise ValueError(f"Hourly sum differs from daily count: {day}, {k}")
    return days, hourly


def summarize(dates, days, hourly):
    n = Counter(int(days[day]["workingday"]) for day in dates)
    periods = ("morning", "afternoon", "both_windows", "outside_windows", "whole_day")
    totals = {period: {0: Counter(), 1: Counter()} for period in periods}
    for day in dates:
        row = days[day]
        day_type = int(row["workingday"])
        for k in CATEGORIES:
            morning = sum(hourly[day][h][k] for h in MORNING)
            afternoon = sum(hourly[day][h][k] for h in AFTERNOON)
            combined = morning + afternoon
            daily_total = int(row[k])
            for period, value in zip(periods, (morning, afternoon, combined, daily_total - combined, daily_total)):
                totals[period][day_type][k] += value
    summary = {}
    for period in periods:
        summary[period] = {}
        for k in CATEGORIES:
            work = Fraction(totals[period][1][k], n[1])
            nonwork = Fraction(totals[period][0][k], n[0])
            summary[period][k] = {
                "working_mean": float(work),
                "nonworking_mean": float(nonwork),
                "working_minus_nonworking": float(work - nonwork),
            }
    return {"n_working_days": n[1], "n_nonworking_days": n[0], "periods": summary}


def analyze():
    days, hourly = load_inputs()
    eligible = [day for day, records in hourly.items() if set(WINDOWS).issubset(records)]
    complete = [day for day, records in hourly.items() if len(records) == 24]
    profiles = []
    for day_type, group in ((1, "working"), (0, "nonworking")):
        group_days = [d for d in complete if int(days[d]["workingday"]) == day_type]
        for h in ALL_HOURS:
            means = {k: sum(hourly[day][h][k] for day in group_days) / len(group_days) for k in CATEGORIES}
            profiles.append({"day_type": group, "hour": h, **means})
    rows = sum(map(len, hourly.values()))
    return {
        "input": {
            "citation": "Fanaee-T, H. (2013). Bike Sharing [Dataset]. UCI Machine Learning Repository.",
            "doi": "https://doi.org/10.24432/C5W894",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "archive_url": "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip",
            "archive_sha256": "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401",
            "uncompressed_hour_csv_sha256": HOUR_HASH,
            "day_csv_sha256": DAY_HASH,
        },
        "coverage": {
            "observed_date_hour_pairs": rows,
            "dates_checked_against_day_csv": len(days),
            "absent_date_hour_labels_in_24_slot_grid": 24 * len(days) - rows,
            "missing_labels_by_hour": [sum(h not in records for records in hourly.values()) for h in ALL_HOURS],
            "dates_without_all_six_window_labels": sorted(set(days) - set(eligible)),
            "incomplete_24_label_dates_by_year": dict(Counter(day[:4] for day in days if len(hourly[day]) < 24)),
            "all_daily_rental_totals_match": True,
        },
        "morning_hour_labels": MORNING,
        "afternoon_hour_labels": AFTERNOON,
        "six_hour_days": summarize(eligible, days, hourly),
        "full_days": summarize(complete, days, hourly),
        "full_day_hourly_means": profiles,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the saved JSON against both source tables")
    args = parser.parse_args()
    serialized = json.dumps(analyze(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if serialized != OUTPUT.read_text(encoding="utf-8"):
            raise SystemExit("hour-results.json differs from the recomputed result")
        print("hour-results.json verified against both pinned UCI files")
    else:
        OUTPUT.write_bytes(serialized.encode("utf-8"))


if __name__ == "__main__":
    main()
