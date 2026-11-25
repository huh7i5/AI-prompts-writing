"""Daily rental contrasts by calendar month in the archived UCI Bike Sharing data."""

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date, timedelta
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "validation/runs/2026-11-25-bike-sharing/workspace/02_evidence/day.csv"
DIGEST = "a6bcf826782d3c0fbfdcbeead17cd0884185a0dafe8ff10cd48a874ee7ba18be"
OUTCOMES = ("registered", "casual", "cnt")


def read_days():
    data = DATA.read_bytes()
    if hashlib.sha256(data).hexdigest() != DIGEST:
        raise ValueError("The daily CSV differs from the original UCI archive member")
    days = []
    seen = set()
    for raw in csv.DictReader(io.StringIO(data.decode("ascii"))):
        day = date.fromisoformat(raw["dteday"])
        row = {key: int(raw[key]) for key in (*OUTCOMES, "holiday", "workingday", "weathersit")}
        if (day in seen or row["holiday"] not in (0, 1)
                or row["workingday"] != int(day.weekday() < 5 and not row["holiday"])
                or min(row[k] for k in OUTCOMES) < 0 or row["cnt"] != row["registered"] + row["casual"]):
            raise ValueError(f"Invalid calendar or counts on {day}")
        seen.add(day)
        row.update(month=day.strftime("%Y-%m"), year=day.year)
        days.append(row)
    if seen != {date(2011, 1, 1) + timedelta(days=i) for i in range(731)}:
        raise ValueError("Incomplete study calendar")
    return days


def aggregate(days):
    """Integer sums and a day count for each of the two day types."""
    totals = {0: Counter(), 1: Counter()}
    for row in days:
        bucket = totals[row["workingday"]]
        bucket["n"] += 1
        for col in OUTCOMES:
            bucket[col] += row[col]
    return totals


def contrasts(totals):
    work, nonwork = totals[1], totals[0]
    return {k: Fraction(work[k], work["n"]) - Fraction(nonwork[k], nonwork["n"]) for k in OUTCOMES}


def crude(days):
    totals = aggregate(days)
    result = {}
    for code, label in ((1, "work"), (0, "nonwork")):
        group = totals[code]
        result[label] = {
            "n_days": group["n"],
            "sums": {k: group[k] for k in OUTCOMES},
            "means": {k: group[k] / group["n"] for k in OUTCOMES},
            "registered_share_of_trips": group["registered"] / group["cnt"],
        }
    result["work_minus_nonwork"] = {k: float(v) for k, v in contrasts(totals).items()}
    return result


def standardize(days, fields):
    """Use the retained calendar days, pooled across day types, as the target mix."""
    strata = defaultdict(list)
    for row in days:
        strata[tuple(row[field] for field in fields)].append(row)
    weighted = Counter()
    retained = []
    excluded = []
    records = []
    for key in sorted(strata):
        subset = strata[key]
        totals = aggregate(subset)
        entry = {**dict(zip(fields, key)), "work_days": totals[1]["n"], "nonwork_days": totals[0]["n"]}
        if not all(group["n"] for group in totals.values()):
            excluded.append(entry)
            continue
        diff = contrasts(totals)
        for col in OUTCOMES:
            weighted[col] += diff[col] * len(subset)
        records.append({**entry, "work_minus_nonwork": {k: float(v) for k, v in diff.items()}})
        retained.extend(subset)
    if not retained:
        raise ValueError("No stratum contained both day types")
    n_work = sum(row["workingday"] for row in retained)
    smaller_groups = [min(r["work_days"], r["nonwork_days"]) for r in records]
    summary = {
        "observed_strata": len(strata),
        "retained_strata": len(records),
        "retained_strata_with_a_single_day_in_either_group": smaller_groups.count(1),
        "retained_strata_with_at_most_two_days_in_either_group": sum(n <= 2 for n in smaller_groups),
        "days": len(retained),
        "work_days": n_work,
        "nonwork_days": len(retained) - n_work,
        "work_minus_nonwork": {k: float(weighted[k] / len(retained)) for k in OUTCOMES},
        "excluded_strata": excluded,
    }
    return summary, records, retained


