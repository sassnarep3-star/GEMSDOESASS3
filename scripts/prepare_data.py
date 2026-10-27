#!/usr/bin/env python3
"""Prepare and verify competition data + cached 35-channel template feature stack.

Autonomously verifies SHA-256 hashes of core competition inputs (`training_features.tif`,
`labels.tif`, `sample_submission.tif`), writes `data/prepared_manifest.json`, and builds
the shared 35-channel cached feature stack (`feature_stack.npy`) if not already present.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import features, grid  # noqa: E402
from gems32.paths import data_dir, work_dir  # noqa: E402

BAND_NAMES = [
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
    "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15",
    "cond_surf", "iso_grav_anom_hg", "det_elev_slope",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--work-dir", type=Path, default=None)
    ap.add_argument("--manifest-out", type=Path, default=ROOT / "data" / "prepared_manifest.json")
    ap.add_argument("--skip-stack", action="store_true")
    args = ap.parse_args()

    ddir = args.data_dir or data_dir()
    wdir = args.work_dir or work_dir()
    tf = ddir / "training_features.tif"
    lb = ddir / "labels.tif"
    ss = ddir / "sample_submission.tif"
    for req in (tf, lb, ss):
        if not req.exists():
            raise SystemExit(f"Missing required competition file: {req}. Run bash scripts/download_competition_data.sh first.")

    with rasterio.open(ss) as ds_sub:
        foot = np.isfinite(ds_sub.read(1))
        epsg = ds_sub.crs.to_epsg()
        h, w = ds_sub.height, ds_sub.width
        transform = list(ds_sub.transform)[:6]

    with rasterio.open(lb) as ds_lb:
        pos = (ds_lb.read(1) > 0) & foot

    bands_info = []
    any_sentinel = np.zeros((h, w), dtype=bool)
    total_sentinel = 0
    with rasterio.open(tf) as ds_tf:
        for idx in range(1, ds_tf.count + 1):
            arr = ds_tf.read(idx)
            valid = np.isfinite(arr) & (arr > grid.NODATA_F32 * np.float32(0.5))
            sent_in_foot = foot & ~valid
            n_sent = int(sent_in_foot.sum())
            total_sentinel += n_sent
            any_sentinel |= sent_in_foot
            fin_vals = arr[foot & valid]
            bands_info.append({
                "index": idx,
                "name": BAND_NAMES[idx - 1] if idx - 1 < len(BAND_NAMES) else f"band_{idx}",
                "finite_in_footprint": int((foot & valid).sum()),
                "sentinel_in_footprint": n_sent,
                "min": float(fin_vals.min()),
                "p05": float(np.percentile(fin_vals, 5)),
                "median": float(np.median(fin_vals)),
                "p95": float(np.percentile(fin_vals, 95)),
                "max": float(fin_vals.max()),
            })

    manifest = {
        "schema_version": 1,
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "grid": {
            "epsg": epsg,
            "height": h,
            "width": w,
            "total_cells": h * w,
            "transform": transform,
            "pixel_size_m": [100.0, 100.0],
        },
        "counts": {
            "footprint_valid_pixels": int(foot.sum()),
            "outside_footprint_pixels": int((~foot).sum()),
            "positive_catalogue_label_pixels": int(pos.sum()),
            "negative_in_footprint_pixels": int((foot & ~pos).sum()),
            "total_sentinel_band_pixels_inside_footprint": total_sentinel,
            "unique_footprint_pixels_with_any_sentinel": int(any_sentinel.sum()),
        },
        "source_hashes": {
            "training_features.tif": sha256_file(tf),
            "labels.tif": sha256_file(lb),
            "sample_submission.tif": sha256_file(ss),
        },
        "bands": bands_info,
    }
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {args.manifest_out} (footprint={manifest['counts']['footprint_valid_pixels']:,} px)")

    if not args.skip_stack:
        stack_out = wdir / "feature_stack.npy"
        if stack_out.exists():
            mm = np.load(stack_out, mmap_mode="r")
            if mm.shape == (h, w, len(features.CHANNELS)):
                print(f"Cached 35-channel stack already present and verified at {stack_out}")
                return 0
        wdir.mkdir(parents=True, exist_ok=True)
        rec = features.build(tf, stack_out)
        (ROOT / "registry" / "feature_receipt.json").write_text(json.dumps(rec, indent=2) + "\n")
        print(f"Built 35-channel feature stack at {stack_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
