#!/usr/bin/env python3
"""Prove a necessary (not sufficient) uniqueness stop from one lattice witness.

This is a read-only preflight, not the required full surface/final-dot registry
comparison and not a geological experiment. Threshold equality is allowed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from geotiff_audit import template_geometry
from restore_audit_inputs import MANIFEST, load_manifest, sha256_file
from io_safety import protect_inputs

ROOT = Path(__file__).resolve().parents[1]


def bound(k: int, uncovered: int, footprint_pixels: int) -> dict:
    """At least max(0, k - uncovered) positive pixels must be in the halo."""
    if type(k) is not int or type(uncovered) is not int or type(footprint_pixels) is not int:
        raise ValueError("counts must be integers")
    if footprint_pixels < 1 or uncovered < 0 or uncovered > footprint_pixels or k < 1 or k > footprint_pixels:
        raise ValueError("counts must describe a nonempty in-footprint candidate")
    minimum = max(0, k - uncovered)
    # Exact arithmetic: minimum/k > 7/10, without float boundary rounding.
    forced_stop = 10 * minimum > 7 * k
    # The first K with 3*K > 10*uncovered, if it exists in the footprint.
    first = (10 * uncovered) // 3 + 1
    return {
        "candidate_dot_budget": k,
        "uncovered_pixels": uncovered,
        "minimum_overlapping_dots": minimum,
        "minimum_overlap_fraction": minimum / k,
        "threshold": 0.7,
        "forced_duplicate_stop": forced_stop,
        "first_forced_stop_budget": first if first <= footprint_pixels else None,
        "interpretation": "A forced stop is conclusive for this witness; absence of a proof is NOT a novelty pass.",
    }


def evaluate(template: Path, lattice: Path, k: int) -> dict:
    geom = template_geometry(template)
    fp = geom["footprint"]
    with rasterio.open(lattice) as ds:
        if (ds.count != 1 or ds.shape != geom["shape"] or ds.crs != geom["crs"]
                or ds.transform != geom["transform"]):
            raise ValueError("registry witness does not match template geometry")
        if ds.driver != "GTiff" or len(ds.files) != 1:
            raise ValueError("registry witness has external sidecars or is not a GeoTIFF")
        a = ds.read(1)
        inside = a[fp]
        if not (ds.read_masks(1)[fp] != 0).all():
            raise ValueError("witness contains masked pixels inside the footprint")
        if not np.isfinite(inside).all() or not np.isin(inside, [0, 1]).all():
            raise ValueError("witness must be a finite binary dot raster inside the footprint")
        support = (a > 0) & fp
    if not support.any():
        raise ValueError("empty witness has no useful overlap geometry")
    distance = distance_transform_edt(~support)
    covered = fp & (distance <= 3.0)
    result = bound(k, int((fp & ~covered).sum()), int(fp.sum()))
    result.update(
        witness_positive_pixels=int(support.sum()),
        covered_footprint_pixels=int(covered.sum()),
        footprint_pixels=int(fp.sum()),
        radius_pixels=3,
        template_sha256=sha256_file(template),
        witness_sha256=sha256_file(lattice),
        evidence_class="COMPUTED — not a score",
        pinned_manifest_verified=False,
        sample_provenance="Caller-supplied; organizer authentication and manifest membership not established by evaluate().",
        scope="One caller-supplied witness; its registry membership and the complete registry are not established here.",
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--dots", type=int, default=37654)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        entries = {e["id"]: e for e in load_manifest()["files"]}
        for name in ("template", "lattice"):
            e = entries[name]
            if sha256_file(args.data_dir / e["destination"]) != e["sha256"]:
                raise ValueError(f"Pinned {name} hash mismatch")
        if args.out:
            protect_inputs(args.out, [MANIFEST, args.data_dir / entries["template"]["destination"],
                                      args.data_dir / entries["lattice"]["destination"]])
        r = evaluate(args.data_dir / entries["template"]["destination"],
                     args.data_dir / entries["lattice"]["destination"], args.dots)
        r["pinned_manifest_verified"] = True
        r["sample_provenance"] = "Owner mirror with manifest-verified bytes; not independently authenticated by the organizer."
        r["scope"] = "One pinned historical registry witness, not the complete current registry."
        text = json.dumps(r, indent=2, allow_nan=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        print(text, end="")
        return 2 if r["forced_duplicate_stop"] else 0
    except (OSError, ValueError, KeyError, rasterio.errors.RasterioError) as exc:
        print(f"Preflight failed closed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
