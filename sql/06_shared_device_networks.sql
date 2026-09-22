-- Shared Device Networks. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT device_id,COUNT(DISTINCT customer_id) AS accounts,COUNT(*) AS payments,SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) AS fraud_events FROM transactions GROUP BY device_id HAVING COUNT(DISTINCT customer_id)>=3 ORDER BY accounts DESC;
