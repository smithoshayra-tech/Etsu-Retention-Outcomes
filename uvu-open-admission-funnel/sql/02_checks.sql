-- Validation checks for the simulated funnel and the real IPEDS limit.
-- Each row: check id, what it protects, severity, number of violations.
-- A passing check returns 0. Check S6 and S9 compare against the two real
-- IPEDS anchors (about 4,752 first-time students, 74.8% Utah residents).
SELECT 'S1' AS check_id, 'lead_id is unique' AS what, 'error' AS severity,
       COUNT(*) - COUNT(DISTINCT lead_id) AS violations
FROM fact_funnel
UNION ALL
SELECT 'S2', 'stages never skip: completed needs started, admitted needs completed, registered needs admitted, enrolled needs registered', 'error',
       SUM(CASE WHEN (completed = 1 AND started = 0)
                  OR (admitted = 1 AND completed = 0)
                  OR (registered = 1 AND admitted = 0)
                  OR (enrolled = 1 AND registered = 0) THEN 1 ELSE 0 END)
FROM fact_funnel
UNION ALL
SELECT 'S3', 'stage and aid flags are 0 or 1', 'error',
       SUM(CASE WHEN started NOT IN (0,1) OR completed NOT IN (0,1) OR admitted NOT IN (0,1)
                  OR registered NOT IN (0,1) OR enrolled NOT IN (0,1) OR fafsa_filed NOT IN (0,1)
                THEN 1 ELSE 0 END)
FROM fact_funnel
UNION ALL
SELECT 'S4', 'every foreign key matches a dimension row', 'error',
       (SELECT COUNT(*) FROM fact_funnel f LEFT JOIN dim_lead_source d USING (source_key) WHERE d.source_key IS NULL)
     + (SELECT COUNT(*) FROM fact_funnel f LEFT JOIN dim_residency d USING (residency_key) WHERE d.residency_key IS NULL)
     + (SELECT COUNT(*) FROM fact_funnel f LEFT JOIN dim_cycle d USING (cycle_year) WHERE d.cycle_year IS NULL)
UNION ALL
SELECT 'S5', 'registration date is after completion date, and both are after the inquiry date', 'error',
       SUM(CASE WHEN completed_date IS NOT NULL AND completed_date < inquiry_date THEN 1
                WHEN registered_date IS NOT NULL AND registered_date <= completed_date THEN 1
                ELSE 0 END)
FROM fact_funnel
UNION ALL
SELECT 'S6', 'enrolled count within 5% of the real anchor of 4,752 in 2021 to 2023 (calibration check)', 'warning',
       COUNT(*)
FROM (SELECT cycle_year, SUM(enrolled) AS n FROM fact_funnel WHERE cycle_year <= 2023 GROUP BY cycle_year)
WHERE ABS(n - 4752) > 0.05 * 4752
UNION ALL
SELECT 'S7', 'no nulls in key columns', 'error',
       SUM(CASE WHEN lead_id IS NULL OR cycle_year IS NULL OR source_key IS NULL OR residency_key IS NULL
                  OR inquiry_date IS NULL OR contact_lag_days IS NULL OR fafsa_filed IS NULL THEN 1 ELSE 0 END)
FROM fact_funnel
UNION ALL
SELECT 'S8', 'stage dates exist exactly when the stage flag is set', 'error',
       SUM(CASE WHEN (completed = 1 AND completed_date IS NULL) OR (completed = 0 AND completed_date IS NOT NULL)
                  OR (registered = 1 AND registered_date IS NULL) OR (registered = 0 AND registered_date IS NOT NULL)
                THEN 1 ELSE 0 END)
FROM fact_funnel
UNION ALL
SELECT 'S9', 'Utah resident share within 2 points of the real 74.8% in every cycle', 'warning',
       COUNT(*)
FROM (SELECT cycle_year, 1.0 * SUM(CASE WHEN residency_key = 1 THEN 1 ELSE 0 END) / COUNT(*) AS share
      FROM fact_funnel GROUP BY cycle_year)
WHERE ABS(share - 3555.0 / 4752) > 0.02
UNION ALL
SELECT 'S10', 'contact lag is never negative', 'error',
       SUM(CASE WHEN contact_lag_days < 0 THEN 1 ELSE 0 END)
FROM fact_funnel
UNION ALL
SELECT 'S11', 'inquiry date falls inside its cycle window, September of the prior year to August of the cycle year', 'error',
       SUM(CASE WHEN inquiry_date < (cycle_year - 1) || '-09-01' OR inquiry_date > cycle_year || '-08-31' THEN 1 ELSE 0 END)
FROM fact_funnel
UNION ALL
SELECT 'S12', 'REAL DATA LIMIT: rows UVU has in IPEDS Admissions, 2014 to 2023 (0 means it does not report; informational)', 'info',
       (SELECT COUNT(*) FROM adm_raw WHERE UNITID = 230737);
