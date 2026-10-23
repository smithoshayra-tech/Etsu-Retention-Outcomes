-- 01_views.sql  |  dimension, peer-group rule, and analysis views
-- Run by src/01_build_db.py right after the raw tables are loaded.

DROP TABLE IF EXISTS dim_institution;
CREATE TABLE dim_institution AS
SELECT UNITID                       AS unitid,
       TRIM(INSTNM)                 AS institution,
       STABBR                       AS state,
       CONTROL                      AS control,        -- 1 = public
       ICLEVEL                      AS level,          -- 1 = four or more years
       C21BASIC                     AS carnegie_2021,
       CASE C21BASIC WHEN 15 THEN 'Doctoral: highest research'
                     WHEN 16 THEN 'Doctoral: higher research'
                     WHEN 17 THEN 'Doctoral/professional'
                     WHEN 18 THEN 'Master''s: larger'
                     WHEN 19 THEN 'Master''s: medium' END AS carnegie_label,
       CASE WHEN UNITID = 227368 THEN 1 ELSE 0 END AS is_home
FROM institution_raw;

-- Peer-group rule (documented in README):
--   public, four-year, currently active, offers undergraduate degrees,
--   Carnegie 2021 Basic class 15-19 (doctoral and master's institutions)
--   regional = TN, NC, VA, KY   |   georgia = GA
DROP TABLE IF EXISTS peer_group;
CREATE TABLE peer_group AS
SELECT i.UNITID AS unitid,
       'texas' AS peer_group
FROM institution_raw i
WHERE i.CONTROL = 1 AND i.ICLEVEL = 1 AND i.CYACTIVE = 1 AND i.UGOFFER = 1
  AND i.C21BASIC BETWEEN 15 AND 19
  AND i.STABBR = 'TX';

-- Latest version wins: use the revised file when one exists, else the original.
DROP VIEW IF EXISTS v_retention;
CREATE VIEW v_retention AS
SELECT e.UNITID AS unitid, e.report_year,
       e.report_year - 1 AS cohort_entry_year,       -- fall cohort of prior year
       e.version, e.RRFTCTA AS ft_cohort_adj, e.RET_NMF AS ft_retained_n,
       e.RET_PCF AS ft_retention_pct, e.XRET_PCF AS retention_flag,
       e.UGENTERN AS entering_ug, e.GRCOHRT AS ft_first_time_ug,
       e.STUFACR AS student_faculty_ratio
FROM ef_retention_raw e
WHERE e.version = 'revised'
   OR NOT EXISTS (SELECT 1 FROM ef_retention_raw r
                  WHERE r.UNITID = e.UNITID AND r.report_year = e.report_year
                    AND r.version = 'revised');

DROP VIEW IF EXISTS v_grad;
CREATE VIEW v_grad AS
WITH pref AS (
  SELECT g.* FROM gr_raw g
  WHERE g.version = 'revised'
     OR NOT EXISTS (SELECT 1 FROM gr_raw r
                    WHERE r.UNITID = g.UNITID AND r.report_year = g.report_year
                      AND r.measure = g.measure AND r.version = 'revised')
)
SELECT UNITID AS unitid, report_year,
       report_year - 6 AS cohort_entry_year,        -- validated in 02_quality_checks
       MAX(CASE WHEN measure='cohort_ba'     THEN GRTOTLT END) AS ba_cohort_n,
       MAX(CASE WHEN measure='completers_ba' THEN GRTOTLT END) AS ba_completers_n,
       MAX(CASE WHEN measure='cohort_4yr_all' THEN GRTOTLT END) AS all_cohort_n,
       MAX(CASE WHEN measure='cohort_ba'     THEN XGRTOTLT END) AS cohort_flag,
       MAX(CASE WHEN measure='completers_ba' THEN XGRTOTLT END) AS completers_flag,
       MAX(version) AS version
FROM pref
GROUP BY UNITID, report_year;

-- Retention and graduation, one row per institution and report year.
-- Retention (report year y) and 6-year graduation (report year y) describe
-- different cohorts; both are kept with their own cohort-entry year.
DROP VIEW IF EXISTS v_outcomes;
CREATE VIEW v_outcomes AS
SELECT d.unitid, d.institution, d.state, d.carnegie_2021, d.carnegie_label,
       d.is_home, p.peer_group,
       r.report_year, r.cohort_entry_year AS retention_cohort_year,
       r.ft_cohort_adj, r.ft_retention_pct, r.retention_flag,
       r.entering_ug, r.student_faculty_ratio,
       g.cohort_entry_year AS grad_cohort_year, g.ba_cohort_n, g.ba_completers_n,
       CASE WHEN g.ba_cohort_n > 0
            THEN ROUND(100.0 * g.ba_completers_n / g.ba_cohort_n, 1) END AS grad_rate_6yr_pct
FROM dim_institution d
JOIN peer_group p      ON p.unitid = d.unitid
JOIN v_retention r     ON r.unitid = d.unitid
LEFT JOIN v_grad g     ON g.unitid = d.unitid AND g.report_year = r.report_year;
