"""Strict synthetic CSV boundary; no dashboard upload or arbitrary SQL surface."""

from pathlib import Path
import ipaddress
import numpy as np
import pandas as pd
from app.services.generation import generate_transactions


def validate_raw(data: pd.DataFrame) -> pd.DataFrame:
    """Validate the complete raw contract without silently imputing risk evidence."""
    required = set(generate_transactions(100).columns)
    if missing := required - set(data.columns):
        raise ValueError(f"Missing required fields: {sorted(missing)}")
    if data.empty or data[list(required)].isnull().any().any():
        raise ValueError("Empty data or missing evidence")
    if (
        not data.transaction_id.str.fullmatch(r"TX-\d{7}").all()
        or not data.transaction_id.is_unique
    ):
        raise ValueError("Invalid or duplicate transaction IDs")
    numeric = [
        "amount",
        "customer_avg_amount",
        "account_age",
        "customer_tenure",
        "email_domain_age",
        "tx_count_1h",
        "tx_count_24h",
        "amount_24h",
        "failed_logins",
        "distance_km",
        "prior_chargebacks",
        "prior_fraud_reports",
        "recipient_age",
        "minutes_since_deposit",
        "hours_since_last_location",
    ]
    try:
        values = data[numeric].to_numpy(float)
    except (TypeError, ValueError) as error:
        raise ValueError("Nonnumeric evidence") from error
    if (
        not np.isfinite(values).all()
        or (values < 0).any()
        or (data.amount <= 0).any()
        or (data.customer_avg_amount <= 0).any()
    ):
        raise ValueError("Invalid numeric evidence")
    if (data.tx_count_24h < data.tx_count_1h).any() or (
        data.customer_tenure < data.account_age
    ).any():
        raise ValueError("Inconsistent aggregates")
    for field in [
        "is_fraud",
        "device_trusted",
        "password_reset",
        "mfa_enabled",
        "vpn_proxy",
        "new_payment_method",
        "recent_method_change",
        "ownership_match",
    ]:
        if not data[field].map(lambda x: isinstance(x, (bool, np.bool_))).all():
            raise ValueError(f"{field} must contain booleans")
    if not data.currency.eq("USD").all():
        raise ValueError("Only synthetic USD-valued payments are supported")
    if not data.direction.isin(["deposit", "withdrawal"]).all():
        raise ValueError("Invalid direction")
    if not data.payment_rail.isin(
        ["ACH", "Debit card", "Credit card", "Wire", "Real-time payment", "Crypto"]
    ).all():
        raise ValueError("Invalid payment rail")
    if not data.recipient_risk.isin(["low", "medium", "high"]).all():
        raise ValueError("Invalid recipient risk")
    pd.to_datetime(data.timestamp, errors="raise")
    for address in data.ip_address.unique():
        if ipaddress.ip_address(address) not in ipaddress.ip_network("192.0.2.0/24"):
            raise ValueError("Only documentation-range synthetic IPs are accepted")
    return data.copy()


def read_synthetic_csv(path: Path, *, synthetic_confirmed: bool) -> pd.DataFrame:
    """Read a bounded, local CSV only with explicit synthetic-data confirmation."""
    if not synthetic_confirmed:
        raise ValueError("Synthetic-only confirmation is required")
    if path.suffix.lower() != ".csv" or path.stat().st_size > 100_000_000:
        raise ValueError("Expected a CSV no larger than 100 MB")
    return validate_raw(pd.read_csv(path, keep_default_na=False))
