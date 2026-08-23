"""Reference numerical preprocessing for dataset construction and golden fixtures."""
from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d


def preprocess(timestamps_s, red, motion, target_hz: int = 30, seconds: int = 15):
    t = np.asarray(timestamps_s, dtype=np.float64)
    r = np.asarray(red, dtype=np.float32)
    m = np.asarray(motion, dtype=np.float32)
    if not (len(t) == len(r) == len(m)) or len(t) < target_hz * 5:
        raise ValueError("Invalid or insufficient input")
    order = np.argsort(t)
    t, r, m = t[order], r[order], m[order]
    unique = np.r_[True, np.diff(t) > 1e-6]
    t, r, m = t[unique], r[unique], m[unique]
    grid = t[0] + np.arange(target_hz * seconds) / target_hz
    if grid[-1] > t[-1]:
        raise ValueError("Insufficient duration for fixed window")
    r = interp1d(t, r, kind="linear")(grid).astype(np.float32)
    m = interp1d(t, m, kind="linear")(grid).astype(np.float32)

    radius = target_hz
    prefix = np.r_[0.0, np.cumsum(r, dtype=np.float64)]
    trend = np.empty_like(r)
    for i in range(len(r)):
        lo, hi = max(0, i - radius), min(len(r), i + radius + 1)
        trend[i] = (prefix[hi] - prefix[lo]) / (hi - lo)
    x = r - trend

    alpha = np.clip(1.0 - np.exp(-2.0 * np.pi * 4.0 / target_hz), 0.05, 0.95)
    for direction in (1, -1):
        seq = x if direction == 1 else x[::-1].copy()
        out = np.empty_like(seq); out[0] = seq[0]
        for i in range(1, len(seq)):
            out[i] = out[i - 1] + alpha * (seq[i] - out[i - 1])
        x = out if direction == 1 else out[::-1].copy()

    median = np.median(x)
    mad = max(float(np.median(np.abs(x - median))), 1e-6)
    x = np.clip((x - median) / (1.4826 * mad), -8, 8).astype(np.float32)
    d1 = np.r_[0.0, np.diff(x)].astype(np.float32)
    d2 = np.r_[0.0, np.diff(d1)].astype(np.float32)
    return np.stack([x, d1, d2, m], axis=-1)
