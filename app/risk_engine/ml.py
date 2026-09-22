"""Time-separated unsupervised fitting; training distribution calibrates anomaly percentiles."""

import numpy as np
import pandas as pd
from typing import Any
from sklearn.ensemble import IsolationForest
from app.risk_engine.features import FEATURES


def fit_anomaly(d: pd.DataFrame) -> tuple[np.ndarray, int, dict[str, Any]]:
    """Fit on the first 70% and score all rows against training percentiles."""
    split = int(len(d) * 0.70)
    x = d[FEATURES].to_numpy(float)
    model = IsolationForest(
        n_estimators=120,
        max_samples=min(2048, split),
        contamination="auto",
        random_state=42,
        n_jobs=1,
    )
    model.fit(x[:split])
    reference = np.sort(-model.score_samples(x[:split]))
    raw = -model.score_samples(x)
    percentile = np.searchsorted(reference, raw, side="right") / len(reference)
    return (
        percentile,
        split,
        {
            "algorithm": "IsolationForest",
            "trees": 120,
            "train_rows": split,
            "test_rows": len(d) - split,
            "features": FEATURES,
            "seed": 42,
        },
    )
