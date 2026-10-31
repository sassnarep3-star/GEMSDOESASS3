#!/usr/bin/env python3
"""Anchor calibration: convert the held-out yardstick score of a candidate into a leaderboard estimate.

The 5-fold yardstick (``scripts/validate_candidate_20261031.py``) is built from only 20 % of the
corpus families, so it is *attenuated*: for any dot set P, DTI(P, T̂_test) < DTI(P, T*) because
T̂_test spreads the truth over more cells than the true 12 000-pixel set does.  The attenuation
depends on the blur of the yardstick, not on P, so it can be measured with anchors: published
rasters whose observed (OWNER-REPORT) score is known and whose own family is excluded from the
yardstick that scores them.

For every fold and every TRAIN raster whose observed score is >= ``--anchor-min``:

    ratio_i = observed_i / estimate_i        (estimate from the fold's own calibration)

and the candidate's estimate is multiplied by the mean ratio.  Using several anchors (not just
the champion) keeps one unusual file from carrying the number.

Usage:
    python scripts/anchor_calibration_20261031.py --n0 12000
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

OUT = ROOT / "evidence" / "anchor_calibration_20261031.json"


def emit_spaced(q, keep, spacing, budget=None):
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n0", type=float, default=12000.0)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--anchor-min", type=float, default=0.15)
    ap.add_argument("--spacing", type=float, default=3.0)
    ap.add_argument("--budget", type=int, default=60000)
    args = ap.parse_args()

    n0 = float(args.n0)
    valid, cat = CP.load_grid()
    rows = CP.load_scored(valid)
    CP.footprint_mean_credit(rows, valid)
    fam, _ = CP.families(rows, 0.60)
    nfam = int(fam.max()) + 1
    order = np.argsort(-np.bincount(fam, minlength=nfam))
    fold_of_fam = np.zeros(nfam, int)
    load = np.zeros(args.folds, int)
    for f in order:
        k = int(np.argmin(load))
        fold_of_fam[f] = k
        load[k] += int(np.bincount(fam, minlength=nfam)[f])

    per_fold = []
    for k in range(args.folds):
        test_fams = {f for f in range(nfam) if fold_of_fam[f] == k}
        test_i = [i for i in range(len(rows)) if fam[i] in test_fams]
        train_i = [i for i in range(len(rows)) if fam[i] not in test_fams]
        T_test = CP.build_T(rows, test_i, n0)
        TT = fastdti.Truth.from_mask(CP.threshold_T(T_test, valid, int(round(n0))))

        # full calibration on TRAIN rasters
        xs, ys = [], []
        for i in train_i:
            d = fastdti.dti_dots(rows[i]["idx"], rows[i]["val"].copy(), TT)
            xs.append(d["dti"])
            ys.append(rows[i]["score"])
        xs, ys = np.array(xs), np.array(ys)
        b, a = np.polyfit(xs, ys, 1)

        # candidate
        q = CP.conv_k(CP.field_from_weights(
            rows, train_i, CP.solve_weights(rows, n0, mu=1e-3, nonneg=True, use=train_i)))
        dot = emit_spaced(q, valid, args.spacing, args.budget or None)
        idx = np.flatnonzero(dot)
        xc = fastdti.dti_dots(idx, np.ones(idx.size), TT)
        cand_raw = xc["dti"]
        cand_est = float(a + b * cand_raw)

        # anchors: TRAIN rasters whose observed score is high AND whose family is not in TEST
        ratios, anch = [], []
        for i in train_i:
            s = rows[i]["score"]
            if s < args.anchor_min:
                continue
            d = fastdti.dti_dots(rows[i]["idx"], rows[i]["val"].copy(), TT)
            est = a + b * d["dti"]
            if est <= 0.01:
                continue
            ratios.append(s / est)
            anch.append({"name": rows[i]["name"], "observed": s, "raw": d["dti"],
                         "estimate": est, "ratio": s / est})
        ratios = np.array(ratios)
        per_fold.append({
            "fold": k, "n_train": len(train_i), "n_test": len(test_i),
            "calibration": {"slope": float(b), "intercept": float(a)},
            "candidate": {"n_dots": int(idx.size), "raw_dti": cand_raw, "estimate": cand_est},
            "n_anchors": int(ratios.size),
            "anchor_ratio_mean": float(ratios.mean()) if ratios.size else None,
            "anchor_ratio_sd": float(ratios.std()) if ratios.size else None,
            "anchor_ratio_median": float(np.median(ratios)) if ratios.size else None,
            "anchors": sorted(anch, key=lambda r: -r["observed"])[:8],
        })
        print(f"fold {k}: cand_raw={cand_raw:.4f} est={cand_est:.4f} "
              f"anchors={ratios.size} ratio_mean={ratios.mean():.3f} "
              f"median={np.median(ratios):.3f} sd={ratios.std():.3f}", flush=True)

    rm = np.array([f["anchor_ratio_mean"] for f in per_fold if f["anchor_ratio_mean"]])
    ce = np.array([f["candidate"]["estimate"] for f in per_fold])
    cr = np.array([f["candidate"]["raw"] if "raw" in f["candidate"] else f["candidate"]["raw_dti"]
                   for f in per_fold])
    summary = {
        "n_folds": len(per_fold),
        "candidate_raw_mean": float(cr.mean()),
        "candidate_estimate_raw_mean": float(ce.mean()),
        "anchor_ratio_mean": float(rm.mean()),
        "anchor_ratio_sd_across_folds": float(rm.std()),
        "anchored_estimate_mean": float(np.mean(ce * rm)),
        "anchored_estimate_sd": float(np.std(ce * rm)),
        "anchored_estimate_min_fold": float(np.min(ce * rm)),
        "interpretation": ("`candidate_estimate_raw_mean` is the un-corrected held-out number and "
                           "is attenuated because the yardstick uses 20 % of the corpus. "
                           "`anchored_estimate_mean` rescales it by the ratio measured on "
                           "published rasters scored on the same yardstick."),
    }
    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "label": "ESTIMATE — OWNER-REPORT inputs, honest held-out design",
        "n0": n0, "anchor_min": args.anchor_min,
        "config": {"spacing": args.spacing, "budget": args.budget},
        "per_fold": per_fold, "summary": summary,
    }, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
