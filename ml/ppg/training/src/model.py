"""Tiny multi-task TCN. No trained weights are distributed with this handoff."""
from __future__ import annotations

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


def residual_block(x, channels: int, dilation: int):
    shortcut = x
    x = layers.SeparableConv1D(channels, 5, padding="same", dilation_rate=dilation)(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("swish")(x)
    x = layers.SpatialDropout1D(0.08)(x)
    x = layers.SeparableConv1D(channels, 3, padding="same", dilation_rate=dilation)(x)
    x = layers.BatchNormalization()(x)
    if shortcut.shape[-1] != channels:
        shortcut = layers.Conv1D(channels, 1, padding="same")(shortcut)
    return layers.Activation("swish")(layers.Add()([x, shortcut]))


def build_tiny_tcn(samples: int = 450, channels: int = 4, classes: int = 6) -> keras.Model:
    inputs = keras.Input((samples, channels), name="ppg_features")
    x = layers.SeparableConv1D(24, 7, padding="same", name="stem")(inputs)
    x = residual_block(x, 24, 1)
    x = residual_block(x, 32, 2)
    x = residual_block(x, 48, 4)
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(32, activation="swish")(x)
    physiology = layers.Dense(classes, name="physiology_logits")(x)
    quality = layers.Dense(1, activation="sigmoid", name="quality_probability")(x)
    model = keras.Model(inputs, {"physiology_logits": physiology, "quality_probability": quality})
    if model.count_params() >= 100_000:
        raise AssertionError(f"Model too large: {model.count_params()} parameters")
    return model


if __name__ == "__main__":
    model = build_tiny_tcn()
    model.summary()
