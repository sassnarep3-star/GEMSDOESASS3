#!/usr/bin/env python3
"""Post-stop verification of the two raw H1 input-band leakage canaries.

Does not rebuild a surface, alter parameters, place dots, or relax the stop.
The initial run tested the derived fields; this audit checks its raw inputs too.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from bootstrap_template import BRIDGE_HASHES, ensure_template, fetch_file, sha256  # noqa: E402
from evidence_io import choose_output  # noqa: E402
from run_h1 import (RUNTIME, LATTICE, LATTICE_REPO, LATTICE_REF, LATTICE_PATH,
                    LATTICE_SHA, build_fold_crops, leakage_canaries)  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="new audit path; never overwrites existing evidence")
    args = parser.parse_args()
    output = choose_output(ROOT / "evidence/h1-input-audit.json", args.output)
    sys.path.insert(0, str(ensure_template()))
    from gems57 import spatial, uniqueness

    receipt = json.loads((RUNTIME / "evidence/feature_cache.json").read_text())
    if receipt.get("source_sha256") != BRIDGE_HASHES["training_features.tif"]:
        raise ValueError("untrusted feature cache source")
    for name in ("sample_submission.tif", "existing_faults.tif"):
        if sha256(RUNTIME / "data/official" / name) != BRIDGE_HASHES[name]:
            raise ValueError(f"untrusted mirrored raster: {name}")
    cached = {int(row["band"]): row for row in receipt["bands"]}
    bands = {}
    for i, name in ((2, "raw_rtp"), (12, "raw_detrended_elevation")):
        p = RUNTIME / cached[i]["cache_file"]
        if sha256(p) != cached[i]["sha256"]:
            raise ValueError(f"untrusted cached band {i}")
        bands[name] = np.load(p, mmap_mode="r")
    with rasterio.open(RUNTIME / "data/official/sample_submission.tif") as src, \
         rasterio.open(RUNTIME / "data/official/existing_faults.tif") as labels:
        if (src.shape, src.crs, src.transform) != (labels.shape, labels.crs, labels.transform):
            raise ValueError("sample / labels grid mismatch")
        sample = src.read(1)
        footprint = np.isfinite(sample)
        cat = (labels.read(1) == 1) & footprint
        grid = src.shape, src.crs, src.transform
    support = ndi.binary_erosion(footprint & np.isfinite(bands["raw_rtp"]) &
                                 np.isfinite(bands["raw_detrended_elevation"]) &
                                 (np.abs(bands["raw_rtp"]) < 1e18) &
                                 (np.abs(bands["raw_detrended_elevation"]) < 1e18),
                                 structure=np.ones((3, 3), bool), iterations=12, border_value=0)
    folds = build_fold_crops(spatial, cat, footprint)
    rows = leakage_canaries(bands, support, folds)
    fetch_file(f"repos/{LATTICE_REPO}/contents/{LATTICE_PATH}?ref={LATTICE_REF}", LATTICE, LATTICE_SHA)
    cert = uniqueness.saturation_certificate(LATTICE, footprint, cat, expected_grid=grid)
    cert["witness_file"] = ".cache/registry/r13-lattice.tif"
    card = {"audit_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "purpose": "Post-stop raw-input canaries and independent registry coverage; no new candidate or experiment",
            "raw_canaries": rows, "max_raw_auc": max(r["direction_free_auc"] for r in rows),
            "raw_auc_passed": all(r["direction_free_auc"] <= 0.90 for r in rows),
            "sample_matches_catalogue_on_footprint": bool(np.array_equal(sample[footprint] == 1, cat[footprint])),
            "sample_nonzero_pixels": int(((sample > 0) & footprint).sum()),
            "lattice_saturation": cert,
            "provenance": "hash-pinned owner mirrors, not an authenticated organizer sample",
            "verdict": "negative — stop unchanged"}
    with output.open("x") as stream:
        stream.write(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(f"raw AUC max={card['max_raw_auc']:.6f}; lattice: {cert}")
    print(f"sample positive pixels exactly match catalogue={card['sample_matches_catalogue_on_footprint']}; wrote {output}")


if __name__ == "__main__":
    main()
