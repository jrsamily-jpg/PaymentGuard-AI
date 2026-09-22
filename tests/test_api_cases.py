import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.research import app, db, dataset
from app.api.security import identity
from app.database.session import Base
from app.database.models import Transaction


@pytest.fixture
def client(cohort):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    row = cohort.iloc[0].to_dict()
    row.update(status="settled", risk_level="Low", triggered_rules="")
    keys = [c.name for c in Transaction.__table__.columns if c.name != "payload"]
    with sessions() as s:
        s.add(Transaction(**{k: row[k] for k in keys}, payload=row))
        s.commit()

    def test_db():
        with sessions() as s:
            yield s

    app.dependency_overrides[db] = test_db
    app.dependency_overrides[dataset] = lambda: cohort
    app.dependency_overrides[identity] = lambda: {
        "role": "manager",
        "actor": "test-manager",
    }
    with TestClient(app) as c:
        yield c, row["transaction_id"]
    app.dependency_overrides.clear()


def test_api_validation_and_search(client):
    c, tx = client
    assert c.get("/health").status_code == 200
    assert c.get("/transactions?limit=501").status_code == 422
    assert c.get("/transactions?min_amount=20&max_amount=10").status_code == 422
    assert c.get("/transactions?search=' OR 1=1 --").json()["total"] == 0
    assert c.get(f"/transactions/{tx}").status_code == 200
    assert c.get("/transactions/does-not-exist").status_code == 404
    assert c.get(f"/transactions/{tx}/explanation").status_code == 200
    assert len(c.get("/rules").json()) == 12
    assert c.post("/rules/simulate", json={"confirmed": False}).status_code == 422
    assert (
        c.post(
            "/rules/simulate", json={"confirmed": True, "thresholds": {"R01": -1}}
        ).status_code
        == 422
    )
    assert c.post("/rules/simulate", json={"confirmed": True}).status_code == 200


def test_case_audit_concurrency_and_rbac(client):
    c, tx = client
    created = c.post("/cases", json={"transaction_id": tx, "assignee": "Alex"})
    assert created.status_code == 201
    case = created.json()
    cid = case["id"]
    assert c.post("/cases", json={"transaction_id": tx}).status_code == 409
    assert (
        c.patch(f"/cases/{cid}", json={"version": 1, "decision": "decline"}).status_code
        == 422
    )
    assert (
        c.patch(f"/cases/{cid}", json={"version": 1, "status": "closed"}).status_code
        == 409
    )
    assert (
        c.patch(
            f"/cases/{cid}",
            json={
                "version": 1,
                "decision": "escalate",
                "reason_code": "suspicious_behavior",
                "note": "Investigate linked device",
                "status": "escalated",
            },
        ).status_code
        == 200
    )
    assert (
        c.patch(f"/cases/{cid}", json={"version": 1, "note": "stale"}).status_code
        == 409
    )
    history = c.get(f"/cases/{cid}/audit").json()
    assert (
        len(history) == 2
        and history[1]["details"]["note"] == "Investigate linked device"
    )
    app.dependency_overrides[identity] = lambda: {
        "role": "auditor",
        "actor": "test-auditor",
    }
    assert c.get("/cases").status_code == 200
    assert c.post("/cases", json={"transaction_id": tx}).status_code == 403
    assert c.post("/rules/simulate", json={"confirmed": True}).status_code == 403


def test_dates_and_nonfinite_amounts(client):
    c, _ = client
    assert c.get("/transactions?start=2026-99-99").status_code == 422
    assert c.get("/transactions?start=2026-08-02&end=2026-08-01").status_code == 422
    assert c.get("/transactions?min_amount=nan").status_code == 422
    assert c.get("/transactions?start=2026-07-01&end=2026-08-30").status_code == 200
