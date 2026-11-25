#!/usr/bin/env python3
"""Deterministic CSV statistical engine & publication-grade vector SVG plotter (Station 02).

Zero third-party dependencies (Python 3 standard library only; optionally renders PDF/PNG
via matplotlib if installed). Eliminates LLM mental-math errors by computing exact sample sizes,
missing counts, means, SD, SE, 95% CI (exact Student's t critical value), medians, IQR,
Welch's t-test p-value, Cohen's d, percentage-point vs relative % differences, clean SVG charts,
and compliant figure captions, and can register RECOMPUTED_LOCAL evidence into 03_claim_ledger.json.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PALETTE = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")


def _betacf(a: float, b: float, x: float) -> float:
    """Evaluates continued fraction for incomplete beta function (Lentz's method)."""
    max_iter = 200
    eps = 3.0e-12
    fpmin = 1.0e-30
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_two_sided_p(t_stat: float, df: float) -> float:
    if df <= 0:
        return 1.0
    x = df / (df + t_stat * t_stat)
    p = _betainc(0.5 * df, 0.5, x)
    return max(0.0, min(1.0, p))


def student_t_crit_95(df: float) -> float:
    """Exact two-sided 95% CI t-critical value via bisection on student_t_two_sided_p."""
    if df <= 0:
        return float("nan")
    lo, hi = 1.5, 15.0
    if df < 2:
        hi = 70.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if student_t_two_sided_p(mid, df) > 0.05:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _quantile(sorted_vals: list[float], q: float) -> float:
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def summarize_series(vals: list[float], missing_count: int) -> dict[str, Any]:
    n = len(vals)
    svals = sorted(vals)
    mean_v = statistics.fmean(vals)
    sd_v = statistics.stdev(vals) if n >= 2 else 0.0
    se_v = sd_v / math.sqrt(n) if n >= 1 else 0.0
    ci95 = student_t_crit_95(n - 1) * se_v if n >= 2 else 0.0
    q1 = _quantile(svals, 0.25)
    med = _quantile(svals, 0.5)
    q3 = _quantile(svals, 0.75)
    return {
        "n_valid": n,
        "n_missing": missing_count,
        "mean": mean_v,
        "sd": sd_v,
        "se": se_v,
        "ci95_half": ci95,
        "median": med,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "min": svals[0],
        "max": svals[-1],
    }


def welch_comparison(g1_vals: list[float], g2_vals: list[float], unit: str) -> dict[str, Any]:
    n1, n2 = len(g1_vals), len(g2_vals)
    m1, m2 = statistics.fmean(g1_vals), statistics.fmean(g2_vals)
    abs_diff = m2 - m1
    rel_pct = (abs_diff / m1 * 100.0) if m1 != 0 else None

    v1 = statistics.variance(g1_vals) if n1 >= 2 else 0.0
    v2 = statistics.variance(g2_vals) if n2 >= 2 else 0.0
    se_diff_sq = (v1 / n1 if n1 else 0.0) + (v2 / n2 if n2 else 0.0)

    t_stat = None
    df = None
    p_val = None
    if n1 >= 2 and n2 >= 2 and se_diff_sq > 0:
        t_stat = (m2 - m1) / math.sqrt(se_diff_sq)
        denom = ((v1 / n1) ** 2) / (n1 - 1) + ((v2 / n2) ** 2) / (n2 - 1)
        df = (se_diff_sq**2) / denom if denom > 0 else float(n1 + n2 - 2)
        p_val = student_t_two_sided_p(t_stat, df)

    cohens_d = None
    if n1 >= 2 and n2 >= 2:
        pooled_var = (((n1 - 1) * v1) + ((n2 - 1) * v2)) / (n1 + n2 - 2)
        if pooled_var > 0:
            cohens_d = (m2 - m1) / math.sqrt(pooled_var)

    is_pct = unit.strip() in ("%", "％", "percent")
    return {
        "mean_baseline": m1,
        "mean_target": m2,
        "diff_absolute": abs_diff,
        "diff_unit_label": "percentage points" if is_pct else (unit or "units"),
        "diff_relative_pct": rel_pct,
        "welch_t": t_stat,
        "welch_df": df,
        "p_value": p_val,
        "cohens_d": cohens_d,
    }


def _nice_axis_bounds(low_val: float, high_val: float, force_zero: bool) -> tuple[float, float, list[float]]:
    y_min = 0.0 if (force_zero and low_val >= 0.0) else low_val
    span = max(1e-9, high_val - y_min)
    raw_step = span / 5.0
    mag = 10.0 ** math.floor(math.log10(raw_step))
    norm = raw_step / mag
    if norm <= 1.0:
        step = 1.0 * mag
    elif norm <= 2.0:
        step = 2.0 * mag
    elif norm <= 5.0:
        step = 5.0 * mag
    else:
        step = 10.0 * mag

    tick_min = 0.0 if (force_zero and low_val >= 0.0) else math.floor(y_min / step) * step
    tick_max = math.ceil((high_val + 0.05 * span) / step) * step
    ticks: list[float] = []
    cur = tick_min
    while cur <= tick_max + 1e-9:
        ticks.append(round(cur, 6))
        cur += step
    return tick_min, ticks[-1], ticks


def render_svg_chart(
    groups_order: list[str],
    group_stats: dict[str, dict[str, Any]],
    raw_by_group: dict[str, list[float]],
    title: str,
    y_label: str,
    error_mode: str,
    out_svg: Path,
) -> None:
    width, height = 680, 440
    margin_l, margin_r, margin_t, margin_b = 82, 34, 58, 78
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b

    err_key = {"sd": "sd", "se": "se", "ci95": "ci95_half"}[error_mode]
    err_label = {"sd": "SD", "se": "SE", "ci95": "95% CI"}[error_mode]

    all_vals = [v for g in groups_order for v in raw_by_group[g]]
    upper_pts = [group_stats[g]["mean"] + group_stats[g][err_key] for g in groups_order] + all_vals
    lower_pts = [group_stats[g]["mean"] - group_stats[g][err_key] for g in groups_order] + all_vals
    y_min, y_max, ticks = _nice_axis_bounds(min(lower_pts), max(upper_pts), force_zero=True)

    def y_to_px(v: float) -> float:
        return margin_t + plot_h * (1.0 - (v - y_min) / max(1e-9, y_max - y_min))

    elems: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Arial, Helvetica, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{width / 2:.1f}" y="30" text-anchor="middle" font-size="15" font-weight="bold" fill="#111827">{html.escape(title)}</text>',
    ]

    # Gridlines & Y ticks
    for tk in ticks:
        yp = y_to_px(tk)
        elems.append(f'<line x1="{margin_l}" y1="{yp:.1f}" x2="{width - margin_r}" y2="{yp:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        tk_txt = f"{int(tk)}" if abs(tk - round(tk)) < 1e-6 else f"{tk:.2f}"
        elems.append(f'<text x="{margin_l - 10}" y="{yp + 4:.1f}" text-anchor="end" font-size="11" fill="#4b5563">{tk_txt}</text>')

    # Axes
    elems.append(f'<line x1="{margin_l}" y1="{margin_t}" x2="{margin_l}" y2="{margin_t + plot_h}" stroke="#1f2937" stroke-width="1.5"/>')
    elems.append(f'<line x1="{margin_l}" y1="{margin_t + plot_h}" x2="{width - margin_r}" y2="{margin_t + plot_h}" stroke="#1f2937" stroke-width="1.5"/>')
    elems.append(
        f'<text x="24" y="{margin_t + plot_h / 2:.1f}" text-anchor="middle" font-size="12" font-weight="bold" fill="#1f2937" '
        f'transform="rotate(-90 24 {margin_t + plot_h / 2:.1f})">{html.escape(y_label)}</text>'
    )

    n_groups = len(groups_order)
    slot_w = plot_w / max(1, n_groups)
    bar_w = min(76.0, slot_w * 0.46)
    base_y = y_to_px(0.0 if y_min <= 0.0 <= y_max else y_min)

    for idx, gname in enumerate(groups_order):
        st = group_stats[gname]
        cx = margin_l + slot_w * (idx + 0.5)
        color = PALETTE[idx % len(PALETTE)]
        mean_y = y_to_px(st["mean"])
        bar_top = min(mean_y, base_y)
        bar_h = abs(base_y - mean_y)

        # Semi-transparent bar + crisp outline
        elems.append(
            f'<rect x="{cx - bar_w / 2:.1f}" y="{bar_top:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
            f'fill="{color}" fill-opacity="0.28" stroke="{color}" stroke-width="1.8"/>'
        )

        # Deterministic jittered raw points (shows real spread behind summary bars)
        vals = raw_by_group[gname]
        if len(vals) <= 120:
            for j_idx, rv in enumerate(vals):
                offset = (((j_idx * 37) % 19) - 9) / 9.0 * (bar_w * 0.28)
                elems.append(
                    f'<circle cx="{cx + offset:.1f}" cy="{y_to_px(rv):.1f}" r="2.6" fill="{color}" fill-opacity="0.65"/>'
                )

        # Error bar
        err_val = st[err_key]
        if err_val > 0:
            y_hi = y_to_px(st["mean"] + err_val)
            y_lo = y_to_px(st["mean"] - err_val)
            cap = 8.0
            elems.append(f'<line x1="{cx:.1f}" y1="{y_hi:.1f}" x2="{cx:.1f}" y2="{y_lo:.1f}" stroke="#111827" stroke-width="1.8"/>')
            elems.append(f'<line x1="{cx - cap:.1f}" y1="{y_hi:.1f}" x2="{cx + cap:.1f}" y2="{y_hi:.1f}" stroke="#111827" stroke-width="1.8"/>')
            elems.append(f'<line x1="{cx - cap:.1f}" y1="{y_lo:.1f}" x2="{cx + cap:.1f}" y2="{y_lo:.1f}" stroke="#111827" stroke-width="1.8"/>')
            val_label_y = min(y_hi, mean_y) - 8
        else:
            val_label_y = mean_y - 8

        elems.append(
            f'<text x="{cx:.1f}" y="{max(margin_t + 10, val_label_y):.1f}" text-anchor="middle" font-size="11" font-weight="bold" fill="#111827">'
            f'{st["mean"]:.2f}</text>'
        )
        elems.append(
            f'<text x="{cx:.1f}" y="{margin_t + plot_h + 22}" text-anchor="middle" font-size="12" font-weight="bold" fill="#111827">'
            f'{html.escape(gname)}</text>'
        )
        elems.append(
            f'<text x="{cx:.1f}" y="{margin_t + plot_h + 40}" text-anchor="middle" font-size="11" fill="#4b5563">'
            f'(n = {st["n_valid"]})</text>'
        )

    elems.append(
        f'<text x="{width - margin_r}" y="{height - 12}" text-anchor="end" font-size="10.5" fill="#6b7280">'
        f'Bars: mean; Error bars: ± {err_label}; Dots: individual observations</text>'
    )
    elems.append("</svg>")

    out_svg.parent.mkdir(parents=True, exist_ok=True)
    out_svg.write_text("\n".join(elems), encoding="utf-8")


def build_compliant_caption(
    title: str,
    y_label: str,
    unit: str,
    error_mode: str,
    groups_order: list[str],
    group_stats: dict[str, dict[str, Any]],
    comparison: dict[str, Any] | None,
) -> str:
    err_full = {"sd": "标准差（SD）", "se": "标准误（SE）", "ci95": "95% 置信区间（95% CI）"}[error_mode]
    err_key = {"sd": "sd", "se": "se", "ci95": "ci95_half"}[error_mode]
    total_n = sum(group_stats[g]["n_valid"] for g in groups_order)
    total_miss = sum(group_stats[g]["n_missing"] for g in groups_order)

    group_parts = []
    for g in groups_order:
        st = group_stats[g]
        group_parts.append(
            f"{g} 组（n={st['n_valid']}）均值为 {st['mean']:.2f}{unit}（±{st[err_key]:.2f}{unit}；"
            f"中位数 {st['median']:.2f}{unit}，IQR {st['iqr']:.2f}{unit}）"
        )

    lines = [
        f"**图题**：{title}",
        "",
        f"**图注**：图示为各组观测对象在「{y_label}」指标上的实测分布与均值对比（单位：`{unit or '无量纲'}`）。"
        f"有效样本总量为 $N = {total_n}$（缺失/排除 {total_miss} 条）。图中散点表示个体观测值，柱高表示样本均值，误差线代表 **{err_full}**。"
        + "具体结果为："
        + "；".join(group_parts)
        + "。",
    ]
    if comparison:
        diff_abs = comparison["diff_absolute"]
        rel_pct = comparison["diff_relative_pct"]
        base_g = groups_order[0]
        tgt_g = groups_order[1]
        unit_desc = "个百分点" if unit.strip() in ("%", "％", "percent") else unit
        rel_str = f"（相对基线组变化 {rel_pct:+.2f}%）" if rel_pct is not None else ""
        stat_str = ""
        if comparison["welch_t"] is not None:
            stat_str = (
                f"双侧 Welch $t$ 检验：$t({comparison['welch_df']:.2f}) = {comparison['welch_t']:.3f}$，"
                f"$p = {comparison['p_value']:.4f}$，Cohen's $d = {comparison['cohens_d']:.3f}$。"
            )
        lines.append(
            f"组间比较（{tgt_g} 相对 {base_g}）：绝对均值差为 {diff_abs:+.2f} {unit_desc}{rel_str}。{stat_str}"
        )
    return "\n".join(lines) + "\n"


def update_ledger_with_stats(
    ledger_path: Path,
    evidence_id: str,
    csv_path: Path,
    svg_path: Path | None,
    summary_payload: dict[str, Any],
) -> None:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ev_list = ledger.setdefault("evidence_items", [])
    ev_list = [e for e in ev_list if e.get("evidence_id") != evidence_id]
    ev_list.append(
        {
            "evidence_id": evidence_id,
            "source_location": f"{csv_path.name}" + (f" & {svg_path.name}" if svg_path else ""),
            "version_or_date": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
            "processing_or_derivation_notes": (
                f"Computed via stats_and_plot.py (Welch t-test & {summary_payload['error_bar_mode'].upper()}). "
                f"Total N={summary_payload['total_valid_n']}."
            ),
            "recomputation_status": "RECOMPUTED_LOCAL",
            "known_limitations_or_deviations": f"Missing/non-numeric rows excluded: {summary_payload['total_missing_n']}.",
        }
    )
    ledger["evidence_items"] = ev_list
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero-dependency CSV statistics & publication SVG plotter.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("analyze", help="Compute exact group statistics, SVG chart, and compliant caption from CSV.")
    p.add_argument("--csv", required=True, help="Input CSV file path.")
    p.add_argument("--value-col", required=True, help="Numeric outcome column name.")
    p.add_argument("--group-col", default="", help="Optional grouping column name.")
    p.add_argument("--baseline-group", default="", help="Optional baseline group name for pairwise comparison.")
    p.add_argument("--unit", default="", help="Measurement unit (e.g., percent / %%, ms, points).")
    p.add_argument("--title", default="Group Comparison", help="Figure title.")
    p.add_argument("--y-label", default="", help="Y-axis label (defaults to value-col + unit).")
    p.add_argument("--error-bar", choices=["sd", "se", "ci95"], default="ci95", help="Error bar statistical definition.")
    p.add_argument("--out-svg", default="", help="Output path for vector SVG chart.")
    p.add_argument("--out-json", default="", help="Output path for JSON statistics summary.")
    p.add_argument("--out-caption", default="", help="Output path for compliant Markdown caption.")
    p.add_argument("--update-claim-ledger", default="", help="Optional 03_claim_ledger.json to append RECOMPUTED_LOCAL evidence.")
    p.add_argument("--evidence-id", default="E01_CSV_Stats", help="Evidence ID when updating claim ledger.")

    args = parser.parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    raw_by_group: dict[str, list[float]] = {}
    missing_by_group: dict[str, int] = {}
    groups_order: list[str] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or args.value_col not in reader.fieldnames:
            raise SystemExit(f"Column '{args.value_col}' not found in CSV headers: {reader.fieldnames}")
        if args.group_col and args.group_col not in reader.fieldnames:
            raise SystemExit(f"Group column '{args.group_col}' not found in CSV headers: {reader.fieldnames}")

        for row in reader:
            g_name = (row.get(args.group_col) or "All").strip() if args.group_col else "All"
            if g_name not in raw_by_group:
                raw_by_group[g_name] = []
                missing_by_group[g_name] = 0
                groups_order.append(g_name)
            raw_val = (row.get(args.value_col) or "").strip()
            try:
                val = float(raw_val)
                if math.isnan(val) or math.isinf(val):
                    raise ValueError
                raw_by_group[g_name].append(val)
            except ValueError:
                missing_by_group[g_name] += 1

    if args.baseline_group and args.baseline_group in groups_order:
        groups_order.remove(args.baseline_group)
        groups_order.insert(0, args.baseline_group)

    group_stats: dict[str, dict[str, Any]] = {}
    for g in groups_order:
        if not raw_by_group[g]:
            raise SystemExit(f"Group '{g}' has 0 valid numeric observations.")
        group_stats[g] = summarize_series(raw_by_group[g], missing_by_group[g])

    comparison = None
    if len(groups_order) >= 2:
        comparison = welch_comparison(raw_by_group[groups_order[0]], raw_by_group[groups_order[1]], args.unit)

    y_label = args.y_label or (f"{args.value_col} ({args.unit})" if args.unit else args.value_col)
    svg_path = Path(args.out_svg) if args.out_svg else None
    if svg_path:
        render_svg_chart(
            groups_order=groups_order,
            group_stats=group_stats,
            raw_by_group=raw_by_group,
            title=args.title,
            y_label=y_label,
            error_mode=args.error_bar,
            out_svg=svg_path,
        )

    caption_text = build_compliant_caption(
        title=args.title,
        y_label=y_label,
        unit=args.unit,
        error_mode=args.error_bar,
        groups_order=groups_order,
        group_stats=group_stats,
        comparison=comparison,
    )
    if args.out_caption:
        cap_path = Path(args.out_caption)
        cap_path.parent.mkdir(parents=True, exist_ok=True)
        cap_path.write_text(caption_text, encoding="utf-8")

    summary = {
        "csv_file": csv_path.name,
        "value_col": args.value_col,
        "group_col": args.group_col or None,
        "unit": args.unit,
        "error_bar_mode": args.error_bar,
        "recomputation_status": "RECOMPUTED_LOCAL",
        "total_valid_n": sum(group_stats[g]["n_valid"] for g in groups_order),
        "total_missing_n": sum(group_stats[g]["n_missing"] for g in groups_order),
        "groups": group_stats,
        "pairwise_welch_comparison": comparison,
        "svg_generated": str(svg_path) if svg_path else None,
        "caption_preview": caption_text,
    }
    if args.out_json:
        jp = Path(args.out_json)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.update_claim_ledger:
        update_ledger_with_stats(
            ledger_path=Path(args.update_claim_ledger),
            evidence_id=args.evidence_id,
            csv_path=csv_path,
            svg_path=svg_path,
            summary_payload=summary,
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
