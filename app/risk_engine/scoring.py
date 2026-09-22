"""Explicit additive score. Weights are demonstration policy, not calibrated probabilities."""

import numpy as np
import pandas as pd
from app.risk_engine.rules import RULES

LEVELS = ["Low", "Medium", "High", "Critical"]


def risk_level(score: float) -> str:
    if not np.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("Score outside 0–100")
    return (
        "Low"
        if score < 30
        else "Medium"
        if score < 60
        else "High"
        if score < 80
        else "Critical"
    )


def score(d: pd.DataFrame, hits: pd.DataFrame, anomaly: np.ndarray) -> pd.DataFrame:
    if (
        len(anomaly) != len(d)
        or not np.isfinite(anomaly).all()
        or ((anomaly < 0) | (anomaly > 1)).any()
    ):
        raise ValueError("Invalid anomaly scores")
    rules = hits.mul({r.rule_id: r.weight for r in RULES}).sum(axis=1)
    parts = pd.DataFrame(
        {
            "rules": rules.clip(upper=55),
            "behavior": (np.maximum(d.amount_ratio - 2, 0) * 1.5).clip(upper=10),
            "device": d.device_novelty * 4 + (d.customer_devices >= 4) * 3,
            "authentication": (~d.mfa_enabled) * 3 + d.password_reset * 2,
            "payment_method": d.new_payment_method * 2 + (~d.ownership_match) * 3,
            "recipient": d.recipient_risk_numeric * 4,
            "geography": (d.travel_speed > 900) * 4,
            "anomaly": np.clip((anomaly - 0.70) / 0.30, 0, 1) * 20,
        },
        index=d.index,
    )
    parts["risk_score"] = parts.sum(axis=1).clip(0, 100).round(1)
    parts["risk_level"] = pd.cut(
        parts.risk_score, [-1, 29.999, 59.999, 79.999, 100], labels=LEVELS
    ).astype(str)
    parts["rules_score"] = rules.clip(upper=100)
    return parts
