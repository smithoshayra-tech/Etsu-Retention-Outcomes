"""Chart UTRGV vs Texas peer median (retention and 6-year graduation), report years 2016-2023."""
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent.parent
df = pd.read_csv(root / "outputs" / "utrgv_vs_tx_all.csv")
df = df[(df["set"] == "all TX 15-19") & (df["year"].between(2016, 2023))]

NAVY, GRAY, ORANGE = "#1F3864", "#8A8A8A", "#C55A11"
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
panels = [("ret", "First-year retention (%)", "Retention: UTRGV stays above the Texas peer median"),
          ("grad", "Six-year graduation (%)", "Graduation: above the median, with a dip in 2023")]
for ax, (m, ylab, title) in zip(axes, panels):
    d = df[df["metric"] == m].sort_values("year")
    ax.plot(d["year"], d["utrgv"], color=NAVY, lw=2.4, marker="o", label="UTRGV")
    ax.plot(d["year"], d["peer_median"], color=GRAY, lw=2, ls="--", marker="o", label="Texas peer median (34 peers)")
    ax.fill_between(d["year"], d["peer_median"], d["utrgv"], color=NAVY, alpha=0.08)
    ax.set_title(title, fontsize=10.5, loc="left", color="#222")
    ax.set_ylabel(ylab, fontsize=9)
    ax.set_xticks(range(2016, 2024))
    ax.tick_params(labelsize=8.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    last = d.iloc[-1]
    ax.annotate(f"{last['utrgv']:.0f}%" if m == "ret" else f"{last['utrgv']:.1f}%", (last["year"], last["utrgv"]),
                textcoords="offset points", xytext=(4, 6), fontsize=8.5, color=NAVY)
    if m == "ret":
        ax.set_ylim(67, 83)
        r = d[d["year"] == 2021].iloc[0]
        ax.annotate("2021: gap narrows to 2 points", (2021, r["utrgv"]), textcoords="offset points",
                    xytext=(-12, -48), fontsize=8.5, color=ORANGE, arrowprops=dict(arrowstyle="-", color=ORANGE))
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, fontsize=9, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0))
fig.text(0.01, 0.01, "Source: IPEDS public files, report years 2016-2023. Peers: Texas public doctoral/master's universities (Carnegie 15-19). "
         "Retention and graduation in one report year describe different entering classes.", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 0.94))
out = root / "outputs" / "figures"
out.mkdir(exist_ok=True)
fig.savefig(out / "utrgv_vs_texas_peers.png", dpi=170)
print("wrote", out / "utrgv_vs_texas_peers.png")
