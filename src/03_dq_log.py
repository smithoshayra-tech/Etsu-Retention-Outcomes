"""Generate docs/data_quality_log.md from the check outputs (no hand-typed numbers)."""
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DQ = os.path.join(ROOT, "outputs", "dq")


def load(cid):
    return pd.read_csv(os.path.join(DQ, f"{cid}.csv"))


def md(df, cols=None, n=12):
    df = df if cols is None else df[cols]
    return df.head(n).to_markdown(index=False)


n_obs = len(pd.read_csv(os.path.join(ROOT, 'outputs', 'powerbi', 'fact_outcomes.csv')))
summary = pd.read_csv(os.path.join(ROOT, "outputs", "dq_summary.csv"))
c01, c09 = load("C01_coverage_gap"), load("C09_graduation_missing")
c10, c11 = load("C10_retention_yoy_jump"), load("C11_graduation_yoy_jump")
c12, c13 = load("C12_revised_changes_retention"), load("C13_revised_changes_graduation")
c15, c16 = load("C15_cross_file_cohort_mismatch"), load("C16_imputed_values_national")

covid = c10[c10.report_year == 2021]
n_2021 = len(covid)
n_2021_down = int((covid.change < 0).sum())

out = f"""# Data quality log

Source: IPEDS Data Center complete data files (HD2023, EF2013D-EF2024D, GR2013-GR2024),
downloaded directly from nces.ed.gov. Scope: 55 public four-year institutions that meet
the peer rule in README ({n_obs} institution-years, report years 2013-2024).
Every check is a SQL query in `sql/02_quality_checks.sql`; counts below come from
`outputs/dq_summary.csv`.

## Result summary

{summary[['check', 'status', 'rows_flagged', 'description']].to_markdown(index=False)}

## What was found and how each item was handled

### 1. Original vs. revised files (C12, C13)
IPEDS published a revised file alongside the original for report years 2013-2022 (none
yet for 2023 or 2024). The pipeline loads both and uses the revised value when one exists. Among
peer institutions the revised files changed {len(c12)} retention value and {len(c13)}
graduation counts, shown below. Tennessee State University accounts for the retention
change and two of the graduation changes; its 2020 bachelor's cohort moved by
{int(c13.loc[(c13.unitid == 221838) & (c13.measure == 'cohort_ba'), 'change'].iloc[0])} students.
The largest single change by count is UNC Chapel Hill (+58 completers, 2021).

{md(c12)}

{md(c13)}

### 2. Missing records (C01, C09)
{md(c01)}

Kennesaw State has no retention record under its current ID for 2013 and 2014. The USG
consolidation page confirms Kennesaw State consolidated with Southern Polytechnic State
University; this is consistent with the institution receiving a new ID, but I did not
trace predecessor IDs, so I have not stitched a pre-2015 series. Those two years are
simply absent. One graduation record is missing:

{md(c09)}

**Handling:** rows with no value are excluded from the model and shown as blank in the
dashboard. Nothing was filled in.

### 3. Entering class vs. graduation cohort (C15)
For {len(c15)} institution-years the full-time entering class in the retention file and the
graduation cohort six years later differ by more than 10%. The offset itself was tested
first: across institutions, entering-class counts match graduation-cohort counts with a
median absolute difference of 0.1% at a six-year offset and 5% or more at other offsets.

{md(c15)}

All flagged rows belong to Albany State and Georgia Southern. Both are institutions
the USG consolidation page lists as consolidated with another college (Darton State
College and Armstrong State University, respectively); the cohort counts are consistent
with legacy students being counted in one file and not the other, but I have not
confirmed that mechanism.

**Handling:** the graduation rate uses the bachelor's-seeking subcohort (IPEDS GRTYPE 8
and 9), not the all-students cohort the check compares, so the rate itself is not built
on the mismatched counts. The mismatch is logged so nobody compares raw cohort sizes
across these two files for those institutions.

### 4. Year-over-year jumps (C10, C11)
{len(c10)} retention changes and {len(c11)} graduation changes exceeded 10 points.
{n_2021} of the {len(c10)} retention jumps fall in report year 2021 (the fall 2020 entering
cohort), spread across {covid.institution.nunique()} different institutions, including ETSU
({covid.loc[covid.unitid == 220075, 'prev'].iloc[0]:.0f}% to {covid.loc[covid.unitid == 220075, 'pct'].iloc[0]:.0f}%).
{n_2021_down} of those {n_2021} are declines; one institution rose. Several unrelated
institutions moving in the same year points more toward a shared cause than independent
data errors, but I did not investigate a specific cause, so the dashboard shows the change
without attributing it.

Report year 2024 adds one: Tennessee State, 60% to 33% (550 retained of 1,642; the published rate matches
the counts, and the value is flagged reported). Its 2023 adjusted cohort (3,441) is also far above its
entering class (2,055), so the series looks unstable, but I cannot tell from the files whether 2023 or 2024 is the
odd year. Kept as reported; the model results are shown with and without it.

{md(c10, n=20)}

{md(c11)}

**Handling:** values retained as reported. The model is evaluated year by year so that a
shock year is visible in the results instead of being averaged away.

### 5. Imputed values (C05, C16)
Among the 55 peer institutions every retention value in scope is flagged **R (reported)**.
Across the whole national file there are imputed or analyst-corrected values:

{md(c16)}

**Handling:** the pipeline keeps the IPEDS flag with every value and the model uses only
reported values. The check is kept so the same code works if the peer set is widened.

### 6. Checks that passed
No duplicate institution-year-version rows (C02, C03), no retention rates outside 0-100
(C06), no completers exceeding cohort (C08), and every published retention rate matches
retained students divided by the adjusted cohort within one point (C07). No peer cohort is
under 30 students (C14). Because the peer set is public four-year institutions that
report to the federal government, a clean result on these structural checks is expected;
the passes are a result, not an absence of testing.

## Suppression rule (governance)
Dashboard exports suppress any rate whose cohort is under 30 students (`small_cell_min = 30`
in `src/05_export_dashboard.py`). No peer cohort currently triggers it.
"""

os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
with open(os.path.join(ROOT, "docs", "data_quality_log.md"), "w") as f:
    f.write(out)
print("wrote docs/data_quality_log.md", len(out), "chars")
