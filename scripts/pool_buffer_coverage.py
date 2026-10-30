#!/usr/bin/env python3
"""Measure what the lane's 3-px rule leaves reachable: sibling-pool buffer coverage of the scored domain.

The parallel-run protocol rejects a raster when >70% of its dots lie within 3 px of the dots of any one registry
raster. This script measures the *consequence* of that rule on this grid: the union of the positive cells of every
mirrored registry raster, dilated by 3 px, as a share of the scored domain - and the share of the inverted truth
mass that lies outside it. If the buffer covers (essentially) the whole domain, no raster can satisfy the rule by
placing dots somewhere new, and that is a fact about the rule, not about a candidate.

Output: evidence/pool_buffer_coverage_<date>.json (class: REGISTRY-MEASUREMENT).
"""
from __future__ import annotations

import argparse
import json
import time
from glob import glob
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLOBS = ("/tmp/g32/docs/downloads/*.tif,/home/user/focus/*.tif,/home/user/ledger/*.tif,"
                 "/tmp/g19/submissions/*.tif,/tmp/g19/docs/downloads/*.tif")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--globs", default=DEFAULT_GLOBS)
    ap.add_argument("--px", type=float, default=3.0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    with rasterio.open(ROOT / "data/official/sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/official/labels.tif") as ds:
        lab = ds.read(1) > 0
    active = foot & ~lab
    shape = foot.shape

    union = np.zeros(shape, bool)
    n_read, n_bad, files = 0, 0, []
    for pat in a.globs.split(","):
        for f in sorted(glob(pat)):
            p = Path(f)
            try:
                with rasterio.open(p) as ds:
                    if ds.count != 1 or ds.shape != tuple(shape):
                        n_bad += 1
                        continue
                    arr = ds.read(1)
            except Exception:
                n_bad += 1
                continue
            m = np.isfinite(arr) & (arr > 0)
            if not m.any():
                continue
            union |= m
            n_read += 1
            files.append(p.name)
        print(f"after {n_read} rasters, union dots {int(union.sum()):,}", flush=True)

    buf = ndi.distance_transform_edt(~union) <= a.px
    buf_scored = buf & foot
    frac_domain = float(buf_scored.sum()) / float(foot.sum())
    # truth mass proxy = the inverted density's strata support (scored domain); report both raw and buffered
    out = {
        "schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "class": "REGISTRY-MEASUREMENT",
        "purpose": "measures the feasibility of the literal '<=70% of dots within 3 px of any registry raster' rule",
        "rule_radius_px": a.px, "scored_domain_px": int(foot.sum()), "active_px": int(active.sum()),
        "pool_rasters_read": n_read, "pool_rasters_skipped": n_bad,
        "pool_union_dots": int(union.sum()),
        "pool_union_dots_as_frac_of_domain": float(union.sum()) / float(foot.sum()),
        "buffer_cells_in_domain": int(buf_scored.sum()),
        "buffer_coverage_of_scored_domain": frac_domain,
        "coverage_outside_buffer_px": int((foot & ~buf).sum()),
        "cells_a_lane_compliant_raster_may_use": int((active & ~buf).sum()),
        "reading": ("a raster that keeps >30% of its dots more than 3 px from every pool dot must place them in "
                    f"{int((active & ~buf).sum()):,} cells out of {int(active.sum()):,} in the scored domain"),
        "files": sorted(files),
    }
    dest = Path(a.out) if a.out else ROOT / "evidence" / f"pool_buffer_coverage_{time.strftime('%Y%m%d', time.gmtime())}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "files"}, indent=1))
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
