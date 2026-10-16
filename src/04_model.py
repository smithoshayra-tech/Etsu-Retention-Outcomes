"""Institution-level model: predict next-year full-time retention.

Target     ft_retention_pct in report year t (fall t-1 cohort retained to fall t)
Features   known one year earlier (t-1) plus fixed institution traits:
           retention t-1 and t-2, 6-year graduation rate t-1, student-faculty
           ratio t-1, log full-time cohort t-1, Carnegie class, Georgia group.
Evaluation expanding window, one step ahead. For each test year T (2018-2024)
           the models are fit only on target years before T. No test year is
           ever used for training, tuning or feature scaling.
Baselines  naive_last (retention stays at last year's value) and naive_avg2.
           A model is only useful if it beats these.
"""
import json
import os
import sqlite3

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "outputs", "ipeds.db")
OUT = os.path.join(ROOT, "outputs")
TEST_YEARS = list(range(2018, 2025))
HOME = 220075
FC_YEAR = 2025
SEED = 42
N_BOOT = 2000

FEATURES = ["ret_l1", "ret_l2", "grad_l1", "sfr_l1", "logcoh_l1",
            "carn_16", "carn_17", "carn_18", "carn_19", "georgia"]


def load_panel():
    con = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT unitid, institution, report_year, carnegie_2021, peer_group,"
        " ft_retention_pct, grad_rate_6yr_pct, student_faculty_ratio, ft_cohort_adj"
        " FROM v_outcomes", con)
    con.close()
    return df


def build_features(df, extra_year=None):
    """One row per institution-year with lagged features. If extra_year is given,
    a target-less row for that year is appended (used for the forward forecast)."""
    d = df.sort_values(["unitid", "report_year"]).copy()
    if extra_year is not None:
        last = d[d.report_year == extra_year - 1][["unitid", "institution", "carnegie_2021", "peer_group"]]
        d = pd.concat([d, last.assign(report_year=extra_year)], ignore_index=True)
        d = d.sort_values(["unitid", "report_year"])
    g = d.groupby("unitid")
    d["ret_l1"] = g["ft_retention_pct"].shift(1)
    d["ret_l2"] = g["ft_retention_pct"].shift(2)
    d["grad_l1"] = g["grad_rate_6yr_pct"].shift(1)
    d["sfr_l1"] = g["student_faculty_ratio"].shift(1)
    d["logcoh_l1"] = np.log(g["ft_cohort_adj"].shift(1))
    for c in (16, 17, 18, 19):          # class 15 is the reference level
        d[f"carn_{c}"] = (d.carnegie_2021 == c).astype(int)
    d["georgia"] = (d.peer_group == "georgia").astype(int)
    d["y"] = d["ft_retention_pct"]
    return d


def make_models():
    return {
        "ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 30))),
        "gbm": GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05,
                                         subsample=0.8, random_state=SEED),
    }


