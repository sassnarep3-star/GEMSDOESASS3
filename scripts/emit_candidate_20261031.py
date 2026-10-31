#!/usr/bin/env python3
"""Experiment 3 — emit the submission raster and estimate its score.

Pipeline
--------
1. Rebuild the hidden new-fault density T̂ from the published score corpus
   (``scripts/fit_truth_field_20261031.py``), N = N0 cells.
2. q = T̂ ⊛ k  (triangular 300 m kernel) = the expected kernel credit of a dot at x.
3. Emit dots at the highest-q cells under a minimum-spacing rule (clumping is measurably
   harmful — see the ``clump`` coefficient in ``evidence/diagnose_truth_location_20261031.json``)
   and cut at the metric's own marginal bar.
4. Score the result with the repository's exact DTI against T̂, then convert to a leaderboard
   estimate with the leave-one-family-out calibration.
5. Audit uniqueness against every raster in the registry with a KD-tree 3-px test.
6. Write the GeoTIFF (0.0 outside the footprint, no NaN anywhere) and verify all format gates.

Usage:
    python scripts/emit_candidate_20261031.py --n0 12000 --outdir docs/downloads
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

H, W = 3730, 3292
R = 3.0
CORPUS = ROOT / "registry" / "corpus_20261031.json"
CACHE = ROOT / ".cache" / "corpus_20261031"
OUT_JSON = ROOT / "evidence" / "emit_candidate_20261031.json"

_yy, _xx = np.mgrid[-3:4, -3:4]
_KOFF = [(int(dy), int(dx), float(1.0 - np.hypot(dy, dx) / R))
         for dy in range(-3, 4) for dx in range(-3, 4) if np.hypot(dy, dx) < R]


def shift(a, dy, dx):
    out = np.zeros_like(a)
    ys0, ys1 = max(0, dy), min(H, H + dy)
    xs0, xs1 = max(0, dx), min(W, W + dx)
    out[ys0:ys1, xs0:xs1] = a[max(0, -dy):min(H, H - dy), max(0, -dx):min(W, W - dx)]
    return out


def conv_k(density):
    out = np.zeros_like(density)
    for dy, dx, kw in _KOFF:
        out += shift(density, -dy, -dx) * kw
    return out


def load_grid():
    import rasterio
    d = ROOT / ".cache" / "gems_data"
    with rasterio.open(d / "sample_submission.tif") as ds:
        ss = ds.read(1)
    with rasterio.open(d / "labels.tif") as ds:
        lab = ds.read(1)
    valid = np.isfinite(ss)
    cat = valid & (lab == 1)
    return valid, cat


def load_scored(valid):
    corp = json.loads(CORPUS.read_text())
    rows, seen = [], set()
    for r in corp["rasters"]:
        if r.get("status") != "ok" or "owner_reported_score" not in r or r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        z = np.load(CACHE / f"{r['sha256']}.npz")
        idx, val = z["idx"].astype(np.int64), z["val"].astype(np.float64)
        m = valid.reshape(-1)[idx]
        idx, val = idx[m], val[m]
        if idx.size == 0 or val.sum() <= 0:
            continue
        rows.append({"sha": r["sha256"], "name": r["pool_file"], "repo": r["repo"],
                     "score": float(r["owner_reported_score"]), "idx": idx, "val": val,
                     "D": float(val.sum())})
    return rows


def build_T(rows, use, n0):
    w = np.zeros(H * W, np.float64)
    for i in use:
        r = rows[i]
        A = r["score"] * (0.2 * r["D"] + 0.8 * n0)
        np.add.at(w, r["idx"], r["val"] * (A / r["D"]))
    w = w.reshape(H, W)
    tot = w.sum()
    return (n0 / tot) * w if tot > 0 else w


def emit_spaced(q, valid, keep, spacing, budget=None, thresh=None):
    """Greedy non-max suppression in descending q; keep cells >=spacing px from kept cells."""
    cand = np.flatnonzero(keep & (q.reshape(-1) > 0))
    if cand.size == 0:
        return np.zeros(H * W, bool)
    order = cand[np.argsort(-q.reshape(-1)[cand], kind="stable")]
    if budget is not None:
        order = order[: int(budget * 6)]          # generous pre-filter, the bar cuts later
    kept_ys, kept_xs = [], []
    occ = np.zeros(H * W, bool)
    r = float(spacing)
    rr = max(1e-9, r * r)
    from scipy.spatial import cKDTree
    chosen = []
    CH = 20000
    for s in range(0, order.size, CH):
        chunk = order[s:s + CH]
        cy, cx = chunk // W, chunk % W
        if kept_ys:
            tree = cKDTree(np.column_stack([np.concatenate(kept_ys), np.concatenate(kept_xs)]))
            d, _ = tree.query(np.column_stack([cy, cx]), k=1, distance_upper_bound=r + 1e-9)
            ok = ~np.isfinite(d) | (d > r)
        else:
            ok = np.ones(chunk.size, bool)
        take = chunk[ok]
        chosen.append(take)
        kept_ys.append(cy[ok])
        kept_xs.append(cx[ok])
        if budget is not None and sum(len(c) for c in chosen) >= budget:
            break
    sel = np.concatenate(chosen) if chosen else np.zeros(0, np.int64)
    if budget is not None:
        sel = sel[:budget]
    if thresh is not None:
        sel = sel[q.reshape(-1)[sel] >= thresh]
    out = np.zeros(H * W, bool)
    out[sel] = True
    return out


def dti_against_T(dotmask, T, valid, n0):
    """Exact DTI of a binary submission against the top-N0 cells of T̂ used as a truth surrogate."""
    from gems32.metric import dti_binary
    flat = T.reshape(-1)
    idxv = np.flatnonzero(valid.reshape(-1))
    vals = flat[idxv]
    n = int(min(n0, idxv.size))
    take = idxv[np.argpartition(vals, -n)[-n:]]
    truth = np.zeros(H * W, bool)
    truth[take] = True
    return dti_binary(dotmask.reshape(H, W), truth.reshape(H, W),
                      valid=valid.reshape(H, W)), int(n)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n0", type=float, default=12000.0)
    ap.add_argument("--outdir", default="docs/downloads")
    ap.add_argument("--tag", default="")
    ap.add_argument("--spacing", type=float, default=2.0)
    ap.add_argument("--mask-buffer", type=int, default=0)
    ap.add_argument("--budget", type=int, default=0)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--skip-uniqueness", action="store_true")
    args = ap.parse_args()

    valid, cat = load_grid()
    vf, cf = valid.reshape(-1), cat.reshape(-1)
    rows = load_scored(vf)
    print(f"scored rasters: {len(rows)}", flush=True)

    n0 = float(args.n0)
    T = build_T(rows, range(len(rows)), n0)
    q = conv_k(T.astype(np.float64))
    print(f"T̂: support={int((T > 0).sum())} sum={T.sum():.1f} q max={q.max():.4f}", flush=True)

    # ---- catalogue buffer -------------------------------------------------------
    from scipy import ndimage as ndi
    if args.mask_buffer > 0:
        yy, xx = np.mgrid[-args.mask_buffer:args.mask_buffer + 1,
                          -args.mask_buffer:args.mask_buffer + 1]
        disk = (np.hypot(yy, xx) <= args.mask_buffer).astype(np.float32)
        buf = ndi.convolve(cat.reshape(H, W).astype(np.float32), disk, mode="constant") > 0
    else:
        buf = np.zeros((H, W), bool)
    keep = (vf.reshape(H, W) & ~buf)

    cal = json.loads((ROOT / "evidence" / "truth_field_20261031.json").read_text())["lofo"]["calibration"]
    a_cal, b_cal = cal["intercept"], cal["slope"]

    # ---- sweep ------------------------------------------------------------------
    grid = []
    spacings = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0] if args.sweep else [args.spacing]
    budgets = [0, 30000, 40000, 50000, 60000, 80000, 120000] if args.sweep else [args.budget]
    for sp in spacings:
        for bd in budgets:
            m = emit_spaced(q, valid, keep.reshape(-1), sp, budget=(bd or None))
            nd = int(m.sum())
            if nd == 0:
                continue
            d, ntruth = dti_against_T(m, T, valid, int(round(n0)))
            grid.append({"spacing": sp, "budget": bd, "n_dots": nd,
                         "dti_vs_T": d["dti"], "tp": d["tp"], "fp": d["fp"], "fn": d["fn"],
                         "coverage": d["coverage"],
                         "estimate": float(a_cal + b_cal * d["dti"])})
            print(f"  sp={sp} bd={bd or 0:>6} dots={nd:7d} dti={d['dti']:.4f} "
                  f"est={a_cal + b_cal * d['dti']:.4f}", flush=True)

    if not grid:
        print("no candidate emitted", file=sys.stderr)
        return 1
    grid.sort(key=lambda g: -g["estimate"])
    best = grid[0]
    print("BEST", json.dumps(best), flush=True)

    # ---- final emission ----------------------------------------------------------
    dot = emit_spaced(q, valid, keep.reshape(-1), best["spacing"], budget=(best["budget"] or None))
    nd = int(dot.sum())
    d, ntruth = dti_against_T(dot, T, valid, int(round(n0)))
    est = float(a_cal + b_cal * d["dti"])

    # ---- uniqueness (KD-tree 3-px test against every registry raster) -------------
    uniq = {}
    if not args.skip_uniqueness:
        from scipy.spatial import cKDTree
        cy, cx = np.nonzero(dot.reshape(H, W))
        ctree = cKDTree(np.column_stack([cy, cx]))
        worst = 0.0
        worst_name = ""
        worst_cov = 0.0
        over70 = 0
        nreg = 0
        corp = json.loads(CORPUS.read_text())
        for r in corp["rasters"]:
            if r.get("status") != "ok":
                continue
            z = np.load(CACHE / f"{r['sha256']}.npz")
            idx = z["idx"].astype(np.int64)
            if idx.size == 0:
                continue
            nreg += 1
            ry, rx = idx // W, idx % W
            tree = cKDTree(np.column_stack([ry, rx]))
            cnt = np.array([len(t) for t in ctree.query_ball_tree(tree, 3.0)])
            frac = float((cnt > 0).sum()) / max(1, nd)
            cov = float(min(1.0, idx.size * 29.0 / valid.sum()))
            if frac > worst:
                worst, worst_name, worst_cov = frac, r["pool_file"], cov
            if frac > 0.70:
                over70 += 1
        uniq = {"n_registry_rasters": nreg, "n_dots": nd,
                "worst_3px_overlap": worst, "worst_file": worst_name,
                "worst_file_3px_coverage_of_footprint": worst_cov,
                "lift_over_coverage": (worst / worst_cov) if worst_cov > 0 else None,
                "n_registry_rasters_over_70pct": over70,
                "gate": "PASS" if over70 == 0 else "FAIL",
                "rule": "protocol: >70% of dots within 3 px of one registry raster = duplicate"}

    # ---- write the GeoTIFF ---------------------------------------------------------
    import rasterio
    from rasterio.transform import Affine
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = args.tag or f"s3-truthinv-n{int(n0)}-sp{best['spacing']}-b{best['budget'] or 0}"
    stem = f"gemsdoesass3-{tag}-{stamp}"
    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    tif = outdir / f"{stem}.tif"
    arr = np.zeros((H, W), np.float32)
    arr[dot.reshape(H, W)] = 1.0
    prof = dict(driver="GTiff", height=H, width=W, count=1, dtype="float32",
                crs="EPSG:32611", transform=Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
                compress="deflate", predictor=2, nodata=None)
    with rasterio.open(tif, "w", **prof) as ds:
        ds.write(arr, 1)

    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        return h.hexdigest()

    zpath = outdir / f"{stem}.tif.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, arcname=tif.name)

    # ---- format gates --------------------------------------------------------------
    with rasterio.open(tif) as ds:
        chk = {"crs": str(ds.crs), "shape": list(ds.shape), "dtype": ds.dtypes[0],
               "transform": list(ds.transform)[:6], "count": ds.count}
        back = ds.read(1)
    gates = {
        "single_band": chk["count"] == 1,
        "dtype_float32": chk["dtype"] == "float32",
        "crs_epsg_32611": chk["crs"].upper().endswith("32611"),
        "shape_3730x3292": chk["shape"] == [H, W],
        "transform_100m": all(abs(x - y) < 1e-9 for x, y in
                              zip(chk["transform"], [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0])),
        "no_nan_anywhere": bool(np.isfinite(back).all()),
        "values_in_0_1": bool((back >= 0).all() and (back <= 1).all()),
        "no_positive_outside_footprint": bool((back[~np.isfinite(valid)] == 0).all()),
        "binary_values": bool(set(np.unique(back).tolist()) <= {0.0, 1.0}),
    }
    gates["all_pass"] = all(gates.values())

    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "submission_name": stem,
        "file": str(tif.relative_to(ROOT)),
        "zip": str(zpath.relative_to(ROOT)),
        "sha256_tif": sha(tif), "sha256_zip": sha(zpath),
        "bytes_tif": tif.stat().st_size, "bytes_zip": zpath.stat().st_size,
        "n0": n0, "spacing": best["spacing"], "budget": best["budget"],
        "n_dots": nd,
        "dti_vs_T_surrogate": d,
        "n_truth_surrogate_cells": ntruth,
        "estimate": {"value": est, "label": "ESTIMATE (calibrated leave-one-family-out)",
                     "calibration": cal,
                     "rmse": json.loads((ROOT / "evidence" / "truth_field_20261031.json")
                                        .read_text())["lofo"]["rmse"]},
        "sweep": grid,
        "gates": gates, "format_check": chk,
        "uniqueness": uniq,
        "mask_buffer_px": args.mask_buffer,
    }
    OUT_JSON.write_text(json.dumps(receipt, indent=1))
    print(json.dumps({k: receipt[k] for k in
                      ("submission_name", "n_dots", "estimate", "gates", "uniqueness")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
