# PaymentGuard

Payment-risk operations with individual accounts, private workspaces, and no preloaded activity. A new account starts with **$0 payment volume, zero payments, zero cases, and no model-performance claims**. Returning users retain only their own records.

## Run locally

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app/dashboard/main.py
# In a second terminal, for API access:
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8501, choose **Create account** on the welcome screen. No shared credentials or role selector are supplied. The operational database initializes its schema automatically; it does not generate payments. Local records persist in `data/workspaces/workspaces.db`. API documentation is available at http://127.0.0.1:8000/docs.

## Working features

- Salted scrypt passwords, hashed bearer sessions, 12-hour expiry, logout revocation, and per-username login throttling.
- Every payment, case, audit entry, query, report, and simulation is scoped to the authenticated account. Client-supplied owner identifiers are rejected.
- Validated CSV import or individual payment entry. Imports commit atomically and reject duplicate references within the account. Amounts are stored as integer cents; USD is the supported currency.
- Twelve explainable rules evaluate only supplied evidence. Missing context stays unknown. Scores are rule points, not fraud probabilities, and no synthetic model score is added.
- Investigations with decisions, reasons, notes, audit history, and optimistic concurrency checks.
- Payment trends, observed rule performance, retrospective policy simulation, and downloadable reports based on the user's events.
- A designed empty state on every page, plus original locally hosted cobalt crypto-security and observatory artwork. No remote font or image dependency.

## Data and API

The UI provides an empty CSV template and previews validated rows before import. Required columns: `external_id`, `customer_ref`, `occurred_at` (ISO 8601 with timezone), `amount`, `direction`. Optional columns: `currency`, `status`, `country`, `confirmed_fraud`, `evidence` (a JSON object). Limits: 5,000 rows and 2 MB per CSV; API request bodies are capped at 5 MB.

`POST /auth/register` and `POST /auth/login` accept username and password. Send the resulting access token as `Authorization: Bearer <token>`. `POST /transactions/import` accepts `{ "payments": [...] }`. `GET /transactions` supports `limit` (1–500) and `offset`. Other routes cover analytics, cases, audit history, rules, simulations, and reports. Passwords require 12–128 characters; use a unique password and keep tokens private. Signing out does not erase saved records.

Payment volume means the sum of submitted event amounts. Blocked fraud is source-reported exposure, not verified savings. Unknown fraud outcomes are excluded from legitimate-event metrics. The application does not initiate, block, settle, or refund funds. It does not independently verify user-submitted statuses or outcomes. Import updates to existing references are rejected rather than silently overwriting records.

## Deployment status

This is a working local application, not a certified or security-reviewed financial production deployment. No exchange, bank, or payment processor is connected. No affiliation with or endorsement by Coinbase is claimed. No machine-learning model has been evaluated on an operational user's data.

Before internet-facing deployment, implement managed identity/SSO and MFA, recovery, perimeter rate limiting, TLS, production secrets, database least privilege, schema migrations, encrypted backups, restore exercises, monitoring, and independent security review. Workspaces currently belong to individual accounts; there is no organization/team permission model. SQLite is intended for local use. Dashboard analytics currently load the owner's event history in memory; large-volume operations require incremental aggregation and paging throughout.

Docker Compose uses PostgreSQL and starts the operational API before the dashboard. Set a strong URL-safe `POSTGRES_PASSWORD` in `.env`, then run `docker compose up --build`. Both services bind only to loopback by default. Set `WORKSPACE_DATABASE_URL` for an external operational database. `DATABASE_URL` and `APP_MODE` belong to the separate historical research code and do not control operational storage.

## Verification

```sh
python -m pytest --cov=app/risk_engine --cov-report=term-missing
```

Operational tests use isolated temporary databases, including two-user access checks, empty metrics, atomic imports, session expiry, logout, missing-evidence behavior, cases, and a full dashboard account lifecycle. See [verification notes](docs/verification.md).

## Research archive

The former synthetic benchmark remains available explicitly as `app/dashboard/research.py` and `app/api/research.py`, with separate research storage and generation scripts. It is not used by the default dashboard, API, or Docker startup. See [historical research documentation](docs/research_reference.md). Do not treat those benchmark results as customer activity or operational model performance.

## Repository

Source: https://github.com/jrsamily-jpg/PaymentGuard-AI

The intro and workspace use separate full-screen artwork, dark reading surfaces, and accessible button feedback. Local accounts, session tokens, operational payments, and environment credentials are excluded from version control. GitHub hosts the source code; this does not publish a running payment service.
