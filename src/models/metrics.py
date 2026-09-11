"""Classification and confidence/OOD metric helpers."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)


def classification_metrics(y_true, y_pred, labels=None) -> dict:
    macro = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    weighted = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(macro[0]),
        "macro_recall": float(macro[1]),
        "macro_f1": float(macro[2]),
        "weighted_f1": float(weighted[2]),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def ood_metrics(is_ood, ood_scores) -> dict:
    """Evaluate calibrated OOD scores; higher score must mean more OOD-like."""
    y = np.asarray(is_ood, dtype=int)
    score = np.asarray(ood_scores, dtype=float)
    if len(np.unique(y)) != 2:
        raise ValueError("OOD metrics require both in-domain and OOD examples")
    fpr, tpr, _ = roc_curve(y, score)
    eligible = np.where(tpr >= 0.95)[0]
    fpr95 = float(fpr[eligible[0]]) if len(eligible) else 1.0
    return {
        "auroc": float(roc_auc_score(y, score)),
        "aupr": float(average_precision_score(y, score)),
        "fpr95": fpr95,
    }
