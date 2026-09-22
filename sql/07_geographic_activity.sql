-- Geographic Activity. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT customer_id,COUNT(DISTINCT country) AS countries,MAX(distance_km) AS max_distance_km,AVG(risk_score) AS average_risk FROM transactions GROUP BY customer_id HAVING MAX(distance_km)>1000 ORDER BY average_risk DESC LIMIT 100;
