#!/usr/bin/env python3
"""Verify or restore pinned competition & CC0/CC-BY-4.0 external datasets into .cache/gems_data
and extract sentinel-cleaned float32 bands into .cache/features/band-01..19.npy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def verify_manifest(manifest_path: Path, cache_root: Path) -> list[dict]:
    manifest = json.loads(manifest_path.read_text())
    receipts = []
    for ds in manifest["files"]:
        target = cache_root / ds["dest"]
        if not target.exists():
            raise FileNotFoundError(
                f"Missing {target}; place official DrivenData / USGS / OpenEI GDR #1391 files or run chunked restore."
            )
        digest = sha256_file(target)
        if digest != ds["sha256"]:
            raise ValueError(f"SHA-256 mismatch on {target}: got {digest}, expected {ds['sha256']}")
        receipts.append({"id": ds["id"], "dest": ds["dest"], "sha256": digest, "bytes": target.stat().st_size})
    return receipts


def ensure_feature_bands(cache_root: Path, feat_dir: Path) -> None:
    feat_dir.mkdir(parents=True, exist_ok=True)
    if all((feat_dir / f"band-{b:02d}.npy").exists() for b in range(1, 20)):
        return
    with rasterio.open(cache_root / "sample_submission.tif") as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(cache_root / "training_features.tif") as src:
        for b in range(1, src.count + 1):
            arr = src.read(b).astype(np.float32)
            bad = (~np.isfinite(arr)) | (np.abs(arr) > 1e30)
            arr[bad] = np.nan
            arr[~fp] = np.nan
            np.save(feat_dir / f"band-{b:02d}.npy", arr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=ROOT / "registry/data_manifest.json")
    ap.add_argument("--cache-root", type=Path, default=ROOT / ".cache/gems_data")
    ap.add_argument("--features-dir", type=Path, default=ROOT / ".cache/features")
    args = ap.parse_args()

    receipts = verify_manifest(args.manifest, args.cache_root)
    ensure_feature_bands(args.cache_root, args.features_dir)
    print(json.dumps({"verified_datasets": len(receipts), "features_dir": str(args.features_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
