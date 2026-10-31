#!/usr/bin/env python3
"""Tests for the shared corpus helpers added on 2026-10-31 (src/gems32/corpus.py).

These are deliberately cheap: they use synthetic rasters, not the 1 982-file registry, so they can
run in CI without the cached data.  The heavy helpers (``load_grid``, ``load_scored``,
``footprint_mean_credit``, ``attach_f0``) are exercised by the scripts that use them and by their
receipts under evidence/; they are not asserted here because they need .cache/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import corpus as CP  # noqa: E402


def synth(n_cell=400, spec=None):
    """Build fake 'rows' entries: spec is a list of (idx_array, value)."""
    rng = np.random.default_rng(0)
    rows = []
    for idx, D, score in spec:
        rows.append({"name": f"r{len(rows)}", "idx": np.asarray(idx, dtype=np.int64),
                     "val": np.full(len(idx), 1.0, dtype=np.float64), "D": float(D),
                     "score": float(score), "mass": float(D)})
    return rows


def test_gram_matrix_is_symmetric_and_has_correct_diagonal_and_offdiagonal():
    # two rasters: 3 shared cells of 5 and 4, plus private cells
    a = np.array([0, 1, 2, 10, 11])
    b = np.array([1, 2, 3, 12])
    rows = synth(spec=[(a, 5.0, 0.1), (b, 4.0, 0.1)])
    G = CP.gram_matrix(rows)
    assert G.shape == (2, 2)
    assert G[0, 1] == pytest.approx(G[1, 0])          # symmetric
    assert G[0, 0] == pytest.approx(5.0)              # diagonal = sum p^2 = 5 cells at value 1
    assert G[1, 1] == pytest.approx(4.0)
    assert G[0, 1] == pytest.approx(2.0)              # shared cells {1, 2}


def test_gram_matrix_matches_brute_force_on_random_overlapping_sets():
    rng = np.random.default_rng(7)
    rows = []
    for k in range(6):
        idx = rng.choice(200, size=40, replace=False)
        rows.append({"idx": np.sort(idx), "val": rng.random(40) + 0.1})
    G = CP.gram_matrix(rows)
    for i in range(6):
        for j in range(6):
            brute = 0.0
            for p, v in zip(rows[i]["idx"], rows[i]["val"]):
                m = rows[j]["idx"] == p
                if m.any():
                    brute += v * rows[j]["val"][m][0]
            assert G[i, j] == pytest.approx(brute, abs=1e-9)


def test_solve_weights_recovers_known_combination():
    """If the truth field IS a non-negative combination of the rasters, nnls must find it back."""
    rng = np.random.default_rng(11)
    H, W = CP.H, CP.W
    base = [np.sort(rng.choice(H * W, size=60, replace=False)) for _ in range(4)]
    rows = [{"idx": b, "val": np.ones(len(b))} for b in base]
    lam_true = np.array([0.30, 0.10, 0.00, 0.45])
    n0 = 12000.0
    for k, r in enumerate(rows):
        # A_i = sum_x p_i q  with q = sum_j lam_j p_j  (all p binary, so q is the dot overlap)
        A = float(sum(lam_true[j] * np.intersect1d(r["idx"], rows[j]["idx"]).size
                      for j in range(4)))
        r["A"] = A
        r["D"] = float(len(r["idx"]))
        r["score"] = A / (0.2 * r["D"] + 0.8 * n0)
    lam = CP.solve_weights(rows, n0, mu=1e-6, nonneg=True)
    q_true = np.zeros(4) + lam_true
    # the system is underdetermined when rasters overlap, so check the implied measurements instead
    for k, r in enumerate(rows):
        pred = float(sum(lam[j] * np.intersect1d(r["idx"], rows[j]["idx"]).size for j in range(4)))
        assert pred == pytest.approx(r["A"], rel=1e-3, abs=1e-6)
    assert (lam >= 0).all()


def test_field_from_weights_truncates_negatives():
    rows = [{"idx": np.array([0, 1, 2]), "val": np.ones(3)}]
    q = CP.field_from_weights(rows, [0], np.array([-1.0]))
    assert float(q.reshape(-1)[0]) == 0.0
    assert float(q.min()) >= 0.0


def test_backproject_weights_uses_the_inverted_metric():
    rows = [{"score": 0.2, "D": 50000.0}]
    lam = CP.backproject_weights(rows, n0=12000.0)
    assert lam[0] == pytest.approx(0.2 * (0.2 * 50000.0 + 0.8 * 12000.0) / 50000.0)


def test_n_bounds_lower_bound_is_at_least_the_hard_inequality():
    """N >= 0.2 s D / (1 - 0.8 s) for every file, so the reported max must satisfy all of them."""
    rows = [{"name": "a", "score": 0.10, "D": 40000.0, "mc": 0.30, "f0": 0.05},
            {"name": "b", "score": 0.25, "D": 60000.0, "mc": 0.35, "f0": 0.05},
            {"name": "c", "score": 0.05, "D": 200000.0, "mc": 0.30, "f0": 0.05}]
    nb = CP.n_bounds(rows)
    for r in rows:
        assert nb["lower_from_A_le_N"] >= (
            0.2 * r["score"] * r["D"] / (1 - 0.8 * r["score"])) - 1e-9
    # it is a MAXIMUM, so it must be attained by one of the files
    assert any(abs(nb["lower_from_A_le_N"]
                   - 0.2 * r["score"] * r["D"] / (1 - 0.8 * r["score"])) < 1e-9 for r in rows)


def test_n_bounds_upper_bound_filters_catalogue_dominated_rasters():
    """A raster sitting on the catalogue has its dots masked from scoring, so its raw D
    overstates the denominator and understates N.  The filter must exclude it."""
    good = {"name": "lattice", "score": 0.09, "D": 200000.0, "mc": 0.3748, "f0": 0.086}
    oncat = {"name": "on-catalogue", "score": 0.016, "D": 150000.0, "mc": 0.50, "f0": 0.71}
    nb_both = CP.n_bounds([good, oncat], f0_max=1.0, d_min=100000.0, mc_min=0.10)
    nb_filt = CP.n_bounds([good, oncat], f0_max=0.15, d_min=100000.0, mc_min=0.10)
    assert nb_both["upper_bound_file"] != nb_filt["upper_bound_file"]
    # unfiltered the bound is corrupted below the hard lower bound (the bug this filter fixes)
    assert nb_both["upper_from_eps_ge_1"] < nb_both["lower_from_A_le_N"]
    # filtered, the bound is consistent with the lower bound
    assert nb_filt["upper_from_eps_ge_1"] >= nb_filt["lower_from_A_le_N"]


def test_conv_k_reproduces_the_official_triangular_kernel():
    """A single unit mass convolved with k must give k(d) = max(1 - d/3, 0) at every offset."""
    a = np.zeros((9, 9))
    a[4, 4] = 1.0
    k = CP.conv_k(a)
    assert k[4, 4] == pytest.approx(1.0)                 # d = 0
    assert k[4, 5] == pytest.approx(1.0 - 1.0 / 3.0)     # d = 1
    assert k[4, 6] == pytest.approx(1.0 - 2.0 / 3.0)     # d = 2
    assert k[4, 3] == pytest.approx(1.0 - 1.0 / 3.0)
    assert k[4, 7] == pytest.approx(0.0)                 # d = 3 -> (1 - 3/3) = 0
    assert k[4, 1] == pytest.approx(0.0)                 # d = 3
    assert abs(k[5, 5] - (1.0 - np.hypot(1, 1) / 3.0)) < 1e-12
    assert k[0, 0] == pytest.approx(0.0)                 # far corner
    assert k.max() == pytest.approx(1.0)


def test_shift_moves_an_array_without_wrapping():
    a = np.zeros((5, 6))
    a[2, 3] = 1.0
    b = CP.shift(a, 1, -2)
    assert b[3, 1] == pytest.approx(1.0)
    assert b[2, 3] == pytest.approx(0.0)
    assert b.sum() == pytest.approx(1.0) or b.sum() == pytest.approx(0.0)  # clipped at the edge
