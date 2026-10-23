-- 02_quality_checks.sql
-- Each block starts with a marker line:  -- check: <id> | <severity> | <what it tests>
-- and holds ONE query that returns the violating rows (zero rows = pass).
-- Run by src/02_quality_checks.py, which counts and logs every result.

-- check: C01_coverage_gap | warn | Peer institution has no retention record for a report year
WITH grid AS (
  SELECT p.unitid, y.yr FROM peer_group p
  CROSS JOIN (SELECT DISTINCT report_year AS yr FROM ef_retention_raw) y)
SELECT g.unitid, d.institution, g.yr AS report_year
FROM grid g JOIN dim_institution d ON d.unitid = g.unitid
LEFT JOIN v_retention r ON r.unitid = g.unitid AND r.report_year = g.yr
WHERE r.unitid IS NULL ORDER BY 2, 3;

-- check: C02_duplicate_ef | fail | More than one row per institution, year and file version (retention)
SELECT UNITID, report_year, version, COUNT(*) AS n
FROM ef_retention_raw GROUP BY 1, 2, 3 HAVING COUNT(*) > 1;

-- check: C03_duplicate_gr | fail | More than one row per institution, year, measure and file version (graduation)
SELECT UNITID, report_year, measure, version, COUNT(*) AS n
FROM gr_raw GROUP BY 1, 2, 3, 4 HAVING COUNT(*) > 1;

-- check: C04_retention_missing | warn | Peer institution-year with no retention rate
SELECT unitid, institution, report_year, retention_flag
FROM v_outcomes WHERE ft_retention_pct IS NULL ORDER BY 2, 3;

-- check: C05_retention_not_reported | info | Retention value not flagged R (reported); IPEDS flag shows it was imputed or derived
SELECT unitid, institution, report_year, ft_retention_pct, retention_flag
FROM v_outcomes
WHERE ft_retention_pct IS NOT NULL AND retention_flag <> 'R' ORDER BY 2, 3;

-- check: C06_retention_out_of_range | fail | Retention rate outside 0-100
SELECT unitid, institution, report_year, ft_retention_pct
FROM v_outcomes WHERE ft_retention_pct < 0 OR ft_retention_pct > 100;

-- check: C07_retention_recompute | warn | Published retention rate differs from retained / adjusted cohort by more than 1 point
SELECT unitid, institution, report_year, ft_retention_pct, ft_retained_n, ft_cohort_adj,
       ROUND(100.0 * ft_retained_n / ft_cohort_adj, 1) AS recomputed
FROM (SELECT o.*, r.ft_retained_n FROM v_outcomes o
      JOIN v_retention r ON r.unitid = o.unitid AND r.report_year = o.report_year)
WHERE ft_cohort_adj > 0 AND ft_retention_pct IS NOT NULL
  AND ABS(ft_retention_pct - 100.0 * ft_retained_n / ft_cohort_adj) > 1
ORDER BY ABS(ft_retention_pct - 100.0 * ft_retained_n / ft_cohort_adj) DESC;

-- check: C08_graduation_logic | fail | Completers exceed cohort, or negative counts
SELECT unitid, institution, report_year, ba_cohort_n, ba_completers_n
FROM v_outcomes
WHERE ba_completers_n > ba_cohort_n OR ba_cohort_n < 0 OR ba_completers_n < 0;

-- check: C09_graduation_missing | warn | Peer institution-year with no bachelor's graduation cohort
SELECT unitid, institution, report_year
FROM v_outcomes WHERE ba_cohort_n IS NULL OR ba_cohort_n = 0 ORDER BY 2, 3;

-- check: C10_retention_yoy_jump | info | Retention moved more than 10 points versus the prior year for the same institution
WITH s AS (SELECT unitid, institution, report_year, ft_retention_pct AS pct,
                  LAG(ft_retention_pct) OVER (PARTITION BY unitid ORDER BY report_year) AS prev
           FROM v_outcomes)
SELECT unitid, institution, report_year, prev, pct, ROUND(pct - prev, 1) AS change
FROM s WHERE prev IS NOT NULL AND pct IS NOT NULL AND ABS(pct - prev) > 10
ORDER BY ABS(pct - prev) DESC;

