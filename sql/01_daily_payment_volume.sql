-- Daily Payment Volume. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT SUBSTR(timestamp,1,10) AS day, COUNT(*) AS transactions, SUM(amount) AS volume_usd FROM transactions GROUP BY SUBSTR(timestamp,1,10) ORDER BY day;
