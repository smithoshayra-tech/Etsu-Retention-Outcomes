"""Load IPEDS ADM (admissions) and HD (institution) files into SQLite.

Raw values are loaded unchanged. Both the original and the revised (_rv) ADM file
are kept for each year the revised file exists (2014-2022). Views in
sql/01_views.sql prefer the revised value.
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
DATA = ROOT / "data"
DB = ROOT / "outputs" / "ipeds_uvu.db"
DB.parent.mkdir(exist_ok=True)
if DB.exists():
    DB.unlink()

ADM_COLS = ["APPLCN", "ADMSSN", "ENRLT", "ENRLM", "ENRLW", "ENRLFT", "ENRLPT",
            "XAPPLCN", "XADMSSN", "XENRLT"]
HD_COLS = ["UNITID", "INSTNM", "CITY", "STABBR", "CONTROL", "ICLEVEL", "UGOFFER",
           "C21BASIC", "CYACTIVE"]

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("""CREATE TABLE adm_raw (
    UNITID INTEGER, report_year INTEGER, version TEXT,
    APPLCN INTEGER, ADMSSN INTEGER, ENRLT INTEGER, ENRLM INTEGER, ENRLW INTEGER,
    ENRLFT INTEGER, ENRLPT INTEGER,
    XAPPLCN TEXT, XADMSSN TEXT, XENRLT TEXT,
    ADMCON1 INTEGER, ADMCON7 INTEGER)""")
cur.execute("""CREATE TABLE institution_raw (
    UNITID INTEGER, INSTNM TEXT, CITY TEXT, STABBR TEXT, CONTROL INTEGER,
    ICLEVEL INTEGER, UGOFFER INTEGER, C21BASIC INTEGER, CYACTIVE INTEGER)""")


def num(v):
    v = (v or "").strip()
    if v == "" or v == ".":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


n_rows = 0
for year in range(2014, 2024):
    folder = DATA / f"ADM{year}"
    for version, fname in (("original", f"adm{year}.csv"), ("revised", f"adm{year}_rv.csv")):
        path = folder / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                vals = [num(r.get(c)) for c in ADM_COLS[:7]]
                flags = [(r.get(c) or "").strip() or None for c in ADM_COLS[7:]]
                cur.execute(
                    "INSERT INTO adm_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [num(r["UNITID"]), year, version, *vals, *flags,
                     num(r.get("ADMCON1")), num(r.get("ADMCON7"))])
                n_rows += 1

with open(DATA / "HD2023" / "HD2023.csv", encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        cur.execute("INSERT INTO institution_raw VALUES (?,?,?,?,?,?,?,?,?)",
                    [num(r["UNITID"]), r["INSTNM"].strip(), r["CITY"].strip(), r["STABBR"],
                     num(r["CONTROL"]), num(r["ICLEVEL"]), num(r["UGOFFER"]),
                     num(r["C21BASIC"]), num(r["CYACTIVE"])])

con.commit()
print("adm_raw rows:", n_rows)
print("institution_raw rows:", cur.execute("SELECT COUNT(*) FROM institution_raw").fetchone()[0])
con.close()
