"""Run the validation checks and analysis queries, cross-check in pandas, draw charts."""
import re
import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1])
DB = ROOT / "outputs" / "ipeds_uvu.db"
OUT = ROOT / "outputs"
CH = OUT / "charts"
CH.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(DB)

# ---------- 1. validation checks ----------
checks = pd.read_sql_query(open(ROOT / "sql" / "02_checks.sql").read(), con)
checks.to_csv(OUT / "checks_summary.csv", index=False)
print(checks.to_string(index=False))
hard_fail = checks[(checks.severity == "error") & (checks.violations > 0)]
assert hard_fail.empty, "an error-level check failed"

# ---------- 2. analysis queries ----------
text = open(ROOT / "sql" / "03_analysis.sql").read()
parts = re.split(r"-- name: (\w+)\n", text)
results = {}
for name, sql in zip(parts[1::2], parts[2::2]):
    df = pd.read_sql_query(sql, con)
    df.to_csv(OUT / f"{name}.csv", index=False)
    results[name] = df
    print("\n==", name)
    print(df.to_string(index=False))

# ---------- 3. pandas cross-check of the SQL ----------
f = pd.read_sql_query("SELECT * FROM fact_funnel", con)
byc = f.groupby("cycle_year").agg(inq=("lead_id", "count"), st=("started", "sum"),
                                 reg=("registered", "sum"), adm=("admitted", "sum"),
                                 enr=("enrolled", "sum"))
sql_cycle = results["funnel_by_cycle"].set_index("term")
for cy, row in byc.iterrows():
    s = sql_cycle.loc[f"Fall {cy}"]
    assert abs(s.start_rate - row.st / row.inq) < 1e-4
    assert abs(s.register_rate - row.reg / row.adm) < 1e-4
    assert s.enrolled == row.enr
print("\nPandas cross-check of funnel_by_cycle: match within 0.0001")

# ---------- 4. does slow first contact really lower the start rate? bootstrap ----------
rng = np.random.default_rng(7)
late = f["contact_lag_days"] >= 4
diffs = []
for _ in range(2000):
    idx = rng.integers(0, len(f), len(f))
    s = f.iloc[idx]
    l = s["contact_lag_days"] >= 4
    diffs.append(s.loc[~l, "started"].mean() - s.loc[l, "started"].mean())
lo, hi = np.percentile(diffs, [2.5, 97.5])
obs = f.loc[~late, "started"].mean() - f.loc[late, "started"].mean()
print(f"\nStart-rate gap, contacted within 3 days minus after 3 days: {obs*100:.1f} points (95% CI {lo*100:.1f} to {hi*100:.1f})")
pd.DataFrame({"gap_points": [round(obs * 100, 2)], "ci_low": [round(lo * 100, 2)],
              "ci_high": [round(hi * 100, 2)]}).to_csv(OUT / "response_speed_gap_ci.csv", index=False)

# ---------- 5. charts ----------
NAVY, TEAL, GREY, ORANGE = "#1F3864", "#2A9D8F", "#8D99AE", "#E76F51"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
SIM = "Simulated data. Cohort size and Utah share anchored to real IPEDS fall 2022 figures."

# 5a funnel, latest full set of cycles pooled 2021-2023
pool = f[f.cycle_year <= 2023]
stages = ["inquiries", "started", "completed", "admitted", "registered", "enrolled"]
vals = [len(pool), pool.started.sum(), pool.completed.sum(), pool.admitted.sum(),
        pool.registered.sum(), pool.enrolled.sum()]
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.barh(stages[::-1], vals[::-1], color=NAVY)
for i, v in enumerate(vals[::-1]):
    ax.text(v + max(vals) * 0.01, i, f"{v:,}  ({v/vals[0]:.0%})", va="center")
ax.set_xlim(0, max(vals) * 1.25)
ax.set_title("Where inquiries are lost, fall 2021 to 2023 pooled")
fig.text(0.01, 0.01, SIM, fontsize=7, color=GREY)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(CH / "01_funnel.png", dpi=160)
plt.close(fig)

# 5b conversion by source
src = results["conversion_by_source"].sort_values("inquiry_to_enrolled")
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.barh(src.lead_source, src.inquiry_to_enrolled * 100, color=TEAL)
for i, v in enumerate(src.inquiry_to_enrolled * 100):
    ax.text(v + 0.3, i, f"{v:.1f}%", va="center")
ax.set_xlabel("Inquiries that enrolled (%), all four cycles")
ax.set_title("Enrollment yield by lead source")
fig.text(0.01, 0.01, SIM, fontsize=7, color=GREY)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(CH / "02_source_yield.png", dpi=160)
plt.close(fig)

# 5c response speed and start rate by cycle
rs = results["response_speed_by_cycle"]
fig, ax = plt.subplots(figsize=(7.5, 4))
x = np.arange(len(rs))
ax.bar(x, rs.share_contacted_after_3_days * 100, color=ORANGE, width=0.5)
ax.set_xticks(x, rs.term)
ax.set_ylabel("Inquiries first contacted after 3 days (%)")
ax2 = ax.twinx()
ax2.plot(x, sc := (results["funnel_by_cycle"].start_rate * 100).values, color=NAVY, marker="o")
ax2.set_ylabel("Inquiries that started an application (%)")
ax2.set_ylim(0, 50)   # full scale from zero so the small drop is not exaggerated
ax.set_ylim(0, 50)
for xi, v in zip(x, sc):
    ax2.text(xi, v + 1.5, f"{v:.1f}%", ha="center", color=NAVY)
ax2.spines["top"].set_visible(False)
ax.set_title("Slower first contact and the application start rate")
fig.text(0.01, 0.01, SIM, fontsize=7, color=GREY)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(CH / "03_response_speed.png", dpi=160)
plt.close(fig)

# 5d aid and residency
ar = results["aid_and_residency"]
fig, ax = plt.subplots(figsize=(7.5, 4))
w = 0.35
order = ["Utah resident", "Out of state"]   # one fixed order for bars and tick labels
for i, status in enumerate(["Filed aid form", "No aid form"]):
    sub = ar[ar.aid_status == status].set_index("residency").loc[order]
    ax.bar(np.arange(len(order)) + i * w, sub.register_rate * 100, w, label=status,
           color=[NAVY, GREY][i])
    for j, v in enumerate(sub.register_rate * 100):
        ax.text(j + i * w, v + 0.8, f"{v:.0f}%", ha="center")
ax.set_ylim(0, 105)
ax.set_xticks(np.arange(2) + w / 2, order)
ax.set_ylabel("Admitted students who registered (%)")
ax.legend(frameon=False)
ax.set_title("Registration by aid filing and residency")
fig.text(0.01, 0.01, SIM, fontsize=7, color=GREY)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(CH / "04_aid_residency.png", dpi=160)
plt.close(fig)
print("\n4 charts written to", CH)
