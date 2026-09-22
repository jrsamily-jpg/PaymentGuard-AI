"""Evidence-only rules: absent context stays unknown; no synthetic ML scores or labels."""

import math
from typing import Any

from app.risk_engine.rules import RULES
from app.workspace.schemas import PaymentInput


def assess(
    payment: PaymentInput, overrides: dict[str, float] | None = None
) -> dict[str, Any]:
    thresholds = {r.rule_id: r.threshold for r in RULES}
    for key, value in (overrides or {}).items():
        rule = next((r for r in RULES if r.rule_id == key), None)
        if (
            not rule
            or not math.isfinite(value)
            or not rule.minimum <= value <= rule.maximum
        ):
            raise ValueError(f"Invalid threshold: {key}")
        thresholds[key] = value
    e = payment.evidence.model_dump()
    a = float(payment.amount)
    t = thresholds
    definitions = [
        (
            "R01",
            ["account_age"],
            lambda: (
                payment.direction == "withdrawal"
                and e["account_age"] < 30
                and a > t["R01"]
            ),
            "New account with a high-value withdrawal",
        ),
        (
            "R02",
            ["tx_count_1h"],
            lambda: e["tx_count_1h"] >= t["R02"],
            "Prior-hour payment count exceeds policy threshold",
        ),
        (
            "R03",
            ["minutes_since_deposit"],
            lambda: (
                payment.direction == "withdrawal"
                and a > 500
                and e["minutes_since_deposit"] <= t["R03"]
            ),
            "Withdrawal shortly after a deposit",
        ),
        (
            "R04",
            ["failed_logins"],
            lambda: e["failed_logins"] >= t["R04"],
            "Repeated authentication failures before payment",
        ),
        (
            "R05",
            ["device_trusted", "password_reset", "customer_devices"],
            lambda: (
                not e["device_trusted"]
                and e["password_reset"]
                and e["customer_devices"] >= t["R05"]
            ),
            "Untrusted device after a password reset",
        ),
        (
            "R06",
            ["distance_km", "hours_since_last_location"],
            lambda: (
                e["distance_km"] > 500
                and e["distance_km"] / e["hours_since_last_location"] > t["R06"]
            ),
            "Reported locations imply excessive travel speed",
        ),
        (
            "R07",
            ["shared_accounts"],
            lambda: e["shared_accounts"] >= t["R07"],
            "Device shared by multiple reported accounts",
        ),
        (
            "R08",
            ["ownership_match"],
            lambda: not e["ownership_match"] and a >= t["R08"],
            "Reported bank-account ownership mismatch",
        ),
        (
            "R09",
            ["prior_chargebacks"],
            lambda: e["prior_chargebacks"] >= t["R09"],
            "Reported chargeback history exceeds threshold",
        ),
        (
            "R10",
            ["recipient_risk", "recipient_age"],
            lambda: e["recipient_risk"] == "high" and e["recipient_age"] <= t["R10"],
            "New recipient with a reported high-risk rating",
        ),
        (
            "R11",
            ["vpn_proxy", "customer_avg_amount"],
            lambda: e["vpn_proxy"] and a / e["customer_avg_amount"] > t["R11"],
            "Reported proxy use and unusual payment amount",
        ),
        (
            "R12",
            ["customer_avg_amount"],
            lambda: a / e["customer_avg_amount"] >= t["R12"],
            "Payment exceeds the provided customer baseline",
        ),
    ]
    signals = []
    evaluated = []
    missing = []
    for key, fields, predicate, description in definitions:
        if any(e[field] is None for field in fields):
            missing.append(key)
            continue
        evaluated.append(key)
        if predicate():
            rule = next(r for r in RULES if r.rule_id == key)
            signals.append(
                {
                    "rule_id": key,
                    "name": rule.name,
                    "weight": rule.weight,
                    "threshold": t[key],
                    "description": description,
                    "evidence": {field: e[field] for field in fields},
                }
            )
    points = (
        min(100, int(sum(signal["weight"] for signal in signals)))
        if evaluated
        else None
    )
    return {
        "score": points,
        "signals": signals,
        "evaluated_rules": len(evaluated),
        "missing_rules": missing,
        "method": "rules-only / provided evidence",
    }
