-- Transaction Velocity. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT transaction_id,customer_id,timestamp,tx_count_1h,LAG(timestamp) OVER (PARTITION BY customer_id ORDER BY timestamp,transaction_id) AS previous_payment FROM transactions ORDER BY tx_count_1h DESC LIMIT 100;
