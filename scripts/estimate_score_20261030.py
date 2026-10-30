#!/usr/bin/env python3
"""Score projections for every file in the executive table, with all inputs named.

The projection is the exact metric evaluated on measured quantities:

    S_hat = x / (x + 0.2*N/M + 0.8*(1 - x)),   x = min(1, eps * e)

    N   dots in the file (measured)
    e   mean kernel credit per footprint cell, i.e. what fraction of the withheld-fault
        credit an area-proportional (eps = 1) field would capture (measured from the file)
    eps enrichment of the field for the withheld faults (measured on the catalogue
        hide-and-recover holdout, or inverted from an owner-reported score)
    M   withheld-fault mass in the scored domain (UNKNOWN; swept over a plausible range)

Only M and eps are unknown for a new file, and both are reported as ranges. Every number
this script writes is labelled MODEL-PROJECTION: it is not a leaderboard score, and the
owner-reported panel it is anchored to is not an organizer receipt.

Usage:
    python scripts/estimate_score_20261030.py --candidate docs/downloads/<file>.tif
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA, RADIUS_PX = 0.2, 0.8, 3.0
M_RANGE = (30_494, 60_988, 121_976, 300_000)   # 0.5x, 1x, 2x, 5x the catalogue mass


def load_footprint() -> np.ndarray:
    fp = np.load(ROOT / "evidence" / "organizer_footprint_mask.npz")
    n = int(fp["shape"][0]) * int(fp["shape"][1])
    return np.unpackbits(fp["packed"])[:n].reshape(tuple(fp["shape"])).astype(bool)


def measure(path: Path, footprint: np.ndarray) -> dict:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    dot = np.isfinite(a) & (a > 0)
    n = int(dot.sum())
    d = distance_transform_edt(~dot)
    e = float(np.maximum(1.0 - d[footprint] / RADIUS_PX, 0.0).mean())
    return {"file": path.name, "n_dots": n, "e_mean_k": round(e, 6),
            "covered_footprint_fraction": round(float((d[footprint] <= RADIUS_PX).mean()), 5)}


def score(n, e, eps, m):
    x = min(1.0, eps * e)
    return x / (x + ALPHA * n / m + BETA * (1.0 - x) + 1e-12)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "score_estimate_20261030.json")
    args = ap.parse_args()

    footprint = load_footprint()
    cand = measure(args.candidate, footprint)
    sweep = json.loads((ROOT / "evidence" / "sweep_tipcont_20261030.json").read_text())
    model = json.loads((ROOT / "evidence" / "focus9_model_20261030.json").read_text())
    built = sweep.get("built_file", sweep["selected"])
    eps_holdout = float(built["enrichment_eps"])
    # Enrichment implied by the 0.2778 champion if its score is explained by the scored subset
    # being fault-dense rather than by the field having skill (inverse solve, M = 1 catalogue).
    eps_selection = float(model["inverse_champion_02778"][1]["implied_enrichment_eps"])
    model = json.loads((ROOT / "evidence" / "focus9_model_20261030.json").read_text())

    rows = []
    for m in M_RANGE:
        for eps, tag in ((1.0, "area-proportional (no enrichment)"),
                         (eps_holdout, "catalogue-holdout enrichment (this file, measured)"),
                         (eps_selection, "champion-implied enrichment under the test-set-selection hypothesis"),
                         (2.0, "twice area-proportional, for sensitivity")):
            rows.append({"withheld_fault_mass_px": m, "enrichment_eps": round(eps, 3),
                         "enrichment_basis": tag,
                         "projected_dti": round(score(cand["n_dots"], cand["e_mean_k"], eps, m), 4)})

    central = score(cand["n_dots"], cand["e_mean_k"], eps_holdout, 60_988)
    skill_rows = [r["projected_dti"] for r in rows
                  if r["enrichment_basis"].startswith(("area-proportional", "catalogue-holdout"))]
    skill_lo, skill_hi = min(skill_rows), max(skill_rows)
    selection = [score(cand["n_dots"], cand["e_mean_k"], eps_selection, m) for m in (30_494, 60_988, 300_000)]

    sites = []
    for r in model["measurements"]:
        if r.get("owner_reported_score") is None:
            continue
        sites.append({"site": r["site"], "file": r["file"], "n_dots": r["n_dots"],
                      "e_mean_k": r["e_mean_k"],
                      "owner_reported_score": r["owner_reported_score"],
                      "model_projection_same_parameters": round(score(
                          r["n_dots"], r["e_mean_k"], model["fit"]["enrichment_eps"],
                          model["fit"]["withheld_fault_mass_M_px"]), 4)})

    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": "MODEL-PROJECTION",
        "warning": ("not a leaderboard score. M (withheld-fault mass) is unknown and is swept; eps for a new "
                    "file comes from the catalogue-recovery holdout, whose transfer to the organizer's new "
                    "faults is unproven"),
        "formula": "S = x/(x + 0.2N/M + 0.8(1-x)), x = min(1, eps*e)",
        "candidate": cand,
        "candidate_eps_holdout": eps_holdout,
        "candidate_projection": {
            "central_skill_hypothesis": round(central, 4),
            "range_skill_hypothesis": [round(skill_lo, 4), round(skill_hi, 4)],
            "range_selection_hypothesis": [round(min(selection), 4), round(max(selection), 4)],
            "basis": ("skill hypothesis: enrichment measured on the catalogue holdout (this file) and M swept "
                      "30k-300k; selection hypothesis: the scored subset is fault-dense, so any field inherits "
                      "the champion-implied enrichment (inverse solve). Both are projections, not scores"),
        },
        "candidate_eps_selection_hypothesis": eps_selection,
        "candidate_grid": rows,
        "focus9_rows": sites,
        "focus9_fit": model["fit"],
        "inverse_champion_02778": model["inverse_champion_02778"],
        "blind_ceiling": model["blind_field_ceiling_grid"],
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({"candidate": cand, "projection": payload["candidate_projection"],
                      "eps_holdout": eps_holdout}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
