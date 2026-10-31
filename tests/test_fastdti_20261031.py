"""Verify src/gems32/fastdti.py against the repo's verified exact metric."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import fastdti, metric  # noqa: E402


def test_fastdti_matches_dti_binary_on_random_fields():
    rng = np.random.default_rng(20261031)
    H, W = fastdti.H, fastdti.W
    for trial in range(3):
        truth = np.zeros(H * W, bool)
        # a few short fault-like segments
        for _ in range(40):
            y = int(rng.integers(5, H - 5))
            x = int(rng.integers(5, W - 5))
            dy = int(rng.integers(-1, 2))
            dx = int(rng.integers(-1, 2))
            L = int(rng.integers(5, 60))
            for k in range(L):
                yy = np.clip(y + dy * k, 0, H - 1)
                xx = np.clip(x + dx * k, 0, W - 1)
                truth[yy * W + xx] = True
        pred_idx = rng.choice(H * W, size=20000, replace=False)
        pred_val = rng.random(pred_idx.size).astype(np.float32)
        pred_full = np.zeros(H * W, np.float32)
        pred_full[pred_idx] = pred_val

        # soft predictions -> compare against dti_exact (dti_binary binarises, so it is
        # checked separately below)
        ref = metric.dti_exact(pred_full.reshape(H, W), truth.reshape(H, W).astype(np.float32))
        t = fastdti.Truth.from_mask(truth)
        got = fastdti.dti_dots(pred_idx, pred_val.copy(), t)
        assert abs(ref["tp"] - got["tp"]) < 1e-5, (ref["tp"], got["tp"])
        assert abs(ref["fp"] - got["fp"]) < 1e-5, (ref["fp"], got["fp"])
        assert abs(ref["fn"] - got["fn"]) < 1e-6
        assert abs(ref["dti"] - got["dti"]) < 1e-6, (ref["dti"], got["dti"])


def test_fastdti_reproduces_official_worked_example_scaling():
    """The published example (TP 3.00, FP 1.89, FN 2.00 -> 0.60) is reproduced by the metric
    module; fastdti must agree with that module on the same numbers."""
    H, W = fastdti.H, fastdti.W
    truth = np.zeros(H * W, bool)
    base = (H // 2) * W + (W // 2)
    for k in range(5):                       # vertical 5-px truth line
        truth[base + k * W] = True
    pred_idx = np.array([base - W, base, base + W, base + 3 * W], dtype=np.int64)
    pred_val = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
    pred_full = np.zeros(H * W, np.float32)
    pred_full[pred_idx] = pred_val
    ref = metric.dti_exact(pred_full.reshape(H, W), truth.reshape(H, W).astype(np.float32))
    t = fastdti.Truth.from_mask(truth)
    got = fastdti.dti_dots(pred_idx, pred_val.copy(), t)
    assert abs(ref["tp"] - got["tp"]) < 1e-5
    assert abs(ref["dti"] - got["dti"]) < 1e-7


def test_fastdti_matches_dti_binary_when_prediction_is_binary():
    rng = np.random.default_rng(7)
    H, W = fastdti.H, fastdti.W
    truth = np.zeros(H * W, bool)
    for _ in range(30):
        y = int(rng.integers(5, H - 5)); x = int(rng.integers(5, W - 5))
        for k in range(int(rng.integers(5, 80))):
            yy = np.clip(y + k, 0, H - 1); xx = np.clip(x, 0, W - 1)
            truth[yy * W + xx] = True
    pred_idx = rng.choice(H * W, size=15000, replace=False)
    pred_val = np.ones(pred_idx.size, dtype=np.float32)
    pred_full = np.zeros(H * W, np.float32)
    pred_full[pred_idx] = pred_val
    ref = metric.dti_binary(pred_full.reshape(H, W), truth.reshape(H, W))
    t = fastdti.Truth.from_mask(truth)
    got = fastdti.dti_dots(pred_idx, pred_val.copy(), t)
    assert abs(ref["tp"] - got["tp"]) < 1e-9
    assert abs(ref["fp"] - got["fp"]) < 1e-6
    assert abs(ref["dti"] - got["dti"]) < 1e-9
