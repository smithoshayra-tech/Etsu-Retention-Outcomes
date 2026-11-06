# Open-Admission Enrollment Funnel: SQL Pipeline on Simulated Data

**The funnel data in this project is simulated.** Two inputs are real public figures from IPEDS. Everything else is generated with a fixed random seed. Nothing here describes the actual recruitment results of Utah Valley University or any other institution.

## Why simulated

I first planned to compare Utah Valley University's application-to-enrollment yield with Utah public peers using IPEDS Admissions data. That cannot be done. I loaded the Admissions files for 2014 to 2023 and Utah Valley University, Weber State University and Utah Tech University have no rows in any year, because open-admission institutions do not complete that survey component. Only Utah State University, the University of Utah and Southern Utah University report (`outputs/real_adm_coverage.csv`). Student-level recruitment funnels sit in an institution's own systems and are not public, so I built a simulated one and anchored it to what is public.

## Real inputs (IPEDS fall 2022, file EF2022C, Utah Valley University)

- About 4,752 first-time degree or certificate-seeking students. This sets the size of each simulated entering class.
- 3,555 of them, 74.8%, Utah residents. This sets the in-state share.

## The question

In a funnel for an open-admission university, where do prospective students drop out, and which levers (lead source, speed of first contact, financial aid filing, residency) move registration and enrollment?

## Data model

A star schema in SQLite: one fact table with one row per inquiry, and three dimension tables.

| Table | Grain | Contents |
|---|---|---|
| `fact_funnel` | One row per inquiry, 93,600 rows over four cycles | Stage flags, stage dates, contact lag in days, aid-form flag |
| `dim_lead_source` | One row per source | Seven lead sources |
| `dim_residency` | One row per residency group | Utah resident, out of state |
| `dim_cycle` | One row per entering term | Fall 2021 to Fall 2024 |

The real IPEDS part uses `dim_institution` and the raw Admissions tables. See `docs/definitions.md` for stage definitions, every assumed rate and the planted effects.

## Validation

Twelve checks in `sql/02_checks.sql`. Eleven test the simulated data (unique IDs, stages that never skip, valid flags, foreign keys, date order, enrolled counts within 5% of the real anchor, in-state share within 2 points of the real share, and others). All pass. Check S12 is informational and reports that Utah Valley University has 0 rows in IPEDS Admissions. The funnel-by-cycle results from SQL match an independent pandas calculation within 0.0001.

## What the analysis shows

These results confirm that the pipeline recovers the effects built into the simulation. They are not findings about real students.

- **Where inquiries are lost (fall 2021 to 2023 pooled, 70,200 inquiries):** 39% start an application, 31% complete one, 30% are admitted, 22% register and 21% are enrolled on census day. Admission removes almost nobody. The losses are at application start, application completion and registration.
- **Lead source:** concurrent-enrollment inquiries enroll at 32.1% and paid social and display at 8.0%, across all four cycles.
- **Speed of first contact (all four cycles):** inquiries first contacted within 3 days start an application at a rate 11.5 points higher than those contacted later (95% bootstrap interval 10.8 to 12.2). The share contacted late rose from 20.9% in 2023 to 36.4% in 2024, the start rate fell from 39.9% to 37.4%, and enrolled students fell from 4,924 to 4,549.
- **Financial aid and residency (all four cycles, 28,032 admitted students):** among admitted students, registration is 87.6% for Utah residents who filed an aid form against 64.4% for those who did not, and 73.1% against 52.0% for out-of-state students. Admitted students without an aid form fail to register at 39.5% against 15.3% for those with one.

Charts are in `outputs/charts/`.

## Limits

- Every stage rate, source multiplier and effect size is an assumption I chose. The effects the analysis "finds" are the ones I planted.
- The only real figures are the two IPEDS anchors above. The simulation says nothing about Utah Valley University's actual conversion rates, lead sources or response times.
- There is no Banner Student or recruitment CRM data here. This project shows how I would structure and analyze that kind of data, not experience with those systems.
- The fall 2024 cycle is simulated, so it should not be compared with any real figure.

## AI use

I drafted the code with an AI assistant (Claude) and reviewed the stage definitions, assumptions, checks and results. The SQL results were checked independently in pandas.

## Reproduce

```
bash src/00_download.sh      # downloads the IPEDS files from NCES
bash src/run_all.sh          # builds the database, simulates, runs checks, analysis and charts
```

The simulation uses a fixed seed (20261106), so every run gives identical numbers.

## Files

- `src/` Python and shell scripts, numbered in run order
- `sql/` views, validation checks and analysis queries
- `docs/definitions.md` stages, assumptions, planted effects, metric formulas
- `outputs/` result tables, `checks_summary.csv`, `run_log.txt`, charts
