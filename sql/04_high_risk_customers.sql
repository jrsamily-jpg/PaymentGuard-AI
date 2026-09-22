-- High Risk Customers. Synthetic USD cohort; SQLite and PostgreSQL compatible.
WITH customer_risk AS (SELECT customer_id, COUNT(*) AS payments, MAX(risk_score) AS max_risk, SUM(CASE WHEN risk_score>=60 THEN amount ELSE 0 END) AS flagged_usd FROM transactions GROUP BY customer_id) SELECT *, DENSE_RANK() OVER (ORDER BY flagged_usd DESC) AS risk_rank FROM customer_risk ORDER BY risk_rank LIMIT 50;
