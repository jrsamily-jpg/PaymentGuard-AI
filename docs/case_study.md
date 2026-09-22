# Case study: tune controls without hiding customer cost
All results describe seed-42 synthetic events, not a real fraud incident.

1. **Pattern appeared.** The generator introduces an account-takeover concentration in the final week. The emerging-pattern table compares the last seven observed days against the preceding seven.
2. **Dashboard surfaced the pattern.** Executive Overview shows the pattern count change, while Transaction Monitor exposes failed authentication, device novelty and reset evidence.
3. **SQL confirmed the descriptive signal.** Run `14_emerging_patterns.sql` for day-by-day labels and `16_authentication_fraud.sql` for the authentication cohort. Query 14 compares previous observed days; use the dashboard for exact seven-day windows. These are descriptive checks, not statistical significance tests.
4. **Controls were evaluated.** Rule Performance exposes false alerts, precision and capture for all 12 rules. Baseline combined holdout precision is 35.28%, recall 53.57%; rules alone recall is 77.93%.
5. **A policy weakness was identified.** A score-60 gate misses lower-scoring fraud while correlated amount and proxy signals create legitimate alerts. The lowest-precision ownership-mismatch rule also warrants separate validation. One rule change is not assumed to solve all typologies.
6. **Strategy tested.** In a full-cohort exploratory simulation, set R01=$2,500, R11=5×, R12=10× and the decision threshold=55. Keep other thresholds fixed. Confirm settings and run the simulator.
7. **Measured outcome.** True positives change by +7; false positives by -1; precision by +0.128 percentage points; recall by +0.265 points. Captured fraud dollars change by $44,405.04; legitimate flagged dollars by $46,963.08. At $8 per false alert, assumed friction cost changes by $-8.00 and net modeled impact by $44,413.04.
8. **Recommendation.** Further validate the scenario on an untouched cohort and test step-up verification. Fewer false-alert counts do not establish acceptable friction: legitimate dollar exposure increases in this scenario. The policy is deliberately not promoted automatically. The stated net impact excludes recoveries, costs of true-positive reviews, and customer lifetime value.

The scenario was selected after inspecting several full-cohort simulations. It is exploratory, not an unbiased holdout improvement. Reproduce the saved inputs and outputs in `data/processed/case_study_simulation.json` via `python -m scripts.generate_portfolio`.
