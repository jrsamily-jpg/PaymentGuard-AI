"""Counterfactual policies are evaluated without changing persisted transactions or rules."""

from typing import Any
import pandas as pd
from app.models.schemas import SimulationInput
from app.risk_engine.rules import evaluate
from app.risk_engine.scoring import score
from app.risk_engine.metrics import evaluate_metrics


def simulate(d: pd.DataFrame, request: SimulationInput) -> dict[str, Any]:
    """Compare a confirmed candidate with the unchanged score-60 baseline."""
    if not request.confirmed:
        raise ValueError("Confirm the proposed settings before running simulation")
    proposed = score(
        d, evaluate(d, request.thresholds), d.anomaly_score.to_numpy()
    ).risk_score
    current = evaluate_metrics(
        d.is_fraud, d.risk_score >= 60, d.amount, d.risk_score, request.friction_cost
    )
    changed = evaluate_metrics(
        d.is_fraud,
        proposed >= request.decision_threshold,
        d.amount,
        proposed,
        request.friction_cost,
    )
    delta = {
        key: changed[key] - current[key]
        for key in [
            "tp",
            "fp",
            "precision",
            "recall",
            "fraud_dollars_detected",
            "legitimate_dollars_blocked",
            "friction_cost",
        ]
    }
    delta["net_financial_impact"] = (
        delta["fraud_dollars_detected"] - delta["friction_cost"]
    )
    return {
        "current": current,
        "proposed": changed,
        "delta": delta,
        "settings": request.model_dump(),
        "scope": "Synthetic full-cohort counterfactual; not a causal or production estimate",
    }
