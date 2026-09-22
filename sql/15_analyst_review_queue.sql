-- Analyst Review Queue. Synthetic USD cohort; SQLite and PostgreSQL compatible.
SELECT c.id AS case_id,c.assignee,c.status AS case_status,t.transaction_id,t.customer_id,t.amount,t.risk_score FROM transactions t LEFT JOIN cases c ON t.transaction_id=c.transaction_id WHERE t.status='review' AND (c.id IS NULL OR c.status<>'closed') ORDER BY t.risk_score DESC,t.timestamp LIMIT 100;
