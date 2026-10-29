#!/usr/bin/env python3
"""Programmatic submission-format validator (no human inspection).

Checks the requirements stated in the official problem description
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format):
  * projected CRS EPSG:32611 (UTM 11N), 100 m grid
  * same bounds as training data: shape 3730 x 3292, transform (100, 0, 243350, 0, -100, 4508550)
    (grid spec recorded in data/prepared_manifest.json and docs/data/*.json)
  * single layer, dtype float32
  * values in [0, 1] (the source of the "Predicted values must be in range [0, 1]" error)
  * no NaN / Inf anywhere in the raster
  * nodata handling is reported explicitly (official text: data outside bounds is null or nan)

Exit code 0 only when every hard check passes. Writes a JSON receipt when --out is given.
Runs the outside-bounds check against sample_submission.tif when it is present; without it the check is PENDING and the
validator fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def _footprint(shape):
    """Boolean mask of finite cells of sample_submission.tif, or None if absent or of the wrong shape."""
    for cand in (Path(".cache/gems_data/sample_submission.tif"), Path("/tmp/gems_data/sample_submission.tif")):
        if cand.exists():
            with rasterio.open(cand) as src:
                a = src.read(1)
            if a.shape != tuple(shape):
                return None
            return np.isfinite(a)
    return None


def validate(path: Path) -> dict:
    checks: dict[str, bool] = {}
    notes: list[str] = []
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with rasterio.open(path) as ds:
        checks["single_band"] = ds.count == 1
        checks["dtype_float32"] = ds.dtypes[0] == "float32"
        checks["crs_epsg_32611"] = ds.crs is not None and ds.crs.to_string() == EXPECTED_CRS
        checks["shape_3730x3292"] = (ds.height, ds.width) == EXPECTED_SHAPE
        tf = tuple(float(v) for v in ds.transform)[:6]
        checks["transform_matches_training_grid"] = all(abs(a - b) < 1e-9 for a, b in zip(tf, EXPECTED_TRANSFORM))
        arr = ds.read(1).astype(np.float64)
        nodata = ds.nodata
    finite = np.isfinite(arr)
    checks["no_nan_or_inf"] = bool(finite.all())
    vals = arr[finite]
    checks["values_in_0_1"] = bool(vals.size > 0 and vals.min() >= 0.0 and vals.max() <= 1.0)
    if not checks["no_nan_or_inf"]:
        notes.append(f"{int((~finite).sum())} non-finite cells")
    if nodata is not None:
        notes.append(f"nodata declared = {nodata}; official text asks outside-bounds cells to be null or NaN")
    # Competition text (page 967): "data outside the bounds is null or nan". Non-zero finite cells outside the
    # organizer footprint fail the rule. Zeros outside are the convention of the owner-scored files (see IR-SASS3-27).
    # Fail closed: without the footprint this check is PENDING and the validator does not pass.
    footprint = _footprint(arr.shape)
    if footprint is None:
        checks["outside_bounds_null_or_zero"] = False
        notes.append("PENDING_DATA: outside-bounds check NOT run; sample_submission.tif footprint is not in this workspace (login-walled). Fails closed.")
    else:
        outside = arr[~footprint]
        n_nonzero_out = int(np.count_nonzero(np.isfinite(outside) & (outside != 0)))
        checks["outside_bounds_null_or_zero"] = n_nonzero_out == 0
        notes.append(f"outside-bounds check: {n_nonzero_out} non-zero finite cells outside the footprint")
    ok = all(checks.values())
    return {
        "file": path.name,
        "sha256": sha,
        "bytes": path.stat().st_size,
        "checks": checks,
        "stats": {
            "min": float(vals.min()) if vals.size else None,
            "max": float(vals.max()) if vals.size else None,
            "positive_pixels": int((vals > 0).sum()),
            "unique_values": int(np.unique(vals).size),
        },
        "notes": notes,
        "all_hard_checks_pass": ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tif", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    rec = validate(args.tif)
    print(json.dumps(rec, indent=1))
    if args.out:
        args.out.write_text(json.dumps(rec, indent=1) + "\n")
    return 0 if rec["all_hard_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
