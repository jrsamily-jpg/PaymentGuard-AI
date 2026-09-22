-- Amount Band Risk. Synthetic USD cohort; SQLite and PostgreSQL compatible.
WITH bands AS (SELECT *,CASE WHEN amount<100 THEN '01 / under $100' WHEN amount<1000 THEN '02 / $100–999' ELSE '03 / $1,000+' END AS amount_band FROM transactions) SELECT amount_band,COUNT(*) AS payments,AVG(CASE WHEN is_fraud THEN 1.0 ELSE 0.0 END) AS fraud_rate FROM bands GROUP BY amount_band ORDER BY amount_band;
