# Data quality log

Source: IPEDS Data Center complete data files (HD2023, EF2013D-EF2024D, GR2013-GR2024),
downloaded directly from nces.ed.gov. Scope: 55 public four-year institutions that meet
the peer rule in README (658 institution-years, report years 2013-2024).
Every check is a SQL query in `sql/02_quality_checks.sql`; counts below come from
`outputs/dq_summary.csv`.

## Result summary

| check                          | status   |   rows_flagged | description                                                                                                          |
|:-------------------------------|:---------|---------------:|:---------------------------------------------------------------------------------------------------------------------|
| C01_coverage_gap               | FLAG     |              2 | Peer institution has no retention record for a report year                                                           |
| C02_duplicate_ef               | PASS     |              0 | More than one row per institution, year and file version (retention)                                                 |
| C03_duplicate_gr               | PASS     |              0 | More than one row per institution, year, measure and file version (graduation)                                       |
| C04_retention_missing          | PASS     |              0 | Peer institution-year with no retention rate                                                                         |
| C05_retention_not_reported     | PASS     |              0 | Retention value not flagged R (reported); IPEDS flag shows it was imputed or derived                                 |
| C06_retention_out_of_range     | PASS     |              0 | Retention rate outside 0-100                                                                                         |
| C07_retention_recompute        | PASS     |              0 | Published retention rate differs from retained / adjusted cohort by more than 1 point                                |
| C08_graduation_logic           | PASS     |              0 | Completers exceed cohort, or negative counts                                                                         |
| C09_graduation_missing         | FLAG     |              1 | Peer institution-year with no bachelor's graduation cohort                                                           |
| C10_retention_yoy_jump         | FLAG     |             14 | Retention moved more than 10 points versus the prior year for the same institution                                   |
| C11_graduation_yoy_jump        | FLAG     |              2 | 6-year graduation rate moved more than 10 points versus the prior year                                               |
| C12_revised_changes_retention  | FLAG     |              1 | Revised file changes the retention rate compared with the original file                                              |
| C13_revised_changes_graduation | FLAG     |              4 | Revised file changes the bachelor's cohort or completers compared with the original file                             |
| C14_small_cell                 | PASS     |              0 | Full-time cohort under 30 students (rate is too volatile to publish at institution level)                            |
| C15_cross_file_cohort_mismatch | FLAG     |              9 | Entering-class count (retention file) and graduation cohort (graduation file, 6 years later) differ by more than 10% |
| C16_imputed_values_national    | FLAG     |              3 | Imputed or carried-forward retention values anywhere in the national file (all institutions, not only peers)         |

## What was found and how each item was handled

### 1. Original vs. revised files (C12, C13)
IPEDS published a revised file alongside the original for report years 2013-2022 (none
yet for 2023 or 2024). The pipeline loads both and uses the revised value when one exists. Among
peer institutions the revised files changed 1 retention value and 4
graduation counts, shown below. Tennessee State University accounts for the retention
change and two of the graduation changes; its 2020 bachelor's cohort moved by
-42 students.
The largest single change by count is UNC Chapel Hill (+58 completers, 2021).

|   unitid | institution                |   report_year |   original_pct |   revised_pct |   change |
|---------:|:---------------------------|--------------:|---------------:|--------------:|---------:|
|   221838 | Tennessee State University |          2020 |             64 |            65 |        1 |

|   unitid | institution                                 |   report_year | measure       |   original_n |   revised_n |   change |
|---------:|:--------------------------------------------|--------------:|:--------------|-------------:|------------:|---------:|
|   199120 | University of North Carolina at Chapel Hill |          2021 | completers_ba |         3685 |        3743 |       58 |
|   221838 | Tennessee State University                  |          2020 | cohort_ba     |         1283 |        1241 |      -42 |
|   221838 | Tennessee State University                  |          2020 | completers_ba |          349 |         388 |       39 |
|   232423 | James Madison University                    |          2018 | completers_ba |         3612 |        3624 |       12 |

### 2. Missing records (C01, C09)
|   unitid | institution               |   report_year |
|---------:|:--------------------------|--------------:|
|   486840 | Kennesaw State University |          2013 |
|   486840 | Kennesaw State University |          2014 |

Kennesaw State has no retention record under its current ID for 2013 and 2014. The USG
consolidation page confirms Kennesaw State consolidated with Southern Polytechnic State
University; this is consistent with the institution receiving a new ID, but I did not
trace predecessor IDs, so I have not stitched a pre-2015 series. Those two years are
simply absent. One graduation record is missing:

