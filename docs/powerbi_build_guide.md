# Power BI build guide

The Power BI file itself is not included: Power BI Desktop is a Windows application and
could not be run in the workspace this project was built in. The tables in
`outputs/powerbi/` are ready to load, and the measures below are written but **untested
in Power BI Desktop**. Use the tie-out checks at the bottom to verify each one before
publishing anything.

## 1. Load
Get Data > Text/CSV, load all five files in `outputs/powerbi/`. Set `unitid` and
`report_year` to Whole Number; leave the rest as detected. Blank cells in the rate and
count columns are intentional (small-cell suppression).

## 2. Relationships (Model view)
| From (many) | To (one) | Column |
|---|---|---|
| fact_outcomes | dim_institution | unitid |
| fact_outcomes | dim_year | report_year |
| fact_model_backtest | dim_institution | unitid |
| fact_model_backtest | dim_year | report_year |

Single-direction filtering from the dimension tables to the facts. `fact_dq_summary` stands alone.

## 3. Measures
```dax
Retention (pts) =
AVERAGE ( fact_outcomes[ft_retention_pct] )

Six-Year Graduation (pts) =
AVERAGE ( fact_outcomes[grad_rate_6yr_pct] )

ETSU Retention (pts) =
CALCULATE ( [Retention (pts)], REMOVEFILTERS ( dim_institution[peer_group] ), dim_institution[is_home] = 1 )

Peer Median Retention (pts) =
MEDIANX (
    FILTER ( ALLSELECTED ( dim_institution[unitid], dim_institution[is_home] ), dim_institution[is_home] = 0 ),
    [Retention (pts)]
)

Gap to Peer Median (pts) = [ETSU Retention (pts)] - [Peer Median Retention (pts)]

ETSU Graduation (pts) =
CALCULATE ( [Six-Year Graduation (pts)], REMOVEFILTERS ( dim_institution[peer_group] ), dim_institution[is_home] = 1 )

Peer Median Graduation (pts) =
MEDIANX (
    FILTER ( ALLSELECTED ( dim_institution[unitid], dim_institution[is_home] ), dim_institution[is_home] = 0 ),
    [Six-Year Graduation (pts)]
)

Model Miss (pts) =
AVERAGEX ( fact_model_backtest, ABS ( fact_model_backtest[ridge] - fact_model_backtest[actual] ) )

Same-as-Last-Year Miss (pts) =
AVERAGEX ( fact_model_backtest, ABS ( fact_model_backtest[naive_last] - fact_model_backtest[actual] ) )
```

## 4. Pages
1. **ETSU vs. peers.** Line chart: report year on the axis, ETSU Retention and Peer Median
   Retention as two series. Cards: latest-year gap. Slicer: dim_institution[peer_group].
   Repeat for graduation.
2. **Institution view.** Table for a selected report year with institution, Carnegie class,
   retention, graduation. Sort by retention; no conditional colors beyond one highlight for ETSU.
3. **Data quality.** Table from fact_dq_summary (check, status, rows flagged, description).
4. **Model.** Clustered column by report year: Model Miss vs. Same-as-Last-Year Miss.
   Add a text box stating the result: the model's gain is small.

## 5. Tie-out checks (do these before sharing)
Filter to report year 2024 and the Regional peer group. Each value must match the README.

| Visual | Expected |
|---|---|
| ETSU Retention (pts) | 76 |
| Peer Median Retention (pts), Regional | 78 |
| Peer Median Retention (pts), Georgia | 77 |
| ETSU Graduation (pts) | 53.2 |
| Peer Median Graduation (pts), Regional | 57.7 |
| Peer Median Graduation (pts), Georgia | 48.9 |
| Model Miss, all years | about 2.49 |
| Same-as-Last-Year Miss, all years | about 2.61 |

If a value does not match, fix the measure, not the expected number.
