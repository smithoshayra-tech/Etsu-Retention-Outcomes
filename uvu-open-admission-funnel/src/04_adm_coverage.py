"""Real-data limit: which Utah public four-year institutions report IPEDS Admissions?

Writes outputs/real_adm_coverage.csv. Open-admission institutions do not complete
the Admissions component, so they have no rows.
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(sys.argv[1])
con = sqlite3.connect(ROOT / "outputs" / "ipeds_uvu.db")
df = pd.read_sql_query("""
SELECT d.institution, d.UNITID,
       COUNT(DISTINCT a.report_year) AS years_with_admissions_data,
       MIN(a.report_year) AS first_year, MAX(a.report_year) AS last_year
FROM dim_institution d
LEFT JOIN adm_raw a ON a.UNITID = d.UNITID
GROUP BY d.institution, d.UNITID
ORDER BY years_with_admissions_data DESC, d.institution
""", con)
df.to_csv(ROOT / "outputs" / "real_adm_coverage.csv", index=False)
print(df.to_string(index=False))
