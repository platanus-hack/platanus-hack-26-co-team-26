"""Decision metrics, calibration error and group-bootstrap confidence intervals."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import balanced_accuracy_score, f1_score, confusion_matrix


def expected_calibration_error(y_true, probabilities, bins: int = 15) -> float:
    y_true = np.asarray(y_true)
    p = np.asarray(probabilities)
    confidence, prediction = p.max(axis=1), p.argmax(axis=1)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (confidence > lo) & (confidence <= hi)
        if mask.any():
            ece += mask.mean() * abs((prediction[mask] == y_true[mask]).mean() - confidence[mask].mean())
    return float(ece)


def metrics(y_true, probabilities) -> dict:
    pred = np.asarray(probabilities).argmax(axis=1)
    return {
        "balanced_accuracy": float(balanced_accuracy_score(y_true, pred)),
        "macro_f1": float(f1_score(y_true, pred, average="macro")),
        "ece": expected_calibration_error(y_true, probabilities),
        "confusion_matrix": confusion_matrix(y_true, pred).tolist(),
    }


def group_bootstrap(y_true, probabilities, subject_ids, repeats: int = 2000, seed: int = 20260822):
    y_true, probabilities, subject_ids = map(np.asarray, (y_true, probabilities, subject_ids))
    subjects = np.unique(subject_ids)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(repeats):
        chosen = rng.choice(subjects, size=len(subjects), replace=True)
        indices = np.concatenate([np.flatnonzero(subject_ids == s) for s in chosen])
        values.append(metrics(y_true[indices], probabilities[indices])["macro_f1"])
    return {"macro_f1_ci95": np.quantile(values, [0.025, 0.975]).tolist()}
