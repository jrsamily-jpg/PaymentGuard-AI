import pytest
from app.services.generation import generate_transactions
from app.risk_engine.features import engineer
from app.risk_engine.rules import evaluate
from app.risk_engine.scoring import score
import numpy as np


@pytest.fixture
def cohort():
    d = engineer(generate_transactions(500, 42))
    d["anomaly_score"] = np.linspace(0.1, 1, len(d))
    s = score(d, evaluate(d), d.anomaly_score.to_numpy())
    d["risk_score"] = s.risk_score
    return d