|   unitid | institution                     |   report_year |
|---------:|:--------------------------------|--------------:|
|   482158 | Middle Georgia State University |          2016 |

**Handling:** rows with no value are excluded from the model and shown as blank in the
dashboard. Nothing was filled in.

### 3. Entering class vs. graduation cohort (C15)
For 9 institution-years the full-time entering class in the retention file and the
graduation cohort six years later differ by more than 10%. The offset itself was tested
first: across institutions, entering-class counts match graduation-cohort counts with a
median absolute difference of 0.1% at a six-year offset and 5% or more at other offsets.

|   unitid | institution                 |   grad_report_year |   entering_class |   grad_cohort |   pct_diff |
|---------:|:----------------------------|-------------------:|-----------------:|--------------:|-----------:|
|   138716 | Albany State University     |               2020 |              428 |          1213 |      183.4 |
|   138716 | Albany State University     |               2019 |              508 |          1416 |      178.7 |
|   138716 | Albany State University     |               2021 |              477 |          1193 |      150.1 |
|   138716 | Albany State University     |               2022 |              435 |           791 |       81.8 |
|   139931 | Georgia Southern University |               2022 |             3560 |          4477 |       25.8 |
|   139931 | Georgia Southern University |               2021 |             3463 |          4342 |       25.4 |
|   139931 | Georgia Southern University |               2023 |             3472 |          4334 |       24.8 |
|   139931 | Georgia Southern University |               2019 |             3544 |          4408 |       24.4 |
|   139931 | Georgia Southern University |               2020 |             3476 |          4253 |       22.4 |

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
14 retention changes and 2 graduation changes exceeded 10 points.
6 of the 14 retention jumps fall in report year 2021 (the fall 2020 entering
cohort), spread across 6 different institutions, including ETSU
(78% to 67%).
5 of those 6 are declines; one institution rose. Several unrelated
institutions moving in the same year points more toward a shared cause than independent
data errors, but I did not investigate a specific cause, so the dashboard shows the change
without attributing it.

Report year 2024 adds one: Tennessee State, 60% to 33% (550 retained of 1,642; the published rate matches
the counts, and the value is flagged reported). Its 2023 adjusted cohort (3,441) is also far above its
entering class (2,055), so the series looks unstable, but I cannot tell from the files whether 2023 or 2024 is the
odd year. Kept as reported; the model results are shown with and without it.

|   unitid | institution                           |   report_year |   prev |   pct |   change |
|---------:|:--------------------------------------|--------------:|-------:|------:|---------:|
|   221838 | Tennessee State University            |          2024 |     60 |    33 |      -27 |
|   141264 | Valdosta State University             |          2021 |     73 |    56 |      -17 |
|   139366 | Columbus State University             |          2021 |     75 |    61 |      -14 |
|   234155 | Virginia State University             |          2021 |     62 |    76 |       14 |
|   138716 | Albany State University               |          2020 |     61 |    74 |       13 |
|   139311 | Clayton  State University             |          2023 |     60 |    73 |       13 |
|   139764 | Georgia Southwestern State University |          2021 |     66 |    54 |      -12 |
|   198543 | Fayetteville State University         |          2016 |     79 |    67 |      -12 |
|   221838 | Tennessee State University            |          2021 |     65 |    53 |      -12 |
|   234155 | Virginia State University             |          2015 |     61 |    73 |       12 |
|   138716 | Albany State University               |          2016 |     78 |    67 |      -11 |
|   198543 | Fayetteville State University         |          2017 |     67 |    78 |       11 |
|   220075 | East Tennessee State University       |          2021 |     78 |    67 |      -11 |
|   482158 | Middle Georgia State University       |          2019 |     64 |    53 |      -11 |

|   unitid | institution                |   report_year |   prev |   pct |   change |
|---------:|:---------------------------|--------------:|-------:|------:|---------:|
|   221838 | Tennessee State University |          2017 |   41.9 |  28.8 |    -13.1 |
|   221838 | Tennessee State University |          2014 |   29.4 |  42.2 |     12.8 |

**Handling:** values retained as reported. The model is evaluated year by year so that a
shock year is visible in the results instead of being averaged away.

### 5. Imputed values (C05, C16)
Among the 55 peer institutions every retention value in scope is flagged **R (reported)**.
Across the whole national file there are imputed or analyst-corrected values:

| flag   | meaning                          |   institution_years |
|:-------|:---------------------------------|--------------------:|
| N      | Imputed: nearest neighbor        |                  50 |
| P      | Imputed: carry forward           |                  43 |
| C      | Analyst corrected reported value |                   1 |

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
