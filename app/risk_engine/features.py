"""Behavior features exclude truth labels and future observations."""

import numpy as np
import pandas as pd

FEATURES = [
    "amount_ratio",
    "tx_count_1h",
    "distance_km",
    "account_age",
    "device_novelty",
    "failed_logins",
    "recipient_risk_numeric",
    "prior_chargebacks",
    "rapid_cashout",
    "travel_speed",
    "shared_accounts",
    "customer_devices",
]


def engineer(raw: pd.DataFrame) -> pd.DataFrame:
    required = {
        "amount",
        "customer_avg_amount",
        "device_trusted",
        "recipient_risk",
        "minutes_since_deposit",
        "direction",
        "distance_km",
        "hours_since_last_location",
        "device_id",
        "customer_id",
        "timestamp",
        "account_age",
        "tx_count_1h",
        "failed_logins",
        "prior_chargebacks",
    }
    if missing := required - set(raw.columns):
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if raw[list(required)].isnull().any().any():
        raise ValueError("Feature input contains missing values")
    if (raw.amount < 0).any() or (raw.customer_avg_amount <= 0).any():
        raise ValueError("Invalid amount or behavioral baseline")
    d = raw.sort_values(["timestamp", "transaction_id"], kind="stable").copy()
    d["amount_ratio"] = (d.amount / d.customer_avg_amount).clip(0, 1000)
    d["device_novelty"] = (~d.device_trusted.astype(bool)).astype(int)
    d["recipient_risk_numeric"] = d.recipient_risk.map(
        {"low": 0, "medium": 0.5, "high": 1}
    )
    if d.recipient_risk_numeric.isnull().any():
        raise ValueError("Unknown recipient risk")
    d["rapid_cashout"] = np.where(
        d.direction == "withdrawal", np.exp(-d.minutes_since_deposit / 30), 0
    )
    d["travel_speed"] = d.distance_km / d.hours_since_last_location.clip(lower=0.1)
    # Count distinct relationships seen at or before each event, never future rows.
    first = ~d.duplicated(["device_id", "customer_id"])
    d["shared_accounts"] = first.astype(int).groupby(d.device_id).cumsum()
    first_device = ~d.duplicated(["customer_id", "device_id"])
    d["customer_devices"] = first_device.astype(int).groupby(d.customer_id).cumsum()
    if not np.isfinite(d[FEATURES].to_numpy(float)).all():
        raise ValueError("Nonfinite feature")
    return d
