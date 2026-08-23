"""Compact PPG-to-estimated-ECG student model for on-device distillation."""
from __future__ import annotations

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


def block(x, channels: int, dilation: int):
    skip = x
    x = layers.SeparableConv1D(channels, 5, padding="same", dilation_rate=dilation)(x)
    x = layers.LayerNormalization()(x)
    x = layers.Activation("swish")(x)
    x = layers.SeparableConv1D(channels, 3, padding="same", dilation_rate=dilation)(x)
    if skip.shape[-1] != channels:
        skip = layers.Conv1D(channels, 1, padding="same")(skip)
    return layers.Activation("swish")(layers.Add()([x, skip]))


def build_ecg_student(samples: int = 1800, channels: int = 5) -> keras.Model:
    inputs = keras.Input((samples, channels), name="ppg_120hz")
    x = layers.SeparableConv1D(24, 9, padding="same")(inputs)
    for width, dilation in ((24, 1), (32, 2), (40, 4), (48, 8), (48, 16)):
        x = block(x, width, dilation)
    x = layers.SeparableConv1D(32, 7, padding="same", activation="swish")(x)
    mean = layers.Conv1D(1, 1, name="estimated_ecg_mean")(x)
    logvar = layers.Conv1D(1, 1, activation="tanh", name="estimated_ecg_logvar")(x)
    quality = layers.GlobalAveragePooling1D()(x)
    quality = layers.Dense(1, activation="sigmoid", name="reconstruction_quality")(quality)
    model = keras.Model(inputs, {
        "estimated_ecg_mean": mean,
        "estimated_ecg_logvar": logvar,
        "reconstruction_quality": quality,
    })
    if model.count_params() >= 250_000:
        raise AssertionError(f"ECG student too large: {model.count_params()}")
    return model


if __name__ == "__main__":
    build_ecg_student().summary()
