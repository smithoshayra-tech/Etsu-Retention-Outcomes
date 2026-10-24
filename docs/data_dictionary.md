# Data dictionary

Source: IPEDS Data Center complete data files, National Center for Education Statistics.
Definitions follow the official IPEDS data dictionaries (HD2023, EF2023D, GR2023; the 2024
files share the 2023 layout). The dictionaries are stored in `dict/`.

This file documents every table, column, metric and check in the pipeline. Where a column
comes straight from IPEDS, the IPEDS variable name is given so it can be traced back to the
publisher's definition. Where a column is derived, the formula is given and the script that
creates it is named.

Contents: 1 Lineage, 2 Source files, 3 Database tables, 4 Views, 5 Metric definitions,
6 Code lists, 7 Power BI tables, 8 Validation checks, 9 Model tables, 10 Peer group,
11 Known definitional limits.

## 1. Lineage

```
IPEDS files (HD, EF, GR) --src/01_build_db.py--> raw tables (SQLite)
   --sql/01_views.sql--> dim_institution, peer_group, v_retention, v_grad, v_outcomes
   --sql/02_quality_checks.sql (src/02_quality_checks.py)--> 16 checks, outputs/dq/, dq_summary.csv
   --src/04_model.py--> model_predictions.csv, model_metrics.csv, ridge_coefficients.csv, forecasts
   --src/05_export_dashboard.py--> outputs/powerbi/*.csv, findings.json
```

The database file `outputs/ipeds.db` is rebuilt on every run and is not committed.

## 2. Source files

| Source file | Report years | Used for |
|---|---|---|
| HD (Institutional Characteristics) | 2023 | Name, city, state, control, level, Carnegie class, active status |
| EF{yr}D (Fall Enrollment, retention) | 2013-2024 | Retention, cohort size, student-faculty ratio |
| GR{yr} (Graduation Rates) | 2013-2024 | Bachelor's cohort and completers within 150% of normal time |

Both the original and the revised (`_rv`) file are loaded for each year the revised file
exists (2013-2022). The revised value takes precedence in the views. There is no revised file
yet for 2023 or 2024, and the 2024 files are provisional.

Report year `y` means the IPEDS collection for fall `y`. The retention cohort entered in fall
`y - 1`. The graduation cohort entered in `y - 6` (tested, see check C15 and the data quality log).

## 3. Database tables (raw, values unchanged)

### `ef_retention_raw` (one row per institution, report year and file version)

| Column | IPEDS variable | Type | Meaning |
|---|---|---|---|
| UNITID | UNITID | integer | Unique IPEDS institution identifier. Primary key across all tables. |
| report_year | derived | integer | Collection year of the file, 2013-2024. |
| version | derived | text | `original` or `revised`, from the file name. |
| GRCOHRT | GRCOHRT | integer | Full-time, first-time degree or certificate-seeking undergraduates (the graduation-rate survey cohort for that year). |
| UGENTERN | UGENTERN | integer | Total entering undergraduates in the fall of the report year. |
| RRFTCT | RRFTCT | integer | Full-time cohort entering the prior fall, before adjustment. |
| RRFTCTA | RRFTCTA | integer | Full-time cohort entering the prior fall, after IPEDS exclusions (adjusted). |
| RET_NMF | RET_NMF | integer | Students from the adjusted cohort enrolled again in the report-year fall. |
| RET_PCF | RET_PCF | integer | Full-time retention rate as published, a whole percent. |
| STUFACR | STUFACR | integer | Student-to-faculty ratio. |
| X{variable} | X + variable | text | IPEDS status flag for the matching variable (for example XRET_PCF). See section 6. Kept wherever the file provides it. |

### `gr_raw` (one row per institution, report year, measure and file version)

| Column | Source | Type | Meaning |
|---|---|---|---|
| UNITID, report_year, version | as above | | |
| measure | derived from GRTYPE | text | `cohort_4yr_all` (GRTYPE 2), `completers_4yr_all` (3), `cohort_ba` (8), `completers_ba` (9). Other GRTYPE rows are not loaded. |
| GRTOTLT | GRTOTLT | integer | Grand total students for that measure. |
| XGRTOTLT | XGRTOTLT | text | IPEDS status flag for GRTOTLT. |

