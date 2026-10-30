#!/usr/bin/env python3
"""Cache the dot coordinates of every registry raster once, for fast uniqueness checks.

Writing ``(y, x)`` integer pairs per raster into a single ``.npz`` turns a 15-minute
uniqueness sweep (342 GeoTIFF reads) into a ~1 second KD-tree query per candidate.
The cache is a derivative artefact: it lives in ``.cache`` and is rebuilt by this script.

Usage
-----
    python scripts/cache_registry_dots.py --registry .cache/focus_registry \
        --data-dir .cache/gems_data --out .cache/registry_dots.npz
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=ROOT / ".cache" / "focus_registry")
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--out", type=Path, default=ROOT / ".cache" / "registry_dots.npz")
    args = ap.parse_args()

    with rasterio.open(args.data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        shape = ds.shape
    payload = {}
    meta = {}
    for p in sorted(args.registry.glob("*.tif")):
        try:
            with rasterio.open(p) as ds:
                if ds.shape != shape:
                    meta[p.name] = {"status": "skipped_shape", "shape": list(ds.shape)}
                    continue
                a = ds.read(1)
        except Exception as exc:  # unreadable / corrupt
            meta[p.name] = {"status": "unreadable", "error": str(exc)[:120]}
            continue
        m = np.isfinite(a) & (a > 0) & foot
        yy, xx = np.nonzero(m)
        if yy.size == 0:
            meta[p.name] = {"status": "empty"}
            continue
        payload[p.name] = np.column_stack([yy, xx]).astype(np.int32)
        meta[p.name] = {"status": "ok", "dots": int(yy.size)}
    np.savez_compressed(args.out, **payload)
    ok = sum(1 for v in meta.values() if v["status"] == "ok")
    print(f"cached {ok} rasters -> {args.out}")
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
