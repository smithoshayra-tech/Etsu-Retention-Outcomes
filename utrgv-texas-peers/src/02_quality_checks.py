"""Run every check in sql/02_quality_checks.sql and log the results.

Writes:
  outputs/dq/<check_id>.csv     offending rows for each check (empty = pass)
  outputs/dq_summary.csv        one line per check: severity, rows flagged
"""
import os
import re
import sqlite3

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "outputs", "ipeds.db")
OUT = os.path.join(ROOT, "outputs", "dq")


def parse(sql_text):
    blocks = re.split(r"^-- check: ", sql_text, flags=re.M)[1:]
    for b in blocks:
        header, _, body = b.partition("\n")
        cid, sev, desc = [s.strip() for s in header.split("|")]
        yield cid, sev, desc, body.strip()


def main():
    os.makedirs(OUT, exist_ok=True)
    con = sqlite3.connect(DB)
    with open(os.path.join(ROOT, "sql", "02_quality_checks.sql")) as f:
        checks = list(parse(f.read()))
    rows = []
    for cid, sev, desc, query in checks:
        df = pd.read_sql(query, con)
        df.to_csv(os.path.join(OUT, f"{cid}.csv"), index=False)
        status = "PASS" if df.empty else ("FAIL" if sev == "fail" else "FLAG")
        rows.append({"check": cid, "severity": sev, "status": status,
                     "rows_flagged": len(df), "description": desc})
        print(f"{status:5s} {cid:34s} {len(df):>6,d}  {desc}")
    pd.DataFrame(rows).to_csv(os.path.join(ROOT, "outputs", "dq_summary.csv"), index=False)


if __name__ == "__main__":
    main()
