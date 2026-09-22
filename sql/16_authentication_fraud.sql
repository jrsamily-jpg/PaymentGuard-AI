-- Authentication Fraud. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT CASE WHEN failed_logins>=4 THEN '4+ failures' ELSE '0–3 failures' END AS authentication_band,COUNT(*) AS payments,AVG(CASE WHEN is_fraud THEN 1.0 ELSE 0.0 END) AS fraud_rate FROM transactions GROUP BY CASE WHEN failed_logins>=4 THEN '4+ failures' ELSE '0–3 failures' END;
