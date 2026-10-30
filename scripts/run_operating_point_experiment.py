#!/usr/bin/env python3
"""E2 - ranking-surface and operating-point sweep on the shared off-catalogue proxy.

E1 (scripts/run_geometry_experiment.py) showed three things on the SGMC off-catalogue proxy:
  * the sibling family (37,654-44,090 dots) sits at HOLDOUT-DTI(SGMC-CAL) 0.0579-0.0644;
  * a 1-2 px collar around the catalogue (121k px) scores 0.0089 there while scoring 0.4055 on
    hide-and-recover - the two instruments reward opposite behaviour, which is why an HR-based
    holdout ranks live submissions backwards (IR-SASS3-20);
  * an oracle that emits the proxy truth itself reaches 0.27, so the family is spending ~4x less
    mass than the proxy optimum, not less than the *score* optimum (DTI = TP / (0.2(TP+FP)+0.8K)
    is cheap in FP: at s=0.28 the break-even marginal kernel credit is alpha*s = 0.056).

This script measures whether a better *ranking surface* plus a larger *operating point* moves the
proxy number past the family, using only the official bands and the pinned LiDAR morphometry.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402
from gemsdoesass3 import ocm  # noqa: E402


def rank_norm(a: np.ndarray) -> np.ndarray:
    """Percentile-normalise to [0,1] using a 1.2M-cell systematic sample (memory-safe, deterministic)."""
    v = a[::37]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros(a.shape, np.float32)
    qs = np.quantile(v, np.linspace(0.0, 1.0, 1025))
    idx = np.searchsorted(qs, np.nan_to_num(a, nan=-np.inf), side="right") - 1
    return (np.clip(idx, 0, 1023) / 1023.0).astype(np.float32)


def top_n_mask(S: np.ndarray, n: int) -> np.ndarray:
    pos = np.flatnonzero(S.ravel() > 0)
    if pos.size == 0:
        return np.zeros(S.shape, bool)
    k = min(n, pos.size)
    vals = S.ravel()[pos]
    thr = float(np.partition(vals, vals.size - k)[vals.size - k])
    return S >= thr


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--masses", default="40000,80000,160000,320000")
    ap.add_argument("--out", default=str(ROOT / "evidence/operating_point_experiment_E2.json"))
    args = ap.parse_args()
    ddir = data_dir()
    masses = [int(x) for x in args.masses.split(",")]
    t0 = time.time()

    ctx = holdout.load_holdout_context(ddir)
    active = ctx.foot & ~ctx.labels
    sgmc_truth = np.zeros(ctx.foot.shape, bool)
    sgmc_truth[ctx.sgmc_truth_coords] = True
    print(f"ctx ready [{time.time()-t0:.1f}s] truth={int(sgmc_truth.sum())}", flush=True)

    fields = ocm.load_fields(ddir)

    # V1: consensus of the provided derivative/edge bands + LiDAR scarp morphometry.
    acc = np.zeros(ctx.foot.shape, np.float32)
    per_band_auc = {}
    for name in ocm.EDGE_BANDS:
        acc += rank_norm(np.abs(np.nan_to_num(fields[name], nan=0.0)))
    for name in ("lidar_step_max", "lidar_ex_max", "lidar_relief"):
        acc += rank_norm(fields[name])
    v1 = (acc / (len(ocm.EDGE_BANDS) + 3)).astype(np.float32)
    v1[~active] = 0.0
    print(f"V1 built [{time.time()-t0:.1f}s]", flush=True)

    cache = ROOT / ".cache/gems_work/S_ocm_E1.npy"
    v2 = np.load(cache).astype(np.float32) if cache.is_file() else None
    if v2 is not None:
        v2[~active] = 0.0
    v3 = (0.5 * v1 + 0.5 * rank_norm(v2)) if v2 is not None else None
    if v3 is not None:
        v3[~active] = 0.0

    surfaces = {"edgeconsensus": v1}
    if v2 is not None:
        surfaces["ocm"] = v2
    if v3 is not None:
        surfaces["hybrid_edge_x_ocm"] = v3

    # Reference: what the best live sibling file actually keys on (learning use only).
    ctl = ddir / "scored/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
    d28 = None
    if ctl.is_file():
        with rasterio.open(ctl) as ds:
            a = ds.read(1)
        d28 = (np.isfinite(a) & (a > 0)) & active

        def auc(mask_like: np.ndarray) -> float:
            """AUC of a scalar field separating the live dots from a 1-in-40 systematic background sample."""
            x = np.nan_to_num(mask_like, nan=0.0)
            pos = x[d28]
            neg_idx = np.flatnonzero(active.ravel())[::40]
            neg_idx = neg_idx[~d28.ravel()[neg_idx]]
            neg = x.ravel()[neg_idx]
            if pos.size == 0 or neg.size == 0:
                return float("nan")
            order = np.argsort(np.concatenate([pos, neg]), kind="stable")
            ranks = np.empty(order.size, np.float64)
            ranks[order] = np.arange(order.size, dtype=np.float64)
            r = ranks[: pos.size]
            return float((r.sum() - pos.size * (pos.size - 1) / 2) / (pos.size * neg.size))

        per_band_auc = {k: round(auc(fields[k]), 4) for k in fields}
        per_band_auc = {k: v for k, v in sorted(per_band_auc.items(), key=lambda kv: -abs(kv[1] - 0.5))}
        print("live-dot keying (AUC dots vs background), top 8:",
              dict(list(per_band_auc.items())[:8]), flush=True)

    rows = []
    for sname, S in surfaces.items():
        for n in masses:
            m = top_n_mask(S, n)
            off = holdout.evaluate_sgmc_with_ci(m, ctx, n_boot=600)
            hr = holdout.evaluate_hide_and_recover(m, ctx, b_visible_px=2.0, name=f"{sname}_{n}")
            dcat = float(np.percentile(distance_transform_edt(~ctx.labels)[m], 90))
            rows.append({
                "surface": sname, "target_px": n, "emitted_px": int(m.sum()),
                "sgmc_cal_dti": off["sgmc_prevalence_calibrated_dti"],
                "sgmc_cal_ci95": off["sgmc_calibrated_ci95"],
                "sgmc_raw_dti": off["sgmc_raw_pooled_dti"],
                "hr_dti": hr["pooled_dti"], "hr_ci95": hr["ci95_cluster_bootstrap"],
                "d_catalogue_p90_px": round(dcat, 2),
                "coverage_sgmc_raw": round(float(off["sgmc_raw_pooled_dti"]), 6),
            })
            r = rows[-1]
            print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)

    out = {
        "schema_version": 1,
        "label": "HOLDOUT-DTI on shared instruments; not an organizer score",
        "evaluator_versions": {"sgmc": holdout.SGMC_EVALUATOR_VERSION, "hide_recover": holdout.HIDE_RECOVER_EVALUATOR_VERSION},
        "n_withheld_positives_sgmc": int(sgmc_truth.sum()),
        "family_reference_band": {"GEMSDOE24": 0.057932, "GEMSDOE25/30": 0.06059, "GEMSDOE27": 0.05826,
                                   "GEMSDOE28 h36": 0.062967, "GEMSDOE28 h27-4": 0.06301, "GEMSDOE31": 0.06301,
                                   "GEMSDOE32 champion": 0.064121, "GEMSDOE36": 0.064444,
                                   "source": "evidence/proxy_leaderboard_concordance.json (rerun here reproduces them)"},
        "live_dot_keying_auc": per_band_auc,
        "rows": rows,
        "runtime_s": round(time.time() - t0, 1),
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out} ({time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
