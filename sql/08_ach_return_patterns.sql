-- Ach Return Patterns. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT SUBSTR(timestamp,1,10) AS day,COUNT(*) AS ach_payments,SUM(CASE WHEN status='returned' THEN 1 ELSE 0 END) AS returns,SUM(CASE WHEN status='returned' THEN amount ELSE 0 END) AS returned_usd FROM transactions WHERE payment_rail='ACH' GROUP BY SUBSTR(timestamp,1,10) ORDER BY day;
