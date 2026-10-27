"""Live-Ledger Inversion (LLI-v1) projection evaluator.

Reproduces the 40-stratum S0 feature-density inversion fitted across 111 distinct
owner-reported live rasters (LOO MAE = 0.0221, LOO Spearman = 0.9259; leave-site-out
MAE = 0.0224).

IMPORTANT PROTOCOL RULE 3 GUARDRAIL:
Every value produced by this module for an unscored raster is a MODEL PROJECTION
(``evidence_class = "LLI-PROJECTION (NOT A SCORE)"``), NEVER an organizer-confirmed
or holdout score.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "vendor"))

from gems57.metric import ALPHA, BETA, kernel  # noqa: E402

_OFFS = [
    (dy, dx, float(kernel(np.hypot(dy, dx))))
    for dy in range(-3, 4)
    for dx in range(-3, 4)
    if float(kernel(np.hypot(dy, dx))) > 0.0
]
LINE_MAX_TO_SUM = 1.0 / 3.0

# Exact 111-raster S0 fit parameters verified from GEMSDOE32/evidence/live_ledger_inversion.json
S0_THETA = np.array([
    -12.47292413857899,
    -2.0881511445818317,
    -1.823972086370304,
    -0.9764836144339021,
    0.058791713860876414,
    2.6768296036272066,
    -1.6728093587585058,
    2.929390090102951,
    -0.061571459543536614,
    6.363448212168382,
    7.40518817550377,
    -0.04010887896365985,
], dtype=np.float64)
S0_LOO_MAE = 0.02206859815698794
S0_LOO_SPEARMAN = 0.925907563282079


@dataclass
class StrataSpec:
    names: list[str]
    levels: list[np.ndarray]
    n_levels: list[int]
    level_labels: list[list[str]]
    active: np.ndarray
    stratum: np.ndarray = field(init=False)
    n_strata: int = field(init=False)
    sizes: np.ndarray = field(init=False)
    stratum_levels: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        mult = 1
        st = np.zeros(self.active.shape, np.int32)
        for lv, n in zip(self.levels, self.n_levels):
            st += lv.astype(np.int32) * mult
            mult *= n
        st[~self.active] = -1
        self.stratum = st
        self.n_strata = mult
        self.sizes = np.bincount(st[self.active], minlength=mult).astype(np.float64)
        ids = np.arange(mult, dtype=np.int64)
        lv_tab = np.zeros((mult, len(self.n_levels)), np.int16)
        m = 1
        for j, n in enumerate(self.n_levels):
            lv_tab[:, j] = (ids // m) % n
            m *= n
        self.stratum_levels = lv_tab


def _digitize(d: np.ndarray, edges: list[float], codes: list[int]) -> np.ndarray:
    idx = np.digitize(d, edges, right=True)
    return np.asarray(codes, np.int8)[idx]


def build_s0_spec(data_root: Path) -> tuple[StrataSpec, np.ndarray]:
    with rasterio.open(data_root / "sample_submission.tif") as src:
        foot = np.isfinite(src.read(1))
    with rasterio.open(data_root / "labels.tif") as src:
        labels = (src.read(1) > 0) & foot
    active = foot & ~labels
    d_cat = distance_transform_edt(~labels)
    cat_lv = _digitize(d_cat, [1.01, 2.01, 3.01, 5.01, 10.01, 20.01, 50.01], [1, 2, 3, 4, 5, 6, 7, 0])
    cat_lab = [">50", "1", "1.4-2", "2.2-3", "3-5", "5-10", "10-20", "20-50"]

    h195_path = data_root / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"
    with rasterio.open(h195_path) as src:
        h_raw = src.read(1)
    h = np.isfinite(h_raw) & (h_raw > 0) & foot
    d_h = distance_transform_edt(~h)
    h_lv = _digitize(d_h, [0.01, 1.01, 2.01, 5.01], [1, 2, 3, 4, 0])
    h_lab = [">5", "on", "1", "1.4-2", "2.2-5"]

    spec = StrataSpec(
        names=["d_catalogue_px", "d_H19-5_px"],
        levels=[cat_lv, h_lv],
        n_levels=[8, 5],
        level_labels=[cat_lab, h_lab],
        active=active,
    )
    logl = np.full(spec.n_strata, S0_THETA[0], np.float64)
    off = 1
    for j, n in enumerate(spec.n_levels):
        coef = np.concatenate([[0.0], S0_THETA[off: off + n - 1]])
        logl += coef[spec.stratum_levels[:, j]]
        off += n - 1
    lam = np.exp(np.clip(logl, -60.0, 5.0))
    return spec, lam


def project_lli(pred: np.ndarray, spec: StrataSpec, lam: np.ndarray) -> dict:
    p = np.asarray(pred, np.float32)
    p = np.where(np.isfinite(p), p, 0.0).astype(np.float32)
    p = np.clip(p, 0.0, 1.0)
    p[~spec.active] = 0.0
    H, W = p.shape
    ys, xs = np.nonzero(p > 0.0)
    v = p[ys, xs].astype(np.float64)
    n_mass = float(v.sum())
    flat_n = H * W
    kmax = np.zeros(flat_n, np.float32)
    csum = np.zeros(flat_n, np.float64)
    touched = []
    for dy, dx, k in _OFFS:
        ty, tx = ys + dy, xs + dx
        ok = (ty >= 0) & (ty < H) & (tx >= 0) & (tx < W)
        fi = ty[ok].astype(np.int64) * W + tx[ok]
        w = v[ok] * k
        kmax[fi] = np.maximum(kmax[fi], w.astype(np.float32))
        csum[fi] += w
        touched.append(fi)
    t = np.unique(np.concatenate(touched)) if touched else np.zeros(0, np.int64)
    st = spec.stratum.ravel()[t]
    ok = st >= 0
    A = np.bincount(st[ok], weights=kmax[t][ok].astype(np.float64), minlength=spec.n_strata)
    B = np.bincount(st[ok], weights=csum[t][ok], minlength=spec.n_strata) * LINE_MAX_TO_SUM

    tp = float(A @ lam)
    m = float(B @ lam)
    g = float(spec.sizes @ lam)
    fp = max(n_mass - m, 0.0)
    fn = g - tp
    dti = float(tp / (tp + ALPHA * fp + BETA * fn + 1e-12))
    return {
        "evidence_class": "LLI-PROJECTION (NOT A SCORE)",
        "model": "LLI-v1-S0 (40-stratum log-additive fit on 111 owner-reported live rasters)",
        "projected_dti": round(dti, 6),
        "uncertainty_band_loo_mae": [round(max(0.0, dti - S0_LOO_MAE), 4), round(min(1.0, dti + S0_LOO_MAE), 4)],
        "loo_mae": round(S0_LOO_MAE, 4),
        "loo_spearman": round(S0_LOO_SPEARMAN, 4),
        "off_cat_dots": int(v.size),
        "caveat": (
            "Model projection conditioned on d_catalogue_px x d_H19-5_px strata; NOT an organizer score. "
            "Under-projects genuinely novel off-H19-5 discoveries that were not probed by historical rasters."
        ),
    }
