"""Verified cohort analytics reused across presentation layers."""

from typing import Any
import pandas as pd
from app.risk_engine.metrics import evaluate_metrics
from app.risk_engine.rules import RULES, evaluate


def summary(d: pd.DataFrame, backlog: int | None = None) -> dict[str, Any]:
    blocked = d.status == "blocked"
    settled = d.status.isin(["settled", "returned"])
    fraud = d.is_fraud.astype(bool)
    loss = float(d.loc[fraud & settled, "amount"].sum())
    metric = evaluate_metrics(fraud, blocked, d.amount, d.risk_score)
    return {
        "total_transactions": len(d),
        "total_volume": float(d.amount.sum()),
        "confirmed_fraud_loss": loss,
        "potential_fraud_prevented": float(d.loc[fraud & blocked, "amount"].sum()),
        "fraud_loss_rate": loss / max(1, float(d.amount.sum())),
        "high_risk_transactions": int((d.risk_score >= 60).sum()),
        "false_positive_rate": metric["false_positive_rate"],
        "legitimate_payments_blocked": metric["fp"],
        "legitimate_dollars_blocked": metric["legitimate_dollars_blocked"],
        "review_backlog": int((d.status == "review").sum())
        if backlog is None
        else backlog,
        "review_transactions": int((d.status == "review").sum()),
        "fraud_rate": float(fraud.mean()),
        "synthetic": True,
        "currency": "USD",
        "start": str(d.timestamp.min()),
        "end": str(d.timestamp.max()),
    }


def trends(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    x["day"] = x.timestamp.str[:10]
    x["loss"] = x.amount.where(x.is_fraud & x.status.isin(["settled", "returned"]), 0)
    return (
        x.groupby("day")
        .agg(
            volume=("amount", "sum"),
            fraud_loss=("loss", "sum"),
            transactions=("transaction_id", "count"),
            fraud_rate=("is_fraud", "mean"),
        )
        .reset_index()
    )


def rule_performance(d: pd.DataFrame) -> list[dict[str, Any]]:
    hits = evaluate(d)
    rows = []
    for r in RULES:
        m = evaluate_metrics(d.is_fraud, hits[r.rule_id], d.amount)
        action = (
            "retain"
            if m["precision"] >= 0.70
            else "monitor"
            if m["precision"] >= 0.40
            else "tune"
            if m["tp"]
            else "retire"
        )
        rows.append(
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "triggered": int(hits[r.rule_id].sum()),
                **m,
                "recommendation": action,
            }
        )
    return rows


def emerging(d: pd.DataFrame) -> pd.DataFrame:
    latest = pd.Timestamp(d.timestamp.max())
    t = pd.to_datetime(d.timestamp)
    current = d[
        (t > latest - pd.Timedelta(days=7)) & d.is_fraud
    ].fraud_category.value_counts()
    previous = d[
        (t > latest - pd.Timedelta(days=14))
        & (t <= latest - pd.Timedelta(days=7))
        & d.is_fraud
    ].fraud_category.value_counts()
    out = (
        pd.DataFrame({"current_week": current, "previous_week": previous})
        .fillna(0)
        .astype(int)
    )
    out["change"] = out.current_week - out.previous_week
    return out.sort_values("change", ascending=False).reset_index(names="pattern")


def recommendations(d: pd.DataFrame) -> list[dict[str, str]]:
    rows = rule_performance(d)
    poor = min(rows, key=lambda x: x["precision"] if x["triggered"] else 2)
    trend = emerging(d).iloc[0]
    trusted = d[
        (d.account_age > 365) & d.device_trusted & ~d.is_fraud & (d.risk_score >= 60)
    ]
    clusters = d[d.shared_accounts >= 3]
    return [
        {
            "title": f"Test a tighter {poor['rule_id']} control",
            "evidence": f"{poor['name']} flags {poor['fp']:,} legitimate payments at {poor['precision']:.1%} precision; estimated friction is ${poor['friction_cost']:,.0f} at $8 per false alert.",
            "action": "Compare threshold changes in the simulator before considering any policy change.",
        },
        {
            "title": f"Investigate {trend['pattern'].lower()}",
            "evidence": f"Latest seven days: {trend['current_week']} synthetic fraud events, versus {trend['previous_week']} in the preceding seven days ({trend['change']:+d}).",
            "action": "Review authentication and device evidence; absolute change alone does not establish statistical significance.",
        },
        {
            "title": "Test step-up verification for established customers",
            "evidence": f"{len(trusted):,} legitimate, trusted-device payments from accounts older than one year exceed the review threshold, totaling ${trusted.amount.sum():,.0f}.",
            "action": "Test verification before decline; do not blanket-exempt longstanding accounts.",
        },
        {
            "title": "Review device clusters",
            "evidence": f"{clusters.device_id.nunique():,} devices have at least three observed accounts across {len(clusters):,} transactions; {clusters.is_fraud.mean() if len(clusters) else 0:.1%} carry synthetic fraud labels.",
            "action": "Prioritize linked cases; shared devices can also be households or shared facilities.",
        },
    ]
