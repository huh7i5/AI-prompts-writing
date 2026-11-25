"""Check the numerical tables in paper.md directly against the two UCI files."""

import argparse
import csv
import gzip
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAILY = HERE.parents[1] / "validation/runs/2026-11-25-bike-sharing/workspace/02_evidence/day.csv"
FIELDS = ("casual", "registered", "cnt")
MORNING = {7, 8, 9}
AFTERNOON = {16, 17, 18}
LABELS = ("临时用户差值", "注册用户差值", "合计差值")


def date_groups(rows):
    return tuple([r for r in rows if int(r["workingday"]) == flag] for flag in (1, 0))


def raw_difference(rows):
    work, other = date_groups(rows)
    return tuple(Fraction(sum(int(r[f]) for r in work), len(work))
                 - Fraction(sum(int(r[f]) for r in other), len(other)) for f in FIELDS)


def strata(rows, include_weather=False):
    groups = defaultdict(list)
    for r in rows:
        key = (r["dteday"][:7], r["weathersit"] if include_weather else "")
        groups[key].append(r)
    return [g for g in groups.values() if all(date_groups(g))]


def standardize(groups):
    n = sum(map(len, groups))
    totals = [Fraction(0) for _ in FIELDS]
    for group in groups:
        for i, delta in enumerate(raw_difference(group)):
            totals[i] += delta * len(group)
    weighted = [value / n for value in totals]
    return (str(n), *weighted)


def display(value):
    if isinstance(value, str):
        return value
    number = Decimal(value.numerator) / Decimal(value.denominator)
    return format(number.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), "f")


def check_table(text, first_col, other_cols, expected):
    header = [first_col, *other_cols, *LABELS]
    rows = [[c.strip() for c in line.strip().strip("|").split("|")]
            if line.startswith("|") else [] for line in text.splitlines()]
    if rows.count(header) != 1:
        raise ValueError(f"Missing or repeated table headed by {header}")
    start = rows.index(header) + 2
    found = {}
    for cells in rows[start:]:
        if not cells:
            break
        key, *values = cells
        if key in found:
            raise ValueError(f"Duplicate table row: {key}")
        found[key] = [v.replace("−", "-").lstrip("+") for v in values]
    if found.keys() != expected.keys():
        raise ValueError(f"{first_col}: observed {list(found)}, expected {list(expected)}")
    for key, values in expected.items():
        wanted = [display(v) for v in values]
        if found[key] != wanted:
            raise ValueError(f"{first_col} / {key}: found {found[key]}, expected {wanted}")


def validate(paper):
    text = paper.read_text(encoding="utf-8")
    with DAILY.open(encoding="ascii", newline="") as f:
        days = list(csv.DictReader(f))
    periods = {year + " 年": [r for r in days if r["dteday"].startswith(year)]
               for year in ("2011", "2012")}
    periods["两年合并"] = days
    annual = {}
    for period, rows in periods.items():
        denominator = "/".join(str(len(g)) for g in date_groups(rows))
        annual[period] = denominator, *raw_difference(rows)
    check_table(text, "观察期", ["工作日/非工作日（天）"], annual)

    nonholidays = [d for d in days if d["holiday"] == "0"]
    weather_groups = strata(days, include_weather=True)
    overlap = [r for g in weather_groups for r in g]
    day_results = {
        "直接合并": (str(len(days)), *raw_difference(days)),
        "按年月比较": standardize(strata(days)),
        "剔除节假日，按年月比较": standardize(strata(nonholidays)),
        "天气有可比记录的日期，按年月比较": standardize(strata(overlap)),
        "同一批日期，按年月和天气比较": standardize(weather_groups),
    }
    check_table(text, "比较口径", ["天数"], day_results)

    by_date = defaultdict(dict)
    with gzip.open(HERE / "hour.csv.gz", "rt", encoding="ascii", newline="") as f:
        for row in csv.DictReader(f):
            h = int(row["hr"])
            group = by_date[row["dteday"]]
            if h in group:
                raise ValueError(f"Duplicate hour on {row['dteday']}")
            group[h] = row
    periods = {"上午三小时": MORNING, "下午三小时": AFTERNOON, "两个时段合计": MORNING | AFTERNOON,
               "其余时段": set(range(24)) - MORNING - AFTERNOON, "全天": set(range(24))}
    windows = defaultdict(list)
    for day in days:
        hours = by_date[day["dteday"]]
        if any(sum(int(row[f]) for row in hours.values()) != int(day[f]) for f in FIELDS):
            raise ValueError("Day/hour totals disagree: " + day["dteday"])
        if not (MORNING | AFTERNOON).issubset(hours):
            continue
        for name, labels in periods.items():
            available = [row for h, row in hours.items() if h in labels]
            counts = {f: sum(int(row[f]) for row in available) for f in FIELDS}
            windows[name].append(dict(counts, workingday=day["workingday"]))
    check_table(text, "时段", [], {name: raw_difference(rows) for name, rows in windows.items()})
    print(f"Verified {len(annual) + len(day_results) + len(windows)} labeled rows in 3 tables against day.csv and hour.csv.gz.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", type=Path, default=HERE / "paper.md")
    validate(parser.parse_args().paper)
