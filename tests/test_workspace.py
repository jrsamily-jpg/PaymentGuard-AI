"""Operational isolation and truthful empty-state checks; fixtures never enter user storage."""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.workspace import api, auth, service
from app.workspace.database import Base
from app.workspace.models import AccessSession, User
from app.workspace.risk import assess
from app.workspace.schemas import PaymentInput

PASSWORD = "isolated-test-password-42"


@pytest.fixture
def workspace(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session_dependency():
        with factory() as session:
            yield session

    api.app.dependency_overrides[api.db] = session_dependency
    monkeypatch.setattr(api, "initialize", lambda: None)
    with TestClient(api.app) as client:
        yield client, factory
    api.app.dependency_overrides.clear()
    engine.dispose()


def account(client, name):
    response = client.post(
        "/auth/register", json={"username": name, "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {"Authorization": "Bearer " + body["access_token"]}, body


def event(**changes):
    return dict(
        external_id="private-payment",
        customer_ref="customer-1",
        occurred_at="2026-01-01T12:00:00+00:00",
        amount="123.45",
        rail="ACH",
        direction="withdrawal",
        **changes,
    )


def test_empty_users_and_cross_user_isolation(workspace):
    client, factory = workspace
    alice, a = account(client, "alice")
    bob, b = account(client, "bob")
    for headers in [alice, bob]:
        metrics = client.get("/analytics/summary", headers=headers).json()
        assert (
            metrics["payment_volume"]
            == metrics["transactions"]
            == metrics["confirmed_fraud_loss"]
            == metrics["blocked_fraud_amount"]
            == 0
        )
        assert metrics["false_positive_rate"] is None
        assert client.get("/transactions", headers=headers).json() == {
            "total": 0,
            "items": [],
        }
    assert (
        client.post(
            "/transactions/import", headers=alice, json={"payments": [event()]}
        ).status_code
        == 201
    )
    rows = client.get("/transactions", headers=alice).json()["items"]
    payment_id = rows[0]["id"]
    assert rows[0]["amount_minor"] == 12345 and rows[0]["score"] is None
    assert (
        client.get("/analytics/summary", headers=alice).json()["payment_volume"]
        == 123.45
    )
    assert client.get("/analytics/summary", headers=bob).json()["payment_volume"] == 0
    assert client.get("/transactions/" + payment_id, headers=bob).status_code == 404
    assert (
        client.get(
            "/transactions/" + payment_id + "/explanation", headers=bob
        ).status_code
        == 404
    )
    assert (
        client.post("/cases", headers=bob, json={"payment_id": payment_id}).status_code
        == 404
    )
    case = client.post("/cases", headers=alice, json={"payment_id": payment_id}).json()
    change = dict(  # noqa: C408
        version=1,
        assignee="Alice",
        status="closed",
        decision="approve",
        reason="verified customer",
        note="Owned record",
    )
    assert (
        client.patch("/cases/" + case["id"], headers=bob, json=change).status_code
        == 404
    )
    assert (
        client.patch("/cases/" + case["id"], headers=alice, json=change).status_code
        == 200
    )
    assert (
        client.patch("/cases/" + case["id"], headers=alice, json=change).status_code
        == 409
    )
    assert client.get("/cases", headers=bob).json() == []
    assert client.get("/audit", headers=bob).json() == []
    assert len(client.get("/audit", headers=alice).json()) == 3
    assert client.get("/analytics/rails", headers=bob).json() == []
    assert "123.45" not in client.get("/reports/risk", headers=bob).text
    assert client.get("/models/performance", headers=alice).json()["metrics"] is None
    # Returning owners retain data; a fresh user never inherits it.
    assert client.post("/auth/logout", headers=alice).status_code == 200
    assert client.get("/transactions", headers=alice).status_code == 401
    login = client.post(
        "/auth/login", json={"username": "alice", "password": PASSWORD}
    ).json()
    returning = {"Authorization": "Bearer " + login["access_token"]}
    assert client.get("/transactions", headers=returning).json()["total"] == 1
    assert (
        client.post(
            "/transactions/import", headers=bob, json={"payments": [event()]}
        ).status_code
        == 201
    )
    with factory() as session:
        user = session.get(User, a["user"]["id"])
        assert PASSWORD not in user.password_hash and auth.verify_password(
            PASSWORD, user.password_hash
        )
        access = session.scalar(
            select(AccessSession).where(AccessSession.owner_id == b["user"]["id"])
        )
        assert access.token_hash != b["access_token"]
        access.expires_at = int(time.time()) - 1
        session.commit()
    assert client.get("/transactions", headers=bob).status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/transactions",
        "/analytics/summary",
        "/analytics/rails",
        "/rules",
        "/rules/performance",
        "/cases",
        "/audit",
        "/models/performance",
        "/reports/risk",
        "/auth/me",
    ],
)
def test_private_routes_require_identity(workspace, path):
    client, _ = workspace
    assert client.get(path).status_code == 401
    assert (
        client.get(path, headers={"Authorization": "Bearer forged-token"}).status_code
        == 401
    )


def test_atomic_duplicates_input_bounds_and_throttle(workspace):
    client, _ = workspace
    headers, _ = account(client, "operator")
    response = client.post(
        "/transactions/import", headers=headers, json={"payments": [event(), event()]}
    )
    assert response.status_code == 409
    assert client.get("/transactions", headers=headers).json()["total"] == 0
    assert (
        client.post(
            "/transactions/import",
            headers=headers,
            json={"payments": [event(owner_id="other")]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/transactions/import", headers=headers, json={"payments": [event()]}
        ).status_code
        == 201
    )
    second = event()
    second["external_id"] = "new-ref"
    assert (
        client.post(
            "/transactions/import",
            headers=headers,
            json={"payments": [second, event()]},
        ).status_code
        == 409
    )
    assert client.get("/transactions", headers=headers).json()["total"] == 1
    assert client.get("/transactions?limit=1&offset=1", headers=headers).json() == {
        "total": 1,
        "items": [],
    }
    assert client.get("/transactions?limit=999999", headers=headers).status_code == 422
    assert client.post("/auth/login", content=b"x" * 5_000_001).status_code == 413
    for _ in range(5):
        assert (
            client.post(
                "/auth/login",
                json={"username": "operator", "password": "wrong-long-password"},
            ).status_code
            == 401
        )
    throttled = client.post(
        "/auth/login", json={"username": "operator", "password": PASSWORD}
    )
    assert throttled.status_code == 401 and "Too many" in throttled.text


def test_csv_and_missing_evidence_are_not_fabricated():
    with pytest.raises(ValueError, match="no payments"):
        service.parse_csv(service.csv_template().encode())
    with pytest.raises(ValueError):
        service.parse_csv(b"amount,amount\n1,2\n")
    with pytest.raises(ValueError):
        service.parse_csv(b"x" * 2_000_001)
    payment = PaymentInput.model_validate(event())
    result = assess(payment)
    assert (
        result["score"] is None
        and result["evaluated_rules"] == 0
        and len(result["missing_rules"]) == 12
    )
    flagged = PaymentInput.model_validate(event(evidence={"failed_logins": 100}))
    result = assess(flagged)
    assert result["evaluated_rules"] == 1 and result["signals"][0]["rule_id"] == "R04"
    with pytest.raises(ValueError):
        assess(flagged, {"R04": float("nan")})
    with pytest.raises(ValueError):
        PaymentInput.model_validate({**event(), "amount": "0.001"})
    with pytest.raises(ValueError):
        PaymentInput.model_validate({**event(), "occurred_at": "2026-01-01T12:00:00"})


def test_unknown_outcomes_do_not_count_as_legitimate(workspace):
    client, _ = workspace
    headers, _ = account(client, "metrics")
    values = [
        event(status="blocked"),
        {**event(status="blocked", confirmed_fraud=True), "external_id": "fraud"},
        {**event(status="settled", confirmed_fraud=False), "external_id": "legit"},
    ]
    client.post("/transactions/import", headers=headers, json={"payments": values})
    metrics = client.get("/analytics/summary", headers=headers).json()
    assert metrics["payment_volume"] == 370.35
    assert metrics["blocked_fraud_amount"] == 123.45
    assert metrics["confirmed_outcomes"] == 2 and metrics["legitimate_blocks"] == 0
    assert metrics["unassessed_transactions"] == 3
    assert client.post("/rules/simulate", headers=headers, json={}).status_code == 409
    simulation = client.post(
        "/rules/simulate", headers=headers, json={"confirmed": True}
    )
    assert (
        simulation.status_code == 200 and simulation.json()["proposed"]["flagged"] == 0
    )


@pytest.mark.parametrize(
    "rule_id,evidence",
    [
        ("R01", {"account_age": 1}),
        ("R02", {"tx_count_1h": 10}),
        ("R03", {"minutes_since_deposit": 2}),
        ("R04", {"failed_logins": 5}),
        (
            "R05",
            {"device_trusted": False, "password_reset": True, "customer_devices": 2},
        ),
        ("R06", {"distance_km": 2000, "hours_since_last_location": 1}),
        ("R07", {"shared_accounts": 5}),
        ("R08", {"ownership_match": False}),
        ("R09", {"prior_chargebacks": 3}),
        ("R10", {"recipient_risk": "high", "recipient_age": 1}),
        ("R11", {"vpn_proxy": True, "customer_avg_amount": 100}),
        ("R12", {"customer_avg_amount": 100}),
    ],
)
def test_each_operational_control_uses_supplied_evidence(rule_id, evidence):
    payment = PaymentInput.model_validate(
        {**event(evidence=evidence), "amount": "2000"}
    )
    result = assess(payment)
    assert rule_id in {item["rule_id"] for item in result["signals"]}
    assert result["score"] > 0
    assert len(result["missing_rules"]) + result["evaluated_rules"] == 12


def test_validation_never_echoes_password(workspace):
    client, _ = workspace
    for path in ["/auth/register", "/auth/login"]:
        response = client.post(
            path, json={"username": "operator", "password": "tiny-pass"}
        )
        assert response.status_code == 422
        assert "tiny-pass" not in response.text
        assert "input" not in response.json()["detail"][0]
