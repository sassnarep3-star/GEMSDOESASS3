#!/usr/bin/env python3
"""Calibrate the field-sum score estimator leave-cluster-out, then re-price every published file.

The candidate build first priced itself with the bag predictor and produced an absurd 493, because
a model fitted on *bag means* has no information about within-bag ranking: extrapolating its top
tail 10x past any corpus value is not measurement.  This script therefore treats the field sum

    A_i = ( sum_{x in P_i} q(x) ) / (0.2 D_i + 0.8 N)

as an *estimator to be calibrated*, not as a score, and fits one scalar k by leave-cluster-out
regression through the origin against the published scores.  The same k then prices the candidate.
Reported next to the predict-mean baseline and next to the bag model's leave-cluster-out error, so
the choice of headline estimator is evidence and not preference.

Usage
-----
    python scripts/calibrate_fieldsum_20261031.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
ALPHA, BETA = 0.2, 0.8
from compare_estimators_20261031 import _mod  # noqa: E402

DIST = _mod("distill_cellcredit_20261031.py")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--psi", type=Path, default=ROOT / ".cache" / "cell_psi.npz")
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "distill_q_cellcredit.npz")
    ap.add_argument("--arms", type=Path, default=ROOT / "evidence" / "estimator_arms_20261031.json")
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "fieldsum_calibration_20261031.json")
    ap.add_argument("--n-grid", type=float, nargs="*", default=[1500, 3000, 6000, 12000, 24000, 44000])
    a = ap.parse_args()

    z = np.load(a.psi)
    ids_cat, offs, s, Dv, labels = z["ids"], z["offs"], z["s"], z["D"], z["labels"]
    ids = [ids_cat[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
    n = len(ids)
    n_groups = int(labels.max() + 1)
    with rasterio.open(a.data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(a.data_dir / "labels.tif") as ds:
        lab = ds.read(1)
    catalogue = (np.isfinite(lab) & (lab >= 1)) & foot
    scored = foot & ~catalogue
    grid_of_fp = np.flatnonzero(foot.ravel())
    fp_of_grid = np.full(foot.size, -1, np.int64)
    fp_of_grid[grid_of_fp] = np.arange(int(foot.sum()))
    fp_scored = fp_of_grid[np.flatnonzero(scored.ravel())]

    rows = []
    for N in a.n_grid:
        q = np.load(a.field)["q"].astype(np.float64)
        denom = ALPHA * Dv + BETA * N
        q_scored = q[fp_scored]
        A = np.array([q_scored[i].sum() for i in ids]) / denom
        # k by leave-cluster-out: fit on the other clusters, price the withheld ones
        pred = np.zeros(n)
        for g in range(n_groups):
            tr, te = labels != g, labels == g
            k = float((A[tr] * s[tr]).sum() / max((A[tr] * A[tr]).sum(), 1e-12))
            pred[te] = k * A[te]
        row = {"N": int(N), "k": round(k, 4),
               "gloo_rmse": round(float(np.sqrt(np.mean((pred - s) ** 2))), 5),
               "gloo_rho": round(DIST.spearman(pred, s), 4),
               "in_sample_rmse": round(float(np.sqrt(np.mean((A - s) ** 2))), 5)}
        rows.append(row)
        print(row, flush=True)
        del q_scored, q
    best = min(rows, key=lambda r: r["gloo_rmse"])
    base = float(np.sqrt(np.mean((s - s.mean()) ** 2)))
    print(json.dumps({"best": best, "baseline_predict_mean": round(base, 5),
                      "bag_model_gloo": json.loads(a.arms.read_text())["best"]["gloo_rmse"]},
                     indent=1), flush=True)
    a.out.write_text(json.dumps({
        "schema_version": 1, "label": "ESTIMATE", "score_inputs": "OWNER-REPORT",
        "estimator": "field sum of the H-CELLDISTILL credit field, single scalar k, leave-cluster-out",
        "n_files": n, "n_clusters": n_groups, "grid": rows, "best": best,
        "baseline_predict_mean_rmse": round(base, 5),
        "caveats": ["k is fitted on the same corpus, so even the leave-cluster-out number is "
                    "conditional on the published scores being transcribed correctly",
                    "the field is a bag-mean fit: within-bag ranking is only weakly identified, "
                    "which is why the raw field sum (A, in-sample column) over-prices everyone"],
    }, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
