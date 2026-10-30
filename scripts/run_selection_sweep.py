#!/usr/bin/env python3
"""E3b - mass-matched designs inside the live-calibrated high-intensity strata.

E3 showed two things:
  * the highest-intensity strata of LLI-v1-S0 (1.4-2 px off an H19-5 trace, 5-50 px from the
    catalogue) contain 113,192 px, but emitting all of them (or even the 292,786 px "h-band"
    version) projects *lower* than the live family control, because the projection's FP term grows
    with every emitted pixel while the family's 44,090-px operating point is what 111 live rasters
    actually calibrated;
  * and the same E3 run measured that the family control sits 89% within 3 px of that geometry,
    i.e. the score-optimal geometry collides with the protocol's 70% lane cap.

So the design question is: at the *live-validated mass* (~40-44k px), can an independent selection
rule inside those strata beat the family's projection while staying under the lane cap?  This script
sweeps selection rules and reports LLI projection + both local holdouts + overlap against the family
control for each.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402
from gemsdoesass3 import lli, ocm  # noqa: E402


def read_mask(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return (np.isfinite(a) & (a > 0)) & foot


def rank_norm(a: np.ndarray) -> np.ndarray:
    v = a[::37]
    v = v[np.isfinite(v)]
    qs = np.quantile(v, np.linspace(0.0, 1.0, 1025))
    idx = np.searchsorted(qs, np.nan_to_num(a, nan=-np.inf), side="right") - 1
    return (np.clip(idx, 0, 1023) / 1023.0).astype(np.float32)


def thin_to(m: np.ndarray, score: np.ndarray, n: int, block: int = 3) -> np.ndarray:
    """Keep the ``n`` highest-scoring px of ``m``, thinned so that no two kept px share a 3x3 block.

    Deterministic rank-priority non-maximum suppression on a coarse grid: equivalent to the
    "Poisson-disk at ~block px" thinning the sibling family used, but keyed to our own score.
    """
    s = np.where(m, np.nan_to_num(score, nan=0.0), -np.inf)
    out = np.zeros(m.shape, bool)
    idx = np.flatnonzero(s.ravel() > -np.inf)
    if n <= 0 or idx.size == 0:
        return out
    order = idx[np.argsort(-s.ravel()[idx], kind="stable")]
    H, W = m.shape
    yy, xx = np.unravel_index(order, (H, W))
    occupied: set[tuple[int, int]] = set()
    kept = 0
    for i in range(order.size):
        by, bx = int(yy[i]) // block, int(xx[i]) // block
        if any(((by + dy, bx + dx) in occupied) for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
            continue
        occupied.add((by, bx))
        out[int(yy[i]), int(xx[i])] = True
        kept += 1
        if kept >= n:
            return out
    left = np.flatnonzero(m.ravel() & True)
    left = left[~out.ravel()[left]][: max(0, n - kept)]
    if left.size:
        out.ravel()[left] = True
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--masses", default="40000,44090,60000")
    ap.add_argument("--out", default=str(ROOT / "evidence/operating_point_E3b_selection.json"))
    args = ap.parse_args()
    ddir = data_dir()
    t0 = time.time()
    ctx = holdout.load_holdout_context(ddir)
    foot, labels = ctx.foot, ctx.labels
    spec, lam = lli.build_s0_spec(ddir)
    L = spec.stratum_levels
    lam_tab = np.zeros((8, 5), np.float64)
    for sid in range(spec.n_strata):
        lam_tab[int(L[sid][0]), int(L[sid][1])] = lam[sid]

    h195 = read_mask(ddir / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif", foot)
    d_h = distance_transform_edt(~h195)
    d_cat = distance_transform_edt(~labels)
    active = foot & ~labels

    fields = ocm.load_fields(ddir)
    E = np.zeros(foot.shape, np.float32)
    for name in ocm.EDGE_BANDS:
        E += rank_norm(np.abs(np.nan_to_num(fields[name], nan=0.0)))
    for name in ("lidar_step_max", "lidar_ex_max", "lidar_relief"):
        E += rank_norm(fields[name])
    E /= (len(ocm.EDGE_BANDS) + 3)
    E[~active] = 0.0
    # local ridge prominence: centre value minus the max of the two profile sides perpendicular to dip
    prom = (E - maximum_filter(E, size=5)).astype(np.float32)  # <=0; local prominence against the 5x5 max
    print(f"setup [{time.time()-t0:.1f}s]", flush=True)

    fam = read_mask(ddir / "scored/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", active)
    d_fam = distance_transform_edt(~fam)

    # stratum masks by level code (see lli.build_s0_spec: cat codes 0..7, h codes 0..4)
    cat_lv, h_lv = spec.levels[0], spec.levels[1]
    band_top = active & (h_lv == 3) & np.isin(cat_lv, [5, 6, 7])          # 1.4-2 px off trace, d_cat>=5 px
    band_top_on = active & np.isin(h_lv, [2, 3]) & np.isin(cat_lv, [5, 6, 7])
    band_wide = active & (h_lv >= 2) & np.isin(cat_lv, [4, 5, 6, 7])

    rows = []
    for name, base in {"lam_top2_strata": band_top, "lam_4_strata": band_top_on, "lam_wide": band_wide}.items():
        for n in (int(x) for x in args.masses.split(",")):
            for rule, sc in (("edge", E), ("edge_x_lam", E * np.maximum(0.0, 1.0 + prom)), ("edge_neg_prom", -prom)):
                sel = thin_to(base, sc, n)
                sel = sel & active
                if not sel.any():
                    continue
                proj = lli.project_lli(sel.astype(np.float32), spec, lam)
                off = holdout.evaluate_sgmc_with_ci(sel, ctx, n_boot=400)
                hr = holdout.evaluate_hide_and_recover(sel, ctx, b_visible_px=2.0, name=name)
                rec = {
                    "design": f"{name}/{rule}/{n}", "emitted_px": int(sel.sum()),
                    "lli_projected_dti": proj["projected_dti"], "lli_band": proj["uncertainty_band_loo_mae"],
                    "sgmc_cal_dti": off["sgmc_prevalence_calibrated_dti"], "sgmc_cal_ci95": off["sgmc_calibrated_ci95"],
                    "hr_dti": hr["pooled_dti"],
                    "lane_overlap_vs_family_3px": round(float((d_fam[sel] <= 3.0).mean()), 4),
                }
                rows.append(rec)
                print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in rec.items()}), flush=True)

    famproj = lli.project_lli(fam.astype(np.float32), spec, lam)
    rows.append({"design": "ctl_family_d2_8_44090", "emitted_px": int(fam.sum()),
                 "lli_projected_dti": famproj["projected_dti"], "lli_band": famproj["uncertainty_band_loo_mae"],
                 "lane_overlap_vs_family_3px": 1.0})
    out = {"schema_version": 1, "label": "LLI-PROJECTION (NOT A SCORE) + HOLDOUT-DTI",
           "lambda_tab_rows_d_catalogue": spec.level_labels[0], "lambda_tab_cols_d_H19-5": spec.level_labels[1],
           "rows": rows, "runtime_s": round(time.time() - t0, 1)}
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