def analyze():
    days = read_days()
    monthly, months, _ = standardize(days, ["month"])
    sign_counts = {}
    for k in OUTCOMES:
        values = [row["work_minus_nonwork"][k] for row in months]
        sign_counts[k] = {"positive": sum(v > 0 for v in values), "negative": sum(v < 0 for v in values),
                          "zero": values.count(0)}
    ordinary, _, _ = standardize([d for d in days if not d["holiday"]], ["month"])
    weather, _, common = standardize(days, ["month", "weathersit"])
    same_days, _, _ = standardize(common, ["month"])
    return {
        "daily_csv_sha256": DIGEST,
        "contrast_units": "rentals/day; working day minus nonworking day",
        "stratum_weight": "number of retained calendar days in stratum / all retained calendar days",
        "crude": {"2011": crude([d for d in days if d["year"] == 2011]),
                  "2012": crude([d for d in days if d["year"] == 2012]), "pooled": crude(days)},
        "month_standardized": monthly,
        "month_sign_counts": sign_counts,
        "months": months,
        "month_standardized_excluding_holidays": ordinary,
        "month_and_weather_standardized": weather,
        "month_standardized_on_weather_common_support": same_days,
    }


def plot_months(months):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib import font_manager, ticker

    # Matplotlib's bundled font can draw the English labels on minimal installations.
    available = {font.name for font in font_manager.fontManager.ttflist}
    chinese_font = next((f for f in ("Microsoft YaHei", "Noto Sans CJK SC", "Source Han Sans SC", "SimHei")
                         if f in available), None)
    config = {"font.family": chinese_font or "DejaVu Sans", "font.size": 11, "axes.unicode_minus": False}
    with plt.rc_context(config):
        fig, ax = plt.subplots(figsize=(10.0, 4.4), layout="constrained")
        labels = ("注册用户", "临时用户", "合计") if chinese_font else ("Registered", "Casual", "Combined")
        styles = [("#21618c", "o", "-"), ("#b7501d", "s", "--"), ("#37434b", "D", "-.")]
        for key, label, (color, marker, line) in zip(OUTCOMES, labels, styles):
            values = [m["work_minus_nonwork"][key] for m in months]
            ax.plot(range(len(months)), values, marker=marker, linestyle=line, linewidth=1.7,
                    markersize=4, color=color, label=label)
        ax.axhline(0, color="#5c6570", linewidth=0.9)
        ax.axvline(11.5, color="#b3bac0", linestyle=":", linewidth=0.9)
        ax.yaxis.set_major_locator(ticker.MultipleLocator(500))
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#e1e6e9", linewidth=0.65)
        ticks = [0, 3, 6, 9, 12, 15, 18, 21, 23]
        ax.set_xticks(ticks, [months[i]["month"] for i in ticks])
        ylabel = "工作日减非工作日（次/日）" if chinese_font else "Workday minus nonworkday (rentals/day)"
        ax.set_ylabel(ylabel)
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.00), ncol=3, frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["bottom", "left"]].set_color("#98a4ab")
        ax.set_xlim(-0.4, 23.4)
        fig.savefig(HERE / "monthly-contrasts.png", dpi=180, facecolor="white")
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare the recalculation with day-results.json")
    parser.add_argument("--plot", action="store_true", help="also regenerate the figure (requires Matplotlib)")
    options = parser.parse_args()
    computed = analyze()
    result_path = HERE / "day-results.json"
    if options.check:
        if json.loads(result_path.read_text(encoding="utf-8")) != computed:
            raise SystemExit("Daily results differ from the saved values")
        print("Daily results verified from UCI day.csv.")
    else:
        result_path.write_bytes((json.dumps(computed, indent=2) + "\n").encode("utf-8"))
        print("Wrote day-results.json.")
    if options.plot:
        plot_months(computed["months"])
        print("Wrote monthly-contrasts.png.")


if __name__ == "__main__":
    main()