### `institution_raw` (one row per institution, HD2023)

| Column | IPEDS variable | Meaning |
|---|---|---|
| UNITID | UNITID | Institution identifier. |
| INSTNM | INSTNM | Institution name. Trimmed in `dim_institution`. |
| CITY | CITY | City. |
| STABBR | STABBR | State abbreviation. |
| CONTROL | CONTROL | 1 public, 2 private not-for-profit, 3 private for-profit. |
| ICLEVEL | ICLEVEL | 1 four or more years, 2 at least two but under four years, 3 under two years. |
| UGOFFER | UGOFFER | 1 offers undergraduate degrees or certificates, 2 does not. |
| C21BASIC | C21BASIC | Carnegie Classification 2021, Basic. Classes 15-19 are used here (section 6). |
| CYACTIVE | CYACTIVE | 1 active in the current year, 3 closed, combined or out of scope. |
| OPEFLAG | OPEFLAG | Title IV eligibility indicator. Loaded, not used in any rule. |
| INSTSIZE | INSTSIZE | Institution size category. Loaded, not used in any rule. |

## 4. Views and derived tables (`sql/01_views.sql`)

| Object | Grain | Purpose |
|---|---|---|
| `dim_institution` | one row per institution | Cleaned name, state, Carnegie class and label, and `is_home` (1 for ETSU, UNITID 220075). |
| `peer_group` | one row per peer institution | Applies the peer rule (section 10) and assigns `regional` or `georgia`. |
| `v_retention` | institution x report year | Retention fields with the revised file preferred over the original. Adds `cohort_entry_year = report_year - 1`. |
| `v_grad` | institution x report year | Pivots the four graduation measures into columns, revised preferred, per measure. Adds `cohort_entry_year = report_year - 6`. |
| `v_outcomes` | peer institution x report year | Joins the three above. This is the base table for the checks, the model and the dashboard exports. |

### `v_outcomes` columns

| Column | Source | Meaning |
|---|---|---|
| unitid, institution, state | `dim_institution` | Identity. |
| carnegie_2021, carnegie_label | `dim_institution` | Carnegie class code and text label. |
| is_home | `dim_institution` | 1 for ETSU. |
| peer_group | `peer_group` | `regional` or `georgia`. |
| report_year | `v_retention` | Collection year. |
| retention_cohort_year | `report_year - 1` | Fall the retention cohort entered. |
| ft_cohort_adj | RRFTCTA | Adjusted full-time entering cohort. |
| ft_retention_pct | RET_PCF | Published retention rate. |
| retention_flag | XRET_PCF | Status flag for the retention rate. |
| entering_ug | UGENTERN | Total entering undergraduates. |
| student_faculty_ratio | STUFACR | Student-to-faculty ratio. |
| grad_cohort_year | `report_year - 6` | Fall the graduation cohort entered. Null when no graduation record exists. |
| ba_cohort_n | GRTOTLT, GRTYPE 8 | Bachelor's-seeking adjusted cohort. |
| ba_completers_n | GRTOTLT, GRTYPE 9 | Completers of that cohort within 150% of normal time. |
| grad_rate_6yr_pct | derived | See section 5. |

## 5. Metric definitions

