#!/usr/bin/env python3
"""Honest out-of-sample validation of the emission design (Experiment 3b).

Why a 3-way split and not leave-one-file-out
--------------------------------------------
The corpus is redundant: the champion raster is published in four repositories and the top
family shares 0.87-1.00 of its dots.  Leave-one-*file*-out is therefore nearly in-sample.  Even
leave-one-*family*-out (``scripts/fit_truth_field_20261031.py``) only measures how well T̂ predicts
a raster that was **not** used to build it — it says nothing about a raster that was *optimised
against* T̂, which is what a new candidate is.

This script removes that optimism:

    TRAIN (4/5 of the families)  -> T̂_train -> emit candidate C
    TEST  (1/5 of the families)  -> T̂_test  -> binary truth surrogate  (independent yardstick)
    rasters in TRAIN             -> scored against T̂_test, regressed on their observed scores
                                    -> calibration (a, b)
    estimate(C) = a + b · DTI(C, T̂_test)

Neither C nor the calibration rasters used the TEST families, so both are attenuated by the same
amount and the regression corrects for it.  Rotated over 5 folds; the headline number is the mean
over folds.

Usage:
    python scripts/validate_candidate_20261031.py --n0 12000
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

from gems32 import corpus as CP, fastdti  # noqa: E402
from gems32.corpus import H, W  # noqa: E402

OUT = ROOT / "evidence" / "validate_candidate_20261031.json"

CONFIGS = [
    {"spacing": 3.0, "budget": 60000, "mask_buffer": 0},
    {"spacing": 4.0, "budget": 60000, "mask_buffer": 0},
    {"spacing": 3.0, "budget": 40000, "mask_buffer": 0},
    {"spacing": 4.0, "budget": 60000, "mask_buffer": 2},
]
VARIANTS = ["bp", "gs"]


def field_for(rows, use, n0, variant):
    """q(x) for the emission: back-projection ('bp') or Gram normal-equations solve ('gs')."""
    if variant == "bp":
        lam = CP.backproject_weights(rows, n0)
        return CP.field_from_weights(rows, list(range(len(rows))),
                                     [lam[i] if i in set(use) else 0.0 for i in range(len(rows))])
    lam = CP.solve_weights(rows, n0, mu=1e-3, nonneg=True, use=use)
    return CP.field_from_weights(rows, use, lam)


def emit_spaced(q, keep, spacing, budget=None):
    """Greedy non-max suppression in descending q, minimum spacing ``spacing`` px."""
    cand = np.flatnonzero(keep & (q.reshape(-1) > 0))
    if cand.size == 0:
        return np.zeros(H * W, bool)
    order = cand[np.argsort(-q.reshape(-1)[cand], kind="stable")]
    from scipy.spatial import cKDTree
    kept_ys, kept_xs, chosen = [], [], []
    r = float(spacing)
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
        chosen.append(chunk[ok])
        kept_ys.append(cy[ok])
        kept_xs.append(cx[ok])
        if budget is not None and sum(len(c) for c in chosen) >= budget:
            break
    sel = np.concatenate(chosen) if chosen else np.zeros(0, np.int64)
    if budget is not None:
        sel = sel[:budget]
    out = np.zeros(H * W, bool)
    out[sel] = True
    return out


def buffer_mask(cat, m):
    if m <= 0:
        return np.zeros(H * W, bool)
    from scipy import ndimage as ndi
    yy, xx = np.mgrid[-m:m + 1, -m:m + 1]
    disk = (np.hypot(yy, xx) <= m).astype(np.float32)
    return (ndi.convolve(cat.reshape(H, W).astype(np.float32), disk, mode="constant") > 0).reshape(-1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n0", type=float, default=12000.0)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--family-thresh", type=float, default=0.60)
    ap.add_argument("--configs", default="")
    args = ap.parse_args()

    n0 = float(args.n0)
    valid, cat = CP.load_grid()
    rows = CP.load_scored(valid)
    CP.footprint_mean_credit(rows, valid)
    fam, _ = CP.families(rows, args.family_thresh)
    nfam = int(fam.max()) + 1
    # group families into `folds` roughly equal parts
    order = np.argsort(-np.bincount(fam, minlength=nfam))
    fold_of_fam = np.zeros(nfam, int)
    load = np.zeros(args.folds, int)
    for f in order:
        k = int(np.argmin(load))
        fold_of_fam[f] = k
        load[k] += int(np.bincount(fam, minlength=nfam)[f])
    print(f"families={nfam} fold sizes (rasters)={load.tolist()}", flush=True)

    configs = CONFIGS
    if args.configs:
        want = {int(x) for x in args.configs.split(",") if x.strip()}
        configs = [c for i, c in enumerate(CONFIGS) if i in want]

    fold_rows = []
    for k in range(args.folds):
        test_fams = {f for f in range(nfam) if fold_of_fam[f] == k}
        test_i = [i for i in range(len(rows)) if fam[i] in test_fams]
        train_i = [i for i in range(len(rows)) if fam[i] not in test_fams]
        if not test_i or not train_i:
            continue
        T_train = CP.build_T(rows, train_i, n0)
        T_test = CP.build_T(rows, test_i, n0)
        truth = CP.threshold_T(T_test, valid, int(round(n0)))
        TT = fastdti.Truth.from_mask(truth)

        recs = []
        for variant in VARIANTS:
            q_train = field_for(rows, train_i, n0, variant)
            q_train = CP.conv_k(q_train)          # expected credit of a dot at x
            for ci, cfg in enumerate(configs):
                keep = valid & ~buffer_mask(cat, cfg["mask_buffer"])
                dot = emit_spaced(q_train, keep, cfg["spacing"], cfg["budget"] or None)
                nd = int(dot.sum())
                idx = np.flatnonzero(dot)
                x = fastdti.dti_dots(idx, np.ones(idx.size), TT)
                recs.append({"variant": variant, "config": ci, **cfg, "n_dots": nd,
                             "dti_vs_Ttest": x["dti"], "tp": x["tp"], "fp": x["fp"],
                             "coverage": x["coverage"]})
                print(f"  fold {k} {variant} cfg {ci} sp={cfg['spacing']} bd={cfg['budget']} "
                      f"mb={cfg['mask_buffer']} dots={nd:7d} dti={x['dti']:.4f}", flush=True)
        # reference: the champion raster scored on the same independent yardstick
        champ = max(range(len(rows)), key=lambda i: rows[i]["score"])
        xc = fastdti.dti_dots(rows[champ]["idx"], rows[champ]["val"].copy(), TT)
        ref = {"champion_name": rows[champ]["name"], "champion_observed": rows[champ]["score"],
               "champion_dti_vs_Ttest": xc["dti"]}

        # calibration: TRAIN rasters scored against the independent TEST yardstick
        xs, ys = [], []
        for i in train_i:
            r = rows[i]
            d = fastdti.dti_dots(r["idx"], r["val"].copy(), TT)
            xs.append(d["dti"])
            ys.append(r["score"])
        xs = np.array(xs)
        ys = np.array(ys)
        b, a = np.polyfit(xs, ys, 1)
        resid = ys - (a + b * xs)
        rmse = float(np.sqrt(np.mean(resid ** 2)))
        rho = float(np.corrcoef(xs, ys)[0, 1])
        for rec in recs:
            rec["estimate"] = float(a + b * rec["dti_vs_Ttest"])
        ref["champion_estimate"] = float(a + b * ref["champion_dti_vs_Ttest"])
        fold_rows.append({"fold": k, "n_train": len(train_i), "n_test": len(test_i),
                          "reference": ref,
                          "calibration": {"slope": float(b), "intercept": float(a),
                                          "rmse": rmse, "pearson_r": rho,
                                          "mean_observed": float(ys.mean()),
                                          "mean_predicted_raw": float(xs.mean())},
                          "configs": recs})
        print(f"  fold {k}: cal slope={b:.3f} int={a:.4f} r={rho:.3f} rmse={rmse:.4f} "
              + " ".join(f"{rec['variant']}c{rec['config']}={rec['estimate']:.4f}" for rec in recs)
              + f"  CHAMP={ref['champion_estimate']:.4f} (obs {ref['champion_observed']})",
              flush=True)

    # aggregate
    agg = []
    nvar = len(VARIANTS)
    for vi, variant in enumerate(VARIANTS):
        for ci, cfg in enumerate(configs):
            sel = [fr["configs"][j] for fr in fold_rows
                   for j in range(len(fr["configs"]))
                   if fr["configs"][j].get("variant") == variant and fr["configs"][j]["config"] == ci]
            if not sel:
                continue
            vals = [r["estimate"] for r in sel]
            agg.append({"variant": variant, "config": ci, **cfg,
                        "n_folds": len(vals), "mean_estimate": float(np.mean(vals)),
                        "sd_estimate": float(np.std(vals)), "min_estimate": float(np.min(vals)),
                        "mean_dots": float(np.mean([r["n_dots"] for r in sel])),
                        "mean_raw_dti_vs_Ttest": float(np.mean([r["dti_vs_Ttest"] for r in sel]))})
    champ_est = [fr["reference"]["champion_estimate"] for fr in fold_rows]
    agg.sort(key=lambda r: -r["mean_estimate"])

    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "label": "ESTIMATE — honest 5-fold out-of-sample; every input score is OWNER-REPORT",
        "n0": n0, "n_scored_rasters": len(rows), "n_families": nfam,
        "N_bounds": CP.n_bounds(rows),
        "design": ("TRAIN families -> T̂_train -> candidate; TEST families -> T̂_test -> "
                   "independent truth surrogate; TRAIN rasters scored on that surrogate give the "
                   "observed-vs-predicted calibration applied to the candidate"),
        "fold_sizes": load.tolist(),
        "folds": fold_rows,
        "aggregate": agg,
        "champion_reference": {
            "name": fold_rows[0]["reference"]["champion_name"],
            "observed": fold_rows[0]["reference"]["champion_observed"],
            "mean_estimate": float(np.mean(champ_est)),
            "sd_estimate": float(np.std(champ_est)),
            "note": "the same honest yardstick applied to the champion raster (which is never in "
                    "TRAIN for the fold that scores it, because its whole family sits in TEST or "
                    "is excluded from TRAIN) — the number a new candidate must beat",
        },
    }, indent=1))
    print("\nAGGREGATE (sorted):")
    for a in agg:
        print(f"  {a['variant']} cfg{a['config']} sp={a['spacing']} bd={a['budget']} "
              f"mb={a['mask_buffer']} dots={a['mean_dots']:.0f} est={a['mean_estimate']:.4f} "
              f"±{a['sd_estimate']:.4f}")
    print(f"  CHAMPION reference: est={np.mean(champ_est):.4f} ±{np.std(champ_est):.4f} "
          f"(observed 0.2778)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
