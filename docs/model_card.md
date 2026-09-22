# Model card
**Purpose:** prioritize unusual synthetic payments for human review, not prove fraud. **Algorithm:** Isolation Forest, 120 estimators, max_samples=2048 (or training size if smaller), contamination=auto, random seed 42, single-worker deterministic fit.

**Data:** 100,000 synthetic USD-valued events, 2,642 fraud labels (2.64%). Dates: 2026-07-01 00:00:10 to 2026-08-29 23:56:28 UTC. 16 simulated typologies, six payment rails. No personal or financial credentials.

**Features:** amount_ratio, tx_count_1h, distance_km, account_age, device_novelty, failed_logins, recipient_risk_numeric, prior_chargebacks, rapid_cashout, travel_speed, shared_accounts, customer_devices. Fraud label, fraud category, transaction ID and status do not enter the model. Upstream synthetic baselines and timing are supplied values. Device relationships use cumulative unique pairs through event time.

**Split:** earliest 70,000 transactions for fitting and percentile calibration; later 30,000 for evaluation. Customers can occur in both splits. No holdout-label fitting. The later period includes a deliberately altered account-takeover mixture.

**Actual evaluation:**
| System | Precision | Recall | F1 | ROC-AUC | False-positive rate | Fraud dollars flagged |
|---|---:|---:|---:|---:|---:|---:|
| Rules only | 38.76% | 77.93% | 0.518 | 0.9316 | 3.13% | $639,076.61 |
| ML only | 24.29% | 32.30% | 0.277 | 0.9430 | 2.56% | $322,331.40 |
| Combined | 35.28% | 53.57% | 0.425 | 0.9697 | 2.50% | $588,596.56 |

**Operating points:** rules weighted sum ≥30; ML ≥97th training percentile; combined ≥60. ROC-AUC uses continuous scores. Full confusion matrices and threshold curve are stored in results.json. No optimized-model superiority claim: combined recall is lower than rules-only at the default gate.

**Explainability:** rule evidence and additive score components are exact policy contributions. Displayed anomaly drivers are input values, not causal attributions or calibrated probabilities.

**Limitations:** generator-induced dependencies, lack of real labels or longitudinally consistent customer profiles, retrospective evaluation, correlated signals, possible population shift, no empirical fairness assessment, and no production drift monitoring. Country is used for descriptive charts; no nationality-based block rule is used. Synthetic data cannot establish fairness or legal compliance. Human review and verification remain essential.

**Artifacts:** model metadata and metrics persist as JSON; no pickle model is loaded or served. Rebuild trains reproducibly. Retraining, model registry and real-time inference are future work.
