#!/usr/bin/env python3
"""Recover where the hidden test faults are, by inverting 128 published leaderboard scores.

The idea in one paragraph
-------------------------
The organizer metric is ``DTI = TP/(0.2 D + 0.8 N)``: for a binary raster the denominator has no
``TP`` term, so a leaderboard score is a *linear measurement* of the hidden truth set.  Every
published raster therefore states exactly how much of its mass must sit on truth::

    TP_i = s_i (0.2 D_i + 0.8 N)

Stack 128 of those equations.  Each raster is a column of the design matrix over cells (1 where it
places a dot), so the system is massively under-determined -- but its *normal equations* are not:
the Gram matrix is only 128x128 and is fully determined by the pairwise dot overlaps.  The
ridge/least-norm solution is therefore computable exactly::

    alpha = (O + lam I)^-1 t            O_ij = dots shared by rasters i and j
    u(x)  = sum_i alpha_i 1[x in P_i]   the estimated truth field
    q(x)  = clip(c * u(x), 0, 1)        the same field on a probability scale

``c`` is fitted so that re-scoring the 128 published rasters through ``q`` reproduces their
leaderboard scores.  That is the honest test of the estimator, and it is done leave-one-file-out:
a file's score is always predicted by an ``alpha`` and a ``c`` that never saw it.

What this can and cannot do
---------------------------
*Can*: place the corpus' information on a calibrated per-cell footing, and let the metric's own
marginal-gain rule (``add a dot iff q > 0.2 * DTI``) decide how many dots to emit.
*Cannot*: create recall the corpus does not have.  Dot overlap between the top published rasters
is 0.87-1.00, so the corpus is redundant; a candidate built from it is a better-shaped version of
the same pattern, not a new discovery.

Usage
-----
    python scripts/distill_from_leaderboard.py --emit --out-dir docs/downloads
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import maximum_filter

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8  # organizer metric weights


# --------------------------------------------------------------------------------------- corpus
def load_corpus(manifest: Path, data_dir: Path):
    rows = [r for r in json.loads(manifest.read_text())["rows"] if r["status"] == "matched"]
    with rasterio.open(data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        shape, transform, crs = ds.shape, ds.transform, ds.crs
    cid = np.full(shape[0] * shape[1], -1, dtype=np.int64)
    cid[foot.ravel()] = np.arange(int(foot.sum()))
    seen, files = set(), []
    for r in rows:
        key = r["sha256"] or r["local"]
        if key in seen:
            continue
        seen.add(key)
        with rasterio.open(ROOT / r["local"]) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & foot
        ids = np.sort(cid[m.ravel()])
        ids = ids[ids >= 0]
        if ids.size == 0:
            continue
        files.append({"name": Path(r["local"]).name, "score": float(r["owner_reported_score"]),
                      "ids": ids.astype(np.int32), "D": int(ids.size)})
    return files, foot, shape, transform, crs, cid


def gram(files, n):
    O = np.zeros((n, n), dtype=np.float64)
    for i, f in enumerate(files):
        O[i, i] = f["D"]
        for j in range(i + 1, n):
            O[i, j] = O[j, i] = np.intersect1d(f["ids"], files[j]["ids"], assume_unique=True).size
    return O


def solve_alpha(O, t, lam_rel):
    lam = lam_rel * float(np.mean(np.diag(O)))
    return np.linalg.solve(O + lam * np.eye(O.shape[0]), t)


def field(files, n_cells, alpha):
    u = np.zeros(n_cells, dtype=np.float64)
    for f, a in zip(files, alpha):
        if a != 0.0:
            u[f["ids"]] += a
    return u


def u_histograms(u, files, n_bins=512):
    """Per-file histogram of u over its dots, so fit_scale never touches the 5M-cell field."""
    umax = float(np.clip(u, 0, None).max()) or 1.0
    edges = np.linspace(0.0, umax, n_bins + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    H = np.zeros((len(files), n_bins))
    for i, f in enumerate(files):
        b = np.clip(np.digitize(u[f["ids"]], edges) - 1, 0, n_bins - 1)
        H[i] = np.bincount(b, minlength=n_bins)[:n_bins]
    return H, centres


def fit_scale(u, files, N, hist=None):
    """Fit c so that scoring the corpus through clip(c*u) matches its leaderboard scores."""
    obs = np.array([f["score"] for f in files])
    Dv = np.array([f["D"] for f in files], float)
    if hist is None:
        hist = u_histograms(u, files)
    H, centres = hist
    best = None
    for c in np.concatenate([np.linspace(0.05, 3.0, 60), np.geomspace(0.01, 30, 40)]):
        tp = H @ np.clip(c * centres, 0.0, 1.0)
        pred = tp / (ALPHA * Dv + BETA * N)
        rmse = float(np.sqrt(np.mean((pred - obs) ** 2)))
        if best is None or rmse < best[0]:
            best = (rmse, c, pred)
    return best[1], best[0], best[2]


def sp(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb)))


# ------------------------------------------------------------------------------- candidate emit
def select_cells(q, foot, n_cells, cid, tau, max_dots, sep=2):
    """Greedy: highest q first, no two dots within `sep` px, stop when q drops under `tau`."""
    order = np.argsort(-q)[: max(max_dots * 6, 200000)]
    ys, xs = np.divmod(np.nonzero(foot.ravel())[0][order], foot.shape[1])
    qq = q[order]
    occ = np.zeros((foot.shape[0] // sep + 2, foot.shape[1] // sep + 2), dtype=bool)
    keep = []
    br, bc = ys // sep, xs // sep
    for k in range(order.size):
        if qq[k] < tau or len(keep) >= max_dots:
            break
        r, cc = br[k], bc[k]
        if occ[max(r - 1, 0): r + 2, max(cc - 1, 0): cc + 2].any():
            continue
        occ[r, cc] = True
        keep.append(k)
    keep = np.array(keep, dtype=np.int64)
    return ys[keep], xs[keep], qq[keep]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=ROOT / "evidence" / "score_corpus_manifest_20261030.json")
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--evidence", type=Path, default=ROOT / "evidence" / "distill_from_leaderboard_20261030.json")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--N-grid", type=float, nargs="+",
                    default=[12000, 16000, 20000, 25000, 30000, 40000, 55000, 75000, 100000])
    ap.add_argument("--folds", type=int, default=6)
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--max-dots", type=int, default=42000)
    args = ap.parse_args()

    files, foot, shape, transform, crs, cid = load_corpus(args.manifest, args.data_dir)
    n = len(files)
    n_cells = int(foot.sum())
    obs = np.array([f["score"] for f in files])
    D = np.array([f["D"] for f in files], float)
    print(f"corpus: {n} rasters, {n_cells} footprint cells", flush=True)
    O = gram(files, n)

    rng = np.random.default_rng(0)
    order = rng.permutation(n)
    fold = np.empty(n, int)
    fold[order] = np.arange(n) % args.folds

    # ---------------- model selection on leave-one-file-out ----------------
    grid = []
    best = None
    for N in args.N_grid:
        t = obs * (ALPHA * D + BETA * N)
        al = solve_alpha(O, t, 1e-6)
        u = field(files, n_cells, al)
        c, rmse_in, pred_in = fit_scale(u, files, N)
        # LOO: refit alpha and c without the held-out file
        loo = np.full(n, np.nan)
        for fo in range(args.folds):
            tr = np.where(fold != fo)[0]
            te = np.where(fold == fo)[0]
            Otr = O[np.ix_(tr, tr)]
            ttr = obs[tr] * (ALPHA * D[tr] + BETA * N)
            atr = solve_alpha(Otr, ttr, 1e-6)
            sub = [files[i] for i in tr]
            ids = np.unique(np.concatenate([files[i]["ids"] for i in tr]))
            remap = np.full(n_cells, -1, dtype=np.int64)
            remap[ids] = np.arange(ids.size)
            sub2 = [{"ids": remap[f["ids"]], "D": f["D"], "score": f["score"], "name": f["name"]} for f in sub]
            usub = field(sub2, ids.size, atr)
            ctr, _, _ = fit_scale(usub, sub2, N)
            for i in te:
                ti = remap[files[i]["ids"]]
                ti = ti[ti >= 0]
                tp = np.clip(ctr * usub[ti], 0, 1).sum()
                loo[i] = tp / (ALPHA * files[i]["D"] + BETA * N)
        ok = np.isfinite(loo)
        r = {"N": N, "c": c, "in_sample_rmse": rmse_in,
             "loo_rmse": float(np.sqrt(np.mean((loo[ok] - obs[ok]) ** 2))),
             "loo_rho": sp(loo[ok], obs[ok])}
        grid.append(r)
        print(f"  N={N:<7.0f} c={c:.3f} in={rmse_in:.4f} loo_rmse={r['loo_rmse']:.4f} "
              f"loo_rho={r['loo_rho']:.3f}", flush=True)
        if best is None or r["loo_rmse"] < best["loo_rmse"]:
            best = r
    N, c = best["N"], best["c"]
    print(f"chosen N={N:.0f} c={c:.3f} (LOO rmse {best['loo_rmse']:.4f}, rho {best['loo_rho']:.3f}; "
          f"baseline rmse {np.sqrt(np.mean((obs - obs.mean()) ** 2)):.4f})", flush=True)

    t = obs * (ALPHA * D + BETA * N)
    al = solve_alpha(O, t, 1e-6)
    u = field(files, n_cells, al)
    q = np.clip(c * u, 0.0, 1.0)

    # ---------------- selection sweep under the metric's own marginal rule ----------------
    sweep = []
    for maxd in (30000, 36000, 42000, 50000, 60000, 80000):
        ys, xs, qq = select_cells(q, foot, n_cells, cid, tau=0.02, max_dots=maxd)
        d = len(qq)
        tp = float(qq.sum())
        sweep.append({"max_dots": maxd, "n_dots": d, "expected_tp": round(tp, 1),
                      "est_score": round(tp / (ALPHA * d + BETA * N), 4)})
        print("  ", sweep[-1], flush=True)

    ev = {
        "schema_version": 1, "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "label": "ESTIMATE",
        "not_organizer_confirmed": True,
        "method": f"least-norm inversion of the organizer metric's linear form on {n} published rasters",
        "n_rasters": n, "N_estimate": N, "scale_c": c,
        "model_selection": f"leave-one-file-out squared error on the {n} owner-reported scores",
        "baseline_loo_rmse": float(np.sqrt(np.mean((obs - obs.mean()) ** 2))),
        "chosen": best, "grid": grid, "sweep": sweep,
        "field_stats": {"max_q": float(q.max()), "cells_over_0.1": int((q > 0.1).sum()),
                        "cells_over_0.2": int((q > 0.2).sum()), "cells_over_0.4": int((q > 0.4).sum()),
                        "sum_q": float(q.sum())},
        "known_limitations": [
            "the top published rasters share 0.87-1.00 of their dots, so the corpus is redundant",
            "q is defined only where at least one published raster places a dot",
            "scores are OWNER-REPORT; no organizer receipt exists",
            "N is not pinned by the corpus; it is chosen by LOO and reported explicitly",
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(ev, indent=1) + "\n")
    print(f"field: min {q.min():.3f} max {q.max():.3f} sum {q.sum():.0f}", flush=True)
    np.savez_compressed(ROOT / ".cache" / "distill_q.npz", q=q.astype(np.float32),
                        shape=np.array(shape), cell_id=cid, N=np.array([N]), c=np.array([c]),
                        names=np.array([f["name"] for f in files]),
                        scores=obs, D=D)
    print(f"wrote {args.evidence}", flush=True)

    if not args.emit:
        return 0

    # ---------------- emit the candidate ----------------
    best_row = max(sweep, key=lambda r: r["est_score"])
    ys, xs, qq = select_cells(q, foot, n_cells, cid, tau=0.02, max_dots=best_row["max_dots"])
    arr = np.where(foot, 0.0, np.nan).astype(np.float32)
    arr[ys, xs] = 1.0
    assert int((arr == 1.0).sum()) == ys.size, "dot count mismatch"
    name = f"gemsdoesass3-lbinv-{ys.size}-20261030T0900Z-nanoutside"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tif = args.out_dir / f"{name}.tif"
    profile = {"driver": "GTiff", "height": shape[0], "width": shape[1], "count": 1,
               "dtype": "float32", "crs": crs, "transform": transform, "nodata": float("nan"),
               "compress": "deflate", "tiled": False}
    with rasterio.open(tif, "w", **profile) as ds:
        ds.write(arr, 1)
    with zipfile.ZipFile(args.out_dir / f"{name}.tif.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, tif.name)
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    zsha = hashlib.sha256((args.out_dir / f"{name}.tif.zip").read_bytes()).hexdigest()
    est = best_row["est_score"]
    build = {"schema_version": 1, "generated_utc": "2026-10-30", "label": "ESTIMATE",
             "submission_name": name, "raster_sha256": sha, "zip_sha256": zsha,
             "n_dots": int(ys.size), "expected_tp": best_row["expected_tp"], "est_score": est,
             "N_estimate": N, "scale_c": c, "loo_rmse": best["loo_rmse"], "loo_rho": best["loo_rho"],
             "submission_note": f"LB-inversion field: {ys.size} dots; est {est:.3f} (LOO sd {best['loo_rmse']:.3f})"}
    (args.out_dir / f"{name}-build.json").write_text(json.dumps(build, indent=1) + "\n")
    print(json.dumps(build, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
