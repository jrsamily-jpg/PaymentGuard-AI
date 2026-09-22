"""Transparent, pure and vectorized controls shared by API, dashboard and simulator."""

from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Rule:
    rule_id: str
    name: str
    description: str
    weight: float
    threshold: float
    minimum: float
    maximum: float
    unit: str
    action: str = "Review and verify"


RULES = [
    Rule(
        "R01",
        "New account cash-out",
        "Withdrawal above the amount threshold from an account under 30 days old",
        28,
        1000,
        50,
        50000,
        "USD",
    ),
    Rule(
        "R02",
        "Velocity spike",
        "Prior-hour transaction count at or above threshold",
        30,
        8,
        2,
        50,
        "transactions",
    ),
    Rule(
        "R03",
        "Rapid cash-out",
        "Withdrawal over $500 within threshold minutes of a deposit",
        32,
        30,
        1,
        120,
        "minutes",
    ),
    Rule(
        "R04",
        "Authentication pressure",
        "Failed logins at or above threshold before payment",
        25,
        4,
        1,
        20,
        "attempts",
    ),
    Rule(
        "R05",
        "Identity reset",
        "Untrusted device with password reset and at least threshold distinct customer devices",
        30,
        1,
        1,
        10,
        "devices",
    ),
    Rule(
        "R06",
        "Impossible travel",
        "Implied travel speed above threshold with distance over 500 km",
        30,
        900,
        300,
        3000,
        "km/h",
    ),
    Rule(
        "R07",
        "Shared device network",
        "Distinct accounts observed on this device at or above threshold",
        32,
        3,
        2,
        20,
        "accounts",
    ),
    Rule(
        "R08",
        "Ownership mismatch",
        "Bank ownership mismatch on a payment at or above threshold",
        28,
        0,
        0,
        10000,
        "USD",
    ),
    Rule(
        "R09",
        "Chargeback history",
        "Prior chargebacks at or above threshold",
        25,
        2,
        1,
        10,
        "chargebacks",
    ),
    Rule(
        "R10",
        "Risky destination",
        "High-risk recipient whose age is at or below threshold",
        26,
        30,
        1,
        900,
        "days",
    ),
    Rule(
        "R11",
        "Proxy and deviation",
        "VPN/proxy combined with amount-to-baseline ratio above threshold",
        24,
        3,
        1,
        30,
        "× baseline",
    ),
    Rule(
        "R12",
        "Amount outlier",
        "Amount-to-baseline ratio at or above threshold",
        28,
        6,
        2,
        40,
        "× baseline",
    ),
]


def catalog() -> list[dict]:
    return [asdict(r) for r in RULES]


def evaluate(
    d: pd.DataFrame, overrides: dict[str, float] | None = None
) -> pd.DataFrame:
    thresholds = {r.rule_id: r.threshold for r in RULES}
    for key, value in (overrides or {}).items():
        rule = next((r for r in RULES if r.rule_id == key), None)
        if (
            rule is None
            or not np.isfinite(value)
            or not rule.minimum <= value <= rule.maximum
        ):
            raise ValueError(f"Invalid threshold for {key}")
        thresholds[key] = value
    t = thresholds
    return pd.DataFrame(
        {
            "R01": (d.direction == "withdrawal")
            & (d.account_age < 30)
            & (d.amount > t["R01"]),
            "R02": d.tx_count_1h >= t["R02"],
            "R03": (d.direction == "withdrawal")
            & (d.amount > 500)
            & (d.minutes_since_deposit <= t["R03"]),
            "R04": d.failed_logins >= t["R04"],
            "R05": (~d.device_trusted)
            & d.password_reset
            & (d.customer_devices >= t["R05"]),
            "R06": (d.travel_speed > t["R06"]) & (d.distance_km > 500),
            "R07": d.shared_accounts >= t["R07"],
            "R08": (~d.ownership_match) & (d.amount >= t["R08"]),
            "R09": d.prior_chargebacks >= t["R09"],
            "R10": (d.recipient_risk == "high") & (d.recipient_age <= t["R10"]),
            "R11": d.vpn_proxy & (d.amount_ratio > t["R11"]),
            "R12": d.amount_ratio >= t["R12"],
        },
        index=d.index,
    )


def explain(row: dict, hits: list[str]) -> list[dict]:
    evidence = {
        "R01": f"Account {row['account_age']} days old; withdrawal ${row['amount']:,.2f}",
        "R02": f"{row['tx_count_1h']} payments in the prior hour",
        "R03": f"{row['minutes_since_deposit']:.0f} minutes since deposit",
        "R04": f"{row['failed_logins']} failed logins",
        "R05": f"Password reset with untrusted device; {row['customer_devices']} devices observed",
        "R06": f"Implied travel {row['travel_speed']:,.0f} km/h over {row['distance_km']:,.0f} km",
        "R07": f"{row['shared_accounts']} accounts observed on device",
        "R08": "Bank-account ownership does not match",
        "R09": f"{row['prior_chargebacks']} prior chargebacks",
        "R10": f"High-risk recipient, {row['recipient_age']} days old",
        "R11": f"Proxy enabled; amount {row['amount_ratio']:.1f}× baseline",
        "R12": f"Amount {row['amount_ratio']:.1f}× customer baseline",
    }
    return [
        {
            **asdict(r),
            "triggered": r.rule_id in hits,
            "explanation": evidence[r.rule_id],
        }
        for r in RULES
        if r.rule_id in hits
    ]
