"""Generate recruiter-facing artifacts from the actual dataset, never invented metrics."""

import json
from app.utils.config import ROOT, DATA
from app.services.data import load_data, model_results
from app.services.analytics import recommendations
from app.services.reporting import report_html
from app.risk_engine.simulation import simulate
from app.models.schemas import SimulationInput


def main():
    d = load_data()
    r = model_results()
    combined = r["evaluation"]["Combined"]
    rules = r["evaluation"]["Rules only"]
    scenario = simulate(
        d,
        SimulationInput(
            confirmed=True,
            decision_threshold=55,
            thresholds={"R12": 10, "R11": 5, "R01": 2500},
        ),
    )
    (DATA / "case_study_simulation.json").write_text(json.dumps(scenario, indent=2))
    delta = scenario["delta"]

    def write(name, content):
        (ROOT / name).write_text(content.strip() + "\n")

    table = "\n".join(
        f"| {name} | {m['precision']:.2%} | {m['recall']:.2%} | {m['f1']:.3f} | {m['roc_auc']:.4f} | {m['false_positive_rate']:.2%} | ${m['fraud_dollars_detected']:,.2f} |"
        for name, m in r["evaluation"].items()
    )
    recs = "\n\n".join(
        f"{i}. **{item['title']}.** {item['evidence']} {item['action']}"
        for i, item in enumerate(recommendations(d), 1)
    )
    write(
        "README.md",
        f"""
# PaymentGuard AI
### Intelligent Payment Fraud Detection & Risk Operations Platform

PaymentGuard AI helps a risk analyst explain suspicious payments, investigate linked accounts, and test controls against fraud loss **and** legitimate-customer friction. Built with **Python, FastAPI, SQLAlchemy, PostgreSQL/SQLite, Pandas, NumPy, scikit-learn, Streamlit, and Plotly**.

**Measured on the included synthetic build:**
- **{len(d):,} transactions** with **{int(d.is_fraud.sum()):,} fraud events ({d.is_fraud.mean():.2%})**, across six payment rails and 16 typologies.
- **{combined["roc_auc"]:.4f} combined-score ROC-AUC** on a chronological **{combined["transactions"]:,}-transaction holdout**; precision {combined["precision"]:.2%}, recall {combined["recall"]:.2%} at score 60.
- An exploratory full-cohort policy scenario detects **{delta["tp"]:+d} fraud events**, changes legitimate alerts by **{delta["fp"]:+d}**, and changes captured fraud exposure by **${delta["fraud_dollars_detected"]:,.2f}**. This is a synthetic counterfactual, not proven savings.

![Original PaymentGuard background artwork](app/dashboard/assets/orbital-art-v2.png)
*Original background artwork used in the working dashboard. The redesigned interface was visually inspected on desktop and at a 390px phone viewport on September 22. This image is the original artwork, not a dashboard screenshot.*

**Live demo:** placeholder — not publicly deployed. **Local dashboard:** [localhost:8501](http://localhost:8501). **API docs:** [localhost:8000/docs](http://localhost:8000/docs).

> All customers, transactions, IPs, and fraud events are synthetic. No real payment credentials or personal information are used. This is an independent portfolio application with no affiliation with Coinbase or any financial institution. It is not a production fraud-control system.

## Why payment risk matters
Blocking everything catches fraud but harms customers. Letting everything through removes friction but exposes the business to loss. This application makes the costs of both decisions visible and supports evidence-based human review.

## Demo in 60 seconds
1. Open **Executive Overview** to inspect volume, losses, blocked legitimate payments, and emerging signals.
2. In **Transaction Monitor**, filter a high-risk transaction, inspect evidence and score contributions, then open a case.
3. In **Investigation Workbench**, assign the case, add a note and a reasoned decision, then inspect the audit history and relationship map.
4. In **Rule Simulator**, confirm threshold changes; compare fraud capture and customer friction without modifying baseline rules.
5. Download the **Leadership Recommendations** report or inspect one of **16 SQL analyses**.

## Features
Nine workspaces: Executive Overview, Transaction Monitor, Investigation Workbench, Fraud Trends, Rule Performance, Rule Simulator, Model Performance, Leadership Recommendations, and SQL Explorer. Includes original background art, dark responsive surfaces, interactive charts, bounded pagination, search and filters, persistent investigations, optimistic concurrency, transaction evidence, three role concepts, audit history, and self-contained HTML reports. No data is sent to an external AI service.

## Architecture
```mermaid
flowchart LR
    G[Synthetic generation / CSV validation] --> F[Point-in-time feature engineering]
    F --> R[12 configurable fraud rules]
    F --> M[Isolation Forest]
    R --> S[Transparent scoring]
    M --> S
    S --> DB[(PostgreSQL / SQLite)]
    S --> A[Analytics artifacts]
    DB --> REPO[Case / audit repositories]
    A --> SERVICE[Metrics / simulation / recommendations]
    REPO --> API[FastAPI]
    SERVICE --> API
    REPO --> UI[Streamlit]
    SERVICE --> UI
    DB --> SQL[16 SQL analyses]
    SQL --> UI
```
Streamlit uses the same service and repository modules as FastAPI. A React frontend could consume the API without rewriting the scoring engine. Analytics CSV/JSON are immutable cohort artifacts; the DB is authoritative for case and audit state. No network call from the dashboard to FastAPI is required.

## Setup
Python **3.11+**; this local build was executed on Python 3.13.13. Run from this directory:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m scripts.ensure_data
python -m streamlit run app/dashboard/research.py
```
In a second activated terminal:
```bash
python -m uvicorn app.api.research:app --host 127.0.0.1 --port 8000
```
`ensure_data` is idempotent. `bootstrap` creates a fresh cohort and refuses to overwrite an existing DB. Startup fails explicitly if DB and analytics artifacts are incomplete. To rebuild, use a separate project checkout/data directory and DB; preserve investigations. The included `requirements-lock-py313.txt` records the exact local environment, while `requirements.txt` allows platform-compatible resolution.

### PostgreSQL and Docker
Set `POSTGRES_PASSWORD` to a URL-safe randomly generated secret in `.env` (for example, generate one with `python -c 'import secrets; print(secrets.token_hex(24))'`). Then:
```bash
docker compose up --build
```
Compose starts PostgreSQL, runs bootstrap once, then serves the API and dashboard on loopback ports 8000 and 8501. Named volumes persist DB and analytics artifacts. The initial bootstrap process fixes volume ownership and drops privileges; application services run as a non-root user. Docker is installed in the local environment, but its daemon was unavailable, so container execution was not locally verified. The CI PostgreSQL job is configured but has not been run on GitHub.

For an existing PostgreSQL server, set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB` in `.env`. SQLite is the automatic fallback only when this variable is absent; an unavailable configured PostgreSQL server must fail rather than silently create another database.

### Authentication and roles
`APP_MODE=demo` is intentionally unauthenticated and loopback-only. The sidebar role switch is a demonstration, not security. For authenticated mode set `APP_MODE=authenticated` and three unique random keys, each at least 24 characters: `ANALYST_API_KEY`, `MANAGER_API_KEY`, `AUDITOR_API_KEY`. API clients send `X-API-Key`; the dashboard asks for a key. Analyst and manager may change cases; only manager may simulate; auditor is read-only. These are role-scoped keys, not individual identities. See the threat model before considering deployment.

## Database schema
- `transactions`: indexed identity, time, USD amount, rail, geography, device, bank/recipient references, risk, status, synthetic truth and validated evidence payload.
- `rule_hits`: transaction foreign key and rule identifier; normalized for joins and analysis.
- `cases`: unique transaction reference, assignee, decision, reason, status and concurrency version.
- `audit_events`: actor, action, UTC timestamp, case foreign key and changes; no application edit/delete path.
Foreign keys are enforced in SQLite. Updates and audit events commit in one transaction; stale updates are rejected. Schema creation uses SQLAlchemy metadata; migrations are a documented deployment prerequisite. Float dollar arithmetic is rounded for reporting; a real ledger would require fixed-precision decimals.

## Risk and ML methodology
Each control includes its ID, description, weight, threshold, action and evidence. Baseline policy: **<30 low**, **30–<60 medium**, **60–<80 review**, **80–100 block**. Rule weights are capped at 55 combined points; behavior, device, authentication, payment-method, recipient, geography and anomaly components add explicit contributions, capped at 100. See [risk methodology](docs/risk_methodology.md).

An Isolation Forest with 120 trees fits the earliest 70% of events without truth labels. Training anomaly scores define a percentile mapping applied to the later 30%. No test labels enter training or percentile calibration. An anomaly percentile is not a fraud probability. The synthetic customer baseline and upstream counters are supplied simulator signals, not reconstructed production histories. Network features count only relationships already observed at event time.

### Actual holdout results
| System | Precision | Recall | F1 | ROC-AUC | False-positive rate | Fraud dollars flagged |
|---|---:|---:|---:|---:|---:|---:|
{table}

Rules-only uses weighted score ≥30; ML-only percentile ≥0.97; combined ≥60. These are different fixed operating points, not an apples-to-apples optimized comparison. The combined score ranks fraud better by ROC-AUC but has **lower recall than rules alone at the chosen threshold**. Precision is low enough that direct deployment would be inappropriate. These results support iteration, not production readiness claims. Full matrices, missed fraud, legitimate exposure, and threshold curves are in `data/processed/results.json` and the Model Performance page.

## SQL analysis
[Sixteen reviewed queries](sql/README.md) use CTEs, window functions, joins, conditional aggregates, cohort bands and time-based comparisons. SQL Explorer displays the exact checked-in query and executes it against the configured database. No free-form SQL or file-upload UI exists.
```bash
python -m scripts.verify_sql
```

## API examples
```bash
curl http://localhost:8000/health
curl 'http://localhost:8000/transactions?risk_level=Critical&limit=5'
curl http://localhost:8000/transactions/TX-0000001/explanation
curl -X POST http://localhost:8000/rules/simulate \\
  -H 'Content-Type: application/json' \\
  -d '{{"thresholds":{{"R12":10}},"decision_threshold":55,"confirmed":true}}'
```
Add `-H "X-API-Key: $MANAGER_API_KEY"` in authenticated mode. Swagger at `/docs` documents every endpoint. Unknown IDs return 404, invalid requests 422, duplicate/stale case changes 409, and unauthorized roles 403.

## What I Would Recommend to Payments Risk Leadership
{recs}

The exploratory case-study scenario sets R01 to $2,500, R11 to 5×, R12 to 10×, and the combined review threshold to 55. It changes recall by {delta["recall"] * 100:+.2f} percentage points and false alerts by {delta["fp"]:+d}, while changing legitimate flagged dollars by ${delta["legitimate_dollars_blocked"]:,.2f}. Do not infer “no customer harm” from fewer false-alert counts: exposed dollars can still rise. Confirm on untouched data, review capacity and recovery assumptions before a controlled pilot.

## Tests and verification
```bash
python -m pytest --cov=app/risk_engine --cov-report=term-missing
python -m scripts.verify_sql
python -m scripts.generate_portfolio
```
The core-engine coverage gate is 80%. Tests cover hand-calculated metrics, rule evidence and thresholds, score boundaries, missing/malformed inputs, time-safe features, reproducibility, nonmutating simulations, API search/validation, role restrictions, transactional case history, concurrency conflicts, every dashboard page, and the investigation workflow. The dashboard test uses a separate temporary database and cohort. See [verification record](docs/verification.md) for actual execution results and limitations.

## Security and privacy
Only synthetic identities and documentation-range IPs. Environment-held keys, bounded inputs, parameterized queries, no uploads, no unsafe model deserialization, and no external AI inference. Audit is append-only at application level; a DB administrator can still alter it. Authenticated mode needs TLS, individual SSO identities, least-privilege DB roles, audit export, rate limiting, migrations and security review before public use. [Threat model](docs/threat_model.md).

## Known limitations and future work
Synthetic fraud patterns share generator assumptions with engineered features and are not evidence of real-world model performance. Customer geography and account-age signals vary per event for synthetic diversity; aggregate velocity and deposit timing are simulated upstream context rather than a replay of underlying events. Holdout is chronological, not customer-disjoint. The rule simulator is retrospective and assumes captured fraudulent dollars are preventable. Labels are visible for evaluation. There is no streaming ingestion, model persistence/serving endpoint, real authentication-event feed, policy promotion, production SSO, or immutable external audit sink. Data fits in memory. Future work: consistent longitudinal customer profiles, event-replayed features, customer-separated validation, cost-aware calibration, human verification experiments, fair-treatment assessment, and monitoring for drift.

## Portfolio materials
[Data dictionary](docs/data_dictionary.md) · [Model card](docs/model_card.md) · [Case study](docs/case_study.md) · [Résumé bullets](docs/resume_bullets.md) · [Two-minute demo](docs/demo_script.md) · [Original art specification](docs/art_direction.md).
""",
    )
    write(
        "docs/case_study.md",
        f"""
# Case study: tune controls without hiding customer cost
All results describe seed-42 synthetic events, not a real fraud incident.

1. **Pattern appeared.** The generator introduces an account-takeover concentration in the final week. The emerging-pattern table compares the last seven observed days against the preceding seven.
2. **Dashboard surfaced the pattern.** Executive Overview shows the pattern count change, while Transaction Monitor exposes failed authentication, device novelty and reset evidence.
3. **SQL confirmed the descriptive signal.** Run `14_emerging_patterns.sql` for day-by-day labels and `16_authentication_fraud.sql` for the authentication cohort. Query 14 compares previous observed days; use the dashboard for exact seven-day windows. These are descriptive checks, not statistical significance tests.
4. **Controls were evaluated.** Rule Performance exposes false alerts, precision and capture for all 12 rules. Baseline combined holdout precision is {combined["precision"]:.2%}, recall {combined["recall"]:.2%}; rules alone recall is {rules["recall"]:.2%}.
5. **A policy weakness was identified.** A score-60 gate misses lower-scoring fraud while correlated amount and proxy signals create legitimate alerts. The lowest-precision ownership-mismatch rule also warrants separate validation. One rule change is not assumed to solve all typologies.
6. **Strategy tested.** In a full-cohort exploratory simulation, set R01=$2,500, R11=5×, R12=10× and the decision threshold=55. Keep other thresholds fixed. Confirm settings and run the simulator.
7. **Measured outcome.** True positives change by {delta["tp"]:+d}; false positives by {delta["fp"]:+d}; precision by {delta["precision"] * 100:+.3f} percentage points; recall by {delta["recall"] * 100:+.3f} points. Captured fraud dollars change by ${delta["fraud_dollars_detected"]:,.2f}; legitimate flagged dollars by ${delta["legitimate_dollars_blocked"]:,.2f}. At $8 per false alert, assumed friction cost changes by ${delta["friction_cost"]:,.2f} and net modeled impact by ${delta["net_financial_impact"]:,.2f}.
8. **Recommendation.** Further validate the scenario on an untouched cohort and test step-up verification. Fewer false-alert counts do not establish acceptable friction: legitimate dollar exposure increases in this scenario. The policy is deliberately not promoted automatically. The stated net impact excludes recoveries, costs of true-positive reviews, and customer lifetime value.

The scenario was selected after inspecting several full-cohort simulations. It is exploratory, not an unbiased holdout improvement. Reproduce the saved inputs and outputs in `data/processed/case_study_simulation.json` via `python -m scripts.generate_portfolio`.
""",
    )
    write(
        "docs/resume_bullets.md",
        f"""
# Résumé bullets — measured synthetic project results
- Built PaymentGuard AI with FastAPI, SQLAlchemy and Streamlit to analyze {len(d):,} synthetic payments across six rails and 16 fraud typologies; implemented 12 explainable controls, 16 SQL analyses and persistent analyst investigations.
- Developed an Isolation Forest and transparent combined risk score, achieving {combined["roc_auc"]:.3f} ROC-AUC on a chronological {combined["transactions"]:,}-payment synthetic holdout; evaluated precision, recall, fraud exposure and legitimate-customer friction across three systems.
- Implemented confirmed, nonmutating policy simulations; an exploratory scenario identified {delta["tp"]:+d} additional synthetic fraud events with {delta["fp"]:+d} legitimate alerts and ${delta["fraud_dollars_detected"]:,.0f} additional flagged fraud exposure, with explicit caveats about increased legitimate-dollar exposure.
- Added input validation, role checks, optimistic case concurrency, transactional audit history, and automated risk-engine and dashboard workflow tests with an 80% minimum core-coverage gate.

Do not describe simulated captured dollars as realized savings or claim production use. Add a test-count or achieved-coverage claim only from the latest verification record.
""",
    )
    write("docs/leadership-report.html", report_html(d))
    write(
        "docs/model_card.md",
        f"""
# Model card
**Purpose:** prioritize unusual synthetic payments for human review, not prove fraud. **Algorithm:** Isolation Forest, 120 estimators, max_samples=2048 (or training size if smaller), contamination=auto, random seed 42, single-worker deterministic fit.

**Data:** {len(d):,} synthetic USD-valued events, {int(d.is_fraud.sum()):,} fraud labels ({d.is_fraud.mean():.2%}). Dates: {d.timestamp.min()} to {d.timestamp.max()} UTC. 16 simulated typologies, six payment rails. No personal or financial credentials.

**Features:** {", ".join(r["model"]["features"])}. Fraud label, fraud category, transaction ID and status do not enter the model. Upstream synthetic baselines and timing are supplied values. Device relationships use cumulative unique pairs through event time.

**Split:** earliest {r["model"]["train_rows"]:,} transactions for fitting and percentile calibration; later {r["model"]["test_rows"]:,} for evaluation. Customers can occur in both splits. No holdout-label fitting. The later period includes a deliberately altered account-takeover mixture.

**Actual evaluation:**
| System | Precision | Recall | F1 | ROC-AUC | False-positive rate | Fraud dollars flagged |
|---|---:|---:|---:|---:|---:|---:|
{table}

**Operating points:** rules weighted sum ≥30; ML ≥97th training percentile; combined ≥60. ROC-AUC uses continuous scores. Full confusion matrices and threshold curve are stored in results.json. No optimized-model superiority claim: combined recall is lower than rules-only at the default gate.

**Explainability:** rule evidence and additive score components are exact policy contributions. Displayed anomaly drivers are input values, not causal attributions or calibrated probabilities.

**Limitations:** generator-induced dependencies, lack of real labels or longitudinally consistent customer profiles, retrospective evaluation, correlated signals, possible population shift, no empirical fairness assessment, and no production drift monitoring. Country is used for descriptive charts; no nationality-based block rule is used. Synthetic data cannot establish fairness or legal compliance. Human review and verification remain essential.

**Artifacts:** model metadata and metrics persist as JSON; no pickle model is loaded or served. Rebuild trains reproducibly. Retraining, model registry and real-time inference are future work.
""",
    )
    print(
        "Generated README, model card, case study, résumé bullets, leadership report and scenario results."
    )


if __name__ == "__main__":
    main()
