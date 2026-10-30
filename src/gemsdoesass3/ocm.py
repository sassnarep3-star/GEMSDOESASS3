"""Orientation-Coherent Multi-physics lineament surface (OCM) - SASS3 lane.

Mechanism (the part that is NOT another magnitude-thresholded ridge map)
------------------------------------------------------------------------
A Quaternary fault that the USGS/INGENIOUS catalogue missed has to break several
independent physical fields *along the same strike*: the magnetic field (offset of
a susceptibility boundary), the isostatic gravity field (offset of a density
boundary), the detrended elevation (a scarp or a warped surface), and the depth to
basement (a vertical offset of the cover thickness).  A lithological contact that
is not a fault is usually expressed in only one or two of those fields and its
gradients are not collinear with the others.

So the surface is built from the *consensus orientation* of the structure tensors
of four potential/level fields, not from the sum of their magnitudes:

    T(x) = sum_i w_i * J_i(x) / trace(J_i(x)),   J_i = G_sigma * (grad I_i grad I_i^T)

For each band i the (smoothed) structure tensor J_i has eigenvalues lambda1 >=
lambda2; anisotropy is (lambda1 - lambda2) / (lambda1 + lambda2) in [0, 1] and the
dominant eigenvector is the local gradient (ridge-normal) direction.  The summed
tensor T gives a consensus normal N.  Two scores are read off the consensus:

* ``coh``  - anisotropy of T: how line-like the local fabric is (isotropic blobs
  score 0, a single straight edge scores 1).
* ``agree`` - mean cos^2 of the angle between each band's own normal and N, weighted
  by that band's edge energy: how many *independent* physical fields agree on that
  same orientation (this is the discriminating statistic: it is invariant to the
  amplitude of any single field).

``S = ridge_energy * coh * agree`` is then enhanced with a scarp term from the LiDAR
morphometry stack (vertical ``step_max`` and the up-facing/down-facing asymmetry),
because the new-fault labels are surface-expression mappings.

Everything is computed from files restored and SHA-pinned by
``scripts/restore_data.py`` (see ``registry/data_manifest.json``); no new external
data is required.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, distance_transform_edt, binary_dilation

# Band indices (1-based) inside training_features.tif, verified against the band
# descriptions carried in the restored file itself (see scripts/prepare_data.py notes).
LEVEL_BANDS = {
    "tmi": 14,               # Total magnetic intensity
    "iso_grav": 13,          # Isostatic gravity anomaly
    "det_elev": 12,          # Detrended elevation
    "depth_base": 15,        # Depth to basement surface
}
EDGE_BANDS = {
    "tmi_hg": 3,
    "tmi_vg": 9,
    "grav_slope": 5,
    "grav_vg": 11,
    "geod_shearrate": 7,
    "geod_dilaterate": 8,
    "geod_2ndinv": 4,
    "det_elev_slope": 19,
}
LIDAR_BANDS = {  # external/lidar_scarp_features_u8.tif, uint8 0-255
    "step_max": 3,
    "ex_max": 1,
    "lapneg_max": 4,
    "downface_max": 6,
    "upface_max": 7,
    "coh100": 10,
    "relief": 9,
    "valid": 12,
}


def _sanitize(a: np.ndarray, nodata: float | None) -> np.ndarray:
    """Replace the file's nodata sentinel and any non-finite value with NaN."""
    a = a.astype(np.float32)
    if nodata is not None and np.isfinite(nodata):
        a[np.abs(a - np.float32(nodata)) < max(1e-20, abs(np.float32(nodata)) * 1e-6)] = np.nan
    a[~np.isfinite(a)] = np.nan
    return a


def load_fields(ddir: Path, sigma_px: float = 2.0) -> dict[str, np.ndarray]:
    """Return the raw float32 fields needed by the surface (NaN where invalid)."""
    feats = ddir / "training_features.tif"
    out: dict[str, np.ndarray] = {}
    with rasterio.open(feats) as ds:
        for name, idx in {**LEVEL_BANDS, **EDGE_BANDS}.items():
            out[name] = _sanitize(ds.read(idx), ds.nodatavals[idx - 1])
    lid = ddir / "external" / "lidar_scarp_features_u8.tif"
    with rasterio.open(lid) as ds:
        for name, idx in LIDAR_BANDS.items():
            out["lidar_" + name] = ds.read(idx).astype(np.float32)
    return out


def _norm01(a: np.ndarray, q: float = 99.0) -> np.ndarray:
    v = a[np.isfinite(a)]
    if v.size == 0:
        return np.zeros_like(a)
    hi = float(np.percentile(v, q))
    lo = float(np.percentile(v, 100.0 - q))
    if not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(a)
    return np.clip((np.nan_to_num(a, nan=lo) - lo) / (hi - lo), 0.0, 1.0)


