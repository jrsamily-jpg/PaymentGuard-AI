-- Fraud By Rail. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT payment_rail, COUNT(*) AS transactions, SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) AS fraud_count, 1.0*SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)/COUNT(*) AS fraud_rate FROM transactions GROUP BY payment_rail ORDER BY fraud_rate DESC;
