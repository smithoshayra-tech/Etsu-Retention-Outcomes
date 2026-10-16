"""Export Power BI-ready tables and a findings summary.

Governance: aggregate institution-level public data only. Any rate whose cohort is
below SMALL_CELL_MIN is blanked, together with the counts it is built from.
"""
import json
import os
import sqlite3

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "outputs", "ipeds.db")
OUT = os.path.join(ROOT, "outputs", "powerbi")
HOME = 220075
small_cell_min = 30


def main():
    os.makedirs(OUT, exist_ok=True)
    con = sqlite3.connect(DB)
    f = pd.read_sql(
        "SELECT o.unitid, o.report_year, o.retention_cohort_year, o.ft_cohort_adj, r.ft_retained_n,"
        " o.ft_retention_pct, o.retention_flag, o.grad_cohort_year, o.ba_cohort_n, o.ba_completers_n,"
        " o.grad_rate_6yr_pct, o.student_faculty_ratio"
        " FROM v_outcomes o JOIN v_retention r ON r.unitid = o.unitid AND r.report_year = o.report_year", con)
    f["retention_suppressed"] = (f.ft_cohort_adj < small_cell_min).astype(int)
    f["grad_suppressed"] = (f.ba_cohort_n < small_cell_min).astype(int)
    for c in ("ft_cohort_adj", "ft_retained_n", "ft_retention_pct"):
        f.loc[f.retention_suppressed == 1, c] = np.nan
    for c in ("ba_cohort_n", "ba_completers_n", "grad_rate_6yr_pct"):
        f.loc[f.grad_suppressed == 1, c] = np.nan
    f.to_csv(os.path.join(OUT, "fact_outcomes.csv"), index=False)

    dim = pd.read_sql(
        "SELECT d.unitid, d.institution, d.state, p.peer_group, d.carnegie_2021, d.carnegie_label, d.is_home"
        " FROM dim_institution d JOIN peer_group p ON p.unitid = d.unitid ORDER BY d.institution", con)
    dim.to_csv(os.path.join(OUT, "dim_institution.csv"), index=False)
    pd.DataFrame({"report_year": sorted(f.report_year.unique())}).to_csv(
        os.path.join(OUT, "dim_year.csv"), index=False)

    pred = pd.read_csv(os.path.join(ROOT, "outputs", "model_predictions.csv"))
    pred[["unitid", "report_year", "y", "naive_last", "naive_avg2", "ridge", "gbm"]].rename(
        columns={"y": "actual"}).to_csv(os.path.join(OUT, "fact_model_backtest.csv"), index=False)
    pd.read_csv(os.path.join(ROOT, "outputs", "dq_summary.csv")).to_csv(
        os.path.join(OUT, "fact_dq_summary.csv"), index=False)

    # ---- findings (generated, cited in README) ---------------------------------
    m = f.merge(dim[["unitid", "peer_group", "is_home"]], on="unitid")
    res = {}
    for metric, col in (("retention", "ft_retention_pct"), ("graduation", "grad_rate_6yr_pct")):
        for yr in (2013, 2024):
            y = m[m.report_year == yr].dropna(subset=[col])
            etsu = y[y.is_home == 1][col].iloc[0]
            peers = y[y.is_home == 0]
            reg = peers[peers.peer_group == "regional"][col]
            geo = peers[peers.peer_group == "georgia"][col]
            res[f"{metric}_{yr}"] = {
                "etsu": float(etsu),
                "regional_median": float(reg.median()), "regional_n": int(len(reg)),
                "georgia_median": float(geo.median()), "georgia_n": int(len(geo)),
                "etsu_pctile_regional": float((reg < etsu).mean() * 100),
                "etsu_pctile_all_peers": float((peers[col] < etsu).mean() * 100)}
    with open(os.path.join(ROOT, "outputs", "findings.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print(json.dumps(res, indent=2))
    for t in ("fact_outcomes", "dim_institution", "dim_year", "fact_model_backtest", "fact_dq_summary"):
        print(t, pd.read_csv(os.path.join(OUT, t + ".csv")).shape)


if __name__ == "__main__":
    main()
