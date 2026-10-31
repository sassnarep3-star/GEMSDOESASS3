#!/usr/bin/env python3
"""Reconstruct the competition grid (``sample_submission.tif``) from the committed footprint receipt.

Why this is needed
------------------
The competition rasters are login-walled (<https://www.drivendata.org/competitions/306/competition-doe-gems/data/>,
verified redirect to a login page).  Several downstream scripts — the leaderboard inversion, the
validator, the dot cache — only need the *grid*, not the labels: the CRS, the shape, the transform
and the boolean footprint of the official sample submission.

Those four things are already committed as a lossless receipt:
``evidence/organizer_footprint_mask.npz`` stores the packed footprint bitmap, the shape, the CRS,
the six transform coefficients, the footprint pixel count and the **SHA-256 of the original
``sample_submission.tif``** that the bitmap was exported from.  This script unpacks that receipt
back into a GeoTIFF so the rest of the pipeline can run unchanged.

It is a reconstruction, not the official file: the pixels are the official footprint (1.0 inside,
0.0 outside) but the byte stream is new, so the original file's SHA-256 will not be reproduced.
Every receipt written downstream records ``grid_source = "reconstructed"``.

Usage
-----
    python scripts/build_grid_reference.py --out .cache/gems_data/sample_submission.tif
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NPZ = ROOT / "evidence" / "organizer_footprint_mask.npz"


def unpack_mask(npz: Path) -> tuple[np.ndarray, dict]:
    d = np.load(npz)
    shape = tuple(int(v) for v in d["shape"])
    bits = np.unpackbits(d["packed"])[: shape[0] * shape[1]]
    mask = bits.reshape(shape).astype(bool)
    meta = {
        "source_npz": str(npz.relative_to(ROOT)),
        "shape": list(shape),
        "crs": str(d["crs"]),
        "transform": [float(v) for v in d["transform"]],
        "footprint_pixels": int(d["footprint_pixels"]),
        "original_sample_submission_sha256": str(d["sample_sha256"]),
    }
    if int(mask.sum()) != meta["footprint_pixels"]:
        raise SystemExit(
            f"footprint pixel count mismatch: mask={int(mask.sum())} receipt={meta['footprint_pixels']}"
        )
    return mask, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--npz", type=Path, default=DEFAULT_NPZ)
    ap.add_argument("--out", type=Path, default=ROOT / ".cache" / "gems_data" / "sample_submission.tif")
    ap.add_argument("--receipt", type=Path, default=ROOT / "evidence" / "grid_reference_receipt.json")
    args = ap.parse_args()

    import rasterio
    from rasterio.transform import Affine

    mask, meta = unpack_mask(args.npz)
    transform = Affine(*meta["transform"])
    arr = np.where(mask, 1.0, np.nan).astype(np.float32)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        args.out, "w", driver="GTiff", height=mask.shape[0], width=mask.shape[1], count=1,
        dtype="float32", crs=meta["crs"], transform=transform, nodata=np.nan, compress="deflate",
    ) as ds:
        ds.write(arr, 1)

    written = args.out.read_bytes()
    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": "RECONSTRUCTED GRID — not the organizer file",
        "out": str(args.out.relative_to(ROOT)) if str(args.out).startswith(str(ROOT)) else str(args.out),
        "sha256_written": hashlib.sha256(written).hexdigest(),
        "original_sample_submission_sha256": meta["original_sample_submission_sha256"],
        "bytes_same_as_original": hashlib.sha256(written).hexdigest()
        == meta["original_sample_submission_sha256"],
        "crs": meta["crs"],
        "shape": meta["shape"],
        "transform": meta["transform"],
        "footprint_pixels": meta["footprint_pixels"],
        "source_npz": meta["source_npz"],
        "note": (
            "The footprint bitmap, CRS, shape and transform are the committed receipt of the official "
            "sample_submission.tif (evidence/organizer_footprint_mask.npz). The GeoTIFF written here is a "
            "re-encoding, so its bytes differ from the organizer file; only geometry and footprint are claimed."
        ),
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({k: receipt[k] for k in ("out", "sha256_written", "crs", "shape", "footprint_pixels")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
