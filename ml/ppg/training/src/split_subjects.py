"""Leakage-safe subject split with explicit disjointness checks."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


def subject_split(meta: pd.DataFrame, seed: int = 20260822):
    required = {"subject_id", "label"}
    if not required <= set(meta.columns):
        raise ValueError(f"Missing columns: {required - set(meta.columns)}")
    first = GroupShuffleSplit(1, train_size=0.70, random_state=seed)
    train_i, rest_i = next(first.split(meta, meta.label, groups=meta.subject_id))
    rest = meta.iloc[rest_i]
    second = GroupShuffleSplit(1, train_size=0.50, random_state=seed + 1)
    val_rel, test_rel = next(second.split(rest, rest.label, groups=rest.subject_id))
    splits = {
        "train": meta.iloc[train_i].index.to_numpy(),
        "validation": rest.iloc[val_rel].index.to_numpy(),
        "test": rest.iloc[test_rel].index.to_numpy(),
    }
    subjects = {k: set(meta.loc[v, "subject_id"]) for k, v in splits.items()}
    assert subjects["train"].isdisjoint(subjects["validation"])
    assert subjects["train"].isdisjoint(subjects["test"])
    assert subjects["validation"].isdisjoint(subjects["test"])
    return splits
