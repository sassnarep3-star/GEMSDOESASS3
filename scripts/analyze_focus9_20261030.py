#!/usr/bin/env python3
"""Measure the nine focus-site historical fields and fit the DTI score model.

Two outputs the task needs:

1. A per-file measurement of everything that enters the official metric and that can be
   observed *without* the withheld labels: dot count, footprint coverage inside the 300 m
   kernel, mean kernel credit per footprint cell (e), and the share of dots that are
   redundant (own no cell, so they buy no kernel credit while still paying the 0.2 FP rate).

2. A two-parameter fit of the exact metric to the nine owner-reported scores:
        S(N) = x / (x + 0.2*N/M + 0.8*(1 - x)),      x = min(1, eps * e(N))
   where M is the withheld-fault mass in the scored domain and eps is the enrichment of the
   field for the withheld faults relative to area. M and eps are fitted; e(N) is measured.
   The analytic inverse of the same equation is used to report the enrichment the 0.2778
   champion must have had, for a range of plausible M.

Labels (protocol rule 3): the fitted numbers are MODEL-PROJECTION on OWNER-REPORT scores.
The owner scores are not organizer receipts (the public leaderboard only exposes the top
rows), so every projection here is explicitly not a score.

Usage:
    python scripts/analyze_focus9_20261030.py --dir .cache/focus9 \
        --out evidence/focus9_model_20261030.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA, RADIUS_PX = 0.2, 0.8, 3.0
FOOTPRINT_NPZ = ROOT / "evidence" / "organizer_footprint_mask.npz"
SCORES = json.loads((ROOT / "registry" / "owner_reported_scores_focus.json").read_text())["entries"]


def load_footprint() -> np.ndarray:
    fp = np.load(FOOTPRINT_NPZ)
    n = int(fp["shape"][0]) * int(fp["shape"][1])
    return np.unpackbits(fp["packed"])[:n].reshape(tuple(fp["shape"])).astype(bool)


def kernel(d):
    return np.maximum(1.0 - np.asarray(d, float) / RADIUS_PX, 0.0)


def measure(tif: Path, footprint: np.ndarray, rng, owner_sample: int = 400_000) -> dict:
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        meta = dict(crs=str(ds.crs), shape=[ds.height, ds.width], dtype=ds.dtypes[0],
                    transform=[float(v) for v in tuple(ds.transform)[:6]],
                    nodata=None if ds.nodata is None else float(ds.nodata))
    finite = np.isfinite(a)
    positive = finite & (a > 0)
    inside = positive & footprint
    outside_positive = int((positive & ~footprint).sum())
    n = int(inside.sum())
    dot = np.zeros(a.shape, bool)
    dot[inside] = True
    if n == 0:
        return dict(file=tif.name, meta=meta, n_dots=0, e_mean_k=0.0, covered_fraction=0.0,
                    outside_positive=outside_positive)
    d = distance_transform_edt(~dot)
    kfield = kernel(d)
    covered = float((d[footprint] <= RADIUS_PX).mean())
    e = float(kfield[footprint].mean())
    # redundancy: how many dots own at least one footprint cell (nearest-dot assignment)
    ys, xs = np.nonzero(dot)
    pts = np.column_stack([ys, xs])
    fy, fx = np.nonzero(footprint)
    idx = rng.choice(fy.size, min(owner_sample, fy.size), replace=False)
    cells = np.column_stack([fy[idx], fx[idx]])
    tree = cKDTree(pts)
    _, owner = tree.query(cells, k=1, workers=-1)
    owners = np.unique(owner)
    n_eff = int(np.ceil(owners.size * (fy.size / cells.shape[0])))
    nn = tree.query(pts, k=2)[0][:, 1] if n > 1 else np.zeros(1)
    return dict(
        file=tif.name, meta=meta, n_dots=n, outside_positive=outside_positive,
        e_mean_k=round(e, 6), covered_fraction=round(covered, 5),
        redundant_dot_fraction=round(1.0 - min(1.0, n_eff / n), 4),
        n_effective_dots_est=n_eff,
        nn_dist_median=round(float(np.median(nn)), 3),
        frac_nn_le_1=round(float((nn <= 1).mean()), 4),
        frac_nn_le_3=round(float((nn <= 3).mean()), 4),
    )


def model_score(n, m, eps, e):
    x = min(1.0, eps * e)
    v = ALPHA * n / m
    return x / (x + v + BETA * (1.0 - x) + 1e-12)


def solve_capture(s: float, n: float, m: float) -> float:
    """Invert S = x/(x + 0.2N/M + 0.8(1-x)) for the captured kernel credit x."""
    v = ALPHA * n / m
    return s * (v + BETA) / (1.0 - ALPHA * s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=ROOT / ".cache" / "focus9")
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "focus9_model_20261030.json")
    args = ap.parse_args()

    footprint = load_footprint()
    rng = np.random.default_rng(20261030)
    rows = []
    for e in SCORES:
        tif = args.dir / f"{e['repo_dir'].replace('-main', '')}__{Path(e['file']).name}"
        if not tif.exists():
            print("MISSING", tif)
            continue
        m = measure(tif, footprint, rng)
        m.update(site=e["site"], prompt_name=e["prompt_name"], owner_reported_score=e["owner_reported_score"],
                 source_url=f"https://github.com/buffedlizard55-lab/{e['repo_dir'].replace('-main', '')}"
                            f"/blob/HEAD/{e['file']}")
        rows.append(m)
        print(f"{m['site']:10s} n={m['n_dots']:6d} e={m['e_mean_k']:.5f} cov={m['covered_fraction']:.4f} "
              f"red={m['redundant_dot_fraction']:.3f} score={m['owner_reported_score']}")

    # ---- fit (M, eps) on the historical-best subset (one row per distinct owner score)
    hist = [r for r in rows if r["owner_reported_score"] is not None and r["n_dots"] > 0]

    def resid(p):
        log_m, log_eps = p
        m, eps = np.exp(log_m), np.exp(log_eps)
        return np.array([model_score(r["n_dots"], m, eps, r["e_mean_k"]) - r["owner_reported_score"] for r in hist])

    best = None
    for m0 in (3e4, 6e4, 1.2e5, 3e5):
        for eps0 in (1.0, 3.0, 10.0):
            sol = least_squares(resid, [np.log(m0), np.log(eps0)], bounds=([np.log(1e3), np.log(0.2)],
                                                                          [np.log(1e7), np.log(1e3)]))
            if best is None or sol.cost < best.cost:
                best = sol
    m_fit, eps_fit = float(np.exp(best.x[0])), float(np.exp(best.x[1]))
    fitted = [dict(site=r["site"], n_dots=r["n_dots"], observed=r["owner_reported_score"],
                   model=round(model_score(r["n_dots"], m_fit, eps_fit, r["e_mean_k"]), 6)) for r in hist]
    rmse = float(np.sqrt(np.mean([(f["model"] - f["observed"]) ** 2 for f in fitted])))

    # ---- inverse: enrichment implied by 0.2778 for a range of withheld-fault masses
    champ = next(r for r in rows if r["site"] == "GEMSDOE32")
    inverse = []
    for m_assumed in (30_494, 60_988, 121_976, 300_000):
        x = solve_capture(0.2778, champ["n_dots"], m_assumed)
        inverse.append(dict(withheld_fault_mass_px=m_assumed, captured_credit_x=round(x, 4),
                            implied_enrichment_eps=round(x / champ["e_mean_k"], 2),
                            implied_gain_over_area_proportional=round(x / champ["e_mean_k"], 2)))

    # ---- analytic ceiling for a blind field (eps = 1) and optimum over the dot budget
    grid = []
    for n in (12_000, 24_000, 40_000, 60_000, 100_000, 150_000, 200_000, 300_000):
        # e(N) from the measured Poisson relation: e = 0.55 * (1 - exp(-29N/A)), anchored at N=24k
        e_pred = float(min(0.9, 0.55 * (1.0 - np.exp(-29.0 * n / footprint.sum()))))
        grid.append(dict(n_dots=n, e_expected=round(e_pred, 5),
                         score_eps1=round(model_score(n, m_fit, 1.0, e_pred), 4),
                         score_eps_fit=round(model_score(n, m_fit, eps_fit, e_pred), 4),
                         score_eps_2=round(model_score(n, m_fit, 2.0, e_pred), 4)))

    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": "MODEL-PROJECTION on OWNER-REPORT scores (not organizer receipts, not a score)",
        "model": "S = x/(x + 0.2N/M + 0.8(1-x)), x = min(1, eps*e); e measured per file",
        "alpha_beta_radius": [ALPHA, BETA, RADIUS_PX],
        "scores_source": "registry/owner_reported_scores_focus.json (OWNER-REPORT, typed in the task prompt)",
        "measurements": rows,
        "fit": {"withheld_fault_mass_M_px": round(m_fit, 1), "enrichment_eps": round(eps_fit, 3),
                "rmse": round(rmse, 5), "n_points": len(fitted), "rows": fitted,
                "caveat": ("M and eps are degenerate in this family because e(N) barely varies over "
                           "37k-61k dots; the fit is therefore informative about scale, not about either "
                           "parameter separately")},
        "inverse_champion_02778": inverse,
        "blind_field_ceiling_grid": grid,
        "footprint_cells": int(footprint.sum()),
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"fit M={m_fit:,.0f} eps={eps_fit:.2f} rmse={rmse:.4f} n={len(fitted)}")
    print("inverse:", inverse)
    print("grid:", grid)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
