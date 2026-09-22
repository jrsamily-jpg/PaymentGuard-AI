"""Decision metrics and money accounting; review is friction, never assumed prevention."""

from numpy.typing import ArrayLike
import numpy as np
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def evaluate_metrics(
    truth: ArrayLike,
    prediction: ArrayLike,
    amounts: ArrayLike,
    scores: ArrayLike | None = None,
    friction_cost: float = 8,
) -> dict[str, int | float | None]:
    """Compute explicit confusion counts, rates and distinct dollar exposure."""
    raw_truth, raw_prediction = np.asarray(truth), np.asarray(prediction)
    if (
        raw_truth.ndim != 1
        or raw_prediction.ndim != 1
        or not np.isin(raw_truth, [0, 1]).all()
        or not np.isin(raw_prediction, [0, 1]).all()
        or not np.isfinite(friction_cost)
        or friction_cost < 0
    ):
        raise ValueError("Labels must be binary and friction cost nonnegative")
    y = np.asarray(truth, dtype=bool)
    p = np.asarray(prediction, dtype=bool)
    a = np.asarray(amounts, dtype=float)
    if (
        a.ndim != 1
        or len(y) != len(p)
        or len(a) != len(y)
        or not np.isfinite(a).all()
        or (a < 0).any()
    ):
        raise ValueError("Invalid metric inputs")
    if scores is not None:
        continuous = np.asarray(scores, dtype=float)
        if (
            continuous.ndim != 1
            or len(continuous) != len(y)
            or not np.isfinite(continuous).all()
        ):
            raise ValueError("Invalid continuous scores")
    tn, fp, fn, tp = confusion_matrix(y, p, labels=[False, True]).ravel()
    return {
        "transactions": len(y),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(precision_score(y, p, zero_division=0)),
        "recall": float(recall_score(y, p, zero_division=0)),
        "f1": float(f1_score(y, p, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, scores))
        if scores is not None and len(np.unique(y)) == 2
        else None,
        "false_positive_rate": float(fp / max(1, fp + tn)),
        "false_negative_rate": float(fn / max(1, fn + tp)),
        "fraud_dollars_detected": round(float(a[y & p].sum()), 2),
        "fraud_dollars_missed": round(float(a[y & ~p].sum()), 2),
        "legitimate_dollars_blocked": round(float(a[~y & p].sum()), 2),
        "friction_cost": float(fp * friction_cost),
    }
