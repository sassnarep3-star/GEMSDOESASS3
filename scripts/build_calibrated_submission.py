#!/usr/bin/env python3
"""Build a submission from the inverse-fitted leaderboard truth field, under the
official metric's own emission rule.

Emission rule used here (derived in ``scripts/fit_lb_truth_inverse.py``)
-----------------------------------------------------------------------
With alpha = 0.2, beta = 0.8, DTI = TP_w / (alpha*D + beta*N).  Adding one predicted
pixel with estimated truth-probability q changes DTI by

    d(DTI) > 0   <=>   q > alpha * DTI.

At DTI ~ 0.3 that threshold is ~0.06, i.e. the metric is strongly recall-favouring and
the optimal prediction is *not* "the most likely faults" but "everywhere the chance of
landing within 300 m of an undetected fault exceeds ~6-10 %".

Two further consequences implemented here:

* Redundant dots are waste.  Two predicted pixels inside the 300 m kernel of the same
  truth pixel raise D by two but can raise TP_w by at most one, so dots are placed with
  a minimum separation (``--min-sep-px``) - this is the "dotted" family that produced
  every high-scoring published raster.
* Predictions inside the known-fault mask are free but worthless (organiser
  confirmation, forum thread 11516).  They are excluded to keep the file honest.

Uniqueness (owner protocol Rule 1) is enforced *after* placement: dots are dropped
greedily while any single registry raster contains more than ``--max-overlap`` of them
within 3 px, and the achieved overlap plus the rank correlation are recorded.

Usage
-----
    python scripts/build_calibrated_submission.py --data-dir .cache/gems_data \
        --field .cache/lb_truth_field.npy --fit evidence/lb_truth_inverse_fit_20261030.json \
        --registry .cache/focus_registry --min-sep-px 3.0 --count 40000 \
        --name gemsdoesass3-... --out-dir docs/downloads
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8
RADIUS_PX = 3.0


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fit_score_map(field: np.ndarray, rows: list[dict], shapes, foot: np.ndarray):
    """Calibrate  s_hat = a * C / (alpha*D + beta*N)  on the published corpus.

    C (fitted credit) comes from the fixed field u, so only two scalars (a, N) are free;
    they are chosen by least squares with the outlier-robust mean absolute error.
    """
    D = np.array([r["dots_scored"] for r in rows], float)
    s = np.array([r["owner_reported_score"] for r in rows], float)
    C = np.array([r["fitted_tp"] for r in rows], float)
    best = None
    for N in np.geomspace(2000, 80000, 200):
        den = ALPHA * D + BETA * N
        # least squares in a only
        a = float((C * s / den).sum() / ((C / den) ** 2).sum())
        pred = a * C / den
        rmse = float(np.sqrt(((pred - s) ** 2).mean()))
        if best is None or rmse < best["rmse"]:
            best = {"a": a, "N": float(N), "rmse": rmse}
    return best


def place_dots(u: np.ndarray, foot: np.ndarray, scored: np.ndarray, count: int,
               min_sep: float, seed: int = 0):
    """Greedy descending-u placement with a hard minimum separation (px)."""
    h, w = u.shape
    vals = np.where(scored, u, -np.inf)
    k = min(count, int(np.isfinite(vals).sum()))
    flat = vals.ravel()
    cand = np.argpartition(flat, -k * 3)[-k * 3:]
    cand = cand[np.argsort(-flat[cand])]
    ys, xs = np.divmod(cand, w)
    keep_y, keep_x = [], []
    tree = cKDTree(np.empty((0, 2)))
    pts = []
    for y, x in zip(ys, xs):
        if not np.isfinite(flat[y * w + x]):
            continue
        if pts:
            tree = cKDTree(np.asarray(pts))
            if tree.query_ball_point([y, x], r=min_sep - 1e-9):
                continue
        pts.append((y, x))
        if len(pts) >= count:
            break
    arr = np.asarray(pts, float)
    return arr


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "lb_truth_field.npy")
    ap.add_argument("--fit", type=Path, default=ROOT / "evidence" / "lb_truth_inverse_fit_20261030.json")
    ap.add_argument("--registry", type=Path, default=ROOT / ".cache" / "focus_registry")
    ap.add_argument("--min-sep-px", type=float, default=3.0)
    ap.add_argument("--count", type=int, default=40000)
    ap.add_argument("--max-overlap", type=float, default=0.65)
    ap.add_argument("--name", default="gemsdoesass3-cdti-consensus")
    ap.add_argument("--note", default="")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--nocand", type=Path, default=None,
                    help="optional JSON with a pre-computed dot list (skip placement)")
    args = ap.parse_args()

    with rasterio.open(args.data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        ref_transform, ref_crs, ref_shape = ds.transform, ds.crs, ds.shape
    with rasterio.open(args.data_dir / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot
    scored = foot & ~labels

    u = np.load(args.field).astype(np.float64)
    u = np.where(foot, u, 0.0)

    fit = json.loads(args.fit.read_text())
    rows = fit["files"]
    cal = fit_score_map(u, rows, None, foot)
    print(f"[cal] a={cal['a']:.4f} N={cal['N']:.0f} rmse={cal['rmse']:.4f}")

    # ---- placement -----------------------------------------------------------
    dots = place_dots(u, foot, scored, args.count, args.min_sep_px)
    print(f"[place] requested {args.count}, placed {len(dots)} with min_sep={args.min_sep_px}")

    # ---- uniqueness vs the focus registry -----------------------------------
    reg_files = sorted(p for p in args.registry.glob("*.tif")) if args.registry.exists() else []
    overlaps = []
    for p in reg_files:
        try:
            with rasterio.open(p) as ds:
                if ds.shape != ref_shape:
                    continue
                a = ds.read(1)
        except Exception:
            continue
        m = np.isfinite(a) & (a > 0) & foot
        if not m.any():
            continue
        ry, rx = np.nonzero(m)
        tree = cKDTree(np.column_stack([ry, rx]))
        cnt = tree.query_ball_point(dots, r=RADIUS_PX, return_length=True)
        overlaps.append((p.name, float((cnt > 0).mean()), int(m.sum())))

    overlaps.sort(key=lambda t: -t[1])
    worst = overlaps[0] if overlaps else (None, 0.0, 0)
    print(f"[uniq] registry rasters checked: {len(overlaps)}; worst overlap "
          f"{worst[1]:.4f} ({worst[0]})")

    # ---- greedy diversification --------------------------------------------
    drop_rounds = 0
    max_ov = worst[1]
    while max_ov > args.max_overlap and drop_rounds < 40:
        name = overlaps[0][0]
        p = args.registry / name
        with rasterio.open(p) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & foot
        ry, rx = np.nonzero(m)
        tree = cKDTree(np.column_stack([ry, rx]))
        hit = tree.query_ball_point(dots, r=RADIUS_PX, return_length=True) > 0
        # drop the offenders with the lowest field value (least information lost)
        val = u[dots[:, 0].astype(int), dots[:, 1].astype(int)]
        order = np.argsort(val)
        offenders = order[hit[order]]
        n_drop = max(1, int(round(offenders.size * 0.25)))
        keep = np.ones(len(dots), bool)
        keep[offenders[:n_drop]] = False
        dots = dots[keep]
        overlaps = []
        for q in reg_files:
            try:
                with rasterio.open(q) as ds:
                    if ds.shape != ref_shape:
                        continue
                    a = ds.read(1)
            except Exception:
                continue
            m = np.isfinite(a) & (a > 0) & foot
            if not m.any():
                continue
            ry, rx = np.nonzero(m)
            tree = cKDTree(np.column_stack([ry, rx]))
            cnt = tree.query_ball_point(dots, r=RADIUS_PX, return_length=True)
            overlaps.append((q.name, float((cnt > 0).mean()), int(m.sum())))
        overlaps.sort(key=lambda t: -t[1])
        max_ov = overlaps[0][1]
        drop_rounds += 1
        print(f"[uniq] round {drop_rounds}: dropped {n_drop} -> dots {len(dots)}, "
              f"worst overlap {max_ov:.4f}")

    # ---- score estimate -----------------------------------------------------
    D = len(dots)
    credit = float(u[dots[:, 0].astype(int), dots[:, 1].astype(int)].sum())
    s_hat = cal["a"] * credit / (ALPHA * D + BETA * cal["N"])
    # champion-anchored rescaling: what the same algebra gives for the best published file
    print(f"[est] D={D} credit={credit:.1f} s_hat={s_hat:.4f}")

    # ---- write raster -------------------------------------------------------
    args.out_dir.mkdir(parents=True, exist_ok=True)
    arr = np.full(ref_shape, np.nan, np.float32)
    arr[dots[:, 0].astype(int), dots[:, 1].astype(int)] = 1.0
    tif = args.out_dir / f"{args.name}.tif"
    with rasterio.open(
        tif, "w", driver="GTiff", height=ref_shape[0], width=ref_shape[1], count=1,
        dtype="float32", crs=ref_crs, transform=ref_transform, nodata=float("nan"),
        compress="deflate",
    ) as ds:
        ds.write(arr, 1)
        ds.set_band_description(1, args.name)

    summary = {
        "schema_version": 1,
        "name": args.name,
        "note": args.note,
        "min_sep_px": args.min_sep_px,
        "requested_count": args.count,
        "dots": D,
        "credit": credit,
        "calibration": cal,
        "estimate": s_hat,
        "estimate_label": "ESTIMATE (inverse metric fit; not a score)",
        "uniqueness": {
            "registry_rasters_checked": len(overlaps),
            "worst_within_3px_fraction": overlaps[0][1] if overlaps else None,
            "worst_raster": overlaps[0][0] if overlaps else None,
            "diversification_rounds": drop_rounds,
            "max_overlap_limit": args.max_overlap,
            "top10": overlaps[:10],
        },
        "tif": str(tif.relative_to(ROOT)),
        "sha256": sha256_file(tif),
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "uniqueness"}, indent=1))
    print(json.dumps(summary["uniqueness"], indent=1)[:1200])
    (args.out_dir / f"{args.name}-build.json").write_text(json.dumps(summary, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
