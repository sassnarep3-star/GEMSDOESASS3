#!/usr/bin/env python3
"""Experiment 1 — where is the hidden truth?  Score-driver regression over the published corpus.

Question
--------
The scored truth set is the sponsor's *new* faults: "any fault pixel not already captured by
USGS/INGENIOUS", which the organizer confirmed "can include newly mapped geometry of an existing
fault system"
(https://community.drivendata.org/t/where-do-you-draw-the-line/11536).  A competitor therefore
needs to know whether new faults hug the published catalogue or sit away from it.

Method
------
For every published raster with an owner-reported score, compute purely geometric statistics
that need no labels:

* ``D``      total prediction mass  Σ p(x)
* ``f0``     share of that mass within 300 m (3 px) of a catalogued fault pixel
* ``f1``     share 3–6 px away, ``f2`` 6–12 px, ``f3`` > 12 px
* ``clump``  mean number of other dots within 3 px (wasted overlap)
* ``en``     mean *catalogue* kernel credit per unit mass  Σ p·(1-d/3)+ / Σ p

Then regress the owner-reported score on these, so the sign of the catalogue-distance
coefficients says whether the truth is near or far from the mapped faults.

Labelling
---------
Every score in the table is **OWNER-REPORT** (typed by the owner on the sibling Pages sites).
Nothing here is ORGANIZER-CONFIRMED.  The regression is a correlation over a redundant corpus,
not a causal estimate.

Usage:
    python scripts/diagnose_truth_location_20261031.py
Writes:
    evidence/diagnose_truth_location_20261031.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CORPUS = ROOT / "registry" / "corpus_20261031.json"
CACHE = ROOT / ".cache" / "corpus_20261031"
OUT = ROOT / "evidence" / "diagnose_truth_location_20261031.json"

H, W = 3730, 3292
R = 3.0


def load_base():
    import rasterio
    from scipy import ndimage as ndi
    d = ROOT / ".cache" / "gems_data"
    with rasterio.open(d / "sample_submission.tif") as ds:
        ss = ds.read(1)
    with rasterio.open(d / "labels.tif") as ds:
        lab = ds.read(1)
    valid = np.isfinite(ss)
    cat = valid & (lab == 1)
    dist = ndi.distance_transform_edt(~cat).astype(np.float32)
    credit = np.maximum(1.0 - dist / R, 0.0).astype(np.float32)
    return valid, cat, dist, credit


def dot_stats(idx: np.ndarray, val: np.ndarray, dist: np.ndarray, credit: np.ndarray,
              occ: np.ndarray) -> dict:
    d = dist.reshape(-1)[idx]
    p = val.astype(np.float64)
    mass = float(p.sum())
    if mass <= 0:
        return None
    c = credit.reshape(-1)[idx]
    # local clumping: expected number of *other* dots within 3 px
    near = occ
    return {
        "D": mass,
        "n_dots": int(idx.size),
        "f0": float(p[d <= 3].sum() / mass),
        "f1": float(p[(d > 3) & (d <= 6)].sum() / mass),
        "f2": float(p[(d > 6) & (d <= 12)].sum() / mass),
        "f3": float(p[d > 12].sum() / mass),
        "clump": float(np.average(near, weights=p)),
        "cat_credit": float(np.dot(p, c) / mass),
        "median_dist": float(np.median(d)),
    }


def main() -> int:
    from scipy import ndimage as ndi

    # 3-px disk kernel (Euclidean distance <= 3), used to measure local dot clumping
    yy, xx = np.mgrid[-3:4, -3:4]
    DISK3 = (np.hypot(yy, xx) <= 3.0).astype(np.float32)

    valid, cat, dist, credit = load_base()
    corpus = json.loads(CORPUS.read_text())
    rows = []
    seen = set()
    occ_grid = np.zeros((H, W), dtype=np.float32)

    for r in corpus["rasters"]:
        if r.get("status") != "ok" or "owner_reported_score" not in r:
            continue
        if r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        z = np.load(CACHE / f"{r['sha256']}.npz")
        idx, val = z["idx"], z["val"]
        flat = occ_grid.reshape(-1)
        flat[:] = 0.0
        np.add.at(flat, idx.astype(np.int64), val)
        # mass of *other* dots within 3 px, via convolution with the 3-px disk
        occ = ndi.convolve(occ_grid, DISK3, mode='constant').reshape(-1)[idx.astype(np.int64)] - val
        st = dot_stats(idx, val, dist, credit, occ)
        if st is None:
            continue
        st.update(score=float(r["owner_reported_score"]), pool_file=r["pool_file"],
                  repo=r["repo"], sha256=r["sha256"], in_range=bool(r.get("in_range")))
        rows.append(st)

    rows.sort(key=lambda x: -x["score"])
    out = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "label": "OWNER-REPORT scores; geometric covariates measured here",
        "n_scored_rasters": len(rows),
        "rows": rows,
    }

    # ---------------- regression -------------------------------------------------
    import statsmodels.api as sm
    y = np.array([r["score"] for r in rows])
    names = ["f0", "f1", "f2", "clump", "logD"]
    X = np.column_stack([
        np.array([r["f0"] for r in rows]),
        np.array([r["f1"] for r in rows]),
        np.array([r["f2"] for r in rows]),
        np.array([r["clump"] for r in rows]),
        np.log10(np.array([r["D"] for r in rows])),
    ])
    Xc = sm.add_constant(X)
    fit = sm.OLS(y, Xc).fit()
    out["regression"] = {
        "formula": "score ~ 1 + f0 + f1 + f2 + clump + log10(D)",
        "n": int(len(y)),
        "r2": float(fit.rsquared),
        "r2_adj": float(fit.rsquared_adj),
        "params": {n: float(v) for n, v in zip(["const"] + names, fit.params)},
        "pvalues": {n: float(v) for n, v in zip(["const"] + names, fit.pvalues)},
        "tvalues": {n: float(v) for n, v in zip(["const"] + names, fit.tvalues)},
        "note": "f0+f1+f2+f3 = 1 so f3 is dropped (perfect collinearity); the f0 coefficient is "
                "the effect of moving mass from >12 px to within 3 px of a catalogued fault.",
    }

    # simple binned view: score vs catalogue distance decile
    med = np.array([r["median_dist"] for r in rows])
    bins = [0, 3, 5, 8, 12, 20, 1e9]
    band = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (med >= lo) & (med < hi)
        if m.sum():
            band.append({"median_dist_band": [lo, hi], "n": int(m.sum()),
                         "mean_score": float(y[m].mean()), "max_score": float(y[m].max())})
    out["score_by_catalogue_distance"] = band

    # N bounds from each file: A <= min(D, N)  =>  N >= 0.2 s D / (1 - 0.8 s) and
    #                                             N <= D (1 - 0.2 s) / (0.8 s)
    lo_b, hi_b = [], []
    for r in rows:
        s, D = r["score"], r["D"]
        if s <= 0:
            continue
        lo_b.append(0.2 * s * D / (1 - 0.8 * s))
        hi_b.append(D * (1 - 0.2 * s) / (0.8 * s))
    out["N_bounds_per_file"] = {
        "derivation": "official DTI = A/(0.2A + 0.2FP + 0.8N) with A = TP_w <= min(D, N). "
                      "A <= N gives the lower bound, A <= D gives the upper bound. "
                      "Bounds hold for every file; the tightest are reported.",
        "lower_bound_max": float(max(lo_b)) if lo_b else None,
        "upper_bound_min": float(min(hi_b)) if hi_b else None,
        "upper_bound_min_file": rows[int(np.argmin(hi_b))]["pool_file"] if hi_b else None,
        "upper_bound_p25": float(np.percentile(hi_b, 25)) if hi_b else None,
    }

    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps(out["regression"], indent=1))
    print(json.dumps(out["score_by_catalogue_distance"], indent=1))
    print(json.dumps(out["N_bounds_per_file"], indent=1))
    print("top rows:")
    for r in rows[:12]:
        print(f"  {r['score']:.4f} D={r['D']:9.0f} f0={r['f0']:.3f} med={r['median_dist']:5.1f} "
              f"clump={r['clump']:.2f} {r['pool_file'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
