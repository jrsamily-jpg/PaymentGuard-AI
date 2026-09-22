-- Account Age Risk. Synthetic USD cohort; SQLite and PostgreSQL compatible.
WITH bands AS (SELECT *,CASE WHEN account_age<30 THEN '01 / under 30d' WHEN account_age<180 THEN '02 / 30–179d' ELSE '03 / 180d+' END AS age_band FROM transactions) SELECT age_band,COUNT(*) AS payments,AVG(CASE WHEN is_fraud THEN 1.0 ELSE 0.0 END) AS fraud_rate FROM bands GROUP BY age_band ORDER BY age_band;
