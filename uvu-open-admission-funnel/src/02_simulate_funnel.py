"""Simulate a first-year recruitment funnel for an open-admission public university.

THIS DATA IS SIMULATED. Only two numbers are real, both from IPEDS fall 2022
(EF2022C, residence of first-time students, UNITID 230737, Utah Valley University):
  * about 4,752 first-time degree or certificate-seeking students
  * 3,555 of them Utah residents (about 74.8%)
They set the size of each simulated entering class and the in-state share.
Everything else (inquiries, sources, response times, aid filing, stage rates)
is generated with a fixed seed and documented in docs/definitions.md.

Funnel stages: inquiry -> application started -> application completed ->
admitted -> registered for classes -> enrolled at census day.
UVU is open admission, so the admit step is near-automatic and the real losses
are application completion and registration.
"""
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1])
DB = ROOT / "outputs" / "ipeds_uvu.db"
OUT = ROOT / "outputs"
rng = np.random.default_rng(20261106)

CYCLES = [2021, 2022, 2023, 2024]
TARGET_ENROLLED = 4752          # real IPEDS anchor, per cycle
IN_STATE_SHARE = 3555 / 4752    # real IPEDS anchor

# lead source: (name, share of inquiries, start multiplier, register multiplier)
SOURCES = [
    ("Concurrent enrollment", 0.16, 1.55, 1.30),
    ("High school counselor", 0.14, 1.20, 1.10),
    ("Campus visit or event", 0.15, 1.35, 1.20),
    ("Organic search", 0.20, 0.95, 1.00),
    ("Paid social and display", 0.17, 0.55, 0.80),
    ("Referral from student", 0.08, 1.25, 1.10),
    ("College fair", 0.10, 0.85, 0.95),
]
BASE_START = 0.38
P_COMPLETE = 0.78
P_ADMIT = 0.985
BASE_REG = 0.58
P_CENSUS = 0.93
FAFSA_REG_MULT = 1.40         # filed aid form before registration deadline
OUT_OF_STATE_REG_MULT = 0.80
LATE_START_MULT = 0.72         # first contact more than 3 days after inquiry
LATE_SHARE = {2021: 0.20, 2022: 0.20, 2023: 0.21, 2024: 0.36}  # planted: 2024 response slows
FAFSA_SHARE_IN, FAFSA_SHARE_OUT = 0.55, 0.40

# Inquiry volume per cycle, set by trial so the 2021 to 2023 simulated enrolled
# counts land near the real anchor (checked in sql/02_checks.sql, check S6).
n_per_cycle = 23400

rows = []
lead_id = 1
src_names = [s[0] for s in SOURCES]
src_share = np.array([s[1] for s in SOURCES])
src_start = np.array([s[2] for s in SOURCES])
src_reg = np.array([s[3] for s in SOURCES])

for cy in CYCLES:
    n = n_per_cycle
    src = rng.choice(len(SOURCES), size=n, p=src_share / src_share.sum())
    instate = rng.random(n) < IN_STATE_SHARE
    late = rng.random(n) < LATE_SHARE[cy]
    lag = np.where(late, rng.integers(4, 15, n), rng.integers(0, 4, n))
    fafsa = rng.random(n) < np.where(instate, FAFSA_SHARE_IN, FAFSA_SHARE_OUT)
    # inquiry dates: September of prior year through August of the cycle year
    start = pd.Timestamp(year=cy - 1, month=9, day=1)
    day = rng.integers(0, 364, n)
    inquiry_date = start + pd.to_timedelta(day, unit="D")

    p_start = np.clip(BASE_START * src_start[src] * np.where(late, LATE_START_MULT, 1.0), 0, 0.95)
    started = rng.random(n) < p_start
    completed = started & (rng.random(n) < P_COMPLETE)
    admitted = completed & (rng.random(n) < P_ADMIT)
    p_reg = np.clip(BASE_REG * src_reg[src] * np.where(fafsa, FAFSA_REG_MULT, 1.0)
                    * np.where(instate, 1.0, OUT_OF_STATE_REG_MULT), 0, 0.97)
    registered = admitted & (rng.random(n) < p_reg)
    enrolled = registered & (rng.random(n) < P_CENSUS)

    complete_lag = rng.integers(3, 40, n)
    reg_lag = rng.integers(10, 120, n)
    df = pd.DataFrame({
        "lead_id": np.arange(lead_id, lead_id + n),
        "cycle_year": cy,
        "source_key": src + 1,
        "residency_key": np.where(instate, 1, 2),
        "inquiry_date": inquiry_date.strftime("%Y-%m-%d"),
        "contact_lag_days": lag,
        "fafsa_filed": fafsa.astype(int),
        "started": started.astype(int),
        "completed": completed.astype(int),
        "admitted": admitted.astype(int),
        "registered": registered.astype(int),
        "enrolled": enrolled.astype(int),
    })
    comp_date = pd.to_datetime(df["inquiry_date"]) + pd.to_timedelta(complete_lag, unit="D")
    reg_date = comp_date + pd.to_timedelta(reg_lag, unit="D")
    df["completed_date"] = np.where(df["completed"] == 1, comp_date.dt.strftime("%Y-%m-%d"), None)
    df["registered_date"] = np.where(df["registered"] == 1, reg_date.dt.strftime("%Y-%m-%d"), None)
    rows.append(df)
    lead_id += n

fact = pd.concat(rows, ignore_index=True)

dim_source = pd.DataFrame({"source_key": range(1, len(SOURCES) + 1), "lead_source": src_names})
dim_residency = pd.DataFrame({"residency_key": [1, 2], "residency": ["Utah resident", "Out of state"]})
dim_cycle = pd.DataFrame({"cycle_year": CYCLES, "term": [f"Fall {c}" for c in CYCLES]})

con = sqlite3.connect(DB)
fact.to_sql("fact_funnel", con, if_exists="replace", index=False)
dim_source.to_sql("dim_lead_source", con, if_exists="replace", index=False)
dim_residency.to_sql("dim_residency", con, if_exists="replace", index=False)
dim_cycle.to_sql("dim_cycle", con, if_exists="replace", index=False)
con.commit()
con.close()

fact.to_csv(OUT / "simulated_funnel.csv", index=False)
print("rows:", len(fact))
print(fact.groupby("cycle_year")[["started", "completed", "admitted", "registered", "enrolled"]].sum())
