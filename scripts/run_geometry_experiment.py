#!/usr/bin/env python3
"""E1 - emission-geometry experiment: is the ~0.27 sibling plateau a geometry problem?

Question this answers
---------------------
Every sibling GEMSDOE site that scored well emits a *sparse dotted* set of
37,654-44,090 pixels in a 2-8 px collar around the catalogue, and the family
plateaus at 0.2449-0.2778.  Under the official metric

    DTI = TP_w / (0.2 FP_w + 0.8 FN_w + TP_w),  FN_w = |G| - TP_w
        = TP_w / (0.2 (TP_w + FP_w) + 0.8 |G|)          (because 1 - beta = alpha)

the *support* is the only design variable (soft scaling of a fixed support is
monotone in the scale, so a fixed support is best served by p = 1), and any pixel
that does not become the argmax for an as-yet-uncovered truth pixel is pure FP.
That predicts a specific optimal morphology (1-px skeleton of the predicted trace
network, not Poisson dots, not a dilated corridor) and a specific optimal mass.
Both are measurable on the shared off-catalogue proxy without any new data.

Arms
----
* family controls : the restored sibling rasters with owner-reported scores
* dots_poisson    : Poisson-disk-spaced top-N dots (what the sibling sites do)
* topN            : top-N pixels of the surface, no geometry
* skeleton        : 1-px skeleton of the ridge network enclosing the top-N pixels
* skeleton_dil1   : skeleton thickened by 1 px
* corridor3       : every pixel within 3 px of the network (thick corridor)
* oracle_exact / oracle_dil1 / oracle_dil3 : upper bounds on the proxy

Outputs are labelled HOLDOUT-DTI (instrument + withheld positives + 95% CI) per
protocol rule 3.  Nothing here is an organizer score.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt, label

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402
from gemsdoesass3 import ocm  # noqa: E402

def poisson_disk_mask(S: np.ndarray, n: int, min_sep_px: float = 3.0) -> np.ndarray:
    """Greedy farthest-point (Poisson-disk) sampling of the top-scoring pixels."""
    s = np.where(np.isfinite(S), S, 0.0).astype(np.float32)
    cand = np.flatnonzero(s > 0)
    if cand.size == 0:
        return np.zeros(s.shape, bool)
    order = cand[np.argsort(-s.ravel()[cand], kind="stable")][: max(4 * n, 60_000)]
    oy, ox = np.unravel_index(order, s.shape)
    keep = np.zeros(order.size, bool)
    taken_y: list[int] = []
    taken_x: list[int] = []
    r2 = min_sep_px * min_sep_px
    # coarse occupancy grid for O(1) neighbourhood rejection
    cell = max(1, int(np.ceil(min_sep_px)))
    gh, gw = (s.shape[0] + cell - 1) // cell, (s.shape[1] + cell - 1) // cell
    occ: dict[int, list[int]] = {}
    for i in range(order.size):
        y, x = int(oy[i]), int(ox[i])
        gy, gx = y // cell, x // cell
        ok = True
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                bucket = occ.get((gy + dy) * gw + (gx + dx))
                if not bucket:
                    continue
                for j in bucket:
                    if (taken_y[j] - y) ** 2 + (taken_x[j] - x) ** 2 < r2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if not ok:
            continue
        keep[i] = True
        taken_y.append(y)
        taken_x.append(x)
        occ.setdefault(gy * gw + gx, []).append(len(taken_y) - 1)
        if sum(keep) >= n:
            break
    m = np.zeros(s.shape, bool)
    m[oy[keep], ox[keep]] = True
    return m


def top_n_mask(S: np.ndarray, n: int) -> np.ndarray:
    """Every pixel at or above the value that encloses ``n`` positive pixels."""
    pos = np.flatnonzero(S.ravel() > 0)
    if pos.size == 0:
        return np.zeros(S.shape, bool)
    k = min(n, pos.size)
    vals = S.ravel()[pos]
    thr = float(np.partition(vals, vals.size - k)[vals.size - k])
    return S >= thr


def skeleton_network(S: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """1-px skeleton of the super-level set of S at the threshold enclosing n pixels."""
    from skimage.morphology import skeletonize

    s = np.where(np.isfinite(S), S, 0.0)
    v = s[s > 0]
    if v.size == 0:
        return np.zeros(s.shape, bool), np.zeros(s.shape, bool)
    thr = float(np.partition(v, max(0, v.size - n))[v.size - n])
    region = s >= thr
    skel = skeletonize(region).astype(bool)
    return skel, region


def components_official(mask: np.ndarray, truth: np.ndarray, active: np.ndarray) -> dict:
    """Exact official DTI components for a binary emission on ``active`` (no proxy calibration)."""
    p = np.asarray(mask, bool) & np.asarray(active, bool)
    g = np.asarray(truth, bool) & np.asarray(active, bool)
    n = int(g.sum())
    if n == 0 or not p.any():
        return {"tp": 0.0, "fp": float(p.sum()), "fn": float(n), "n_truth": n, "dti": 0.0, "coverage": 0.0}
    dp = distance_transform_edt(~p)
    k = np.maximum(1.0 - dp[g] / 3.0, 0.0)
    tp = float(k.sum())
    dg = distance_transform_edt(~g)
    kf = np.maximum(1.0 - dg[p] / 3.0, 0.0)
    fp = float((1.0 - kf).sum())
    fn = float(n) - tp
    return {"tp": tp, "fp": fp, "fn": fn, "n_truth": n,
            "dti": float(tp / (tp + 0.2 * fp + 0.8 * fn + 1e-12)), "coverage": tp / n}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--masses", default="20000,40000,80000,160000,320000,640000")
    ap.add_argument("--out", default=str(ROOT / "evidence/geometry_experiment_E1.json"))
    ap.add_argument("--skip-skel", action="store_true")
    ap.add_argument("--reuse-cache", action="store_true", help="reuse .cache/gems_work/S_ocm_E1.npy")
    args = ap.parse_args()
    ddir = Path(args.data_dir) if args.data_dir else data_dir()
    masses = [int(x) for x in args.masses.split(",")]

    t0 = time.time()
    ctx = holdout.load_holdout_context(ddir)
    active = ctx.foot & ~ctx.labels
    truth = ctx.sgmc_truth_coords
    sgmc_truth = np.zeros(ctx.foot.shape, bool)
    sgmc_truth[truth] = True
    print(f"footprint {int(ctx.foot.sum())} px, labels {int(ctx.labels.sum())} px, "
          f"SGMC off-catalogue truth {int(sgmc_truth.sum())} px  [{time.time()-t0:.1f}s]", flush=True)

    work = ROOT / ".cache" / "gems_work"
    work.mkdir(parents=True, exist_ok=True)
    cache = work / "S_ocm_E1.npy"
    if args.reuse_cache and cache.is_file():
        S = np.load(cache)
        print(f"surface reused from {cache}", flush=True)
    else:
        surf = ocm.ocm_surface(ddir)
        fields = ocm.load_fields(ddir)
        S = ocm.add_edge_support(surf["S"], fields)
        np.save(cache, S)
    S = S.astype(np.float32)
    S[~active] = 0.0
    print(f"surface built: positive px {int((S>0).sum())}, max {float(S.max()):.4f}  [{time.time()-t0:.1f}s]", flush=True)

    rows = []

    def emit(tag: str, mask: np.ndarray, extra: dict | None = None) -> dict:
        mask = mask & active
        n = int(mask.sum())
        rec: dict = {"arm": tag, "emitted_px": n}
        if n:
            off = holdout.evaluate_sgmc_with_ci(mask, ctx, n_boot=600)
            hr = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=2.0, name=tag)
            rec["sgmc_raw"] = components_official(mask, sgmc_truth, active)
            rec["sgmc_cal_dti"] = off["sgmc_prevalence_calibrated_dti"]
            rec["sgmc_cal_ci95"] = off["sgmc_calibrated_ci95"]
            rec["sgmc_raw_dti_instrument"] = off["sgmc_raw_pooled_dti"]
            rec["hr_dti"] = hr["pooled_dti"]
            rec["hr_ci95"] = hr["ci95_cluster_bootstrap"]
            rec["hr_n_withheld"] = hr["n_withheld_positives"]
        if extra:
            rec.update(extra)
        rows.append(rec)
        print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v)
                          for k, v in rec.items() if k != "sgmc_raw"}), flush=True)
        return rec

    # ---- family controls (real live submissions, restored + SHA-pinned) ----
    controls = {
        "ctl_GEMSDOE24_h25_1_d1_5_0.2477": "scored/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
        "ctl_GEMSDOE25_d2_8_0.2600": "scored/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
        "ctl_GEMSDOE27_topogap_0.2449": "scored/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif",
        "ctl_GEMSDOE28_h27_4_0.2708": "scored/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif",
    }
    for tag, rel in controls.items():
        p = ddir / rel
        if not p.is_file():
            print("missing control", p)
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        emit(tag, np.isfinite(a) & (a > 0), {"control_owner_score": tag.split("_")[-1]})

    # ---- oracle bounds on the proxy ----
    emit("oracle_exact_truth", sgmc_truth)
    for r in (1, 2, 3):
        emit(f"oracle_dil{r}", binary_dilation(sgmc_truth, iterations=r))

    # ---- collar around the catalogue (the mechanism the sibling family exploits) ----
    d_cat = distance_transform_edt(~ctx.labels)
    emit("collar_cat_1_2px", active & (d_cat >= 1.01) & (d_cat <= 2.0))
    emit("collar_cat_1_3px", active & (d_cat >= 1.01) & (d_cat <= 3.0))
    emit("collar_cat_all", active & (d_cat <= 8.0))

    # ---- geometry arms at matched mass ----
    for n in masses:
        emit(f"topN_{n}", top_n_mask(S, n))
        emit(f"dots_poisson3_{n}", poisson_disk_mask(S, n))
        if not args.skip_skel:
            skel, region = skeleton_network(S, n)
            emit(f"skeleton_{n}", skel, {"skeleton_region_px": int(region.sum())})
            emit(f"skeleton_dil1_{n}", binary_dilation(skel, iterations=1))
            emit(f"corridor3_{n}", binary_dilation(region, iterations=3) & active)

    out = {
        "schema_version": 1,
        "label": "HOLDOUT-DTI on shared instruments (gems32.holdout) + official-formula components on the SGMC off-catalogue proxy",
        "evaluator_versions": {
            "sgmc": holdout.SGMC_EVALUATOR_VERSION,
            "hide_recover": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
            "proxy_truth": "external/derived_sgmc_faults_100m_u8.tif, off-catalogue only (>300 m from labels.tif)",
        },
        "n_withheld_positives": int(sgmc_truth.sum()),
        "footprint_px": int(ctx.foot.sum()),
        "labels_px": int(ctx.labels.sum()),
        "surface": "OCM v1 (orientation-coherent multi-physics structure-tensor consensus + LiDAR scarp/step)",
        "rows": rows,
        "runtime_s": round(time.time() - t0, 1),
        "caveat": "SGMC-CAL and hide-and-recover are proxies. Only SGMC-CAL has a measured rank agreement with the "
                  "owner-reported live scores (Spearman 0.87, n=21, evidence/proxy_leaderboard_concordance.json). "
                  "Neither is an organizer score.",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {args.out}  ({time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
