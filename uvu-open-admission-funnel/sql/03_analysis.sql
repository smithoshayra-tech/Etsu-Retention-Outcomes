-- name: funnel_by_cycle
SELECT c.term,
       COUNT(*) AS inquiries,
       SUM(f.started) AS started,
       SUM(f.completed) AS completed,
       SUM(f.admitted) AS admitted,
       SUM(f.registered) AS registered,
       SUM(f.enrolled) AS enrolled,
       ROUND(1.0 * SUM(f.started) / COUNT(*), 4) AS start_rate,
       ROUND(1.0 * SUM(f.completed) / NULLIF(SUM(f.started), 0), 4) AS complete_rate,
       ROUND(1.0 * SUM(f.registered) / NULLIF(SUM(f.admitted), 0), 4) AS register_rate,
       ROUND(1.0 * SUM(f.enrolled) / NULLIF(SUM(f.registered), 0), 4) AS census_rate,
       ROUND(1.0 * SUM(f.enrolled) / COUNT(*), 4) AS inquiry_to_enrolled
FROM fact_funnel f
JOIN dim_cycle c USING (cycle_year)
GROUP BY c.term
ORDER BY c.term;

-- name: conversion_by_source
SELECT s.lead_source,
       COUNT(*) AS inquiries,
       ROUND(1.0 * SUM(f.started) / COUNT(*), 4) AS start_rate,
       ROUND(1.0 * SUM(f.registered) / NULLIF(SUM(f.admitted), 0), 4) AS register_rate,
       ROUND(1.0 * SUM(f.enrolled) / COUNT(*), 4) AS inquiry_to_enrolled,
       SUM(f.enrolled) AS enrolled
FROM fact_funnel f
JOIN dim_lead_source s USING (source_key)
GROUP BY s.lead_source
ORDER BY inquiry_to_enrolled DESC;

-- name: response_speed_by_cycle
SELECT c.term,
       ROUND(1.0 * SUM(CASE WHEN f.contact_lag_days >= 4 THEN 1 ELSE 0 END) / COUNT(*), 4) AS share_contacted_after_3_days,
       ROUND(1.0 * SUM(CASE WHEN f.contact_lag_days < 4 THEN f.started ELSE 0 END)
             / NULLIF(SUM(CASE WHEN f.contact_lag_days < 4 THEN 1 ELSE 0 END), 0), 4) AS start_rate_within_3_days,
       ROUND(1.0 * SUM(CASE WHEN f.contact_lag_days >= 4 THEN f.started ELSE 0 END)
             / NULLIF(SUM(CASE WHEN f.contact_lag_days >= 4 THEN 1 ELSE 0 END), 0), 4) AS start_rate_after_3_days
FROM fact_funnel f
JOIN dim_cycle c USING (cycle_year)
GROUP BY c.term
ORDER BY c.term;

-- name: aid_and_residency
SELECT r.residency,
       CASE WHEN f.fafsa_filed = 1 THEN 'Filed aid form' ELSE 'No aid form' END AS aid_status,
       SUM(f.admitted) AS admitted,
       ROUND(1.0 * SUM(f.registered) / NULLIF(SUM(f.admitted), 0), 4) AS register_rate
FROM fact_funnel f
JOIN dim_residency r USING (residency_key)
GROUP BY r.residency, f.fafsa_filed
ORDER BY r.residency, f.fafsa_filed DESC;

-- name: lost_before_registration
-- Where do admitted students stop? Admitted but not registered, by aid status.
SELECT CASE WHEN fafsa_filed = 1 THEN 'Filed aid form' ELSE 'No aid form' END AS aid_status,
       SUM(admitted) AS admitted,
       SUM(admitted) - SUM(registered) AS admitted_not_registered,
       ROUND(1.0 * (SUM(admitted) - SUM(registered)) / SUM(admitted), 4) AS melt_rate
FROM fact_funnel
GROUP BY fafsa_filed
ORDER BY fafsa_filed DESC;
