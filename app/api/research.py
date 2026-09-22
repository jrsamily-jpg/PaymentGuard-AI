"""FastAPI adapters; no scoring or persistence logic is embedded in routes."""

from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from app.database.session import Base, engine, SessionLocal
from app.database.models import Transaction, RuleHit, Case
from app.models.schemas import CaseCreate, CaseUpdate, SimulationInput
from app.repositories.cases import (
    create_case,
    update_case,
    list_cases,
    audit_history,
    review_backlog,
)
from app.services.data import load_data, model_results
from app.services.analytics import summary, trends, rule_performance, recommendations
from app.services.reporting import report_html
from app.risk_engine.rules import catalog, explain
from app.risk_engine.simulation import simulate
from app.api.security import identity, authorize, validate_security


@asynccontextmanager
async def lifespan(app):
    validate_security()
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="PaymentGuard AI",
    version="1.0.0",
    description="Synthetic payment-risk operations. Local demo only unless authenticated mode is configured.",
    lifespan=lifespan,
)


def db():
    with SessionLocal() as s:
        yield s


def dataset():
    try:
        return load_data()
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


def handle(call):
    try:
        return call()
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/health")
def health():
    return {"status": "ok", "synthetic": True}


@app.get("/transactions")
def transactions(
    search: str = Query("", max_length=100),
    rail: str | None = None,
    risk_level: str | None = None,
    country: str | None = None,
    status: str | None = None,
    fraud_category: str | None = None,
    rule_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    min_amount: float = Query(0, ge=0, allow_inf_nan=False),
    max_amount: float = Query(100000, ge=0, allow_inf_nan=False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    s=Depends(db),
    user=Depends(identity),
):
    if start and end and start > end:
        raise HTTPException(422, "Start date exceeds end date")
    if min_amount > max_amount:
        raise HTTPException(422, "Minimum exceeds maximum")
    q = select(Transaction).where(
        Transaction.amount >= min_amount, Transaction.amount <= max_amount
    )
    if search:
        q = q.where(
            Transaction.transaction_id.contains(search, autoescape=True)
            | Transaction.customer_id.contains(search, autoescape=True)
        )
    for field, val in [
        ("payment_rail", rail),
        ("risk_level", risk_level),
        ("country", country),
        ("status", status),
        ("fraud_category", fraud_category),
    ]:
        if val:
            q = q.where(getattr(Transaction, field) == val)
    if rule_id:
        q = q.where(
            Transaction.transaction_id.in_(
                select(RuleHit.transaction_id).where(RuleHit.rule_id == rule_id)
            )
        )
    if start:
        q = q.where(Transaction.timestamp >= start.isoformat())
    if end:
        q = q.where(Transaction.timestamp <= end.isoformat() + " 23:59:59")
    total = s.scalar(select(func.count()).select_from(q.subquery()))
    return {
        "total": total,
        "items": [
            t.payload
            for t in s.scalars(
                q.order_by(Transaction.risk_score.desc(), Transaction.transaction_id)
                .offset(offset)
                .limit(limit)
            )
        ],
    }


def get_transaction(tx, s):
    t = s.get(Transaction, tx)
    if t is None:
        raise HTTPException(404, "Transaction not found")
    return t.payload


@app.get("/transactions/{transaction_id}")
def transaction(transaction_id: str, s=Depends(db), user=Depends(identity)):
    return get_transaction(transaction_id, s)


@app.get("/transactions/{transaction_id}/explanation")
def explanation(transaction_id: str, s=Depends(db), user=Depends(identity)):
    row = get_transaction(transaction_id, s)
    return {
        "transaction_id": transaction_id,
        "score": row["risk_score"],
        "signals": explain(row, row["triggered_rules"].split(",")),
        "caution": "Anomaly scores indicate unusual behavior, not proof of fraud.",
    }


@app.get("/analytics/summary")
def analytics_summary(d=Depends(dataset), s=Depends(db), user=Depends(identity)):
    backlog = review_backlog(s)
    return summary(d, backlog)


@app.get("/analytics/trends")
def analytics_trends(d=Depends(dataset), user=Depends(identity)):
    return trends(d).to_dict("records")


@app.get("/rules")
def rules(user=Depends(identity)):
    return catalog()


@app.get("/rules/performance")
def performance(d=Depends(dataset), user=Depends(identity)):
    return rule_performance(d)


@app.post("/rules/simulate")
def simulation(request: SimulationInput, d=Depends(dataset), user=Depends(identity)):
    authorize(user, ["manager"])
    try:
        return simulate(d, request)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/cases")
def cases(s=Depends(db), user=Depends(identity)):
    return list_cases(s)


@app.post("/cases", status_code=201)
def new_case(request: CaseCreate, s=Depends(db), user=Depends(identity)):
    authorize(user, ["analyst", "manager"])
    return handle(lambda: create_case(s, request, user["actor"]))


@app.patch("/cases/{case_id}")
def edit_case(case_id: int, request: CaseUpdate, s=Depends(db), user=Depends(identity)):
    authorize(user, ["analyst", "manager"])
    return handle(lambda: update_case(s, case_id, request, user["actor"]))


@app.get("/cases/{case_id}/audit")
def case_audit(case_id: int, s=Depends(db), user=Depends(identity)):
    if s.get(Case, case_id) is None:
        raise HTTPException(404, "Case not found")
    return audit_history(s, case_id)


@app.get("/models/performance")
def models(d=Depends(dataset), user=Depends(identity)):
    return model_results()


@app.get("/recommendations")
def leadership(d=Depends(dataset), user=Depends(identity)):
    return recommendations(d)


@app.get("/reports/risk", response_class=HTMLResponse)
def report(d=Depends(dataset), s=Depends(db), user=Depends(identity)):
    backlog = review_backlog(s)
    return report_html(d, backlog)
