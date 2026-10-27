#!/usr/bin/env python3
"""Independently remeasure the stopped H1 overlap; never place or emit dots.

Reconstructs exactly the recorded fixed surface, verifies its raw-pixel hash,
then uses Euclidean distance transform rather than the shared dilation method.
This is verification of the negative result, not a new candidate or experiment.
"""
from __future__ import annotations
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from bootstrap_template import BRIDGE_HASHES, fetch_file, sha256  # noqa: E402
from evidence_io import choose_output  # noqa: E402
from lane_h1 import make_fields  # noqa: E402
from run_h1 import RUNTIME, LATTICE, LATTICE_PATH, LATTICE_REF, LATTICE_REPO, LATTICE_SHA  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="new verification path; never overwrites existing evidence")
    args = parser.parse_args()
    output = choose_output(ROOT / "evidence/h1-overlap-verification.json", args.output)
    original = json.loads((ROOT / "evidence/h1-run-card.json").read_text())
    if original.get("verdict") != "negative" or original.get("raster_sha256") is not None:
        raise ValueError("verification is restricted to the already-stopped H1 run")
    receipt = json.loads((RUNTIME / "evidence/feature_cache.json").read_text())
    if receipt.get("source_sha256") != BRIDGE_HASHES["training_features.tif"]:
        raise ValueError("untrusted feature cache source")
    cached = {int(row["band"]): row for row in receipt["bands"]}
    bands = []
    for i in (2, 12):
        path = RUNTIME / cached[i]["cache_file"]
        if sha256(path) != cached[i]["sha256"]:
            raise ValueError(f"untrusted cached band {i}")
        bands.append(np.load(path, mmap_mode="r"))
    sample = RUNTIME / "data/official/sample_submission.tif"
    if sha256(sample) != BRIDGE_HASHES["sample_submission.tif"]:
        raise ValueError("untrusted sample mirror")
    with rasterio.open(sample) as ref:
        footprint = np.isfinite(ref.read(1))
        grid = ref.shape, ref.crs, ref.transform
    fields, _ = make_fields(*bands, footprint)
    surface = fields["combined_surface"]
    digest = hashlib.sha256(surface.astype("<f4", copy=False).tobytes()).hexdigest()
    if digest != original["surface_sha256"]:
        raise ValueError("reconstructed surface does not match the stopped experiment")
    fetch_file(f"repos/{LATTICE_REPO}/contents/{LATTICE_PATH}?ref={LATTICE_REF}", LATTICE, LATTICE_SHA)
    with rasterio.open(LATTICE) as ds:
        if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError("lattice and sample grids differ")
        a = ds.read(1)
    reference = np.isfinite(a) & (a > 0)
    support = np.isfinite(surface) & (surface > 0)
    if not reference.any() or not support.any():
        raise ValueError("empty support cannot independently verify overlap")
    near = distance_transform_edt(~reference) <= 3.0
    near_count = int((near & support).sum())
    support_count = int(support.sum())
    overlap = near_count / support_count
    original_overlap = original["correlation_overlap_vs_registry"]["fraction_of_positive_surface_within_3px"]
    if abs(overlap - original_overlap) > 1e-12:
        raise ValueError("independent EDT and recorded dilation overlap disagree")
    report = {
        "audit_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": "Verify the existing surface hash and overlap, without placement or a new experiment",
        "method": "Euclidean distance transform on finite positive witness support, radius <= 3 pixels",
        "surface_sha256": digest, "reference_sha256": LATTICE_SHA,
        "positive_surface_pixels": support_count, "positive_surface_within_3px": near_count,
        "independent_overlap": overlap, "original_dilation_overlap": original_overlap,
        "measurements_agree": True, "verdict": "negative — duplicate stop unchanged"
    }
    with output.open("x") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Verified surface hash {digest}; independent overlap={overlap:.6f} ({near_count}/{support_count}); wrote {output}")
    print("No dots, TIFF, upload, slot, or new candidate created.")


if __name__ == "__main__":
    main()
