#!/usr/bin/env python3
"""E3 - design the emission support to maximise the LIVE-CALIBRATED projection (LLI-v1-S0).

Why this is the right instrument for the decision
-------------------------------------------------
Two local instruments exist and both have measured problems:
  * hide-and-recover on catalogue faults: Spearman 0.14 vs live scores (evidence/proxy_leaderboard_
    concordance.json) and, in E1, it ranks a 1-2 px catalogue collar at 0.405 - the exact opposite of
    the live behaviour of the same idea (GEMSDOE16/29 published catalogue-adjacent and SGMC-adjacent
    files at 0.036 and 0.051).
  * SGMC-CAL: Spearman 0.87 within the dot family, but it rewards "emit the SGMC raster itself"
    (E1 oracle = 0.559) which live scoring punished (GEMSDOE29 sgmc-off-catalogue-44k = 0.0512).
Both are therefore structurally blind to what the leaderboard actually rewards.

LLI-v1-S0 is different in kind: it is a 40-stratum intensity field *inverted from 111 real live
submission scores* (LOO MAE 0.0221, LOO Spearman 0.9259, leave-site-out MAE 0.0224).  Its strata are
distance-to-catalogue x distance-to-the-H19-5 lineament trace, so it states - empirically, from live
outcomes - where label material is dense:

    d_catalogue 20-50 px & 1.4-2 px off an H19-5 trace : lambda = 1.18e-1  (densest)
    d_catalogue  5-10 px & 1.4-2 px off an H19-5 trace  : lambda = 9.2e-2
    d_catalogue 20-50 px & 1.0 px on an H19-5 trace     : lambda = 4.2e-2
    d_catalogue  5-10 px & 1.0 px on an H19-5 trace     : lambda = 3.2e-2
    d_catalogue <= 2 px (any H19-5)                     : lambda <= 8e-4   (dead)

That is a falsifiable geological statement: the expert-mapped new faults run as *sub-parallel strands*
0.5-5 km from the catalogue trace, hugging the same lineaments the H19-5 family detected - not on the
catalogue, and not in the far field.  This script searches emission supports inside that geometry and
reports the LLI projection for each (labelled PROJECTION, never a score), plus the SGMC-CAL and
hide-and-recover numbers for the same supports so the disagreement between instruments is on the record.
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
from gemsdoesass3 import lli, ocm  # noqa: E402


def read_mask(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return (np.isfinite(a) & (a > 0)) & foot


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "evidence/operating_point_E3_design.json"))
    ap.add_argument("--edge-top", type=int, default=400000, help="keep the top-N edge-consensus px as a support filter")
    args = ap.parse_args()
    ddir = data_dir()
    t0 = time.time()

    ctx = holdout.load_holdout_context(ddir)
    foot, labels = ctx.foot, ctx.labels
    spec, lam = lli.build_s0_spec(ddir)
    st = spec.stratum
    cat_lv = spec.stratum_levels[:, 0]
    h_lv = spec.stratum_levels[:, 1]
    lab_cat = spec.level_labels[0]
    lab_h = spec.level_labels[1]
    L = spec.stratum_levels

    # per-stratum lambda lookup by (cat level, h level)
    lam_tab = np.zeros((8, 5), np.float64)
    for sid in range(spec.n_strata):
        c, h = int(L[sid][0]), int(L[sid][1])
        lam_tab[c, h] = lam[sid]
    print("lambda table (rows d_catalogue, cols d_H19-5):", flush=True)
    print("        " + "".join(f"{x:>10}" for x in lab_h), flush=True)
    for ci, cn in enumerate(lab_cat):
        print(f"{cn:>8}" + "".join(f"{v:10.2e}" for v in lam_tab[ci]), flush=True)

    d_cat = distance_transform_edt(~labels)
    # H19-5 trace distance, rebuilt the same way lli.build_s0_spec does
    h195 = read_mask(ddir / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif", foot)
    d_h = distance_transform_edt(~h195)
    active = foot & ~labels

    # edge-consensus ranking surface (same construction as E2, cached)
    work = ROOT / ".cache/gems_work"
    cache = work / "edgeconsensus_E3.npy"
    if cache.is_file():
        E = np.load(cache)
    else:
        fields = ocm.load_fields(ddir)
        acc = np.zeros(foot.shape, np.float32)

        def rank_norm(a):
            v = a[::37]
            v = v[np.isfinite(v)]
            qs = np.quantile(v, np.linspace(0.0, 1.0, 1025))
            idx = np.searchsorted(qs, np.nan_to_num(a, nan=-np.inf), side="right") - 1
            return (np.clip(idx, 0, 1023) / 1023.0).astype(np.float32)

        for name in ocm.EDGE_BANDS:
            acc += rank_norm(np.abs(np.nan_to_num(fields[name], nan=0.0)))
        for name in ("lidar_step_max", "lidar_ex_max", "lidar_relief"):
            acc += rank_norm(fields[name])
        E = (acc / (len(ocm.EDGE_BANDS) + 3)).astype(np.float32)
        E[~active] = 0.0
        work.mkdir(parents=True, exist_ok=True)
        np.save(cache, E)
    print(f"edge surface loaded [{time.time()-t0:.1f}s]", flush=True)

    # family control
    fam = read_mask(ddir / "scored/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", active)

    # --- candidate supports -------------------------------------------------
    h_band = (d_h >= 1.01) & (d_h <= 2.5)          # 1.4-2 px band off the H19-5 trace
    h_on = (d_h >= 0.5) & (d_h < 1.01)             # "on" the trace
    strata_best = active & h_band & (d_cat >= 4.0) & (d_cat <= 51.0)
    strata_mid = active & (h_band | h_on) & (d_cat >= 4.0) & (d_cat <= 51.0)
    n_edge = args.edge_top
    thr_edge = float(np.partition(E[active], (E[active]).size - min(n_edge, int(active.sum())))[(E[active]).size - min(n_edge, int(active.sum()))])
    edge_top = active & (E >= thr_edge)
    sup = {
        "ctl_family_d2_8_44k": fam,
        "S1_hband_x_cat4_50": strata_best,
        "S2_hband_or_hon_x_cat4_50": strata_mid,
        "S3_hband_x_cat4_50_AND_edge_top": strata_best & edge_top,
        "S4_S1_plus_topedge": strata_best | (edge_top & ~h_band),
        "S5_edge_top_120k": top_n(E, 120000, active),
        "S6_edge_top_40k": top_n(E, 40000, active),
        "S7_dil1_of_S3": binary_dilation(strata_best & edge_top, iterations=1) & active,
        "S8_S1_x_lidarvalid": strata_best & (read_u8(ddir / "external/lidar_scarp_features_u8.tif", 12) > 0),
    }

    rows = []
    for name, m in sup.items():
        m = np.asarray(m, bool) & active
        if not m.any():
            continue
        proj = lli.project_lli(m.astype(np.float32), spec, lam)
        off = holdout.evaluate_sgmc_with_ci(m, ctx, n_boot=400)
        hr = holdout.evaluate_hide_and_recover(m, ctx, b_visible_px=2.0, name=name)
        # overlap of this support with the family control (lane metric, one direction)
        d_fam = distance_transform_edt(~fam)
        ys, xs = np.nonzero(m)
        rec = {
            "support": name,
            "emitted_px": int(m.sum()),
            "lli_projected_dti": proj["projected_dti"],
            "lli_band_loo_mae": proj["uncertainty_band_loo_mae"],
            "sgmc_cal_dti": off["sgmc_prevalence_calibrated_dti"],
            "sgmc_cal_ci95": off["sgmc_calibrated_ci95"],
            "hr_dti": hr["pooled_dti"],
            "frac_within_3px_of_family_control": round(float((d_fam[m] <= 3.0).mean()), 4),
            "median_d_catalogue_px": float(np.median(d_cat[m])),
            "median_d_H19_5_px": float(np.median(d_h[m])),
        }
        rows.append(rec)
        print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in rec.items()}), flush=True)

    out = {
        "schema_version": 1,
        "label": "LLI-PROJECTION (NOT A SCORE) + HOLDOUT-DTI on two local instruments",
        "lli_model": "LLI-v1-S0, 40-stratum intensity inverted from 111 live owner-reported scores; LOO MAE 0.0221",
        "lambda_table": {
            "rows_d_catalogue_px": lab_cat,
            "cols_d_H19-5_px": lab_h,
            "lambda": [[float(v) for v in row] for row in lam_tab],
            "K_estimate_px": float(spec.sizes @ lam),
        },
        "rows": rows,
        "runtime_s": round(time.time() - t0, 1),
        "caveat": ("LLI is fit on historical rasters, so projections for supports that leave the probed geometry "
                   "are extrapolations; SGMC-CAL and hide-and-recover disagree with each other and with live "
                   "scores (see docstring). No number here is an organizer score."),
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out} ({time.time()-t0:.1f}s)")
    return 0


def top_n(S: np.ndarray, n: int, active: np.ndarray) -> np.ndarray:
    v = S[active]
    if v.size == 0:
        return np.zeros(S.shape, bool)
    thr = float(np.partition(v, max(0, v.size - n))[max(0, v.size - n)])
    return active & (S >= thr)


def read_u8(path: Path, idx: int) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(idx)


if __name__ == "__main__":
    raise SystemExit(main())
