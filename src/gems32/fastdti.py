"""Fast exact distance-weighted Tversky evaluation for many rasters against one fixed truth.

The repository's :func:`gems32.metric.dti_binary` recomputes two full-grid Euclidean distance
transforms per call (~2-3 s at 3730x3292).  When many submissions are scored against the *same*
truth set, the truth-side transform can be built once and reused, and the prediction-side term
reduces to a gather.  This module does that, and is verified against ``gems32.metric.dti_binary``
in ``tests/test_fastdti_20261031.py``.

Definitions (page 967, https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):

    TP_w = Σ_{g∈G} max_{x: d(x,g) ≤ R} p(x)·k(d(x,g))
    FP_w = Σ_{x: p(x)>0} p(x)·[1 − max_{g∈G} k(d(x,g))]
    FN_w = |G| − TP_w
    DTI  = TP_w / (TP_w + α·FP_w + β·FN_w + ε),  α = 0.2, β = 0.8, k(d) = max(1 − d/R, 0), R = 3 px
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt

from . import metric as M

H, W = 3730, 3292

# kernel offsets with 0 < d < R
_OFF_DY = np.array([o[0] for o in M._OFFS], dtype=np.int64)
_OFF_DX = np.array([o[1] for o in M._OFFS], dtype=np.int64)
_OFF_K = np.array([o[2] for o in M._OFFS], dtype=np.float64)


@dataclass
class Truth:
    """A fixed truth set with its cached distance-to-truth field."""

    idx: np.ndarray          # flat indices of truth cells
    dist: np.ndarray         # (H*W,) float32 Euclidean distance to the nearest truth cell
    n: int

    @classmethod
    def from_mask(cls, mask: np.ndarray) -> "Truth":
        m = np.asarray(mask, bool).reshape(H, W)
        idx = np.flatnonzero(m.ravel())
        if idx.size == 0:
            dist = np.full(H * W, 1e9, np.float32)
        else:
            dist = distance_transform_edt(~m).astype(np.float32).reshape(-1)
        return cls(idx=idx, dist=dist, n=int(idx.size))


def dti_dots(dot_idx: np.ndarray, dot_val: np.ndarray, truth: Truth,
             alpha: float = M.ALPHA, beta: float = M.BETA) -> dict:
    """Exact DTI of a sparse submission (dot indices + values) against ``truth``."""
    if truth.n == 0:
        return dict(tp=0.0, fp=float(np.sum(dot_val)), fn=0.0, n_truth=0, dti=0.0, coverage=0.0)
    p = np.zeros(H * W, np.float64)
    if dot_idx.size:
        np.clip(dot_val, 0.0, 1.0, out=dot_val)
        p[dot_idx] = np.asarray(dot_val, dtype=np.float64)
    # truth-side: for every truth cell, the best p·k over the 29 in-kernel offsets
    ti = truth.idx
    ty, tx = ti // W, ti % W
    best = np.zeros(ti.size, dtype=np.float64)
    for dy, dx, kw in zip(_OFF_DY, _OFF_DX, _OFF_K):
        ny, nx = ty + dy, tx + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        flat = ny * W + nx
        v = np.zeros(ti.size, dtype=np.float64)
        v[ok] = p[flat[ok]] * kw
        np.maximum(best, v, out=best)
    tp = float(best.sum())
    fn = float(truth.n) - tp
    # prediction-side: each dot's unmatched mass
    if dot_idx.size:
        kmax = M.kernel(truth.dist[dot_idx].astype(np.float64))
        fp = float(np.sum(np.asarray(dot_val, dtype=np.float64) * (1.0 - kmax)))
    else:
        fp = 0.0
    dti = tp / (tp + alpha * fp + beta * fn + M.EPS)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=truth.n, dti=float(dti),
                coverage=tp / max(truth.n, 1))
