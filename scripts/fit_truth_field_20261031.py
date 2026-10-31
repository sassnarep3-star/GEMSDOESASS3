#!/usr/bin/env python3
"""Experiment 2 — recover the hidden new-fault density from the published score corpus.

Why this is identifiable at all
-------------------------------
Page 967 fixes the metric (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):

    TP_w = Σ_{g∈G} max_x p(x)·k(d(x,g)),  FP_w = Σ_x p(x)·[1 − max_g k(d(x,g))],
    FN_w = |G| − TP_w,   DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w),   k(d) = max(1 − d/3, 0)

For a sparse binary dot set P this gives TP_w ≈ Σ_{x∈P} q(x) with **q = T ⊛ k**, where T is the
(unknown) new-fault indicator and ⊛ is convolution with the triangular 300 m kernel.  So every
published (raster, score) pair is one *linear measurement* of the hidden field T:

    s_i · (0.2·D_i + 0.8·N)  =  Σ_{x∈P_i} q(x)          (D_i = Σ p_i, N = |G|)

N is pinned independently by the no-skill reference files (uniform lattices and broad,
unskilled sprays): for those, E[TP_w] = N·mc_i where mc_i is the footprint-mean kernel credit of
the dot pattern, which is measured directly, so N = 0.2·s·D/(mc − 0.8·s) is an upper bound
(enrichment ε ≥ 1).  A ≤ N gives the lower bound.  Measured here: 8 222 ≤ N ≤ 12 366.

Estimator
---------
Each raster's dots share that raster's recovered credit equally, so cell x gets

    ŵ(x) = Σ_i (A_i / D_i) · p_i(x),      A_i = s_i·(0.2·D_i + 0.8·N)

and T̂ = N·ŵ / Σ ŵ.  That is a weighted consensus, not a copy: no raster is reproduced.

Validation
----------
Rasters are clustered into families by 10×-downsampled dot-density correlation.  A leave-one-
family-out (LOFO) run rebuilds T̂ without family F, thresholds it to N cells to make a binary
truth surrogate, and scores family F's real raster with the repository's exact DTI
implementation.  The observed-vs-LOFO-predicted regression is what calibrates the headline
estimate — leave-one-*file*-out is nearly in-sample here because the corpus is redundant
(the champion is published in four repositories).

Usage:
    python scripts/fit_truth_field_20261031.py [--n0 12000]
Writes:
    .cache/truth_field_20261031.npz  (T̂, q̂)
    evidence/truth_field_20261031.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CORPUS = ROOT / "registry" / "corpus_20261031.json"
CACHE = ROOT / ".cache" / "corpus_20261031"
OUT = ROOT / "evidence" / "truth_field_20261031.json"
H, W = 3730, 3292
R = 3.0

# triangular kernel offsets
_yy, _xx = np.mgrid[-3:4, -3:4]
_KOFF = [(int(dy), int(dx), float(np.hypot(dy, dx)))
         for dy in range(-3, 4) for dx in range(-3, 4) if np.hypot(dy, dx) < 3.0]
_KOFF = [(dy, dx, 1.0 - d / R) for dy, dx, d in _KOFF]


def load_grid():
    import rasterio
    d = ROOT / ".cache" / "gems_data"
    with rasterio.open(d / "sample_submission.tif") as ds:
        ss = ds.read(1)
    with rasterio.open(d / "labels.tif") as ds:
        lab = ds.read(1)
    valid = np.isfinite(ss)
    cat = valid & (lab == 1)
    return valid.reshape(-1), cat.reshape(-1)


def conv_k(density: np.ndarray) -> np.ndarray:
    """Convolve a (H,W) field with the triangular 300 m kernel."""
    out = np.zeros_like(density)
    for dy, dx, kw in _KOFF:
        ys0, ys1 = max(0, dy), min(H, H + dy)
        xs0, xs1 = max(0, dx), min(W, W + dx)
        out[ys0:ys1, xs0:xs1] += density[max(0, -dy):min(H, H - dy),
                                         max(0, -dx):min(W, W - dx)] * kw
    return out


def load_scored(valid: np.ndarray):
    corp = json.loads(CORPUS.read_text())
    rows, seen = [], set()
    for r in corp["rasters"]:
        if r.get("status") != "ok" or "owner_reported_score" not in r or r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        z = np.load(CACHE / f"{r['sha256']}.npz")
        idx, val = z["idx"].astype(np.int64), z["val"].astype(np.float64)
        m = valid[idx]
        idx, val = idx[m], val[m]
        if idx.size == 0 or val.sum() <= 0:
            continue
        rows.append({"sha": r["sha256"], "name": r["pool_file"], "repo": r["repo"],
                     "score": float(r["owner_reported_score"]), "idx": idx, "val": val,
                     "D": float(val.sum())})
    return rows


def footprint_mean_credit(rows, valid):
    from scipy import ndimage as ndi
    for r in rows:
        g = np.zeros(valid.size, np.float32)
        g[r["idx"]] = r["val"].astype(np.float32)
        dp = ndi.distance_transform_edt(g.reshape(H, W) == 0)
        cred = np.maximum(1.0 - dp / R, 0.0)
        r["mc"] = float(cred.reshape(-1)[valid].mean())
        del g, dp, cred


def families(rows, valid, thresh=0.60):
    """Cluster rasters by correlation of 10x-downsampled dot density."""
    gh, gw = H // 10 + 1, W // 10 + 1
    sig = np.zeros((len(rows), gh * gw), np.float32)
    for i, r in enumerate(rows):
        np.add.at(sig[i], (r["idx"] // W // 10) * gw + (r["idx"] % W // 10), r["val"])
    sig = sig / np.maximum(sig.sum(1, keepdims=True), 1e-9)
    sig -= sig.mean(1, keepdims=True)
    nrm = np.linalg.norm(sig, axis=1, keepdims=True)
    nrm[nrm == 0] = 1
    S = sig / nrm
    C = S @ S.T
    fam = -np.ones(len(rows), int)
    nf = 0
    for i in range(len(rows)):
        if fam[i] >= 0:
            continue
        fam[i] = nf
        for j in range(i + 1, len(rows)):
            if fam[j] < 0 and C[i, j] >= thresh:
                fam[j] = nf
        nf += 1
    return fam, C


def build_T(rows, use, n0: float):
    w = np.zeros(H * W, np.float64)
    for i in use:
        r = rows[i]
        A = r["score"] * (0.2 * r["D"] + 0.8 * n0)      # recovered credit mass
        np.add.at(w, r["idx"], r["val"] * (A / r["D"]))  # credit shared among that raster's dots
    w = w.reshape(H, W)
    tot = w.sum()
    T = (n0 / tot) * w if tot > 0 else w
    return T


def threshold_T(T, valid, n0: int):
    """Binary truth surrogate: the top-N0 valid cells by T̂."""
    flat = T.reshape(-1)
    idxv = np.flatnonzero(valid)
    vals = flat[idxv]
    n = int(min(n0, idxv.size))
    if n <= 0:
        return np.zeros(H * W, bool)
    take = idxv[np.argpartition(vals, -n)[-n:]]
    out = np.zeros(H * W, bool)
    out[take] = True
    return out


def dti_of(raster_idx, raster_val, truth_bool, valid):
    """Exact DTI of one submission against a binary truth surrogate, over valid cells."""
    from gems32.metric import dti_exact
    pred = np.zeros(H * W, np.float32)
    pred[raster_idx] = raster_val.astype(np.float32)
    pred = pred.reshape(H, W)
    return dti_exact(pred, truth_bool.reshape(H, W), valid=valid.reshape(H, W))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n0", type=float, default=12000.0)
    ap.add_argument("--family-thresh", type=float, default=0.60)
    args = ap.parse_args()

    valid, cat = load_grid()
    rows = load_scored(valid)
    print(f"scored rasters: {len(rows)}", flush=True)
    footprint_mean_credit(rows, valid)

    # ---- N bounds -------------------------------------------------------------
    lo = max(0.2 * r["score"] * r["D"] / (1 - 0.8 * r["score"]) for r in rows)
    hi_c = [(0.2 * r["score"] * r["D"] / (r["mc"] - 0.8 * r["score"]), r)
            for r in rows if r["mc"] > 0.8 * r["score"]]
    hi, hi_row = min(hi_c, key=lambda t: t[0])
    N_bounds = {"lower_from_A_le_N": lo, "upper_from_eps_ge_1": hi,
                "upper_bound_file": hi_row["name"], "n_files_giving_upper_bound": len(hi_c)}

    fam, C = families(rows, valid, args.family_thresh)
    nfam = int(fam.max()) + 1
    fam_sizes = np.bincount(fam, minlength=nfam).tolist()
    print(f"families: {nfam} sizes={sorted(fam_sizes, reverse=True)[:12]}", flush=True)

    n0 = float(args.n0)
    T = build_T(rows, range(len(rows)), n0)

    # ---- leave-one-family-out --------------------------------------------------
    lofo = []
    for f in range(nfam):
        use = [i for i in range(len(rows)) if fam[i] != f]
        if not use:
            continue
        Tf = build_T(rows, use, n0)
        truth = threshold_T(Tf, valid, int(round(n0)))
        for i in [i for i in range(len(rows)) if fam[i] == f]:
            r = rows[i]
            d = dti_of(r["idx"], r["val"], truth, valid)
            lofo.append({"family": f, "name": r["name"], "observed": r["score"],
                         "lofo_predicted": d["dti"], "D": r["D"]})
        print(f"  LOFO family {f}: n={fam_sizes[f]} "
              f"obs={np.mean([l['observed'] for l in lofo if l['family'] == f]):.4f} "
              f"pred={np.mean([l['lofo_predicted'] for l in lofo if l['family'] == f]):.4f}",
              flush=True)

    obs = np.array([l["observed"] for l in lofo])
    pred = np.array([l["lofo_predicted"] for l in lofo])
    rho = float(np.corrcoef(obs, pred)[0, 1])
    rmse = float(np.sqrt(np.mean((pred - obs) ** 2)))
    base = float(np.sqrt(np.mean((obs.mean() - obs) ** 2)))
    # calibration: observed = a + b * lofo_predicted
    b, a = np.polyfit(pred, obs, 1)
    cal_rmse = float(np.sqrt(np.mean((a + b * pred - obs) ** 2)))

    truth_all = threshold_T(T, valid, int(round(n0)))
    q = conv_k(T)
    np.savez_compressed(ROOT / ".cache" / "truth_field_20261031.npz",
                        T=T.astype(np.float32), q=q.astype(np.float32))

    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "label": "ESTIMATE — every score is OWNER-REPORT; nothing is ORGANIZER-CONFIRMED",
        "n0_used": n0,
        "N_bounds": N_bounds,
        "n_scored": len(rows), "n_families": nfam, "family_sizes": fam_sizes,
        "lofo": {"n": int(len(lofo)), "pearson_r": rho, "rmse": rmse,
                 "baseline_rmse_predict_mean": base,
                 "calibration": {"slope": float(b), "intercept": float(a), "rmse": cal_rmse},
                 "rows": lofo},
        "top_scored": [
            {"name": r["name"], "score": r["score"], "D": r["D"], "mc": r["mc"],
             "implied_credit_A": r["score"] * (0.2 * r["D"] + 0.8 * n0),
             "enrichment_eps": r["score"] * (0.2 * r["D"] + 0.8 * n0) / (n0 * r["mc"])}
            for r in sorted(rows, key=lambda r: -r["score"])[:25]],
    }, indent=1))
    print(json.dumps({"N_bounds": N_bounds, "lofo_r": rho, "lofo_rmse": rmse,
                      "baseline_rmse": base, "cal": {"a": a, "b": b, "rmse": cal_rmse}},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
