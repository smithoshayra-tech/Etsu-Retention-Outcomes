# Governance notes

## Data handling
- Public, aggregate, institution-level data only. No student-level records were used or are needed.
- Source files are downloaded by script (`src/00_download.sh`) from the publisher and are not edited by hand.

## Lineage
IPEDS complete files -> SQLite raw tables (unchanged values, original and revised kept) ->
SQL views (revised preferred, peer rule applied) -> 16 validation queries -> model and
Power BI exports. Every transformation is a SQL view or a Python script in this repository.

## Rules applied
| Rule | Where | Effect |
|---|---|---|
| Small-cell suppression: cohort under 30 | `src/05_export_dashboard.py` | Rate and underlying counts blanked in exports |
| Imputation flags kept | `ef_retention_raw`, `fact_outcomes.retention_flag` | Imputed values stay identifiable |
| Revised over original | `sql/01_views.sql` | Differences logged in the data quality log |
| No stitching across institution mergers | README limitations | Gaps are shown, not filled |

## Scope statement
The suppression rule and lineage notes are a demonstration on public data. They are not
evidence of experience handling restricted student records or of FERPA training.
