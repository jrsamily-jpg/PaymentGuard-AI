# Data dictionary

All fields are synthetic. Counts, dates and dollar values describe a simulation, not actual customers. No real payment credentials are stored. Raw imports require complete evidence; missing values are rejected rather than silently imputed.

| Field | Stored cohort type | Meaning |
|---|---|---|
| `transaction_id` | object | Unique artificial payment identifier (TX-0000001). |
| `customer_id` | object | Artificial customer identifier; customers repeat across events. |
| `timestamp` | object | Event time in UTC, fixed synthetic July–August 2026 window. |
| `amount` | float64 | Positive payment value in USD equivalents, capped at $100,000. |
| `customer_avg_amount` | float64 | Synthetic upstream customer baseline in USD, not a future-row average. |
| `currency` | object | USD for every event; crypto amounts are USD equivalents. |
| `payment_rail` | object | ACH, Debit card, Credit card, Wire, Real-time payment or Crypto. |
| `direction` | object | deposit or withdrawal. |
| `account_age` | int64 | Synthetic account-age context in days at payment time; not a consistent creation date across customer rows. |
| `customer_tenure` | int64 | Customer relationship tenure context in days, always at least account age. |
| `country` | object | Synthetic ISO alpha-2 country code used for descriptive analysis. |
| `region` | object | Artificial Region A/B/C label, not a real address. |
| `ip_address` | object | Artificial IP within documentation range 192.0.2.0/24; collisions are intentional and not proof of linkage. |
| `device_id` | object | Artificial device; most follow customer identity, with injected shared clusters or novel devices. |
| `bank_account_id` | object | Opaque synthetic bank relation identifier; no routing or account credentials. |
| `recipient_id` | object | Opaque synthetic recipient identifier. |
| `device_trusted` | bool | Boolean upstream trust context, false for some legitimate and fraudulent events. |
| `email_domain_age` | int64 | Synthetic domain age in days; no actual email address. |
| `tx_count_1h` | int64 | Simulated upstream previous-hour payment count, not reconstructed ledger count. |
| `tx_count_24h` | int64 | Simulated upstream previous-24-hour count, at least previous-hour count. |
| `amount_24h` | float64 | Simulated upstream previous-24-hour total, USD. |
| `failed_logins` | int64 | Simulated failed-authentication count prior to payment. |
| `password_reset` | bool | Boolean recent upstream password-reset signal; no exact reset timestamp is logged. |
| `mfa_enabled` | bool | Boolean upstream MFA state. |
| `vpn_proxy` | bool | Boolean simulated proxy/VPN signal; not real IP intelligence. |
| `distance_km` | float64 | Synthetic distance from usual location, kilometers. |
| `new_payment_method` | bool | Boolean new-method signal. |
| `recent_method_change` | bool | Boolean recent change signal; recorded as evidence, not directly weighted. |
| `ownership_match` | bool | Boolean bank ownership signal; mismatch does not prove fraud. |
| `prior_chargebacks` | int64 | Synthetic historical chargeback count. |
| `prior_fraud_reports` | int64 | Synthetic previous fraud reports; recorded but not directly weighted. |
| `recipient_age` | int64 | Synthetic recipient relationship age in days. |
| `recipient_risk` | object | Categorical upstream recipient risk: low, medium or high. |
| `minutes_since_deposit` | float64 | Simulated minutes since earlier deposit; not a reconstructed transaction link. |
| `hours_since_last_location` | float64 | Simulated hours since prior location context. |
| `is_fraud` | bool | Synthetic ground-truth Boolean. Evaluation only; excluded from model inputs. |
| `fraud_category` | object | One of 16 simulated typologies or Legitimate. Excluded from model inputs. |
| `crypto_asset` | object | BTC, ETH or USDC for Crypto; empty otherwise. |
| `amount_ratio` | float64 | Current amount / synthetic customer baseline, capped at 1,000. |
| `device_novelty` | int64 | 1 if untrusted device, otherwise 0. |
| `recipient_risk_numeric` | float64 | low=0, medium=0.5, high=1. |
| `rapid_cashout` | float64 | exp(−minutes_since_deposit/30) for withdrawals, 0 for deposits. |
| `travel_speed` | float64 | distance_km / max(hours_since_last_location,0.1), km/h. |
| `shared_accounts` | int64 | Distinct customer/device pairs observed on the device through this event; no future rows. |
| `customer_devices` | int64 | Distinct customer/device pairs observed for the customer through this event. |
| `anomaly_score` | float64 | Percentile of negative Isolation Forest score relative to training observations, 0–1. |
| `risk_score` | float64 | Rounded capped additive policy score, 0–100; not a probability. |
| `risk_level` | object | Low <30; Medium <60; High <80; Critical ≥80. |
| `rules_score` | int64 | Uncapped-by-component weighted rule sum, clipped at 100; rules-only evaluation uses ≥30. |
| `triggered_rules` | object | Comma-separated rule IDs. Normalized separately into rule_hits table. |
| `score_components` | object | JSON of exact additive component contributions before final clipping. |
| `status` | object | Synthetic original policy: settled, review, blocked, or returned. Case decisions do not rewrite this baseline. |
| `evaluation_split` | object | train for earliest 70%; test for remaining 30%. |

## Operational tables

Cases have integer IDs, unique transaction references, assignee, status, optional decision/reason, integer version and creation time. Audit entries have case reference, actor role, action, JSON changes and UTC timestamp. Notes are limited to 2,000 characters; assignees to 80. See SQLAlchemy models for exact column types and indices.
