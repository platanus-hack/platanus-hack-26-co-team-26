"""Train only on a pre-built, provenance-audited NPZ split."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

from .model import build_tiny_tcn


def train(npz_path: Path, output: Path, seed: int = 20260822):
    tf.keras.utils.set_random_seed(seed)
    data = np.load(npz_path, allow_pickle=False)
    required = {"x_train", "y_train", "q_train", "x_val", "y_val", "q_val"}
    if not required <= set(data.files):
        raise ValueError(f"Missing arrays: {required - set(data.files)}")
    x_train = data["x_train"].astype(np.float32)
    x_val = data["x_val"].astype(np.float32)
    if x_train.shape[1:] != (450, 4) or x_val.shape[1:] != (450, 4):
        raise ValueError("Expected windows [N, 450, 4]")

    model = build_tiny_tcn()
    model.compile(
        optimizer=tf.keras.optimizers.AdamW(2e-3, weight_decay=1e-4),
        loss={
            "physiology_logits": tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
            "quality_probability": tf.keras.losses.BinaryCrossentropy(),
        },
        loss_weights={"physiology_logits": 1.0, "quality_probability": 0.35},
        metrics={
            "physiology_logits": [tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
            "quality_probability": [tf.keras.metrics.AUC(name="auc")],
        },
    )
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=12, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", patience=5, factor=0.4),
    ]
    history = model.fit(
        x_train,
        {"physiology_logits": data["y_train"], "quality_probability": data["q_train"]},
        validation_data=(x_val, {"physiology_logits": data["y_val"], "quality_probability": data["q_val"]}),
        batch_size=64,
        epochs=120,
        callbacks=callbacks,
        verbose=2,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    model.save(output)
    output.with_suffix(".history.json").write_text(json.dumps(history.history, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("dataset", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    train(a.dataset, a.output)
