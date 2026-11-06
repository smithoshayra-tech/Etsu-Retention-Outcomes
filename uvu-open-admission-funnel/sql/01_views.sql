-- Dimension: one row per institution in the comparison set.
-- Peer rule: Utah public (CONTROL = 1), four-year-or-above (ICLEVEL = 1),
-- Carnegie 2021 basic class 15-22 (doctoral and master's institutions and
-- baccalaureate colleges with a bachelor's focus), active in 2023.
-- Snow College (class 14, associate's focus) is left out: it is not
-- primarily a bachelor's-granting institution.
DROP TABLE IF EXISTS dim_institution;
CREATE TABLE dim_institution AS
SELECT UNITID,
       TRIM(INSTNM) AS institution,
       CITY,
       C21BASIC,
       CASE WHEN UNITID = 230737 THEN 1 ELSE 0 END AS is_home
FROM institution_raw
WHERE STABBR = 'UT'
  AND CONTROL = 1
  AND ICLEVEL = 1
  AND CYACTIVE = 1
  AND C21BASIC BETWEEN 15 AND 22;

-- Admissions facts at institution x report-year grain.
-- Revised file preferred over the original where one exists.
DROP VIEW IF EXISTS v_adm;
CREATE VIEW v_adm AS
SELECT a.UNITID, a.report_year, a.version,
       a.APPLCN AS applied, a.ADMSSN AS admitted, a.ENRLT AS enrolled,
       a.ENRLFT AS enrolled_ft, a.ENRLPT AS enrolled_pt,
       a.ENRLM AS enrolled_m, a.ENRLW AS enrolled_w,
       a.XAPPLCN, a.XADMSSN, a.XENRLT,
       a.ADMCON1,
       ROUND(1.0 * a.ADMSSN / a.APPLCN, 4) AS admit_rate,
       ROUND(1.0 * a.ENRLT / a.ADMSSN, 4) AS yield_rate,
       ROUND(1.0 * a.ENRLT / a.APPLCN, 4) AS app_to_enroll
FROM adm_raw a
WHERE a.UNITID IN (SELECT UNITID FROM dim_institution)
  AND (a.version = 'revised'
       OR (a.version = 'original'
           AND NOT EXISTS (SELECT 1 FROM adm_raw b
                           WHERE b.UNITID = a.UNITID
                             AND b.report_year = a.report_year
                             AND b.version = 'revised')));

-- UVU against the median of the other institutions, by year.
DROP VIEW IF EXISTS v_peer_median_yield;
CREATE VIEW v_peer_median_yield AS
WITH ranked AS (
  SELECT report_year, yield_rate,
         ROW_NUMBER() OVER (PARTITION BY report_year ORDER BY yield_rate) AS rn,
         COUNT(*)    OVER (PARTITION BY report_year) AS n
  FROM v_adm
  WHERE UNITID <> 230737 AND yield_rate IS NOT NULL
)
SELECT report_year,
       ROUND(AVG(yield_rate), 4) AS peer_median_yield,
       MAX(n) AS peer_count
FROM ranked
WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
GROUP BY report_year;

DROP VIEW IF EXISTS v_uvu_vs_peers;
CREATE VIEW v_uvu_vs_peers AS
SELECT u.report_year,
       u.applied, u.admitted, u.enrolled,
       u.admit_rate, u.yield_rate AS uvu_yield,
       p.peer_median_yield, p.peer_count,
       ROUND(100.0 * (u.yield_rate - p.peer_median_yield), 2) AS gap_points
FROM v_adm u
JOIN v_peer_median_yield p USING (report_year)
WHERE u.UNITID = 230737;
