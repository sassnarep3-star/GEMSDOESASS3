#!/usr/bin/env python3
"""Programmatic submission-format validator (no human inspection).

Checks the requirements stated in the official problem description
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format):
  * projected CRS EPSG:32611 (UTM 11N), 100 m grid
  * same bounds as training data: shape 3730 x 3292, transform (100, 0, 243350, 0, -100, 4508550)
    (grid spec recorded in data/prepared_manifest.json and docs/data/*.json)
  * single layer, dtype float32
  * values in [0, 1] (the source of the "Predicted values must be in range [0, 1]" error)
  * no Inf anywhere; NaN is REQUIRED outside the footprint and FORBIDDEN inside it (official: outside bounds is null or nan)
  * nodata handling is reported explicitly

Exit code 0 only when every hard check passes. Writes a JSON receipt when --out is given.
Footprint source: sample_submission.tif when present, otherwise evidence/organizer_footprint_mask.npz (checked against
the recorded sample SHA-256). If neither is usable the footprint check is PENDING and the validator fails closed.
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


FOOTPRINT_NPZ = Path(__file__).resolve().parents[1] / "evidence" / "organizer_footprint_mask.npz"
SAMPLE_SHA256 = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"  # sample_submission.tif (data/restore_receipt.json)


def _footprint(shape):
    """Boolean mask of the organizer footprint (finite cells of sample_submission.tif), or None.

    Source order: (1) sample_submission.tif when it is present locally; (2) the committed
    evidence/organizer_footprint_mask.npz exported from that sample (bit-packed; its recorded
    sample_sha256 must equal SAMPLE_SHA256). Returns None (fail closed) if neither is usable.
    """
    for cand in (Path(".cache/gems_data/sample_submission.tif"), Path("/tmp/gems_data/sample_submission.tif")):
        if cand.exists():
            with rasterio.open(cand) as src:
                a = src.read(1)
            if a.shape != tuple(shape):
                return None
            return np.isfinite(a)
    if FOOTPRINT_NPZ.exists():
        with np.load(FOOTPRINT_NPZ) as z:
            if str(z["sample_sha256"]) != SAMPLE_SHA256:
                return None
            h, w = (int(v) for v in z["shape"])
            if (h, w) != tuple(shape):
                return None
            bits = np.unpackbits(z["packed"])[: h * w].reshape(h, w).astype(bool)
            if int(bits.sum()) != int(z["footprint_pixels"]):
                return None
            return bits
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
    checks["no_inf_anywhere"] = bool(not np.isinf(arr).any())
    vals = arr[finite]
    checks["values_in_0_1"] = bool(vals.size > 0 and vals.min() >= 0.0 and vals.max() <= 1.0)
    if nodata is not None:
        notes.append(f"nodata declared = {nodata}; official text asks outside-bounds cells to be null or nan")
    # Competition text (page 967): "Your submission has the same bounds as the training data, and data outside
    # the bounds is null or nan." Every cell outside the footprint must therefore be NaN (not zero, not finite).
    # Every cell inside the footprint must be finite (no NaN holes). Fail closed without the footprint.
    footprint = _footprint(arr.shape)
    if footprint is None:
        checks["nan_outside_and_finite_inside_footprint"] = False
        notes.append("PENDING_DATA: footprint unavailable (no sample_submission.tif and no valid committed mask). Fails closed.")
    else:
        n_finite_out = int(np.count_nonzero(finite & ~footprint))
        n_nan_in = int(np.count_nonzero(~finite & footprint))
        checks["nan_outside_and_finite_inside_footprint"] = (n_finite_out == 0) and (n_nan_in == 0)
        notes.append(f"footprint check: {n_finite_out} finite cells outside the footprint; {n_nan_in} NaN cells inside it")
    if not checks["no_inf_anywhere"]:
        notes.append(f"{int(np.isinf(arr).sum())} infinite cells")
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
