"""Verify the repo's DTI implementation against the official DrivenData worked example.

Source: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric
Worked example: TP_w = 3.00, FP_w = 1.89, FN_w = 2.00 -> TI_w(alpha=0.2, beta=0.8) = 0.60
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32.metric import ALPHA, BETA, RADIUS_PX, dti_binary, dti_bruteforce, dti_exact, kernel  # noqa: E402


def test_constants_match_official_rules():
    assert ALPHA == 0.2
    assert BETA == 0.8
    assert RADIUS_PX == 3.0


def test_official_worked_example_formula():
    tp, fp, fn = 3.00, 1.89, 2.00
    ti = tp / (tp + ALPHA * fp + BETA * fn)
    assert round(ti, 2) == 0.60


def test_triangular_kernel_values():
    assert float(kernel(0.0)) == 1.0
    assert abs(float(kernel(1.5)) - 0.5) < 1e-12
    assert float(kernel(3.0)) == 0.0
    assert float(kernel(4.0)) == 0.0


def test_three_implementations_agree_on_binary_predictions():
    rng = np.random.default_rng(1)
    for _ in range(3):
        truth = rng.random((30, 30)) < 0.03
        pred = rng.random((30, 30)) < 0.05
        a = dti_bruteforce(pred.astype(float), truth)["dti"]
        b = dti_exact(pred.astype(float), truth)["dti"]
        c = dti_binary(pred, truth)["dti"]
        assert abs(a - b) < 1e-9 and abs(b - c) < 1e-9