-- check: C11_graduation_yoy_jump | info | 6-year graduation rate moved more than 10 points versus the prior year
WITH s AS (SELECT unitid, institution, report_year, grad_rate_6yr_pct AS pct,
                  LAG(grad_rate_6yr_pct) OVER (PARTITION BY unitid ORDER BY report_year) AS prev
           FROM v_outcomes)
SELECT unitid, institution, report_year, prev, pct, ROUND(pct - prev, 1) AS change
FROM s WHERE prev IS NOT NULL AND pct IS NOT NULL AND ABS(pct - prev) > 10
ORDER BY ABS(pct - prev) DESC;

-- check: C12_revised_changes_retention | info | Revised file changes the retention rate compared with the original file
SELECT o.UNITID AS unitid, d.institution, o.report_year,
       o.RET_PCF AS original_pct, r.RET_PCF AS revised_pct, r.RET_PCF - o.RET_PCF AS change
FROM ef_retention_raw o
JOIN ef_retention_raw r ON r.UNITID = o.UNITID AND r.report_year = o.report_year AND r.version = 'revised'
JOIN dim_institution d ON d.unitid = o.UNITID
JOIN peer_group p ON p.unitid = o.UNITID
WHERE o.version = 'original' AND o.RET_PCF IS NOT r.RET_PCF
ORDER BY ABS(r.RET_PCF - o.RET_PCF) DESC;

-- check: C13_revised_changes_graduation | info | Revised file changes the bachelor's cohort or completers compared with the original file
SELECT o.UNITID AS unitid, d.institution, o.report_year, o.measure,
       o.GRTOTLT AS original_n, r.GRTOTLT AS revised_n, r.GRTOTLT - o.GRTOTLT AS change
FROM gr_raw o
JOIN gr_raw r ON r.UNITID = o.UNITID AND r.report_year = o.report_year
             AND r.measure = o.measure AND r.version = 'revised'
JOIN dim_institution d ON d.unitid = o.UNITID
JOIN peer_group p ON p.unitid = o.UNITID
WHERE o.version = 'original' AND o.measure IN ('cohort_ba', 'completers_ba')
  AND o.GRTOTLT IS NOT r.GRTOTLT
ORDER BY ABS(r.GRTOTLT - o.GRTOTLT) DESC;

-- check: C14_small_cell | info | Full-time cohort under 30 students (rate is too volatile to publish at institution level)
SELECT unitid, institution, report_year, ft_cohort_adj, ft_retention_pct
FROM v_outcomes WHERE ft_cohort_adj > 0 AND ft_cohort_adj < 30 ORDER BY 2, 3;

-- check: C15_cross_file_cohort_mismatch | warn | Entering-class count (retention file) and graduation cohort (graduation file, 6 years later) differ by more than 10%
SELECT d.unitid, d.institution, g.report_year AS grad_report_year,
       r.ft_first_time_ug AS entering_class, g.all_cohort_n AS grad_cohort,
       ROUND(100.0 * (g.all_cohort_n - r.ft_first_time_ug) / r.ft_first_time_ug, 1) AS pct_diff
FROM v_grad g
JOIN v_retention r ON r.unitid = g.unitid AND r.report_year = g.report_year - 6
JOIN peer_group p ON p.unitid = g.unitid
JOIN dim_institution d ON d.unitid = g.unitid
WHERE r.ft_first_time_ug > 0 AND g.all_cohort_n > 0
  AND ABS(1.0 * (g.all_cohort_n - r.ft_first_time_ug) / r.ft_first_time_ug) > 0.10
ORDER BY ABS(1.0 * (g.all_cohort_n - r.ft_first_time_ug) / r.ft_first_time_ug) DESC;

-- check: C16_imputed_values_national | info | Imputed or carried-forward retention values anywhere in the national file (all institutions, not only peers)
SELECT retention_flag AS flag,
       CASE retention_flag WHEN 'N' THEN 'Imputed: nearest neighbor'
                           WHEN 'P' THEN 'Imputed: carry forward'
                           WHEN 'C' THEN 'Analyst corrected reported value'
                           ELSE 'Other' END AS meaning,
       COUNT(*) AS institution_years
FROM v_retention
WHERE retention_flag IS NOT NULL AND retention_flag NOT IN ('R', 'A')
GROUP BY 1, 2 ORDER BY 3 DESC;
