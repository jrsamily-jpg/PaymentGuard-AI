# Risk methodology

The score is an interpretable demonstration policy, not a fraud probability. It is computed before policy status is assigned; truth labels never enter scoring. The scoring path is shared by initial build and simulator.

| Component | Calculation | Maximum points |
|---|---|---:|
| Rules | Sum weights of all fired rules, capped | 55 |
| Behavioral deviation | max(amount/customer baseline − 2, 0) × 1.5 | 10 |
| Device | Untrusted device: 4; four or more observed customer devices: 3 | 7 |
| Authentication | No MFA: 3; password reset: 2 | 5 |
| Payment method | New method: 2; ownership mismatch: 3 | 5 |
| Recipient | low=0, medium=0.5, high=1 multiplied by 4 | 4 |
| Geography | Implied travel speed above 900 km/h | 4 |
| Anomaly | clip((training-percentile − 0.70)/0.30, 0, 1) × 20 | 20 |

Sum contributions, cap at 100 and round to one decimal. 0–<30 Low, 30–<60 Medium, 60–<80 High, 80–100 Critical. Baseline synthetic policy settles scores below 60, reviews scores 60–<80, and blocks scores ≥80. Fraud-labeled settled ACH events are marked returned.

The rules component is capped independently of the sum. Individual rule weights displayed in explanations therefore do not necessarily sum to the final score. Some signals intentionally overlap between rules and components; the cap mitigates but does not calibrate this dependence. No score has been validated for real production use.

## Control catalog
R01 new-account withdrawal ($1,000, account under 30 days, weight 28); R02 prior-hour velocity (8, weight 30); R03 cash-out after deposit (30 minutes, withdrawal over $500, weight 32); R04 failed logins (4, weight 25); R05 reset on untrusted device (≥1 observed customer device, weight 30); R06 impossible travel (900 km/h and >500 km, weight 30); R07 shared device (3 accounts, weight 32); R08 ownership mismatch (amount ≥$0, weight 28); R09 prior chargebacks (2, weight 25); R10 high-risk recipient (age ≤30 days, weight 26); R11 proxy and amount deviation (>3×, weight 24); R12 amount outlier (≥6×, weight 28).

Every rule has bounds and a threshold unit in the catalog. Higher thresholds do not always tighten the rule: increasing a maximum timing window or recipient age broadens detection. API and dashboard validate bounds and reject unknown rule IDs.

## Feature timing
Rows are ordered by timestamp and transaction ID. Distinct device/customer pairs contribute only when first observed, then accumulate through each event. Amount baseline, counts, geographic offset, reset flags and deposit timing are synthetic upstream context. They must not be mistaken for features independently reconstructed from the generated transaction ledger. No future relationship observations enter event scoring.

## Accounting and denominators
- Actual policy false-positive rate = legitimate *blocked* count / all legitimate count.
- Model or simulation false-positive rate = legitimate *flagged* count / all legitimate count at the stated threshold.
- Precision = true-positive alerts / all alerts; recall = true-positive alerts / all fraud labels.
- Confirmed fraud loss = fraud-labeled settled or returned amount.
- Potential prevented exposure = fraud-labeled blocked amount; review is excluded.
- Fraud dollars flagged = all fraud-labeled amount at/above the selected decision threshold; not realized savings.
- Counterfactual legitimate dollars blocked = legitimate amount flagged, assuming a hypothetical block; baseline review is not an actual block.
- Review backlog = review-status payments without a closed case, including unassigned payments.
- Default estimated friction = $8 × false alerts; configurable in simulation. Net impact = delta captured fraud exposure − delta assumed friction. This excludes recoveries, manual-review costs on true positives, customer lifetime value and downstream consequences.

All amounts are synthetic USD equivalents, including crypto transfers; there is no exchange-rate lookup. Money uses float calculations with display rounding; this is analytics, not a payment ledger. Rule captures overlap and must not be summed.

## Simulation
The user explicitly confirms the proposed settings before evaluation. The engine rescans the full fixed cohort with proposed rule thresholds and the same already-fitted anomaly scores. Current baseline is score ≥60. No rules, transaction statuses, cases, model, or DB records are changed. Results preserve the last confirmed settings so unsaved form edits cannot masquerade as a new run. There is no production-policy promotion action.
