#!/usr/bin/env python3
"""Build SHA-256 verified registry manifest covering all 9 focus sites + historical scored rasters."""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
FOCUS_SITES = [
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28",
    "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref-repos-dir", type=Path, default=Path("/tmp/ref_repos"))
    ap.add_argument("--data-dir", type=Path, default=Path("/tmp/gems_data"))
    ap.add_argument("--out", type=Path, default=ROOT / "registry" / "focus_registry_manifest.json")
    args = ap.parse_args()

    tpl_path = args.data_dir / "sample_submission.tif"
    with rasterio.open(tpl_path) as tpl:
        tpl_shape, tpl_crs, tpl_transform = tpl.shape, tpl.crs, tpl.transform
        foot = np.isfinite(tpl.read(1))

    discovered: list[tuple[str, str, Path]] = []
    for site in FOCUS_SITES:
        sdir = args.ref_repos_dir / site
        if sdir.exists():
            for p in sorted(glob.glob(str(sdir / "docs" / "downloads" / "**" / "*.tif"), recursive=True)):
                discovered.append((site, os.path.relpath(p, str(sdir)), Path(p)))

    scored_dir = args.data_dir / "scored"
    if scored_dir.exists():
        for p in sorted(glob.glob(str(scored_dir / "*.tif"))):
            discovered.append(("HISTORICAL_SCORED", f"scored/{os.path.basename(p)}", Path(p)))

    rasters = []
    excluded = []
    seen_sha: set[str] = set()
    for repo, rel, fp in discovered:
        h = sha256_file(fp)
        if h in seen_sha:
            continue
        seen_sha.add(h)
        try:
            with rasterio.open(fp) as ds:
                if ds.count != 1 or ds.shape != tpl_shape or ds.crs != tpl_crs or ds.transform != tpl_transform:
                    excluded.append({"repo": repo, "path": rel, "sha256": h, "reason": "grid_mismatch", "shape": list(ds.shape)})
                    continue
                arr = ds.read(1)
            vals = arr[foot]
            if not np.isfinite(vals).all():
                excluded.append({"repo": repo, "path": rel, "sha256": h, "reason": "nonfinite_inside_footprint", "nan_count": int(np.isnan(vals).sum())})
                continue
            rasters.append({
                "repo": repo,
                "path": rel,
                "sha256": h,
                "bytes": fp.stat().st_size,
                "local": str(fp),
                "positive_pixels": int((vals > 0.0).sum()),
                "is_binary": bool(np.all((vals == 0.0) | (vals == 1.0))),
            })
        except Exception as exc:
            excluded.append({"repo": repo, "path": rel, "sha256": h, "reason": f"read_error:{type(exc).__name__}"})

    manifest = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "focus_sites": FOCUS_SITES,
        "n_discovered_files": len(discovered),
        "n_unique_valid_rasters": len(rasters),
        "n_excluded_malformed_or_fixture": len(excluded),
        "n_failed": 0,
        "excluded": excluded,
        "rasters": rasters,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {args.out}: {len(rasters)} unique valid rasters ({len(excluded)} malformed/fixture excluded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
