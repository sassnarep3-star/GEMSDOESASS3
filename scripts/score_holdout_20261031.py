#!/usr/bin/env python3
"""Score arbitrary rasters on the mandated spatially-blocked holdout.

Reuses the official evaluator and the 4 km blocked catalogue split from
``scripts/experiment_catalogue_holdout_20261030.py`` unchanged (protocol rule 2: never fork the
shared tools).  Reports **HOLDOUT-DTI (catalogue-recovery surrogate v1)** with a 95 % block
bootstrap CI, plus the enrichment over a uniform-random baseline at the same dot budget.

Honest caveat, stated in the output: this holdout measures recovery of *catalogue* faults, and
the competition scores expert-mapped faults that are **absent** from the catalogue.  A previous
session measured the rank correlation between this proxy and the owner-reported scores at only
ρ = +0.143 (n = 21) and retired it as a *score proxy*.  It is retained here only because the
parallel-run protocol requires every candidate to be run through the shared holdout before a
submission slot is spent.  It is a gate, not a score.

Usage
    python scripts/score_holdout_20261031.py --tif docs/downloads/<a>.tif --tif <b>.tif \
        --out evidence/holdout_final_20261031.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import experiment_catalogue_holdout_20261030 as E1  # noqa: E402


def dots_from_tif(path: Path):
    with rasterio.open(path) as ds:
        a = ds.read(1)
    ys, xs = np.nonzero(np.isfinite(a) & (a > 0))
    return np.column_stack([ys, xs]), hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", action="append", required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "holdout_final_20261031.json")
    ap.add_argument("--uniform-dots", type=int, default=60000)
    args = ap.parse_args()

    footprint, cat_yx, prev = E1.load_masks()
    held = E1.split_blocks(E1.block_id(cat_yx))
    is_held = np.array([b in held for b in E1.block_id(cat_yx)])
    truth_yx = cat_yx[is_held]

    rng = np.random.default_rng(E1.SEED)
    fy, fx = np.nonzero(footprint)
    pick = rng.choice(fy.size, args.uniform_dots, replace=False)
    uniform_yx = np.column_stack([fy[pick], fx[pick]])

    def score(name, yx):
        s = E1.scores_from_dots(yx, truth_yx, footprint)
        tp = float(s["k_tp"].sum()); fn = float((1 - s["k_tp"]).sum()); fp = float(s["fp_terms"].sum())
        ci = E1.block_bootstrap(s)
        return {"file": name, "n_dots": int(len(yx)),
                "holdout_dti": E1.dti_from_components(tp, fp, fn),
                "ci95": ci, "tp_w": tp, "fp_w": fp, "fn_w": fn}

    rows = [{"strategy": "uniform-random baseline", **score("uniform", uniform_yx)}]
    for t in args.tif:
        yx, sha = dots_from_tif(ROOT / t if not Path(t).is_absolute() else Path(t))
        rows.append({"strategy": Path(t).name, "sha256": sha,
                     **score(Path(t).name, yx)})
    base = rows[0]["holdout_dti"]
    for r in rows[1:]:
        r["enrichment_over_uniform"] = r["holdout_dti"] / max(base, 1e-12)

    cat_bytes = (ROOT / "evidence" / "gsd_hua_map_preview.npz").read_bytes()
    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": "HOLDOUT-DTI (catalogue-recovery surrogate v1)",
        "evaluator_version": E1.EVALUATOR,
        "withheld_positive_cells": int(len(truth_yx)),
        "holdout_blocks": {"block_cells": E1.BLOCK, "block_km": E1.BLOCK * 0.1,
                           "n_blocks": len(held), "fraction": E1.HOLDOUT_FRACTION, "seed": E1.SEED},
        "caveat": ("measures recovery of catalogued faults, not of the withheld new faults the "
                   "leaderboard scores; rank correlation with owner-reported scores was only "
                   "rho=+0.143 (n=21) in the 2026-10-30 session, so this is a gate, not a score"),
        "catalogue_npz_sha256": hashlib.sha256(cat_bytes).hexdigest(),
        "rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    for r in rows:
        print(f"{r['file'][:64]:64s} dots={r['n_dots']:7d} HOLDOUT-DTI={r['holdout_dti']:.4f} "
              f"CI=[{r['ci95'][0]:.4f},{r['ci95'][1]:.4f}] enrich={r.get('enrichment_over_uniform', 1.0):.2f}")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
