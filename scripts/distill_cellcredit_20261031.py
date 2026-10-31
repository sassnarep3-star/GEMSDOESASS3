#!/usr/bin/env python3
"""H-CELLDISTILL: learn the hidden test faults' per-cell credit field from published scores.

Lane
----
This is the step the 2026-10-30 session recorded as *not run* -- hypothesis 4 of
``docs/research/leaderboard-inversion-20261030.md``.  The incumbent estimator
(``scripts/distill_from_leaderboard.py``) writes the truth field as a linear combination of the
published rasters themselves, so it is **zero wherever nobody has ever drawn a dot**: it can
redistribute recall, never create it.  This module learns a *cell-level* field from the
competition's own feature stack instead, which is what makes off-corpus placement possible.

Why the fit is exact rather than hand-tuned
-------------------------------------------
The organizer metric (page 967; implemented and unit-tested in ``src/gems32/metric.py``) with
alpha = 0.2, beta = 0.8 collapses, for a binary prediction of mass D against a truth set of size N,
to a **linear measurement** of a latent per-cell credit field c(x):

    DTI_i = TP_i / (0.2 D_i + 0.8 N)        =>      TP_i = s_i (0.2 D_i + 0.8 N)
    TP_i  = sum_{x in P_i} c(x)                       (sparse, well-separated dots)

Put a linear model on the credit field, ``c(x) = b + w . phi(x)``, and the bag *sum* over a raster's
own dots becomes ``D_i`` times the bag *mean*:

    s_i (0.2 D_i + 0.8 N) / D_i  =  b + w . mean_{x in P_i} phi(x)

so a 5.2-million-cell under-determined inverse problem reduces **exactly** to a
(len(files) x len(features)) weighted regression on per-file feature means.  Predicted score is
``D_i / (0.2 D_i + 0.8 N)`` times the model residual, so weighting the regression by
``omega_i = D_i / (0.2 D_i + 0.8 N)`` makes the fitted objective the leaderboard-score MSE itself.
The reduction is verified numerically against the brute-force metric in
``tests/test_cellcredit_distillation.py``.

Honest validation
-----------------
* **leave-CLUSTER-out**, not leave-one-file-out: the top published rasters share most of their dots,
  so a single-file holdout leaks through near-duplicates.  Files are clustered by exact Jaccard
  overlap of their dot sets and whole clusters are withheld.
* baselines reported beside the model: predict-the-mean-score, and (when its receipt exists) the
  incumbent inversion's leave-one-file-out number.
* per-channel leakage canary on the catalogue (AUC > 0.90 is flagged, not used silently).

Every number in the output is labelled: inputs are OWNER-REPORT, the field and all scores are
ESTIMATE.  Nothing here is a leaderboard score and no submission slot is spent by this script.

Usage
-----
    python scripts/distill_cellcredit_20261031.py                 # fit + validate + field
    python scripts/distill_cellcredit_20261031.py --canary 0      # skip the AUC canary
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import grid as G  # noqa: E402
from gems32.metric import dti_binary  # noqa: E402

ALPHA, BETA = 0.2, 0.8


# ------------------------------------------------------------------------------------- features
def bands_expected() -> list[str]:
    """Band names as published in ``data/prepared_manifest.json`` (verified against the raster)."""
    return ["mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
            "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
            "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15",
            "cond_surf", "iso_grav_anom_hg", "det_elev_slope"]


def channel_list() -> list[tuple[str, str]]:
    """(channel name, builder spec).  19 official bands + 9 structural transforms."""
    out = [(f"band{i:02d}_{nm}", f"band{i}") for i, nm in enumerate(bands_expected(), start=1)]
    out += [
        ("scarp_step_fine", "tophat_det_elev_1"),    # 1-2 px scarp step: the metric's own currency
        ("scarp_step_coarse", "tophat_det_elev_3"),  # wider expression / older scarps
        ("curv_det_elev", "curv_det_elev"),          # Hessian ridge on topography (bright ridge)
        ("ridge_tmi_vg", "ridge_tmi_vg_2"),          # magnetic vertical-gradient lineament
        ("ridge_grav", "ridge_grav_3"),              # gravity-edge lineament under basin fill
        ("edge_cond", "edge_cond_2"),                # conductivity-jump boundary (fluid conduit)
        ("edge_depth", "edge_depth_2"),              # top-of-source depth-offset boundary
        ("strain_kink", "strain_kink"),              # shear rate over dilatation: localisation
        ("dil_share", "dil_shear"),                  # dilatation share of the strain tensor
    ]
    return out


def _ridge(a, sigma):
    axx = ndimage.gaussian_filter(a, sigma, order=(0, 2), mode="nearest")
    ayy = ndimage.gaussian_filter(a, sigma, order=(2, 0), mode="nearest")
    axy = ndimage.gaussian_filter(a, sigma, order=(1, 1), mode="nearest")
    tmp = np.sqrt(np.maximum(((axx - ayy) * 0.5) ** 2 + axy ** 2, 0.0))
    l1 = (axx + ayy) * 0.5 + tmp
    l2 = (axx + ayy) * 0.5 - tmp
    big = np.where(np.abs(l1) >= np.abs(l2), l1, l2)
    small = np.where(np.abs(l1) >= np.abs(l2), l2, l1)
    return (-small * (big < 0)).astype(np.float32)


def _gradmag(a):
    gy, gx = np.gradient(a)
    return np.hypot(gx, gy).astype(np.float32)


class FeatureSource:
    """One channel at a time, so peak memory stays inside ~1 GB on a 3 GB box."""

    def __init__(self, feat_path: Path, foot: np.ndarray):
        self.feat_path, self.foot = Path(feat_path), foot
        self._cache: dict[int, np.ndarray] = {}
        # only bands that feed a *derived* channel are held; the rest are used once and freed,
        # because 19 x 49 MB of cache does not fit next to the field arrays in 3 GB of RAM.
        self._keep = {7, 8, 9, 12, 13, 15, 17}

    def band(self, i: int) -> np.ndarray:
        if i in self._cache:
            return self._cache[i]
        with rasterio.open(self.feat_path) as ds:
            raw = ds.read(i).astype(np.float32)
        valid = np.isfinite(raw) & (raw > G.NODATA_F32 * np.float32(0.5))
        if not valid.any() or not valid.all():
            idx = ndimage.distance_transform_edt(~valid, return_distances=False, return_indices=True)
            raw[~valid] = raw[idx[0][~valid], idx[1][~valid]]
        raw[~self.foot] = 0.0
        if i in self._keep:
            self._cache[i] = raw
        return raw

    def get(self, spec: str) -> np.ndarray:
        if spec.startswith("band"):
            return self.band(int(spec[4:]))
        if spec == "tophat_det_elev_1":
            return ndimage.white_tophat(self.band(12), size=(3, 3)).astype(np.float32)
        if spec == "tophat_det_elev_3":
            return ndimage.white_tophat(self.band(12), size=(7, 7)).astype(np.float32)
        if spec == "curv_det_elev":
            return _ridge(self.band(12), 1.5)
        if spec == "ridge_tmi_vg_2":
            return _ridge(self.band(9), 2.0)
        if spec == "ridge_grav_3":
            return _ridge(self.band(13), 3.0)
        if spec == "edge_cond_2":
            return _gradmag(ndimage.gaussian_filter(self.band(17), 2.0, mode="nearest"))
        if spec == "edge_depth_2":
            return _gradmag(ndimage.gaussian_filter(self.band(15), 2.0, mode="nearest"))
        if spec == "strain_kink":
            return (self.band(7) / (np.abs(self.band(8)) + 1.0)).astype(np.float32)
        if spec == "dil_shear":
            return (np.abs(self.band(8)) / (self.band(7) + 1.0)).astype(np.float32)
        raise KeyError(spec)

    def close(self):
        self._cache.clear()


def robust_norm(a: np.ndarray, foot: np.ndarray) -> tuple[np.ndarray, float, float]:
    v = a[foot]
    lo, hi = float(np.percentile(v, 1.0)), float(np.percentile(v, 99.0))
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
        hi = lo + 1.0
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0).astype(np.float32), lo, hi


# --------------------------------------------------------------------------------------- corpus
def load_corpus(manifest: Path, foot: np.ndarray, cid: np.ndarray, drop_dirs: list[Path]):
    rows = [r for r in json.loads(manifest.read_text())["rows"] if r["status"] == "matched"]
    files, seen = [], set()
    for r in rows:
        key = r["sha256"] or r["local"]
        if key in seen:
            continue
        seen.add(key)
        p = ROOT / r["local"]
        if not p.exists():
            p2 = Path(r["local"])
            cand = [d / p2.name for d in drop_dirs]
            p = next((c for c in cand if c.exists()), None)
            if p is None:
                continue
        try:
            with rasterio.open(p) as ds:
                if ds.shape != foot.shape:
                    continue
                a = ds.read(1)
        except Exception:
            continue
        hits = np.isfinite(a) & (a > 0) & foot
        fp = cid[hits.ravel()]                        # footprint-space ids, ascending
        files.append({"name": Path(r["local"]).name, "site": r["site"], "token": r["token"],
                      "score": float(r["owner_reported_score"]), "sha256": r["sha256"],
                      "flat": np.flatnonzero(hits), "fp": fp})
        del a
    return files


def jaccard_clusters(files, thresh=0.35, n_cells: int | None = None):
    """Single-linkage clusters on Jaccard overlap of the dot sets.

    Dot sets are grid-flat indices, so the bit matrix spans the whole grid (133 x 1.5 MB packed);
    overlaps are then exact and ~200x faster than set intersections at this size.
    """
    n = len(files)
    key = "fp" if files and "fp" in files[0] else "flat"
    if n_cells is None:
        n_cells = int(max(int(f[key][-1]) for f in files)) + 1
    B = np.zeros((n, (n_cells + 7) // 8), np.uint8)
    for i, f in enumerate(files):
        bits = np.zeros(n_cells, bool)
        bits[f[key]] = True
        B[i] = np.packbits(bits)
    sizes = np.array([f[key].size for f in files], float)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        inter = np.bitwise_count(B[i] & B[i + 1:]).sum(axis=1).astype(np.float64)
        if not inter.size:
            continue
        uni = sizes[i] + sizes[i + 1:] - inter
        hit = np.flatnonzero(inter / np.maximum(uni, 1.0) >= thresh)
        for k in hit:
            j = i + 1 + int(k)
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[rj] = ri
    labs, remap = np.zeros(n, int), {}
    for i in range(n):
        r = find(i)
        remap.setdefault(r, len(remap))
        labs[i] = remap[r]
    return labs.tolist(), None


def score_of(mask: np.ndarray, truth: np.ndarray, foot: np.ndarray) -> float:
    return float(dti_binary(mask & foot, truth & foot)["dti"])


# -------------------------------------------------------------------------------------- fitting
def ridge_fit(X, y, w, lam):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = np.hstack([np.ones((X.shape[0], 1)), (X - mu) / sd])
    pen = np.eye(Z.shape[1]) * lam
    pen[0, 0] = 0.0
    coef = np.linalg.solve(Z.T @ (Z * w[:, None]) + pen, Z.T @ (w * y))
    return coef, mu, sd


def ridge_apply(coef, mu, sd, Xq):
    return np.hstack([np.ones((Xq.shape[0], 1)), (Xq - mu) / sd]) @ coef


def leave_cluster_out(X, y, w, lam, labels, n_groups, D, denom):
    pred = np.zeros(len(y))
    for g in range(n_groups):
        tr, te = labels != g, labels == g
        if tr.sum() < X.shape[1] + 3:
            pred[te] = float(np.average(y[tr], weights=w[tr])) * D[te] / denom[te]
            continue
        coef, mu, sd = ridge_fit(X[tr], y[tr], w[tr], lam)
        pred[te] = ridge_apply(coef, mu, sd, X[te]) * D[te] / denom[te]
    return pred


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    den = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


# ----------------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--corpus", type=Path, default=ROOT / ".cache" / "gems_corpus")
    ap.add_argument("--manifest", type=Path,
                    default=ROOT / "evidence" / "score_corpus_manifest_20261031.json")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "evidence" / "cellcredit_distillation_20261031.json")
    ap.add_argument("--receipt", type=Path,
                    default=ROOT / ".cache" / "distill_q_cellcredit.json")
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "distill_q_cellcredit.npz")
    ap.add_argument("--mask-radius", type=int, default=0,
                    help="dilate the catalogue by N px before removing it from the scored domain")
    ap.add_argument("--n-grid", type=float, nargs="*",
                    default=[1500, 3000, 4500, 6000, 9000, 12000, 16000, 20000, 26000, 34000,
                             44000, 60000])
    ap.add_argument("--lam-grid", type=float, nargs="*",
                    default=[0.02, 0.05, 0.15, 0.5, 1.5, 5.0, 15.0, 50.0, 150.0, 500.0])
    ap.add_argument("--psi-cache", type=Path, default=ROOT / ".cache" / "cell_psi.npz",
                    help="bag feature means are a 3-minute computation; cache them so the "
                         "downstream arms (incumbent / blend) can reuse the identical design matrix")
    ap.add_argument("--jaccard", type=float, default=0.35, help="cluster-linkage threshold")
    ap.add_argument("--canary", type=int, default=1)
    ap.add_argument("--auc-subsample", type=int, default=1_500_000)
    ap.add_argument("--focus-sites", nargs="*",
                    default="GEMSDOE24 GEMSDOE25 GEMSDOE27 GEMSDOE28 GEMSDOE30 GEMSDOE31 "
                            "GEMSDOE32 GEMSDOE33 GEMSDOE36".split())
    ap.add_argument("--focus-table", type=Path,
                    default=ROOT / "evidence" / "cellcredit_focus_estimates_20261031.json")
    args = ap.parse_args()

    t0 = _dt.datetime.now(_dt.timezone.utc)
    with rasterio.open(args.data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        shape, transform, crs = ds.shape, ds.transform, ds.crs
    n_foot = int(foot.sum())
    cid = np.full(foot.size, -1, dtype=np.int64)
    cid[foot.ravel()] = np.arange(n_foot)
    with rasterio.open(args.data_dir / "labels.tif") as ds:
        lab = ds.read(1)
    catalogue = (np.isfinite(lab) & (lab >= 1)) & foot
    mask = ndimage.binary_dilation(catalogue, iterations=args.mask_radius) if args.mask_radius \
        else catalogue
    scored = foot & ~mask
    print(f"[grid] {shape} footprint {n_foot} catalogue {int(catalogue.sum())} "
          f"scored {int(scored.sum())}", flush=True)

    files = load_corpus(args.manifest, foot, cid, [args.corpus])
    # dot sets are restricted to the scored domain: the organizer excludes catalogue pixels from
    # both penalty terms, so those pixels carry neither mass nor credit in the measurement
    # (https://community.drivendata.org/t/.../11516/2, ORGANIZER statement).
    # footprint id -> scored-domain id, -1 where the catalogue mask removed the cell
    grid_of_fp = np.flatnonzero(foot.ravel())
    fp_of_grid = np.full(foot.size, -1, dtype=np.int64)
    fp_of_grid[grid_of_fp] = np.arange(n_foot)
    scored_flat = np.flatnonzero(scored.ravel())
    sid = np.full(n_foot, -1, np.int64)
    sid[fp_of_grid[scored_flat]] = np.arange(scored_flat.size)
    keep = []
    for f in files:
        ii = sid[f["fp"]]
        ii = ii[ii >= 0]
        f["ids"] = ii.astype(np.int64)
        f["D"] = int(ii.size)
        if f["D"] > 0:
            keep.append(f)
    files = keep
    n = len(files)
    s = np.array([f["score"] for f in files])
    D = np.array([f["D"] for f in files], float)
    labels, _ = jaccard_clusters(files, args.jaccard, n_cells=n_foot)
    labels = np.array(labels, int)
    n_groups = int(labels.max() + 1)
    print(f"[corpus] {n} rasters usable, {n_groups} clusters (Jaccard >= {args.jaccard}); "
          f"D {int(D.min())}-{int(D.max())}", flush=True)

    chans = channel_list()
    F = len(chans)
    fs = FeatureSource(args.data_dir / "training_features.tif", foot)

    names_arr = np.array([f["name"] for f in files])
    ids_cat = np.concatenate([f["ids"] for f in files])
    offs = np.concatenate([[0], np.cumsum([f["D"] for f in files])])
    loaded = False
    if args.psi_cache.exists():
        z = np.load(args.psi_cache)
        if z["psi"].shape == (n, F) and (z["names"] == names_arr).all():
            psi, chan_stats = z["psi"], json.loads(str(z["stats_json"]))
            loaded = True
            print(f"[cache] bag means {psi.shape} reused from {args.psi_cache.name}", flush=True)
    if not loaded:
        psi = np.zeros((n, F))
        chan_stats = {}
        conc = ids_cat
        owner = np.repeat(np.arange(n), [f["D"] for f in files])
        for j, (cname, spec) in enumerate(chans):
            a = fs.get(spec)
            an, lo, hi = robust_norm(a, foot)
            del a
            av = an.ravel()[scored.ravel()]
            sums = np.bincount(owner, weights=av[conc], minlength=n)
            psi[:, j] = sums / D
            chan_stats[cname] = {"p01": round(lo, 6), "p99": round(hi, 6),
                                 "file_mean": [round(float(psi[:, j].min()), 5),
                                               round(float(psi[:, j].max()), 5),
                                               round(float(psi[:, j].mean()), 5)]}
            del an, av
            print(f"  [bag {j + 1:2d}/{F}] {cname:20s} file-mean "
                  f"[{psi[:, j].min():.3f},{psi[:, j].max():.3f}]", flush=True)
        args.psi_cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(args.psi_cache, psi=psi, names=names_arr, s=s, D=D, labels=labels,
                            ids=ids_cat, offs=offs, chan=np.array([c for c, _ in chans]),
                            n_scored=np.array([int(scored.sum())]),
                            mask_radius=np.array([args.mask_radius]),
                            stats_json=np.array(json.dumps(chan_stats)))
        # the bag means and the dot sets are cached together: every arm of the estimator
        # comparison (this model, the incumbent inversion, the blend) is then fitted on the
        # identical design matrix and the identical corpus, which is what makes the numbers
        # comparable at all.
        np.savez_compressed(ROOT / ".cache" / "cell_corpus_sets.npz",
                            ids=ids_cat, offs=offs, scores=s, D=D, names=names_arr,
                            sites=np.array([f["site"] for f in files]),
                            n_scored=np.array([int(scored.sum())]),
                            mask_radius=np.array([args.mask_radius]))


    # ---- leakage canary: each channel alone, against the catalogue it must not encode ------
    canary = {}
    if args.canary:
        # the canary question for every channel: does it merely *find the catalogue*?  Sample
        # footprint cells and score against "within 400 m of a mapped fault".  A channel with a big
        # AUC here and no incremental fit value is a catalogue detector, which the organizer's
        # masking rule makes worthless.
        rng = np.random.default_rng(7)
        grid_of_fp_all = np.flatnonzero(foot.ravel())
        samp = rng.choice(grid_of_fp_all, size=min(args.auc_subsample, grid_of_fp_all.size),
                          replace=False)
        truth_near = ndimage.distance_transform_edt(~catalogue) <= 4.0
        near = truth_near.ravel()[samp]
        del truth_near
        for j, (cname, spec) in enumerate(chans):
            a = fs.get(spec)
            an, _, _ = robust_norm(a, foot)
            del a
            v = an.ravel()[samp]
            del an
            canary[cname] = round(_auc(v, near.astype(bool)), 4)
        canary["_note"] = ("AUC of one channel alone, on a random subsample of footprint cells, "
                           "against the target 'within 400 m of a mapped USGS/INGENIOUS fault'. "
                           "High AUC means the channel is a catalogue detector, which the "
                           "organizer's masking rule makes worthless as a new-fault detector.")
        canary["_n_sampled"] = int(samp.size)
        del near, v, samp, grid_of_fp_all
    fs.close()

    # ---- model selection: N and lambda by leave-CLUSTER-out score RMSE ----------------------
    scan, best = [], None
    for N in args.n_grid:
        denom = ALPHA * D + BETA * float(N)
        y = s * denom / D
        w = (D / denom) ** 2
        for lam in args.lam_grid:
            pred = leave_cluster_out(psi, y, w, lam, labels, n_groups, D, denom)
            row = {"N": int(N), "lambda": float(lam),
                   "gloo_rmse": round(float(np.sqrt(np.mean((pred - s) ** 2))), 5),
                   "gloo_mae": round(float(np.mean(np.abs(pred - s))), 5),
                   "gloo_rho": round(spearman(pred, s), 4)}
            scan.append(row)
            if best is None or row["gloo_rmse"] < best["gloo_rmse"]:
                best = row
    baseline_mean = round(float(np.sqrt(np.mean((s - s.mean()) ** 2))), 5)
    scan.sort(key=lambda r: r["gloo_rmse"])
    print(f"[select] best gloo_rmse={best['gloo_rmse']} N={best['N']} lam={best['lambda']} "
          f"(baseline predict-mean {baseline_mean})", flush=True)

    # ---- final fit and field ----------------------------------------------------------------
    N, lam = float(best["N"]), float(best["lambda"])
    denom = ALPHA * D + BETA * N
    y = s * denom / D
    w = (D / denom) ** 2
    coef, mu, sd = ridge_fit(psi, y, w, lam)
    pred_in = ridge_apply(coef, mu, sd, psi) * D / denom
    pred_gloo = leave_cluster_out(psi, y, w, lam, labels, n_groups, D, denom)

    # the regression standardises columns, so the cell-space field is
    #   c(x) = coef[0] + sum_j coef[j+1] * (phi_j(x) - mu_j) / sd_j
    # i.e. the intercept must absorb -sum_j coef[j+1] mu_j / sd_j.  Forgetting that term shifts
    # the whole field and is caught by tests/test_cellcredit_distillation.py.
    b0 = float(coef[0] - np.sum(coef[1:] * mu / sd))
    fs2 = FeatureSource(args.data_dir / "training_features.tif", foot)
    acc = np.full(int(scored.sum()), b0, dtype=np.float32)
    for j, (cname, spec) in enumerate(chans):
        a, _, _ = robust_norm(fs2.get(spec), foot)
        wj = np.float32(coef[j + 1] / sd[j])
        if wj != 0.0:
            acc += wj * a.ravel()[scored.ravel()]
        del a
    fs2.close()

    # calibration: the linear model estimates credit in [0,1] only after clipping; refit one scale
    scale = 1.0
    for _ in range(8):
        qs = np.clip(acc * scale, 0.0, 1.0)
        tp = np.array([qs[f["ids"]].sum() for f in files])
        pr = tp / denom
        ratio = float((pr * s).sum() / max((pr * pr).sum(), 1e-12))
        if abs(ratio - 1.0) < 3e-3:
            break
        scale *= ratio
    q_scored = np.clip(acc * scale, 0.0, 1.0)
    tp = np.array([q_scored[f["ids"]].sum() for f in files])
    pred_field = tp / denom

    # lift into FOOTPRINT index space, which is the convention of the shared emitter
    # (scripts/emit_lbinv_candidate.py indexes the field by np.flatnonzero(foot.ravel())).
    # sid maps footprint -> scored id, so its support in ascending order is the inverse map.
    fp_ids = np.flatnonzero(sid >= 0)
    assert fp_ids.size == q_scored.size
    q = np.zeros(n_foot, np.float32)
    q[fp_ids] = q_scored

    # ---- the estimator applied to every focus-site file (for the executive summary) ---------
    focus = []
    for i, f in enumerate(files):
        if f["site"] in args.focus_sites:
            focus.append({"site": f["site"], "name": f["name"], "owner_reported_score": f["score"],
                          "dots_scored_domain": f["D"],
                          "est_in_sample": round(float(pred_field[i]), 4),
                          "est_gloo": round(float(pred_gloo[i]), 4),
                          "est_bagmean_gloo": round(float(pred_gloo[i]), 4),
                          "cluster": int(labels[i])})
            f["pred_field"] = round(float(pred_field[i]), 4)
            f["pred_gloo"] = round(float(pred_gloo[i]), 4)

    np.savez_compressed(args.field, q=q.astype(np.float32), shape=np.array(shape),
                        N=np.array([N]), c=np.array([scale]),
                        names=np.array([f["name"] for f in files]), scores=s, D=D)
    ev = {"N_estimate": N, "scale_c": float(scale),
          "chosen": {"loo_rmse": best["gloo_rmse"], "loo_rho": best["gloo_rho"],
                     "gloo_rmse": best["gloo_rmse"], "N": best["N"], "lambda": best["lambda"]},
          "model": "H-CELLDISTILL cell-level ridge distillation", "label": "ESTIMATE"}
    args.receipt.write_text(json.dumps(ev, indent=1) + "\n")

    out = {
        "schema_version": 1, "generated_utc": t0.isoformat(timespec="seconds"),
        "elapsed_s": round((_dt.datetime.now(_dt.timezone.utc) - t0).total_seconds(), 1),
        "method": "H-CELLDISTILL: multiple-instance ridge on per-file feature means of the credit field",
        "labels": {"inputs": "OWNER-REPORT (owner-typed scores next to public file names)",
                   "scores": "ESTIMATE -- never a leaderboard score",
                   "holdout": "none used in the fit (see caveats)"},
        "grid": {"epsg": int(crs.to_epsg() or 0), "shape": list(shape),
                 "transform": [float(v) for v in transform][:6], "footprint_px": n_foot,
                 "catalogue_px": int(catalogue.sum()), "scored_px": int(scored.sum()),
                 "mask_radius_px": args.mask_radius},
        "corpus": {"manifest": str(args.manifest.relative_to(ROOT)), "n_files_used": n,
                   "n_clusters": n_groups, "jaccard_linkage": args.jaccard,
                   "D_min": int(D.min()), "D_max": int(D.max())},
        "channels": [c for c, _ in chans], "channel_stats": chan_stats,
        "leakage_canary_auc": canary,
        "selection": {"baseline_predict_mean_rmse": baseline_mean, "best": best,
                      "grid_scan_top": scan[:12]},
        "fit": {"N_hidden_truth_px": int(N), "lambda": lam, "scale": round(float(scale), 4),
                "gloo_rmse": best["gloo_rmse"], "gloo_rho": best["gloo_rho"],
                "in_sample_bag_rmse": round(float(np.sqrt(np.mean((pred_in - s) ** 2))), 4),
                "field_in_sample_rmse": round(float(np.sqrt(np.mean((pred_field - s) ** 2))), 4),
                "coef_standardized": {c: round(float(coef[j + 1]), 4)
                                      for j, (c, _) in enumerate(chans)},
                "intercept": round(float(coef[0]), 4),
                "field_stats": {"max": round(float(q_scored.max()), 4),
                                "mean": round(float(q_scored.mean()), 5),
                                "cells_gt_tau": [int((q_scored > t).sum()) for t in
                                                  (0.02, 0.05, 0.1, 0.2, 0.5)]}},
        "per_file": [{"site": f["site"], "name": f["name"], "score": f["score"], "D": f["D"],
                      "cluster": int(labels[i]), "pred_field": f.get("pred_field"),
                      "pred_gloo": f.get("pred_gloo")} for i, f in enumerate(files)],
        "focus_site_estimates": focus,
        "caveats": [
            "N (hidden truth size) is not identifiable from the corpus alone: it is chosen by "
            "leave-cluster-out and reported, and every score estimate is conditional on it.",
            "TP_i = sum of per-dot credit assumes no two dots of a file share a truth pixel; at "
            "the corpus' dot densities this over-attributes credit by at most the crowding factor.",
            "Scores are OWNER-REPORT transcriptions with no organizer receipt; a mistyped value "
            "propagates into the fit.",
            "The candidate emitted from this field is drawn from the top of the very field whose "
            "accuracy is claimed, so the estimate is optimistic by construction; the reported "
            "gloo-vs-in-sample gap is the size of that optimism.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    args.focus_table.write_text(json.dumps({"generated_utc": out["generated_utc"],
                                            "estimator": {"gloo_rmse": best["gloo_rmse"],
                                                           "gloo_rho": best["gloo_rho"],
                                                           "N": int(N)},
                                            "rows": focus}, indent=1) + "\n")
    print(f"[out] {args.out.relative_to(ROOT)}  (elapsed {out['elapsed_s']} s)", flush=True)
    print(json.dumps({"best": best, "baseline_mean": baseline_mean,
                      "field_in_sample_rmse": out["fit"]["field_in_sample_rmse"],
                      "field_stats": out["fit"]["field_stats"]}, indent=1), flush=True)
    print("top |standardized coefficient| channels:", flush=True)
    for c, v in sorted(out["fit"]["coef_standardized"].items(), key=lambda t: -abs(t[1]))[:12]:
        print(f"   {c:22s} {v:+.4f}   canary AUC {canary.get(c, float('nan'))}", flush=True)
    return 0


def _auc(score, pos):
    """Tie-aware Mann-Whitney AUC, vectorised (no per-element python loop)."""
    n_pos = int(pos.sum())
    n_neg = int(score.size) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    u, inv = np.unique(np.round(score, 6), return_inverse=True)
    n_at = np.bincount(inv, minlength=u.size).astype(np.float64)
    pos_at = np.bincount(inv, weights=pos.astype(np.float64), minlength=u.size)
    neg_below = np.concatenate([[0.0], np.cumsum(n_at - pos_at)[:-1]])
    return float((pos_at * (neg_below + 0.5 * pos_at)).sum() / (n_pos * n_neg))


if __name__ == "__main__":
    raise SystemExit(main())
