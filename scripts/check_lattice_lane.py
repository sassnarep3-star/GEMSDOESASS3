#!/usr/bin/env python3
"""Parallel-run protocol Rule 1 (dot-level), reproducible.

For each candidate GeoTIFF given on the command line (default: every .tif in docs/downloads):
  * the candidate's dots are its connected positive blobs (8-connectivity, value == 1),
    each represented by its centroid rounded to the nearest pixel;
  * a dot is "within 3 px" if the nearest calibration-lattice positive pixel is <= 3 px away;
  * reports the within-3-px fraction (limit 0.70) and the Spearman rank correlation with the
    lattice over finite cells (limit 0.90, sampled).

The lattice is the 13GEMSDOE calibration raster from buffedlizard55-lab/GEMSDOE24 at
commit 07345ea0604953d7efb858d9cfbc21e20c7aca0b. Its SHA-256 is pinned below and checked.
Fetch it with:
  gh api "repos/buffedlizard55-lab/GEMSDOE24/contents/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif?ref=07345ea0604953d7efb858d9cfbc21e20c7aca0b" -H "Accept: application/vnd.github.raw" > .cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif

Exit code 0 only if every candidate passes both limits (fail-closed).
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
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
LATTICE = ROOT / ".cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SHA256 = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
LIMIT_WITHIN3 = 0.70
LIMIT_RHO = 0.90


def check(path: Path, lat: np.ndarray, dist: np.ndarray, lat_crs, lat_shape, lat_tf) -> dict:
    with rasterio.open(path) as c:
        same_grid = (c.crs == lat_crs) and (c.shape == lat_shape) and (c.transform == lat_tf)
        ca = c.read(1)
    m = ca == 1
    lab, n = ndi.label(m, structure=np.ones((3, 3), dtype=int))
    if n == 0:
        return {"file": path.name, "same_grid": bool(same_grid), "blobs": 0, "within3": 0.0,
                "spearman": None, "pass": False, "reason": "no positive dots"}
    cent = np.round(np.array(ndi.center_of_mass(m, lab, range(1, n + 1)))).astype(int)
    d = dist[cent[:, 0], cent[:, 1]]
    within3 = float((d <= 3.0).mean())
    finite = np.isfinite(lat)
    idx = np.flatnonzero(finite.ravel())
    rng = np.random.default_rng(0)
    s = rng.choice(idx, size=min(300_000, idx.size), replace=False)
    rho = float(spearmanr(ca.ravel()[s], lat.ravel()[s]).correlation)
    ok = bool(same_grid and within3 <= LIMIT_WITHIN3 and abs(rho) <= LIMIT_RHO)
    return {
        "file": path.name,
        "same_grid": bool(same_grid),
        "positive_pixels": int(m.sum()),
        "blobs_dots": int(n),
        "within3_dot_fraction": round(within3, 6),
        "spearman_vs_lattice_sampled": round(rho, 6),
        "pass": ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tifs", nargs="*")
    ap.add_argument("--out", default=str(ROOT / "evidence/lattice_lane_check_20261029.json"))
    args = ap.parse_args()

    if not LATTICE.exists():
        print(f"FAIL-CLOSED: lattice not found at {LATTICE}", file=sys.stderr)
        return 2
    sha = hashlib.sha256(LATTICE.read_bytes()).hexdigest()
    if sha != LATTICE_SHA256:
        print(f"FAIL-CLOSED: lattice sha256 {sha} != pinned {LATTICE_SHA256}", file=sys.stderr)
        return 2

    with rasterio.open(LATTICE) as w:
        lat = w.read(1).astype(np.float64)
        lat_crs, lat_shape, lat_tf = w.crs, w.shape, w.transform
    wpos = np.isfinite(lat) & (lat > 0)
    dist = ndi.distance_transform_edt(~wpos)

    tifs = [Path(t) for t in args.tifs] or sorted((ROOT / "docs/downloads").glob("*.tif"))
    results = [check(p, lat, dist, lat_crs, lat_shape, lat_tf) for p in tifs]
    all_pass = all(r["pass"] for r in results)
    record = {
        "schema_version": 1,
        "recorded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lattice": {"path": str(LATTICE.relative_to(ROOT)), "sha256": sha,
                    "source": "https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"},
        "limits": {"within3_dot_fraction_max": LIMIT_WITHIN3, "abs_spearman_max": LIMIT_RHO},
        "results": results,
        "all_pass": all_pass,
        "scope_note": "Lattice only. Other registry rasters (451 downloads audit) are NOT covered by this file.",
    }
    Path(args.out).write_text(json.dumps(record, indent=1) + "\n")
    for r in results:
        print(json.dumps(r))
    print("ALL PASS" if all_pass else "NOT ALL PASS")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
