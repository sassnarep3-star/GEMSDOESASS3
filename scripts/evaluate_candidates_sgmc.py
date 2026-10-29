#!/usr/bin/env python3
"""HOLDOUT-DTI evaluation (GEMSDOE32-SGMC-CAL-v3.0) of one or more candidate GeoTIFFs.

Reuses src/gems32/holdout.py (load_holdout_context, evaluate_sgmc_with_ci) unchanged.
Every number written here is labelled HOLDOUT-DTI with the evaluator name, the number of
withheld off-catalogue positives, and the 95% spatial-cluster bootstrap CI. None of these numbers
is an organizer score.

Usage: python scripts/evaluate_candidates_sgmc.py <out.json> name=path.tif [name=path.tif ...]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402

DDIR = ROOT / ".cache" / "gems_data"
EVAL_VERSION = "GEMSDOE32-SGMC-CAL-v3.0"


def main() -> int:
    out_path = Path(sys.argv[1])
    pairs = [a.split("=", 1) for a in sys.argv[2:]]
    t0 = time.time()
    ctx = holdout.load_holdout_context(DDIR)
    results = {}
    for name, path in pairs:
        with rasterio.open(path) as ds:
            arr = ds.read(1)
        mask = (arr > 0) & np.isfinite(arr)
        r = holdout.evaluate_sgmc_with_ci(mask, ctx, name=name)
        keep = {k: v for k, v in r.items() if not k.startswith("_") and not isinstance(v, np.ndarray)}
        results[name] = {
            "file": str(Path(path).name),
            "dots": int(mask.sum()),
            "score_label": "HOLDOUT-DTI",
            "evaluator_version": EVAL_VERSION,
            "n_withheld_positives": int(ctx.sgmc_n_truth),
            "raw": r.get("sgmc_raw_pooled_dti", r.get("raw_pooled_dti")),
            "calibrated": r.get("sgmc_prevalence_calibrated_dti", r.get("prevalence_calibrated_dti")),
            "calibrated_ci95": r.get("sgmc_calibrated_ci95", r.get("prevalence_calibrated_ci95")),
            "raw_ci95": r.get("sgmc_raw_ci95", r.get("raw_ci95")),
            "all_fields": keep,
        }
        print(name, results[name]["calibrated"], results[name]["calibrated_ci95"], flush=True)
    out = {
        "evaluator_version": EVAL_VERSION,
        "n_withheld_positives": int(ctx.sgmc_n_truth),
        "elapsed_s": round(time.time() - t0, 1),
        "results": results,
    }
    out_path.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
