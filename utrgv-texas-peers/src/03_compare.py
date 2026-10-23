"""UTRGV vs. Texas public peers: yearly medians, gaps and percentiles.

Reads outputs/ipeds.db (built by 01_build_db.py) and writes two CSVs:
  outputs/utrgv_vs_tx_all.csv     all Texas peers in the rule (Carnegie 15-19)
  outputs/utrgv_vs_tx_no_r1.csv   same, without class 15 (research-heavy) schools
"""
import os
import sqlite3
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "outputs", "ipeds.db")


def summarize(df, label):
    rows = []
    for year, g in df.groupby("report_year"):
        home, peers = g[g.is_home == 1], g[g.is_home == 0]
        if home.empty:
            continue
        for col, name in (("ft_retention_pct", "ret"), ("grad_rate_6yr_pct", "grad")):
            pv, hv = peers[col].dropna(), home[col].iloc[0]
            if pd.isna(hv) or pv.empty:
                continue
            rows.append(dict(set=label, year=year, metric=name, utrgv=hv,
                             peer_median=pv.median(), gap=hv - pv.median(),
                             n=len(pv), pctile=(pv < hv).mean() * 100))
    return pd.DataFrame(rows)


def main():
    con = sqlite3.connect(DB)
    d = pd.read_sql("SELECT * FROM v_outcomes", con)
    summarize(d, "all TX 15-19").to_csv(
        os.path.join(ROOT, "outputs", "utrgv_vs_tx_all.csv"), index=False)
    summarize(d[d.carnegie_2021.between(16, 19) | (d.is_home == 1)],
              "TX class 16-19 (no R1)").to_csv(
        os.path.join(ROOT, "outputs", "utrgv_vs_tx_no_r1.csv"), index=False)


if __name__ == "__main__":
    sys.exit(main())
