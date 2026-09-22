-- False Positive Analysis. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT payment_rail,COUNT(*) AS legitimate_payments,SUM(CASE WHEN risk_score>=60 THEN 1 ELSE 0 END) AS false_alerts,AVG(CASE WHEN risk_score>=60 THEN 1.0 ELSE 0.0 END) AS false_positive_rate FROM transactions WHERE NOT is_fraud GROUP BY payment_rail ORDER BY false_positive_rate DESC;
