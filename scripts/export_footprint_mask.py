#!/usr/bin/env python3
"""Export the organizer scored-region footprint (finite cells of sample_submission.tif) as a packed mask.

The competition data is not checked in (it lives under .cache/, which is git-ignored). The packed mask lets
the gate check the official outside-bounds rule in a fresh checkout, such as CI. Re-run only when the sample changes.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / ".cache/gems_data/sample_submission.tif"
OUT = ROOT / "evidence/organizer_footprint_mask.npz"


LATTICE = ROOT / ".cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_OUT = ROOT / "evidence/calibration_lattice_mask.npz"


def export_lattice() -> int:
    """Packed positive-cell mask of the 13GEMSDOE calibration lattice (the literal Rule 1 comparator)."""
    if not LATTICE.is_file():
        print(f"missing {LATTICE}; restore the calibration lattice first", file=sys.stderr)
        return 1
    with rasterio.open(LATTICE) as src:
        lat = np.nan_to_num(src.read(1), nan=0.0) > 0.0
        shape = np.array(lat.shape)
    np.savez_compressed(
        LATTICE_OUT,
        packed=np.packbits(lat.ravel()),
        shape=shape,
        source_sha256=np.array(hashlib.sha256(LATTICE.read_bytes()).hexdigest()),
        positive_cells=np.array(int(lat.sum())),
    )
    print(f"wrote {LATTICE_OUT.relative_to(ROOT)}: shape {tuple(int(x) for x in shape)}, positive {int(lat.sum()):,}")
    return 0


def main() -> int:
    if export_lattice():
        return 1
    if not SAMPLE.is_file():
        print(f"missing {SAMPLE}; restore the competition data first", file=sys.stderr)
        return 1
    with rasterio.open(SAMPLE) as src:
        foot = np.isfinite(src.read(1))
        shape = np.array(foot.shape)
        crs = str(src.crs)
        transform = np.array(tuple(src.transform)[:6])
    np.savez_compressed(
        OUT,
        packed=np.packbits(foot.ravel()),
        shape=shape,
        crs=np.array(crs),
        transform=transform,
        sample_sha256=np.array(hashlib.sha256(SAMPLE.read_bytes()).hexdigest()),
        footprint_pixels=np.array(int(foot.sum())),
    )
    print(f"wrote {OUT.relative_to(ROOT)}: shape {tuple(shape)}, footprint {int(foot.sum()):,} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
