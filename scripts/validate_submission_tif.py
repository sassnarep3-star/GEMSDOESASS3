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


def portal_range_gate(arr: np.ndarray) -> tuple[bool, int]:
    """Reproduce the DrivenData form's literal element-wise range test on the *stored* array.

    The portal compares every stored cell with [0, 1]; NaN and Inf compare False, so a file that puts
    NaN outside the footprint is rejected with "Predicted values must be in range [0, 1]" even when all
    its in-footprint values are legal - measured on 2026-10-30 on the promoted disp21k file (7,111,787
    non-finite stored cells, IR-SASS3-81). The null-outside requirement can therefore be carried by a
    GDAL mask band instead of a NaN payload; both readings of the official sentence are then satisfied.
    Returns (passes, number of violating cells).
    """
    bad = int(np.count_nonzero(~((arr >= 0.0) & (arr <= 1.0))))
    return bad == 0, bad


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
        try:
            mask_flags = sorted({f"{int(f.value)}:{f.name}" for grp in ds.mask_flag_enums for f in grp})
        except Exception:  # noqa: BLE001 - older rasterio / no mask band
            mask_flags = []
        try:
            masked = ds.read(1, masked=True)
            masked_frac = float(np.ma.getmaskarray(masked).mean())
            outside_masked = np.ma.getmaskarray(masked)[0] if np.ma.getmaskarray(masked).ndim == 3 else np.ma.getmaskarray(masked)
        except Exception:  # noqa: BLE001
            masked_frac, outside_masked = 0.0, None
    finite = np.isfinite(arr)
    checks["no_inf_anywhere"] = bool(not np.isinf(arr).any())
    vals = arr[finite]
    checks["values_in_0_1"] = bool(vals.size > 0 and vals.min() >= 0.0 and vals.max() <= 1.0)
    if nodata is not None:
        notes.append(f"nodata declared = {nodata}; official text asks outside-bounds cells to be null or nan")
    # PORTAL GATE (measured 2026-10-30, IR-SASS3-81): the form's element-wise [0,1] test on stored cells.
    checks["portal_range_test_all_cells"], n_range_bad = portal_range_gate(arr)
    if not checks["portal_range_test_all_cells"]:
        notes.append(f"portal range gate FAIL: {n_range_bad} stored cells violate the element-wise [0,1] test "
                     "(this is the live 'Predicted values must be in range [0, 1]' error)")
    # Competition text (page 967): "Your submission has the same bounds as the training data, and data outside
    # the bounds is null or nan." Two encodings satisfy that sentence: a NaN payload, or a finite payload whose
    # outside cells are *masked* by an internal GDAL mask band (rasterio/GDAL report those cells as nodata).
    # Only the second one also survives the portal's range test, so the check is mask-aware and the NaN-only
    # reading is no longer required (IR-SASS3-81, IR-SASS3-74, IR-SASS3-86).
    # Every cell inside the footprint must be finite (no NaN holes). Fail closed without the footprint.
    footprint = _footprint(arr.shape)
    if footprint is None:
        checks["finite_inside_footprint"] = False
        checks["outside_cells_are_null"] = False
        notes.append("PENDING_DATA: footprint unavailable (no sample_submission.tif and no valid committed mask). Fails closed.")
    else:
        checks["finite_inside_footprint"] = bool(np.isfinite(arr[footprint]).all())
        null_out = np.isnan(arr[~footprint]) if outside_masked is None else (np.isnan(arr[~footprint]) | outside_masked[~footprint])
        n_notnull_out = int(np.count_nonzero(~null_out))
        checks["outside_cells_are_null"] = n_notnull_out == 0 and bool(mask_flags or np.isnan(arr[~footprint]).all())
        n_nan_in = int(np.count_nonzero(~finite & footprint))
        how = "internal mask band" if mask_flags else "NaN payload"
        notes.append(f"outside-bounds check: {n_notnull_out} non-null cells outside the footprint, carried by the {how}; "
                     f"{n_nan_in} non-finite cells inside it")
        if not checks["outside_cells_are_null"] and n_notnull_out == 0:
            notes.append("outside cells are finite zeros with no mask band: the official sentence is not met in the GDAL sense")
    checks["nan_outside_and_finite_inside_footprint"] = bool(checks["outside_cells_are_null"] and checks["finite_inside_footprint"])
    if not checks["no_inf_anywhere"]:
        notes.append(f"{int(np.isinf(arr).sum())} infinite cells")
    ok = all(checks.values())
    return {
        "file": path.name,
        "sha256": sha,
        "bytes": path.stat().st_size,
        "checks": checks,
        "mask": {"has_internal_mask_band": bool(mask_flags), "mask_flags": mask_flags,
                 "masked_fraction": round(masked_frac, 6)},
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
