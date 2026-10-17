# ETSU retention and graduation vs. public peer universities

**The question.** How do East Tennessee State University's first-year retention rate and
six-year graduation rate compare with similar public universities, how has that changed
since 2013, and can next year's retention be predicted?

**Data.** Public, school-level numbers that every U.S. college reports to the federal
government (IPEDS), report years 2013 to 2024. No student records. **Tools:** SQL (SQLite),
Python (pandas, scikit-learn) and Power BI tables.

*Retention rate: the share of first-time, full-time students who come back the next fall.
Graduation rate: the share who finish a bachelor's degree within six years.*

![Model error by year](outputs/figures/model_error_by_year.png)

## The short answer

1. **Retention has nearly caught up.** ETSU's retention rate rose from 66% to
   76%. The typical regional peer is at 78%, so the gap
   shrank from 12 points to 2.
2. **Graduation still trails.** ETSU graduates 53.2% of students within six years.
   The typical regional peer graduates 57.7%, a gap of
   4.5 points.
3. **Next year's retention is hard to beat with a model.** Guessing "same as last year" is
   about as accurate as the more complex models I tested.

## What the data shows

**Retention.** ETSU rose from 66% (2013) to 76% (2024). The middle
regional peer (the median of 39 schools) was 78% in 2013 and
78% in 2024. In 2013 ETSU was higher than only 5% of
regional peers. In 2024 it was higher than 23%. Compared with the
Georgia group (median 77%), ETSU was 1 point lower.

**Graduation.** ETSU went from 41.3% to 53.2%. The regional median went from
51.2% to 57.7%, so the gap narrowed from
9.9 to 4.5 points. ETSU is
4.3 points above the Georgia group median (48.9%).

**One thing to keep in mind.** Graduation is measured six years after students enter, so the
53.2% rate in 2024 describes the class that started in 2017. That class had a
retention rate of 73%, below today's 76%. Newer classes may therefore graduate at a
somewhat higher rate. That is something to check with ETSU's own tracking, not a prediction.

## What I would recommend, and to whom

These are recommendations from public data only. Each one says what to do and what to check
first, because public data cannot show why a student left.

| Who | What the data suggests | What I would do |
|---|---|---|
| **Provost and student success leaders** | Retention is 2 points behind peers, but graduation is 4.5 points behind. | Make graduation the next target, with the regional median (57.7%) as the reference point. Track each entering class by year so progress is visible before the six-year mark. |
| **Enrollment and budget planners** | Retention is very steady from year to year, and no model beat "same as last year." | Plan next year's retention at this year's rate, plus or minus about 4 points. Keep a contingency for shocks: ETSU fell from 78% to 67% in 2021 and no model saw it coming. |
| **Institutional research** | Public data has no aid, major, first-generation or part-time detail. | Use ETSU's own cohort data to find which groups leave and in which year. Re-run this analysis when 2025 files are published, and replace the provisional 2024 values when a revised file is released. |
| **Advising and student support** | Peer data can show that a gap exists but not who is affected. | Start with the groups and years where the internal data shows the most loss, before adding new programs. |

**What this data cannot say.** It does not show why ETSU's retention improved. The peers are
a mixed group, so medians show position and not cause. It covers only first-time, full-time
students.

## How peers were chosen

Public, four-year schools that offer undergraduate degrees and are classified as doctoral or
master's universities (Carnegie 2021 classes 15 to 19). The rule runs in SQL
(`sql/01_views.sql`), so I did not hand-pick schools.

| Group | States | Schools |
|---|---|---|
| Regional (includes ETSU, so 39 peers) | TN, NC, VA, KY | 40 |
| Georgia | GA | 15 |

Schools that merged under a new ID keep only the years filed under the current ID.

## How the data was checked

16 checks run on every build. 8 pass and the rest are flags, each with a decision
about how to handle it (full log: `docs/data_quality_log.md`). The main points:

- **Revised files win.** IPEDS publishes original and revised files, and they differ for some
  schools. The pipeline uses the revised value and logs every difference.
