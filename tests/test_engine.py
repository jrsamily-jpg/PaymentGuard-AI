import numpy as np
import pandas as pd
import pytest
from app.services.generation import generate_transactions
from app.risk_engine.features import engineer, FEATURES
from app.risk_engine.rules import evaluate, RULES, explain, catalog
from app.risk_engine.scoring import score, risk_level
from app.risk_engine.metrics import evaluate_metrics
from app.risk_engine.simulation import simulate
from app.risk_engine.ml import fit_anomaly
from app.models.schemas import SimulationInput


def test_generation_reproducible_and_imbalanced():
    a = generate_transactions(5000)
    b = generate_transactions(5000)
    pd.testing.assert_frame_equal(a, b)
    assert 0.015 < a.is_fraud.mean() < 0.04
    assert a.transaction_id.is_unique and a.amount.min() > 0
    assert len(a[a.is_fraud].fraud_category.unique()) == 16
    assert (a.tx_count_24h >= a.tx_count_1h).all()
    with pytest.raises(ValueError):
        generate_transactions(1)


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "Low"),
        (29.9, "Low"),
        (30, "Medium"),
        (59.9, "Medium"),
        (60, "High"),
        (79.9, "High"),
        (80, "Critical"),
        (100, "Critical"),
    ],
)
def test_boundaries(value, expected):
    assert risk_level(value) == expected


@pytest.mark.parametrize("value", [-1, 101, float("nan")])
def test_bad_scores(value):
    with pytest.raises(ValueError):
        risk_level(value)


def test_all_rule_triggers_and_counterexamples(cohort):
    d = cohort.iloc[[0]].copy()
    values = {
        "direction": "withdrawal",
        "account_age": 1,
        "amount": 5000,
        "tx_count_1h": 30,
        "minutes_since_deposit": 1,
        "failed_logins": 10,
        "device_trusted": False,
        "password_reset": True,
        "customer_devices": 5,
        "travel_speed": 2000,
        "distance_km": 3000,
        "shared_accounts": 5,
        "ownership_match": False,
        "prior_chargebacks": 4,
        "recipient_risk": "high",
        "recipient_age": 1,
        "vpn_proxy": True,
        "amount_ratio": 20,
    }
    for k, v in values.items():
        d[k] = v
    assert evaluate(d).iloc[0].all()
    explanations = explain(d.iloc[0].to_dict(), [r.rule_id for r in RULES])
    assert len(explanations) == 12 and all(x["explanation"] for x in explanations)
    safe = {
        "direction": "deposit",
        "account_age": 100,
        "amount": 20,
        "tx_count_1h": 0,
        "minutes_since_deposit": 10000,
        "failed_logins": 0,
        "device_trusted": True,
        "password_reset": False,
        "customer_devices": 1,
        "travel_speed": 0,
        "distance_km": 0,
        "shared_accounts": 1,
        "ownership_match": True,
        "prior_chargebacks": 0,
        "recipient_risk": "low",
        "recipient_age": 100,
        "vpn_proxy": False,
        "amount_ratio": 1,
    }
    for k, v in safe.items():
        d[k] = v
    assert not evaluate(d).iloc[0].any()
    assert len(catalog()) == 12


@pytest.mark.parametrize("changes", [{"BAD": 10}, {"R01": 0}, {"R01": float("nan")}])
def test_invalid_thresholds(cohort, changes):
    with pytest.raises(ValueError):
        evaluate(cohort, changes)


def test_threshold_inclusivity(cohort):
    d = cohort.iloc[:1].copy()
    d["tx_count_1h"] = 8
    assert evaluate(d).R02.iloc[0]
    assert not evaluate(d, {"R02": 9}).R02.iloc[0]


def test_feature_no_future_network_leakage():
    d = generate_transactions(100).iloc[:3].copy()
    d["device_id"] = "shared"
    d["customer_id"] = ["a", "b", "c"]
    features = engineer(d)
    assert features.shared_accounts.tolist() == [1, 2, 3]
    assert "is_fraud" not in FEATURES and "fraud_category" not in FEATURES


def test_feature_validation():
    d = generate_transactions(100)
    with pytest.raises(ValueError):
        engineer(d.drop(columns="amount"))
    d.loc[0, "amount"] = np.nan
    with pytest.raises(ValueError):
        engineer(d)
    d.loc[0, "amount"] = -1
    with pytest.raises(ValueError):
        engineer(d)
    d.loc[0, "amount"] = 1
    d.loc[0, "recipient_risk"] = "unknown"
    with pytest.raises(ValueError):
        engineer(d)


def test_score_bounded_and_additive(cohort):
    out = score(cohort, evaluate(cohort), cohort.anomaly_score.to_numpy())
    parts = out.drop(columns=["risk_score", "risk_level", "rules_score"])
    assert np.allclose(out.risk_score, parts.sum(axis=1).clip(0, 100).round(1))
    assert out.risk_score.between(0, 100).all()
    with pytest.raises(ValueError):
        score(cohort, evaluate(cohort), np.array([np.nan]))


def test_metrics_hand_calculated():
    m = evaluate_metrics(
        [1, 1, 0, 0], [1, 0, 1, 0], [100, 200, 300, 400], [90, 20, 80, 10]
    )
    assert (m["tp"], m["fp"], m["tn"], m["fn"]) == (1, 1, 1, 1)
    assert m["precision"] == m["recall"] == m["f1"] == 0.5
    assert m["fraud_dollars_detected"] == 100 and m["fraud_dollars_missed"] == 200
    assert m["legitimate_dollars_blocked"] == 300 and m["friction_cost"] == 8
    assert evaluate_metrics([0], [0], [10])["roc_auc"] is None
    with pytest.raises(ValueError):
        evaluate_metrics([1], [1], [-1])


def test_simulator_identity_and_no_mutation(cohort):
    before = cohort.copy(deep=True)
    result = simulate(cohort, SimulationInput(confirmed=True))
    assert all(v == 0 for v in result["delta"].values())
    changed = simulate(
        cohort,
        SimulationInput(confirmed=True, decision_threshold=90, thresholds={"R02": 20}),
    )
    assert changed["proposed"]["tp"] <= result["proposed"]["tp"]
    pd.testing.assert_frame_equal(before, cohort)
    with pytest.raises(ValueError):
        simulate(cohort, SimulationInput())


def test_model_is_reproducible(cohort):
    a, split, meta = fit_anomaly(cohort)
    b, _, _ = fit_anomaly(cohort)
    assert np.array_equal(a, b) and split == 350 and meta["test_rows"] == 150
    assert np.all((a >= 0) & (a <= 1))


def test_nonfinite_feature_rejected():
    d = generate_transactions(100)
    d["distance_km"] = float("inf")
    with pytest.raises(ValueError):
        engineer(d)


@pytest.mark.parametrize(
    "truth,prediction,amounts,scores",
    [
        ([None], [1], [10], None),
        ([1], [2], [10], None),
        ([[1]], [1], [10], None),
        ([1], [1], [[10]], None),
        ([0, 1], [0, 1], [10, 20], [0.1, float("nan")]),
        ([0, 1], [0, 1], [10, 20], [0.1]),
    ],
)
def test_malformed_metric_inputs(truth, prediction, amounts, scores):
    with pytest.raises(ValueError):
        evaluate_metrics(truth, prediction, amounts, scores)