def structure_tensor(img: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Smoothed structure tensor of a float32 field.

    Returns (a, b, c, mag2) with a=gx^2, b=gx*gy, c=gy^2 smoothed by ``sigma`` and
    ``mag2`` the smoothed squared gradient magnitude.  Central differences at 1 px.
    """
    x = np.nan_to_num(img, nan=0.0).astype(np.float32)
    gy = np.zeros_like(x)
    gx = np.zeros_like(x)
    np.subtract(x[2:, 1:-1], x[:-2, 1:-1], out=gy[1:-1, 1:-1], dtype=np.float32)  # d/dy
    np.subtract(x[1:-1, 2:], x[1:-1, :-2], out=gx[1:-1, 1:-1], dtype=np.float32)   # d/dx
    gy *= 0.5
    gx *= 0.5
    if sigma > 0:
        gx = gaussian_filter(gx, sigma, mode="nearest")
        gy = gaussian_filter(gy, sigma, mode="nearest")
    a = gaussian_filter(gx * gx, sigma, mode="nearest")
    b = gaussian_filter(gx * gy, sigma, mode="nearest")
    c = gaussian_filter(gy * gy, sigma, mode="nearest")
    return a, b, c, (a + c)


def ocm_surface(ddir: Path, sigma_px: float = 2.0, scarp_gain: float = 0.6) -> dict[str, np.ndarray]:
    """Build the orientation-coherent multi-physics surface.

    Keys: ``S`` (float32 prospectivity in [0,1]), ``coh``, ``agree``, ``energy``,
    ``ridge_dir`` (float32 azimuth in radians mod pi), ``scarp``.
    """
    f = load_fields(ddir)
    wsum = np.zeros(f["tmi"].shape, np.float32)
    aa = np.zeros_like(wsum)
    bb = np.zeros_like(wsum)
    cc = np.zeros_like(wsum)
    energy = np.zeros_like(wsum)
    norm_a = np.zeros_like(wsum)
    norm_b = np.zeros_like(wsum)
    wtot = np.zeros_like(wsum)
    for name in LEVEL_BANDS:
        img = f[name]
        a, b, c, mag2 = structure_tensor(img, sigma_px)
        tr = mag2 + 1e-12
        aa += a / tr
        bb += b / tr
        cc += c / tr
        wsum += np.ones_like(tr)
        energy += _norm01(np.sqrt(mag2))
        # per-band dominant normal (unnormalised eigen-direction proxy)
        t = 0.5 * np.arctan2(2.0 * b, a - c)
        norm_a += np.cos(2.0 * t)
        norm_b += np.sin(2.0 * t)
        wtot += 1.0
    aa /= wsum
    bb /= wsum
    cc /= wsum
    energy /= len(LEVEL_BANDS)

    tr = aa + cc + 1e-12
    det = aa * cc - bb * bb
    disc = np.sqrt(np.maximum(0.25 * (aa - cc) ** 2 + bb * bb, 0.0))
    l1 = 0.5 * tr + disc
    l2 = 0.5 * tr - disc
    coh = np.clip((l1 - l2) / (l1 + l2 + 1e-12), 0.0, 1.0).astype(np.float32)
    # consensus normal angle (mod pi) -> stored as 2theta
    th2 = np.arctan2(2.0 * bb, aa - cc)
    ridge_dir = (0.5 * th2 + 0.5 * np.pi) % np.pi  # gradient normal; ridge strike = normal + 90 deg
    # agreement: mean cos^2 between each band's normal and the consensus normal
    agree = (0.5 + 0.5 * np.cos(th2 - np.arctan2(2.0 * norm_b / wtot, norm_a / wtot))).astype(np.float32)

    step = _norm01(f["lidar_step_max"])
    asym = _norm01(np.abs(f["lidar_upface_max"] - f["lidar_downface_max"]))
    valid = f["lidar_valid"] > 0
    scarp = np.where(valid, np.maximum(step, 0.5 * (step + asym)), 0.0).astype(np.float32)

    e = _norm01(energy)
    S = (e ** 0.5 * coh * agree * (1.0 + scarp_gain * scarp)).astype(np.float32)
    S = np.clip(S, 0.0, 1.0).astype(np.float32)
    return {"S": S, "coh": coh, "agree": agree, "energy": e, "ridge_dir": ridge_dir, "scarp": scarp}


def add_edge_support(S: np.ndarray, f: dict[str, np.ndarray], gain: float = 0.35) -> np.ndarray:
    """Multiply the level-field consensus by consensus of the provided *derivative* bands."""
    acc = np.zeros(S.shape, np.float32)
    for name in EDGE_BANDS:
        acc += _norm01(np.abs(np.nan_to_num(f[name], nan=0.0)))
    acc /= len(EDGE_BANDS)
    return np.clip(S * (1.0 - gain + gain * acc * 2.0), 0.0, 1.0).astype(np.float32)