- **I tested the graduation year instead of assuming it.** Entering-class counts matched
  graduation counts six years later within 0.1% (median). Other offsets were 5% or worse.
- **Two Georgia schools look odd.** Albany State and Georgia Southern show counts more than
  10% apart in 9 school-years. Both were consolidated, so
  this is expected. The graduation rate does not depend on those counts.
- **No estimated values.** All 658 peer observations are reported figures, not estimates.

## Can next year's retention be predicted?

I tried to predict each school's retention from what was known a year earlier (the last two
years of retention, graduation rate, students per faculty member, class size and school type).
Each test year used only earlier years to learn, and there were 385 test predictions
from 2018 to 2024.

| Method | Average miss (percentage points) |
|---|---|
| Same as last year | 2.61 |
| Average of last two years | 2.52 |
| Ridge regression (a statistical model) | 2.49 |
| Gradient boosting (a machine learning model) | 2.65 |

**What this means.** A simple rule works as well as the complex models. The best model
improved on "same as last year" by only 0.12 points, and that gain could easily be
chance (range -0.02 to +0.26). Gradient boosting did not help either
(-0.05). An earlier version of this analysis, ending in 2023, showed a small gain.
It disappeared when 2024 was added, which is why I trust the larger result.

**Where every method failed.** 2021 (students who entered in fall 2020) caught all of them off
guard. ETSU fell from 78% to 67%. In 2024, Tennessee State fell from 60% to 33%, and the ridge
model missed it by 31 points. The comparison barely changes without that school
(+0.11, range -0.04 to +0.26).

![ETSU backtest](outputs/figures/etsu_backtest.png)

**A forecast I made before seeing the answer.** Before loading the 2024 files, the model
forecast 74% for ETSU (a likely range of about 4 points either way, saved in
`docs/forecast_2024_made_before_data.json`). ETSU reported 76%, which is inside that range.
"Same as last year" would have said 74%, so the model added nothing. My forecast for report year 2025
is 76% (`outputs/etsu_forecast_2025.json`). It cannot be checked until the 2025 files are published.

## Privacy

Public school-level data only, with no student records. Rates based on fewer than 30 students
would be hidden along with the counts behind them (none apply today). Definitions and data
lineage are in `docs/data_dictionary.md` and `docs/governance.md`. This shows how a small-group
rule and lineage notes work. It is not experience with restricted student data.

## Limitations

- Retention covers first-time, full-time students only. Part-time and transfer students are not included.
- Medians are not weighted by school size, and the peer group is mixed.
- The model uses last year's published numbers, so it is a benchmark, not an early-warning tool.
- There are no admissions, financial aid or demographic inputs.
- Schools that changed IDs in a merger are not joined into one series.
- Report year 2025 (fall 2025) is not published yet. The 2024 files were downloaded by hand
  from IPEDS and are provisional, so values may change when a revised file is released.
- The peer list comes from the 2023 directory. Schools that closed or changed class in 2024
  were not re-checked.
- The Power BI file is built from `outputs/powerbi/` using `docs/powerbi_build_guide.md`.
  The DAX was written outside Power BI Desktop and still needs testing in it.

## Run it

```bash
bash src/00_download.sh            # downloads 2013-2023 (2024 files: see note in that script)
pip install pandas scikit-learn matplotlib tabulate openpyxl
bash run_all.sh                    # build db, checks, log, model, export, figures, README
```

| Script | Purpose |
|---|---|
| `src/01_build_db.py`, `sql/01_views.sql` | Load files, define peer rule and views |
| `sql/02_quality_checks.sql`, `src/02_quality_checks.py` | Sixteen validation queries |
| `src/03_dq_log.py` | Generate the data-quality log |
| `src/04_model.py` | Out-of-time model evaluation |
| `src/05_export_dashboard.py` | Power BI tables, findings summary |
| `src/06_charts.py`, `src/07_build_readme.py` | Figures and this README |

Source: National Center for Education Statistics, IPEDS Data Center.
