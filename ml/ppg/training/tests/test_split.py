import pandas as pd
from src.split_subjects import subject_split


def test_subjects_do_not_leak():
    rows = [{"subject_id": f"s{i}", "label": i % 3} for i in range(100) for _ in range(3)]
    df = pd.DataFrame(rows)
    split = subject_split(df)
    groups = {k: set(df.loc[v, "subject_id"]) for k, v in split.items()}
    assert groups["train"].isdisjoint(groups["validation"] | groups["test"])
    assert groups["validation"].isdisjoint(groups["test"])
