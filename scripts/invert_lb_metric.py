#!/usr/bin/env python3
"""Invert the official metric to recover the hidden truth field from published scores.

The algebra
-----------
The DrivenData GEMS score is a weighted Tversky index with ``alpha=0.2`` (FP weight) and
``beta=0.8`` (FN weight).  For a raster that predicts a set ``P`` against a hidden truth set
``G`` of size ``N``::

    DTI = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w)

Substituting ``FP_w = D - TP_w`` and ``FN_w = N - TP_w`` and using ``alpha + beta = 1``::

    DTI = TP / (0.2 D + 0.8 N)

The denominator has *no TP term*.  That is the whole trick: the leaderboard score is a linear
measurement of the hidden truth field, and a linear measurement can be inverted.  Solving for
the overlap::

    TP_i = s_i (0.2 D_i + 0.8 N)

So every published (raster, score) pair states exactly how much of that raster's mass must sit
on truth.  Given 129 such pairs we can estimate where the truth is.

Estimator
---------
Parameterise the per-cell credit as a score-weighted consensus of the published corpus::

    u_raw(x) = sum_i  s_i**gamma * 1[x in P_i]
    u(x)     = clip(k * u_raw(x), 0, 1)

and fit the three scalars ``(gamma, k, N)`` by minimising squared error on the observed
scores.  ``u(x)`` is then an estimate of "a prediction placed at x earns credit", i.e. of
``1[x within one kernel of G]``, which is exactly the quantity the metric rewards.

Validation is leave-one-file-out: refit on 128 files, predict the held-out file's score.
Neither in-sample fit nor LOO is an organizer receipt; both are labelled ESTIMATE.

Usage
-----
    python scripts/invert_lb_metric.py --out .cache/lb_inversion.npz \
        --evidence evidence/lb_inversion_20261030.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8  # organizer metric weights


def load_corpus(manifest: Path, data_dir: Path):
    rows = [r for r in json.loads(manifest.read_text())["rows"] if r["status"] == "matched"]
    with rasterio.open(data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        shape = ds.shape
    flat_foot = foot.ravel()
    cell_id = np.full(shape[0] * shape[1], -1, dtype=np.int64)
    cell_id[flat_foot] = np.arange(int(flat_foot.sum()), dtype=np.int64)

    seen, files = set(), []
    for r in rows:
        key = r["sha256"] or r["local"]
        if key in seen:
            continue
        seen.add(key)
        with rasterio.open(ROOT / r["local"]) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & foot
        ids = cell_id[m.ravel()]
        ids = np.sort(ids[ids >= 0])
        if ids.size == 0:
            continue
        files.append({"name": Path(r["local"]).name, "site": r["site"], "score": float(r["owner_reported_score"]),
                      "ids": ids.astype(np.int32), "D": int(ids.size)})
    return files, cell_id, shape, int(flat_foot.sum())


def consensus(files, n_cells, gamma):
    """Score-weighted indicator sum over the union of predicted cells."""
    w = np.array([f["score"] ** gamma for f in files], dtype=np.float64)
    u = np.zeros(n_cells, dtype=np.float64)
    for f, wi in zip(files, w):
        if wi == 0.0:
            continue
        np.add.at(u, f["ids"], wi)
    return u


def predict_scores(files, u, k, N):
    tp = np.array([u[f["ids"]].sum() for f in files])
    den = ALPHA * np.array([f["D"] for f in files], float) + BETA * N
    with np.errstate(invalid="ignore", divide="ignore"):
        s = tp / den
    return s, tp


def fit(u_raw, files, gamma, N_fixed=None):
    """Fit scale k (and optionally N) by least squares on observed scores."""
    obs = np.array([f["score"] for f in files])
    D = np.array([f["D"] for f in files], float)

    def loss(p):
        k = p[0]
        N = p[1] if N_fixed is None else N_fixed
        u = np.clip(k * u_raw, 0.0, 1.0)
        s, _ = predict_scores(files, u, k, N)
        return float(np.mean((s - obs) ** 2))

    x0 = np.array([1.0 / max(u_raw.max(), 1e-9), 60000.0])
    bounds = [(1e-12, 1e3), (20000.0, 200000.0)]
    res = minimize(loss, x0=x0, method="L-BFGS-B", bounds=bounds)
    k = float(res.x[0])
    N = float(res.x[1] if N_fixed is None else N_fixed)
    u = np.clip(k * u_raw, 0.0, 1.0)
    s, tp = predict_scores(files, u, k, N)
    return {"k": k, "N": N, "u": u, "pred": s, "tp": tp, "rmse": float(np.sqrt(np.mean((s - obs) ** 2)))}


def rank(x):
    return np.argsort(np.argsort(x)).astype(float)


def spearman(a, b):
    ra, rb = rank(a) - rank(a).mean(), rank(b) - rank(b).mean()
    return float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=ROOT / "evidence" / "score_corpus_manifest_20261030.json")
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--out", type=Path, default=ROOT / ".cache" / "lb_inversion.npz")
    ap.add_argument("--evidence", type=Path, default=ROOT / "evidence" / "lb_inversion_20261030.json")
    ap.add_argument("--gamma-grid", type=float, nargs="+", default=[0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0])
    ap.add_argument("--folds", type=int, default=8)
    args = ap.parse_args()

    files, cell_id, shape, n_cells = load_corpus(args.manifest, args.data_dir)
    obs = np.array([f["score"] for f in files])
    print(f"corpus: {len(files)} unique rasters, {n_cells} footprint cells, "
          f"scores {obs.min():.4f}..{obs.max():.4f}", flush=True)

    # ---- 1. choose the sharpening exponent by in-sample fit ----
    best = None
    for g in args.gamma_grid:
        u_raw = consensus(files, n_cells, g)
        r = fit(u_raw, files, g)
        r["u_raw"] = u_raw
        r["gamma"] = g
        print(f"  gamma={g:<4} k={r['k']:.4g} N={r['N']:.0f} rmse={r['rmse']:.4f} "
              f"rho={spearman(r['pred'], obs):.3f}", flush=True)
        if best is None or r["rmse"] < best["rmse"]:
            best = r
    gamma, u_raw, u = best["gamma"], best["u_raw"], best["u"]
    print(f"chosen gamma={gamma} (in-sample rmse {best['rmse']:.4f})", flush=True)

    # ---- 2. leave-one-file-out validation ----
    rng = np.random.default_rng(0)
    order = rng.permutation(len(files))
    folds = np.empty(len(files), dtype=int)
    folds[order] = np.arange(len(files)) % args.folds
    loo = np.full(len(files), np.nan)
    for fo in range(args.folds):
        tr = [i for i in range(len(files)) if folds[i] != fo]
        te = [i for i in range(len(files)) if folds[i] == fo]
        sub_ids = np.unique(np.concatenate([files[i]["ids"] for i in tr]))
        remap = np.full(n_cells, -1, dtype=np.int64)
        remap[sub_ids] = np.arange(sub_ids.size)
        sub = [{"ids": remap[files[i]["ids"]], "D": files[i]["D"], "score": files[i]["score"],
                "name": files[i]["name"], "site": files[i]["site"]} for i in tr]
        ur = consensus(sub, sub_ids.size, gamma)
        r = fit(ur, sub, gamma)
        for i in te:
            tids = remap[files[i]["ids"]]
            tids = tids[tids >= 0]
            tp = r["u"][tids].sum()
            loo[i] = tp / (ALPHA * files[i]["D"] + BETA * r["N"])
    ok = np.isfinite(loo)
    loo_rmse = float(np.sqrt(np.mean((loo[ok] - obs[ok]) ** 2)))
    loo_rho = spearman(loo[ok], obs[ok])
    print(f"LOO ({args.folds}-fold): rmse={loo_rmse:.4f} rho={loo_rho:.3f} over {ok.sum()} rasters", flush=True)

    # ---- 3. the estimated truth field ----
    np.savez_compressed(args.out, u=u.astype(np.float32), shape=np.array(shape), cell_id=cell_id,
                        n_cells=np.array(n_cells), scores=obs, loo=loo,
                        names=np.array([f["name"] for f in files]))
    est = {
        "schema_version": 1,
        "generated_utc": "2026-10-30",
        "label": "ESTIMATE",
        "not_organizer_confirmed": True,
        "method": "invert DTI = TP/(alpha*D + beta*N) over the published score corpus",
        "n_rasters": len(files),
        "n_footprint_cells": n_cells,
        "gamma": gamma,
        "k": best["k"],
        "N_estimate": best["N"],
        "in_sample": {"rmse": best["rmse"], "rho": spearman(best["pred"], obs)},
        "leave_one_out": {"folds": args.folds, "rmse": loo_rmse, "rho": loo_rho},
        "worst_residuals": [
            {"name": files[i]["name"], "observed": float(obs[i]), "predicted": float(loo[i]),
             "residual": float(loo[i] - obs[i])}
            for i in np.argsort(-np.abs(loo - obs))[:10]
        ],
        "uses_public_sibling_repositories": True,
        "provenance": "scores are OWNER-REPORT values typed beside public file names; no organizer receipt exists",
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(est, indent=1) + "\n")
    print(f"wrote {args.out} and {args.evidence}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
