#!/usr/bin/env python3
"""Inspect exact GeoTIFF bytes; format checks are NOT submission approval.

The sample can be an owner mirror or organizer sample. Its band mask, not its
values, defines the footprint. The official wording asks for null/NaN outside;
the separate raw-array test addresses the reported [0,1] error. Portal behavior
and the provenance of a caller-supplied template are not authenticated here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import rasterio

from restore_audit_inputs import sha256_file
from io_safety import protect_inputs


def template_geometry(path: Path):
    with rasterio.open(path) as src:
        if src.driver != "GTiff" or len(src.files) != 1:
            raise ValueError("template must be a self-contained GeoTIFF without external sidecars")
        if src.count != 1 or src.crs is None or src.crs.to_epsg() != 32611:
            raise ValueError("template must have one band and CRS EPSG:32611")
        t = src.transform
        if not (t.a == 100 and t.b == 0 and t.d == 0 and t.e == -100):
            raise ValueError("template must be a north-up 100 m grid")
        mask = src.read_masks(1) != 0
        if not mask.any():
            raise ValueError("template footprint is empty")
        values = src.read(1)
        if not np.isfinite(values[mask]).all():
            raise ValueError("template footprint contains non-finite values")
        return {
            "shape": src.shape,
            "crs": src.crs,
            "transform": src.transform,
            "footprint": mask,
        }


def validate_tif(path: Path, template: Path) -> dict:
    t = template_geometry(template)
    fp = t["footprint"]
    report = {
        "path": str(path),
        "file_sha256": sha256_file(path),
        "template_sha256": sha256_file(template),
        "template_provenance": "caller-supplied; authenticity not established by this validator",
        "organizer_acceptance": "unknown",
        "submission_approved": False,
    }
    with rasterio.open(path) as src:
        checks = {
            "geotiff_driver": src.driver == "GTiff",
            "single_file": len(src.files) == 1,
            "single_band": src.count == 1,
            "float32": src.count >= 1 and src.dtypes[0] == "float32",
            "crs_matches": src.crs == t["crs"],
            "shape_matches": src.shape == t["shape"],
            "transform_matches": src.transform == t["transform"],
        }
        report.update(crs=str(src.crs), shape=list(src.shape), transform=list(src.transform)[:6],
                      bands=src.count, dtypes=list(src.dtypes), nodata_repr=repr(src.nodata),
                      gdal_files=src.files)
        if src.count < 1 or src.shape != t["shape"]:
            report["checks"] = checks
            report["local_official_profile_pass"] = False
            report["raw_whole_array_finite_range_pass"] = False
            report["conservative_both_profiles_pass"] = False
            report["reason"] = "Pixel checks unavailable: candidate and template have incompatible shape or bands."
            return report
        arr = src.read(1)
        visible = src.read_masks(1) != 0
    inside, outside = arr[fp], arr[~fp]
    finite_inside = np.isfinite(inside)
    outside_null = (~visible[~fp]) | np.isnan(outside)
    checks.update({
        "inside_mask_valid": bool(visible[fp].all()),
        "inside_all_finite": bool(finite_inside.all()),
        "inside_values_in_0_1": bool((finite_inside & (inside >= 0) & (inside <= 1)).all()),
        "outside_null_or_nan": bool(outside_null.all()),
        "outside_zero_or_nan": bool(((outside == 0) | np.isnan(outside)).all()),
    })
    raw_finite = np.isfinite(arr)
    raw_in_range = raw_finite & (arr >= 0) & (arr <= 1)
    report.update(
        checks=checks,
        footprint_pixels=int(fp.sum()),
        inside_nonfinite=int((~finite_inside).sum()),
        inside_out_of_range=int((finite_inside & ((inside < 0) | (inside > 1))).sum()),
        inside_invalid_mask=int((~visible[fp]).sum()),
        outside_unmasked_non_nan=int((~outside_null).sum()),
        inside_min=float(inside.min()) if finite_inside.all() else None,
        inside_max=float(inside.max()) if finite_inside.all() else None,
        raw_nonfinite=int((~raw_finite).sum()),
        raw_out_of_range=int((raw_finite & ((arr < 0) | (arr > 1))).sum()),
        raw_whole_array_finite_range_pass=bool(raw_in_range.all()),
    )
    required = ("geotiff_driver", "single_file", "single_band", "float32", "crs_matches", "shape_matches",
                "transform_matches", "inside_mask_valid", "inside_all_finite", "inside_values_in_0_1",
                "outside_null_or_nan")
    report["local_official_profile_pass"] = all(checks[k] for k in required)
    report["conservative_both_profiles_pass"] = bool(
        report["local_official_profile_pass"] and report["raw_whole_array_finite_range_pass"]
    )
    report["qualification"] = (
        "Local checks only. An internal mask can make outside pixels null while retaining "
        "finite raw bytes, but the organizer's actual reader and acceptance are unknown. "
        "No format check establishes novelty, holdout performance or slot authorization."
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        report = validate_tif(args.candidate, args.template)
        encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.out:
            # Include every GDAL-visible sidecar, not only the main TIFF paths.
            with rasterio.open(args.template) as sample:
                template_files = [Path(p) for p in sample.files]
            candidate_files = [Path(p) for p in report.get("gdal_files", [])]
            protect_inputs(args.out, [args.candidate, args.template, *candidate_files, *template_files])
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
        # Fail closed on either profile given the reported portal ambiguity; even 0 is not approval.
        return 0 if report["conservative_both_profiles_pass"] else 2
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
