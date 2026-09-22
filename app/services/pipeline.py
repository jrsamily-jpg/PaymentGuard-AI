"""Build an immutable synthetic cohort, evaluate, and persist normalized facts."""

import json
import numpy as np
from sqlalchemy import select, func
from app.services.generation import generate_transactions
from app.services.ingestion import validate_raw
from app.risk_engine.features import engineer
from app.risk_engine.rules import evaluate
from app.risk_engine.scoring import score
from app.risk_engine.ml import fit_anomaly
from app.risk_engine.metrics import evaluate_metrics
from app.database.session import Base, engine, SessionLocal
from app.database.models import Transaction, RuleHit
from app.utils.config import DATA


def build(n: int = 100_000, seed: int = 42) -> dict:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(Transaction)):
            raise ValueError(
                "Dataset already exists. Use a new DATABASE_URL/data directory to preserve case history."
            )
    d = engineer(validate_raw(generate_transactions(n, seed)))
    anomaly, split, model = fit_anomaly(d)
    hits = evaluate(d)
    parts = score(d, hits, anomaly)
    d["anomaly_score"] = anomaly
    for name in ["risk_score", "risk_level", "rules_score"]:
        d[name] = parts[name]
    d["triggered_rules"] = hits.apply(lambda row: ",".join(row.index[row]), axis=1)
    d["score_components"] = [
        json.dumps(r)
        for r in parts.drop(
            columns=["risk_score", "risk_level", "rules_score"]
        ).to_dict("records")
    ]
    d["status"] = np.where(
        d.risk_score >= 80, "blocked", np.where(d.risk_score >= 60, "review", "settled")
    )
    d.loc[
        d.is_fraud & (d.payment_rail == "ACH") & (d.status == "settled"), "status"
    ] = "returned"
    d["evaluation_split"] = np.where(np.arange(len(d)) < split, "train", "test")
    test = d.iloc[split:]
    results = {
        "model": model,
        "cohort": {
            "rows": len(d),
            "fraud_count": int(d.is_fraud.sum()),
            "fraud_rate": float(d.is_fraud.mean()),
            "seed": seed,
        },
        "evaluation": {},
    }
    for name, pred, continuous in [
        ("Rules only", test.rules_score >= 30, test.rules_score),
        ("ML only", test.anomaly_score >= 0.97, test.anomaly_score),
        ("Combined", test.risk_score >= 60, test.risk_score),
    ]:
        results["evaluation"][name] = evaluate_metrics(
            test.is_fraud, pred, test.amount, continuous
        )
    results["threshold_curve"] = [
        {
            "threshold": t,
            **evaluate_metrics(test.is_fraud, test.risk_score >= t, test.amount),
        }
        for t in range(10, 101, 5)
    ]
    cols = [c.name for c in Transaction.__table__.columns if c.name != "payload"]
    with SessionLocal() as session:
        for start in range(0, len(d), 2000):
            records = json.loads(d.iloc[start : start + 2000].to_json(orient="records"))
            session.bulk_insert_mappings(
                Transaction,
                [{**{k: r[k] for k in cols}, "payload": r} for r in records],
            )
        session.flush()
        rule_rows = [
            {"transaction_id": tx, "rule_id": rule}
            for tx, rules in zip(d.transaction_id, d.triggered_rules)
            for rule in rules.split(",")
            if rule
        ]
        for start in range(0, len(rule_rows), 3000):
            session.bulk_insert_mappings(RuleHit, rule_rows[start : start + 3000])
        session.commit()
    d.to_csv(DATA / "transactions.csv", index=False)
    (DATA / "results.json").write_text(json.dumps(results, indent=2))
    return results