| Metric | Formula | Notes |
|---|---|---|
| Retention rate (`ft_retention_pct`) | As published in RET_PCF | A whole percent. Check C07 recomputes it as `100 x ft_retained_n / ft_cohort_adj` and flags gaps over 1 point. Zero were flagged. |
| Six-year graduation rate (`grad_rate_6yr_pct`) | `ROUND(100 x ba_completers_n / ba_cohort_n, 1)`, only when `ba_cohort_n > 0` | Matches the IPEDS Graduation Rate definition: share of the first-time, full-time bachelor's-seeking cohort that completed any award within 150% of normal time (six years). GRTYPE 9 counts all completers in that cohort, which can include students who finished a sub-bachelor's award. |
| Peer median | Median of `ft_retention_pct` or `grad_rate_6yr_pct` across peers in one group and report year, home institution excluded | Unweighted by school size. Computed in `src/05_export_dashboard.py`. |
| Gap (points) | ETSU value minus peer median | Positive means ETSU is higher. |
| Percentile among peers | Share of peers with a value below ETSU's, times 100 | Stored in `outputs/findings.json` as `etsu_pctile_regional` and `etsu_pctile_all_peers`. |
| Small-cell suppression | A cohort under 30 students blanks the rate and the counts behind it | Threshold is `small_cell_min = 30` in `src/05_export_dashboard.py`. No row is affected today. |

## 6. Code lists

**IPEDS status flags (XRET_PCF, XGRTOTLT).** Only `R` appears among the 658 peer retention
values. The national check C16 counts the others.

| Code | Meaning |
|---|---|
| R | Reported |
| A | Not applicable |
| B | Institution left item blank |
| C | Analyst corrected reported value |
| G | Data generated from other data values |
| H | Value not derived, data not usable |
| J | Logical imputation |
| K | Ratio adjustment |
| L | Imputed using the group median procedure |
| N | Imputed using the nearest neighbor procedure |
| P | Imputed using the carry forward procedure |
| Z | Implied zero |

**GRTYPE values loaded.**

| GRTYPE | Loaded as | Meaning |
|---|---|---|
| 2 | cohort_4yr_all | Four-year institutions, adjusted cohort (revised cohort minus exclusions) |
| 3 | completers_4yr_all | Four-year institutions, completers within 150% of normal time |
| 8 | cohort_ba | Bachelor's or equivalent subcohort, adjusted cohort |
| 9 | completers_ba | Bachelor's or equivalent subcohort, completers within 150% of normal time, total |

**Carnegie 2021 Basic classes used.**

| Code | Label in this project | IPEDS label |
|---|---|---|
| 15 | Doctoral: highest research | Doctoral Universities: Highest Research Activity |
| 16 | Doctoral: higher research | Doctoral Universities: Higher Research Activity |
| 17 | Doctoral/professional | Doctoral/Professional Universities |
| 18 | Master's: larger | Master's Colleges and Universities: Larger Programs |
| 19 | Master's: medium | Master's Colleges and Universities: Medium Programs |

## 7. Power BI tables (`outputs/powerbi/`, written by `src/05_export_dashboard.py`)

### `fact_outcomes.csv` (658 rows, one per peer institution and report year, 55 institutions, 2013-2024)

| Column | Source | Meaning | Nulls today |
|---|---|---|---|
| unitid | UNITID | Institution key. Joins to `dim_institution`. | 0 |
| report_year | derived | Collection year. Joins to `dim_year`. | 0 |
| retention_cohort_year | `report_year - 1` | Fall the retention cohort entered. | 0 |
| ft_cohort_adj | RRFTCTA | Full-time adjusted entering cohort. | 0 |
| ft_retained_n | RET_NMF | Students from that cohort enrolled again the following fall. | 0 |
| ft_retention_pct | RET_PCF | Full-time retention rate, as published. | 0 |
| retention_flag | XRET_PCF | IPEDS status flag (section 6). | 0 |
| grad_cohort_year | `report_year - 6` | Entering year of the graduation cohort. | 1 |
| ba_cohort_n | GRTOTLT, GRTYPE 8 | Bachelor's-seeking adjusted cohort. | 1 |
| ba_completers_n | GRTOTLT, GRTYPE 9 | Completers within 150% of normal time. | 1 |
| grad_rate_6yr_pct | derived | `100 x ba_completers_n / ba_cohort_n`, one decimal. | 1 |
| student_faculty_ratio | STUFACR | Student-to-faculty ratio. Not suppressed. | 0 |
| retention_suppressed | derived | 1 when `ft_cohort_adj < 30`, which blanks the retention fields. | 0 (all values 0) |
| grad_suppressed | derived | 1 when `ba_cohort_n < 30`, which blanks the graduation fields. | 0 (all values 0) |

