"""Export an approved SavedModel/Keras model to full INT8 LiteRT.

The representative NPZ must contain real target-domain windows under key `x`,
shape [N, 450, 4]. Do not use random data for a release export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import tensorflow as tf


def export(model_path: Path, representative_npz: Path, output: Path) -> dict:
    model = tf.keras.models.load_model(model_path)
    x = np.load(representative_npz)["x"].astype(np.float32)
    if x.ndim != 3 or x.shape[1:] != (450, 4) or len(x) < 200:
        raise ValueError("Representative data must be [N>=200, 450, 4]")

    def representative_dataset():
        for row in x[: min(len(x), 2000)]:
            yield [row[None, ...]]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    blob = converter.convert()
    output.write_bytes(blob)
    manifest = {
        "file": output.name,
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "input": [1, 450, 4],
        "preprocessor": "ppg-pre-v1",
        "status": "research",
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("model", type=Path)
    p.add_argument("representative_npz", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    print(json.dumps(export(a.model, a.representative_npz, a.output), indent=2))