def main():
    panel = load_panel()
    d = build_features(panel)
    usable = d.dropna(subset=FEATURES + ["y"]).copy()
    dropped = d[d.y.notna()].shape[0] - usable.shape[0]
    print(f"rows with a target: {d.y.notna().sum()} | usable after lags: {usable.shape[0]} "
          f"| dropped (missing lag or feature): {dropped}")

    preds = []
    for T in TEST_YEARS:
        tr, te = usable[usable.report_year < T], usable[usable.report_year == T].copy()
        te["naive_last"] = te["ret_l1"]
        te["naive_avg2"] = (te["ret_l1"] + te["ret_l2"]) / 2
        for name, model in make_models().items():
            model.fit(tr[FEATURES], tr["y"])
            te[name] = model.predict(te[FEATURES])
        te["n_train"] = len(tr)
        preds.append(te)
    P = pd.concat(preds, ignore_index=True)
    models = ["naive_last", "naive_avg2", "ridge", "gbm"]
    for m in models:
        P[f"err_{m}"] = P[m] - P["y"]

    # ---- metrics -----------------------------------------------------------
    rows = []
    for T, g in list(P.groupby("report_year")) + [("all", P)]:
        for m in models:
            e = g[f"err_{m}"]
            rows.append({"test_year": T, "model": m, "n": len(g),
                         "mae": e.abs().mean(), "rmse": np.sqrt((e ** 2).mean()),
                         "bias": e.mean()})
    metrics = pd.DataFrame(rows)
    metrics.to_csv(os.path.join(OUT, "model_metrics.csv"), index=False)

    # ---- cluster bootstrap: does a model beat naive_last? ------------------
    def boot_ci(PP):
        rng = np.random.default_rng(SEED)
        units = PP.unitid.unique()
        by_unit = {u: PP[PP.unitid == u] for u in units}
        boot = {m: [] for m in ("ridge", "gbm", "naive_avg2")}
        for _ in range(N_BOOT):
            sample = pd.concat([by_unit[u] for u in rng.choice(units, len(units), replace=True)])
            base = sample["err_naive_last"].abs().mean()
            for m in boot:
                boot[m].append(base - sample[f"err_{m}"].abs().mean())   # >0 means model is better
        return {m: (float(np.mean(v)), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
                for m, v in boot.items()}

    ci = boot_ci(P)
    # Sensitivity: Tennessee State's 2024 rate (60% -> 33%) is a single 31-point miss.
    TSU = 221838
    ci_x = boot_ci(P[P.unitid != TSU])
    with open(os.path.join(OUT, "model_vs_naive_ci.json"), "w") as f:
        json.dump({**{m: {"mae_gain_points": c[0], "ci95_low": c[1], "ci95_high": c[2]}
                      for m, c in ci.items()},
                   "excluding_tsu": {m: {"mae_gain_points": c[0], "ci95_low": c[1], "ci95_high": c[2]}
                                     for m, c in ci_x.items()},
                   "tsu_2024_abs_error_ridge": float(P[(P.unitid == TSU) & (P.report_year == 2024)]["err_ridge"].abs().iloc[0])},
                  f, indent=2)

    # ---- full-sample ridge coefficients (descriptive only) ------------------
    full = make_models()["ridge"].fit(usable[FEATURES], usable["y"])
    coefs = pd.DataFrame({"feature": FEATURES,
                          "std_coef": full[-1].coef_}).sort_values("std_coef", key=abs, ascending=False)
    coefs.to_csv(os.path.join(OUT, "ridge_coefficients.csv"), index=False)

    # ---- ETSU actual vs predicted, and an unvalidated forward forecast ------
    etsu = P[P.unitid == HOME][["report_year", "y", "naive_last", "ridge", "gbm"]]
    etsu.to_csv(os.path.join(OUT, "etsu_backtest.csv"), index=False)

    d24 = build_features(panel, extra_year=FC_YEAR)
    row = d24[(d24.unitid == HOME) & (d24.report_year == FC_YEAR)]
    fc = {}
    if row[FEATURES].notna().all(axis=None):
        for name, model in make_models().items():
            model.fit(usable[FEATURES], usable["y"])
            fc[name] = float(model.predict(row[FEATURES])[0])
        fc["naive_last"] = float(row["ret_l1"].iloc[0])
        q = P["err_ridge"].abs().quantile(0.8)
        fc["ridge_80pct_band_pts"] = float(q)
    with open(os.path.join(OUT, "etsu_forecast_2025.json"), "w") as f:
        json.dump(fc, f, indent=2)

    P.to_csv(os.path.join(OUT, "model_predictions.csv"), index=False)

    # ---- console summary ------------------------------------------------------
    pd.set_option("display.width", 160)
    print("\nMAE by test year (percentage points)")
    print(metrics.pivot(index="test_year", columns="model", values="mae").round(2).to_string())
    print("\nMAE gain over naive_last, 95% cluster-bootstrap CI (positive = model better)")
    for m, c in ci.items():
        print(f"  {m:11s} {c[0]:+.2f}  [{c[1]:+.2f}, {c[2]:+.2f}]")
    print("excluding Tennessee State:")
    for m, c in ci_x.items():
        print(f"  {m:11s} {c[0]:+.2f}  [{c[1]:+.2f}, {c[2]:+.2f}]")
    print("\nridge coefficients (standardized)"); print(coefs.round(2).to_string(index=False))
    print("\nETSU back-test"); print(etsu.round(1).to_string(index=False))
    print("\nETSU 2025 forecast (not yet validated):", {k: round(v, 1) for k, v in fc.items()})


if __name__ == "__main__":
    main()
