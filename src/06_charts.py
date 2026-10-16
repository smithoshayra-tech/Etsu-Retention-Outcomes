"""Two figures for the README. Palette: validated reference slots 1-3 (blue, orange, aqua)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=INK2, length=0, labelsize=10)
    ax.set_axisbelow(True)


def fig1():
    m = pd.read_csv(os.path.join(OUT, "model_metrics.csv"))
    m = m[m.test_year != "all"].assign(test_year=lambda d: d.test_year.astype(int))
    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=200, facecolor=SURFACE)
    style(ax)
    series = [("naive_last", "Same as last year", BLUE),
              ("naive_avg2", "Average of last two years", AQUA),
              ("ridge", "Ridge model", ORANGE)]
    for key, label, color in series:
        s = m[m.model == key].sort_values("test_year")
        ax.plot(s.test_year, s.mae, color=color, linewidth=2, marker="o", markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=label)
    ax.set_xticks(range(2018, 2025))
    ax.set_ylim(0, 5)
    ax.set_ylabel("Average miss, percentage points", color=INK2, fontsize=10)
    ax.set_xlabel("Report year predicted", color=INK2, fontsize=10)
    ax.annotate("2021 was hard for every method\n(the fall 2020 entering cohort)",
                xy=(2021, 4.5), xytext=(2021.25, 4.55), color=INK2, fontsize=9, va="center")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK, loc="lower left", ncol=3,
              bbox_to_anchor=(0, -0.32))
    ci = json.load(open(os.path.join(OUT, "model_vs_naive_ci.json")))["ridge"]
    fig.suptitle(f"No model reliably beats 'same as last year' (ridge gain {ci['mae_gain_points']:+.2f} points)",
                 x=0.06, y=0.99, ha="left", color=INK, fontsize=13, fontweight="bold")
    ax.set_title("Out-of-time test: each year predicted using only earlier years (55 peer institutions)",
                 loc="left", color=INK2, fontsize=9.5, pad=6)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(os.path.join(FIG, "model_error_by_year.png"), facecolor=SURFACE)
    plt.close(fig)


def fig2():
    b = pd.read_csv(os.path.join(OUT, "etsu_backtest.csv"))
    fc = json.load(open(os.path.join(OUT, "etsu_forecast_2025.json")))
    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=200, facecolor=SURFACE)
    style(ax)
    ax.plot(b.report_year, b.y, color=BLUE, linewidth=2.2, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label="ETSU actual")
    ax.plot(b.report_year, b.ridge, color=ORANGE, linewidth=2, marker="o", markersize=6,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label="Ridge model (out-of-time)")
    ax.plot(b.report_year, b.naive_last, color=AQUA, linewidth=1.6, linestyle="--", marker="o",
            markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5, label="Same as last year")
    ax.errorbar([2025], [fc["ridge"]], yerr=[fc["ridge_80pct_band_pts"]], fmt="o", color=ORANGE,
                markersize=7, markerfacecolor=SURFACE, markeredgewidth=1.8, capsize=4, linewidth=1.4)
    ax.annotate(f"2025 forecast {fc['ridge']:.0f}%\n(not yet validated)",
                xy=(2025, fc["ridge"]), xytext=(2023.6, 60.5), color=INK2, fontsize=9, ha="left")
    ax.set_xticks(range(2018, 2026))
    ax.set_ylim(58, 82)
    ax.set_ylabel("Full-time retention rate, %", color=INK2, fontsize=10)
    ax.set_xlabel("Report year", color=INK2, fontsize=10)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK, loc="lower left", ncol=3,
              bbox_to_anchor=(0, -0.32))
    fig.suptitle("ETSU's 2021 drop was not predictable from the prior year",
                 x=0.06, y=0.99, ha="left", color=INK, fontsize=13, fontweight="bold")
    ax.set_title("ETSU retention, actual vs. predictions made one year ahead; band is the model's typical 80% miss",
                 loc="left", color=INK2, fontsize=9.5, pad=6)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(os.path.join(FIG, "etsu_backtest.png"), facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    print("figures written to", FIG)
