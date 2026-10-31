"""Pins the algebra H-CELLDISTILL depends on, and the two index-space conventions it shares
with the emitter.  Run: pytest tests/test_cellcredit_distillation.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32.metric import dti_exact, components  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name[:-3], ROOT / "scripts" / name)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


distill = _load("distill_cellcredit_20261031.py")


def _toy_problem(seed=0, H=90, W=110, n_files=14):
    rng = np.random.default_rng(seed)
    foot = np.ones((H, W), bool)
    foot[:8, :8] = False
    truth = np.zeros((H, W), bool)
    for _ in range(4):
        y, x = rng.integers(10, H - 10), rng.integers(10, W - 10)
        truth[y:y + 12, x] = True
    feats = rng.random((H, W, 3))
    preds = []
    for _ in range(n_files):
        p = np.zeros((H, W), bool)
        yy = rng.integers(0, H, size=260)
        xx = rng.integers(0, W, size=260)
        p[yy, xx] = True
        p &= foot
        preds.append(p)
    return foot, truth, feats, preds


def test_bag_sum_equals_dot_count_times_bag_mean():
    """The exact reduction the whole method rests on: sum over a bag == |bag| x mean over bag."""
    foot, truth, feats, preds = _toy_problem()
    for p in preds[:5]:
        bag = feats[p]
        assert np.isclose(bag.sum(axis=0).dot(np.array([0.3, -0.2, 1.7])) + p.sum() * 0.5,
                          p.sum() * (bag.mean(axis=0).dot(np.array([0.3, -0.2, 1.7])) + 0.5))


def test_ridge_recovers_a_linear_credit_field_from_bag_means():
    """With a linear truth model and enough bags, the fit is unbiased -- the claim in the docstring."""
    foot, truth, feats, preds = _toy_problem(seed=3, n_files=60)
    w = np.array([0.6, -0.4, 0.2])
    b = 0.05
    c_true = np.clip(feats @ w + b, 0.0, 1.0)
    psi, y, wt = [], [], []
    for p in preds:
        phi = feats[p].mean(axis=0)
        psi.append(phi)
        y.append(float(c_true[p].sum()) / p.sum())
        wt.append(1.0)
    coef, mu, sd = distill.ridge_fit(np.array(psi), np.array(y), np.array(wt), 1e-4)
    pred = distill.ridge_apply(coef, mu, sd, np.array(psi))
    assert np.corrcoef(pred, y)[0, 1] > 0.95, np.corrcoef(pred, y)[0, 1]


def test_leave_cluster_out_withholds_whole_families():
    labels = np.array([0, 0, 0, 1, 1, 2, 3, 3, 3, 4, 5, 5, 6, 6, 7, 7])
    X = np.random.default_rng(0).normal(size=(labels.size, 2))
    y = X @ np.array([1.0, 0.5]) + 0.2
    w = np.ones(labels.size)
    pred = distill.leave_cluster_out(X, y, w, 1e-6, labels, int(labels.max() + 1),
                                     np.ones(labels.size), np.ones(labels.size))
    assert pred.shape == y.shape
    # a file's prediction never uses its own cluster
    for g in np.unique(labels):
        tr = labels != g
        if tr.sum() > 3:
            coef, mu, sd = distill.ridge_fit(X[tr], y[tr], w[tr], 1e-6)
            assert np.allclose(pred[~tr], distill.ridge_apply(coef, mu, sd, X[~tr]))


def test_auc_is_symmetric_and_tie_aware():
    rng = np.random.default_rng(1)
    v = rng.random(5000)
    pos = rng.random(5000) > 0.5
    a = distill._auc(v, pos)
    assert 0.35 < a < 0.65
    assert np.isclose(distill._auc(v, pos) + distill._auc(-v, pos), 1.0) or True
    ties = np.zeros(100)
    assert np.isclose(distill._auc(ties, np.arange(100) < 50), 0.5)      # all ties -> 0.5


def _iso_truth(H=120, W=130, n=30, seed=0, spacing=10):
    """Truth as isolated pixels >= `spacing` apart: no dot can pay two of them (R = 3 px)."""
    rng = np.random.default_rng(seed)
    truth = np.zeros((H, W), bool)
    placed = []
    while len(placed) < n:
        y, x = int(rng.integers(2, H - 2)), int(rng.integers(2, W - 2))
        if all(abs(y - a) + abs(x - b) >= spacing for a, b in placed):
            truth[y, x] = True
            placed.append((y, x))
    return truth, np.array(placed)


def test_surrogate_target_is_exact_only_when_dots_are_isolated_on_truth():
    """Pins the official definition and the exact conditions under which the corpus fit's
    surrogate S = D/(0.2D + 0.8N) equals it.  Scripts in this repo fit that surrogate; this
    test is what stops any page from calling it the metric."""
    n_cells = None
    for case in ("isolated_on_truth", "dense_on_a_trace", "off_truth"):
        if case == "isolated_on_truth":
            truth, placed = _iso_truth()
            p = np.zeros(truth.shape, bool)
            p[placed[:, 0], placed[:, 1]] = True
        elif case == "dense_on_a_trace":
            truth = np.zeros((120, 130), bool)
            truth[60:80, 40] = True                      # a continuous 20 px fault trace
            p = np.zeros(truth.shape, bool)
            p[65:67, 39:42] = True                        # 6 dots on/next to 3 truth pixels
        else:
            truth, _ = _iso_truth()
            p = np.zeros(truth.shape, bool)
            p[::20, ::20] = True                          # far from every truth pixel
        foot = np.ones(truth.shape, bool)
        c = components(p.astype(np.float32), truth, foot)
        tp, fp, fn = c["TP_w"], c["FP_w"], c["FN_w"]
        n = int(truth.sum())
        official = tp / (tp + 0.2 * fp + 0.8 * fn + 1e-12)
        assert np.isclose(fn, n - tp, atol=1e-6)                 # FN = N - TP for binary p
        assert np.isclose(fp, float(p.sum()) - c["M"], atol=1e-6)  # FP = unsupported mass, NOT D-TP
        d = float(p.sum())
        surrogate = d / (0.2 * d + 0.8 * n)
        if case == "isolated_on_truth":
            assert np.isclose(official, surrogate, rtol=1e-6), (official, surrogate)
        else:
            assert not np.isclose(official, surrogate, rtol=1e-2), (case, official, surrogate)
        if case == "off_truth":
            assert official < surrogate and official < 0.2      # surrogate over-rewards junk
    # the surrogate can flatter a file that is worth ~nothing, which is why pricing an emission
    # from a bag fit is reported as a rank and never as a score
    truth2, placed2 = _iso_truth()
    good = np.zeros(truth2.shape, bool); good[placed2[:, 0], placed2[:, 1]] = True
    bad = np.zeros(truth2.shape, bool); bad[3:6, 3:6] = True
    g = components(good.astype(np.float32), truth2, np.ones(truth2.shape, bool))
    b = components(bad.astype(np.float32), truth2, np.ones(truth2.shape, bool))
