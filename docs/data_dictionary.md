# Data dictionary

Source: IPEDS Data Center complete data files, National Center for Education Statistics.
Definitions below follow the official IPEDS data dictionaries (HD2023, EF2023D, GR2023; 2024 files share the 2023 layout).

## Files used

| Source file | Report years | Used for |
|---|---|---|
| HD (Institutional Characteristics) | 2023 | Name, state, control, level, Carnegie class |
| EF{yr}D (Fall Enrollment, retention) | 2013-2024 | Retention, cohort size, student-faculty ratio |
| GR{yr} (Graduation Rates) | 2013-2024 | Bachelor's cohort and 150% completers |

Both the original and the revised (`_rv`) file are loaded for each year the revised file
exists (2013-2022). Revised values take precedence.

## Output columns (`outputs/powerbi/fact_outcomes.csv`)

| Column | IPEDS variable | Meaning |
|---|---|---|
| ft_cohort_adj | RRFTCTA | Full-time adjusted entering cohort, fall of (report year - 1) |
| ft_retained_n | RET_NMF | Students from that cohort enrolled again the following fall |
| ft_retention_pct | RET_PCF | Full-time retention rate, as published |
| retention_flag | XRET_PCF | IPEDS status flag (R reported, A not applicable, N/P imputed, C analyst corrected) |
| grad_cohort_year | derived | Entering year of the graduation cohort = report year - 6 (tested, see data quality log) |
| ba_cohort_n | GRTOTLT, GRTYPE 8 | Bachelor's-seeking adjusted cohort |
| ba_completers_n | GRTOTLT, GRTYPE 9 | Bachelor's-subcohort completers within 150% of normal time |
| grad_rate_6yr_pct | derived | 100 x completers / cohort, rounded to one decimal |
| student_faculty_ratio | STUFACR | Student-to-faculty ratio |
| retention_suppressed, grad_suppressed | derived | 1 when the cohort is under 30 and the values are blanked |

## Peer group

Public (CONTROL = 1), four-year (ICLEVEL = 1), active (CYACTIVE = 1), offers undergraduate
degrees (UGOFFER = 1), Carnegie 2021 Basic class 15 to 19. Regional = TN, NC, VA, KY;
Georgia = GA.

## Known definitional limits

- Retention counts first-time, full-time degree-seeking undergraduates only.
- Graduation rates cover the first-time, full-time bachelor's-seeking cohort, 150% of normal time.
- Carnegie class is the 2021 classification, applied to all years.