The one null graduation row is Middle Georgia State University, report year 2016 (check C09).

### `dim_institution.csv` (55 rows)

| Column | Meaning |
|---|---|
| unitid | Institution key. |
| institution | Institution name. |
| state | State abbreviation. |
| peer_group | `regional` (40, includes ETSU) or `georgia` (15). |
| carnegie_2021, carnegie_label | Carnegie class code and label. |
| is_home | 1 for ETSU, 0 for all others. |

### `dim_year.csv` (12 rows)

| Column | Meaning |
|---|---|
| report_year | Each report year from 2013 to 2024. |

### `fact_model_backtest.csv` (385 rows)

| Column | Meaning |
|---|---|
| unitid, report_year | Institution and test year, 2018-2024. |
| actual | Published retention rate for that year. |
| naive_last | Prediction: same as last year. |
| naive_avg2 | Prediction: average of the last two years. |
| ridge | Ridge regression prediction. |
| gbm | Gradient boosting prediction. |

### `fact_dq_summary.csv` (16 rows)

| Column | Meaning |
|---|---|
| check | Check identifier, C01 to C16. |
| severity | `fail`, `warn` or `info` (section 8). |
| status | `PASS` when no rows are returned, `FLAG` when rows are returned. |
| rows_flagged | Number of rows the check returned. |
| description | What the check tests. |

## 8. Validation checks (`sql/02_quality_checks.sql`)

Each check is one query that returns the violating rows. Zero rows means pass. The rows for
every check are written to `outputs/dq/{check}.csv`. Decisions on each flag are in
`docs/data_quality_log.md`.

| Check | Severity | What it tests | Fields protected | Result |
|---|---|---|---|---|
| C01_coverage_gap | warn | Peer institution has no retention record for a report year | `v_retention` coverage | FLAG, 2 rows |
| C02_duplicate_ef | fail | More than one retention row per institution, year and file version | `ef_retention_raw` key | PASS |
| C03_duplicate_gr | fail | More than one graduation row per institution, year, measure and version | `gr_raw` key | PASS |
| C04_retention_missing | warn | Peer institution-year with no retention rate | `ft_retention_pct` | PASS |
| C05_retention_not_reported | info | Retention value with a status flag other than R | `retention_flag` | PASS |
| C06_retention_out_of_range | fail | Retention rate below 0 or above 100 | `ft_retention_pct` | PASS |
| C07_retention_recompute | warn | Published rate differs from retained / adjusted cohort by more than 1 point | `ft_retention_pct`, `ft_retained_n`, `ft_cohort_adj` | PASS |
| C08_graduation_logic | fail | Completers exceed cohort, or negative counts | `ba_cohort_n`, `ba_completers_n` | PASS |
| C09_graduation_missing | warn | Peer institution-year with no bachelor's cohort | `ba_cohort_n` | FLAG, 1 row |
| C10_retention_yoy_jump | info | Retention moved more than 10 points versus the prior year | `ft_retention_pct` | FLAG, 14 rows |
| C11_graduation_yoy_jump | info | Graduation rate moved more than 10 points versus the prior year | `grad_rate_6yr_pct` | FLAG, 2 rows |
| C12_revised_changes_retention | info | Revised file changes the retention rate versus the original | `ft_retention_pct` | FLAG, 1 row |
| C13_revised_changes_graduation | info | Revised file changes the bachelor's cohort or completers versus the original | `ba_cohort_n`, `ba_completers_n` | FLAG, 4 rows |
| C14_small_cell | info | Full-time cohort under 30 students | `ft_cohort_adj` | PASS |
| C15_cross_file_cohort_mismatch | warn | Entering class (retention file) and graduation cohort six years later differ by more than 10% | `grad_cohort_year` offset | FLAG, 9 rows |
| C16_imputed_values_national | info | Imputed or carried-forward retention values across the whole national file | `retention_flag` | FLAG, 3 rows |

Severity meaning: `fail` would stop a trustworthy build, `warn` needs a decision that is
written in the data quality log, `info` is reported so a reader can see it.

