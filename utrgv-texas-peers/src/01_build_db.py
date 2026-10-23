"""Build the SQLite database from raw IPEDS files.

Reads, for report years 2013-2024:
  - EF{yr}D   Fall Enrollment, retention rate component (original + revised files)
  - GR{yr}    Graduation Rates (original + revised files)
  - HD2023    Institutional Characteristics (directory)

Nothing is dropped silently: original and revised files are both loaded and
tagged, imputation flags are kept, and the peer-group rule is applied in SQL
(see sql/01_views.sql), not hard-coded here.
"""
import os
import sqlite3
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACT = os.path.join(ROOT, "extract")
DB = os.path.join(ROOT, "outputs", "ipeds.db")
YEARS = range(2013, 2024)

EF_KEEP = ["UNITID", "GRCOHRT", "UGENTERN", "RRFTCT", "RRFTCTA", "RET_NMF",
           "RET_PCF", "STUFACR"]
GR_TYPES = {2: "cohort_4yr_all", 3: "completers_4yr_all",
            8: "cohort_ba", 9: "completers_ba"}


def find(folder, name):
    """Case-insensitive file lookup inside an extracted folder."""
    path = os.path.join(EXTRACT, folder)
    for f in os.listdir(path):
        if f.lower() == name.lower():
            return os.path.join(path, f)
    return None


def read(path):
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    # HD files start with a UTF-8 byte-order mark; read as latin-1 it shows up
    # as stray characters glued to the first column name.
    df.columns = [c.replace("ï»¿", "").strip() for c in df.columns]
    return df


def load_ef():
    frames = []
    for y in YEARS:
        for version, fname in (("original", f"ef{y}d.csv"),
                               ("revised", f"ef{y}d_rv.csv")):
            p = find(f"EF{y}D", fname)
            if p is None:
                continue
            df = read(p)
            cols = [c for c in df.columns
                    if c in EF_KEEP or (c.startswith("X") and c[1:] in EF_KEEP)]
            df = df[cols].copy()
            df.insert(1, "report_year", y)
            df.insert(2, "version", version)
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_gr():
    frames = []
    for y in YEARS:
        for version, fname in (("original", f"gr{y}.csv"),
                               ("revised", f"gr{y}_rv.csv")):
            p = find(f"GR{y}", fname)
            if p is None:
                continue
            df = read(p)
            df = df[df["GRTYPE"].isin(GR_TYPES)].copy()
            df["measure"] = df["GRTYPE"].map(GR_TYPES)
            df = df[["UNITID", "measure", "XGRTOTLT", "GRTOTLT"]]
            df.insert(1, "report_year", y)
            df.insert(2, "version", version)
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_hd():
    df = read(find("HD2023", "HD2023.csv"))
    keep = ["UNITID", "INSTNM", "CITY", "STABBR", "CONTROL", "ICLEVEL", "UGOFFER",
            "C21BASIC", "CYACTIVE", "OPEFLAG", "INSTSIZE"]
    return df[keep]


def main():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    ef, gr, hd = load_ef(), load_gr(), load_hd()
    con = sqlite3.connect(DB)
    ef.to_sql("ef_retention_raw", con, index=False)
    gr.to_sql("gr_raw", con, index=False)
    hd.to_sql("institution_raw", con, index=False)
    con.executescript("""
        CREATE INDEX ix_ef ON ef_retention_raw (UNITID, report_year, version);
        CREATE INDEX ix_gr ON gr_raw (UNITID, report_year, measure, version);
        CREATE INDEX ix_inst ON institution_raw (UNITID);
    """)
    with open(os.path.join(ROOT, "sql", "01_views.sql")) as f:
        con.executescript(f.read())
    con.commit()
    for t in ("ef_retention_raw", "gr_raw", "institution_raw", "dim_institution",
              "peer_group"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:20s} {n:>8,d} rows")
    con.close()


if __name__ == "__main__":
    sys.exit(main())
