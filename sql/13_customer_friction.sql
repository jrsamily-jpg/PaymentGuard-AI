-- Customer Friction. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT status,COUNT(DISTINCT customer_id) AS affected_customers,COUNT(*) AS payments,SUM(amount) AS legitimate_usd,COUNT(*)*8 AS assumed_friction_usd FROM transactions WHERE NOT is_fraud AND status IN ('blocked','review') GROUP BY status;