## 9. Model tables (`src/04_model.py`)

**Target.** `y`, the retention rate in report year `t`. **Features** are known one year
earlier. Each test year `T` from 2018 to 2024 is predicted by a model fit only on target
years before `T`. Rows with a missing lag or feature are dropped before fitting.

| Feature | Definition |
|---|---|
| ret_l1 | Retention rate in `t - 1` |
| ret_l2 | Retention rate in `t - 2` |
| grad_l1 | Six-year graduation rate in `t - 1` |
| sfr_l1 | Student-to-faculty ratio in `t - 1` |
| logcoh_l1 | Natural log of the adjusted full-time cohort in `t - 1` |
| carn_16, carn_17, carn_18, carn_19 | 1 if the Carnegie class equals that code. Class 15 is the reference level. |
| georgia | 1 if the institution is in the Georgia group |

### `outputs/model_predictions.csv` (385 rows)

Identity columns (`unitid`, `institution`, `report_year`, `carnegie_2021`, `peer_group`), the
source values (`ft_retention_pct`, `grad_rate_6yr_pct`, `student_faculty_ratio`,
`ft_cohort_adj`), the ten features above, `y`, the four predictions, `n_train` (rows used to
fit that year's models, 162 to 492), and one error column per prediction.

| Column | Definition |
|---|---|
| naive_last | `ret_l1` |
| naive_avg2 | `(ret_l1 + ret_l2) / 2` |
| ridge | Standardized features, ridge regression, penalty chosen by cross-validation on the training rows only |
| gbm | Gradient boosting, 200 trees, depth 2, learning rate 0.05, subsample 0.8, seed 42 |
| err_{model} | Prediction minus actual, in percentage points. Positive means the model over-predicted. |

### `outputs/model_metrics.csv`

| Column | Definition |
|---|---|
| test_year | 2018-2024, or `all` |
| model | `naive_last`, `naive_avg2`, `ridge` or `gbm` |
| n | Predictions scored |
| mae | Mean absolute error, percentage points |
| rmse | Root mean squared error, percentage points |
| bias | Mean signed error, percentage points |

### Other model outputs

| File | Contents |
|---|---|
| `outputs/model_vs_naive_ci.json` | MAE gain over `naive_last` for each model, with a 95% cluster-bootstrap interval (2,000 resamples of institutions), with and without Tennessee State. |
| `outputs/ridge_coefficients.csv` | Standardized coefficients from a ridge fit on all usable rows. Descriptive only, not tested out of time. |
| `outputs/etsu_backtest.csv` | ETSU actual and predicted retention for 2018-2024. |
| `outputs/etsu_forecast_2025.json` | Unvalidated forecast for report year 2025, plus the 80th percentile absolute ridge error as a band. |
| `docs/forecast_2024_made_before_data.json` | Forecast saved before the 2024 files were loaded. |

## 10. Peer group

Public (`CONTROL = 1`), four-year (`ICLEVEL = 1`), active (`CYACTIVE = 1`), offers undergraduate
degrees (`UGOFFER = 1`), Carnegie 2021 Basic class 15 to 19. Regional = TN, NC, VA, KY;
Georgia = GA. The rule lives in `sql/01_views.sql`, so no school was chosen by hand. The home
institution is ETSU (UNITID 220075). The peer list uses the 2023 directory.

## 11. Known definitional limits

- Retention counts first-time, full-time degree-seeking undergraduates only.
- Graduation rates cover the first-time, full-time bachelor's-seeking cohort, 150% of normal time.
- Carnegie class is the 2021 classification, applied to all years.
- Schools that merged under a new IPEDS ID are not stitched into one series. Gaps are shown, not filled.
- Retention rates are whole percents as published, so a gap between two schools carries up to one point of rounding.
- The 2024 files are provisional and were downloaded by hand.
- Unweighted medians show position, not cause.

Related: `docs/governance.md` (handling rules and scope), `docs/data_quality_log.md` (check
results and decisions), `docs/powerbi_build_guide.md` (dashboard build).
