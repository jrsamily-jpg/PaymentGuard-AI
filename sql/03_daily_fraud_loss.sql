-- Daily Fraud Loss. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT SUBSTR(timestamp,1,10) AS day, SUM(CASE WHEN is_fraud AND status IN ('settled','returned') THEN amount ELSE 0 END) AS loss_usd FROM transactions GROUP BY SUBSTR(timestamp,1,10) ORDER BY day;
