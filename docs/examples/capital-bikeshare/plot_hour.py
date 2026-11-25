"""Render the hourly profiles on the same full-day sample at every clock hour."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parent


def main():
    data = json.loads((ROOT / "hour-results.json").read_text(encoding="utf-8"))
    available = {f.name for f in font_manager.fontManager.ttflist}
    fonts = ["Microsoft YaHei", "Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC", "SimHei"]
    font = next((f for f in fonts if f in available), None)
    if font is None:
        raise SystemExit("Install a Chinese font listed in plot_hour.py to render the Chinese figure.")
    plt.rcParams.update({"font.family": font, "font.size": 10, "axes.unicode_minus": False})
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4), sharex=True)
    fig.subplots_adjust(left=.087, right=.984, bottom=.18, top=.80, wspace=.20)

    profiles = data["full_day_hourly_means"]
    panels = (("registered", "A  注册用户", "#21618c"), ("casual", "B  临时用户", "#b7501d"))
    for ax, (key, title, color) in zip(axes, panels):
        ax.axvspan(6.5, 9.5, color="#edede9", zorder=0)
        ax.axvspan(15.5, 18.5, color="#edede9", zorder=0)
        for group, linestyle in (("working", "-"), ("nonworking", (0, (4, 2)))):
            curve = [r for r in profiles if r["day_type"] == group]
            ax.plot([r["hour"] for r in curve], [r[key] for r in curve], lw=2.25,
                    color=color, linestyle=linestyle, zorder=3)
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=8)
        ax.set_xlim(0, 23)
        ax.set_ylim(bottom=0)
        ax.set_xticks([0, 4, 8, 12, 16, 20, 23])
        ax.grid(axis="y", color="#dae0e3", linewidth=.65)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#a9b4b8")
        ax.tick_params(color="#a9b4b8", labelcolor="#37434b", length=3)
    fig.supylabel("平均租借次数（次／小时）", x=.017, y=.46, fontsize=10)
    fig.supxlabel("小时", y=.045, fontsize=10)
    n_work = data["full_days"]["n_working_days"]
    n_other = data["full_days"]["n_nonworking_days"]
    labels = [Line2D([], [], color="#37434b", lw=2.2, label=f"工作日（{n_work} 天）"),
              Line2D([], [], color="#37434b", lw=2.2, ls=(0, (4, 2)), label=f"非工作日（{n_other} 天）"),
              Patch(facecolor="#edede9", edgecolor="#d2d2ce", label="选定的早、晚时段")]
    fig.legend(handles=labels, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(.53, .996), columnspacing=2)
    fig.savefig(ROOT / "hour-profiles.png", dpi=220, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
