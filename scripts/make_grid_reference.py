#!/usr/bin/env python3
"""Rebuild the synthetic grid reference ``.cache/gems_data/sample_submission.tif``.

Why this exists: the real ``sample_submission.tif`` lives behind the DrivenData login and is not in
this workspace.  The organizer grid is fully recorded in ``evidence/organizer_footprint_mask.npz``
(np.packbits of the exact finite-cell mask, plus CRS/transform/shape, saved 2026-10-30 from the
owner's authenticated copy; ``sample_sha256`` in that npz names the original's SHA).  Every pipeline
stage only needs a raster with (a) the exact shape/transform/CRS and (b) the exact finite mask, so
this script writes a stand-in with 0.0 inside the footprint and NaN outside (nodata=NaN), and proves
the mask equality against the committed candidate raster byte-for-byte in mask space.

Usage:
    python scripts/make_grid_reference.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    npz_path = ROOT / "evidence" / "organizer_footprint_mask.npz"
    z = np.load(npz_path)
    shape = tuple(int(v) for v in z["shape"])
    transform_vals = [float(v) for v in z["transform"]]
    assert len(transform_vals) == 6, transform_vals
    crs = str(z["crs"])
    n_expected = int(z["footprint_pixels"])
    flat = np.unpackbits(z["packed"])[: shape[0] * shape[1]]
    foot = flat.reshape(shape).astype(bool)
    assert int(foot.sum()) == n_expected, (int(foot.sum()), n_expected)

    arr = np.where(foot, 0.0, np.nan).astype(np.float32)
    out = ROOT / ".cache" / "gems_data" / "sample_submission.tif"
    out.parent.mkdir(parents=True, exist_ok=True)
    transform = rasterio.Affine(transform_vals[0], transform_vals[1], transform_vals[2],
                                transform_vals[3], transform_vals[4], transform_vals[5])
    with rasterio.open(out, "w", driver="GTiff", height=shape[0], width=shape[1], count=1,
                       dtype="float32", crs=crs, transform=transform, nodata=float("nan"),
                       compress="deflate") as ds:
        ds.write(arr, 1)

    # cross-check against the committed candidate: its finite mask must be identical
    checks = {}
    probe = ROOT / "docs" / "downloads" / "gemsdoesass3-lbinv-84262-20261030T0900Z-nanoutside.tif"
    if probe.exists():
        with rasterio.open(probe) as ds:
            a = ds.read(1)
            checks["probe_shape_matches"] = list(a.shape) == list(shape)
            checks["probe_crs_matches"] = str(ds.crs) == crs
            checks["probe_transform_matches"] = [float(v) for v in ds.transform][:6] == transform_vals
            fin = np.isfinite(a)
            checks["probe_finite_mask_identical"] = bool((fin == foot).all())
            checks["probe_mask_mismatch_cells"] = int((fin != foot).sum())
        assert all(checks[k] for k in ("probe_shape_matches", "probe_crs_matches",
                                       "probe_transform_matches", "probe_finite_mask_identical")), checks

    receipt = {
        "schema_version": 1,
        "generated_utc": "2026-10-31",
        "source": "evidence/organizer_footprint_mask.npz (np.packbits mask saved 2026-10-30 from the owner's authenticated sample_submission.tif)",
        "original_sample_sha256_recorded": str(z["sample_sha256"]),
        "output": str(out.relative_to(ROOT)),
        "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "shape": list(shape),
        "transform": transform_vals,
        "crs": crs,
        "footprint_pixels": n_expected,
        "grid_cells": shape[0] * shape[1],
        "outside_cells": shape[0] * shape[1] - n_expected,
        "cross_checks": checks,
        "label": "SYNTHETIC STAND-IN (mask identical to organizer footprint)",
    }
    rp = ROOT / "data" / "grid_reference_receipt_20261031.json"
    rp.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(receipt, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
