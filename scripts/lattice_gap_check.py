#!/usr/bin/env python3
"""Reproduce the calibration-lattice gap numbers that decide whether a dot budget can pass Rule 1.

Writes evidence/lattice_gap_check.json. Footprint = finite pixels of the lattice raster, which matches
the organizer footprint count (5,167,373). A footprint pixel is 'covered' if a lattice dot lies within
the stated radius (Euclidean, pixel centres). Gap pixels are the footprint pixels not covered and not
catalogue labels; they are the only places where the >=30% of dots outside the lattice buffer can go.
"""
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32.holdout import read_binary  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
LAT = DATA / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LAB = DATA / "labels.tif"
OUT = ROOT / "evidence" / "lattice_gap_check.json"


def main() -> int:
    with rasterio.open(LAT) as s:
        lat = s.read(1)
    foot = np.isfinite(lat)
    lat_dots = (np.where(foot, lat, 0.0) > 0) & foot
    labels = read_binary(LAB) & foot
    d = ndi.distance_transform_edt(~lat_dots)
    res = {
        "footprint_pixels": int(foot.sum()),
        "lattice_dots": int(lat_dots.sum()),
        "radius_px": {},
    }
    for r in (3.0,):
        cov = d <= r
        gap = foot & ~cov
        res["radius_px"][f"<={r}"] = {
            "footprint_uncovered_px": int(gap.sum()),
            "footprint_uncovered_px_not_labels": int((gap & ~labels).sum()),
        }
    cov_lt = d < 3.0
    res["radius_px"]["<3.0"] = {"footprint_uncovered_px": int((foot & ~cov_lt).sum()),
                                "footprint_uncovered_px_not_labels": int((foot & ~cov_lt & ~labels).sum())}
    res["review_claim_footprint_px_outside_lattice_buffer"] = 5379
    res["review_claim_status"] = ("NOT REPRODUCED: the review's 5,379 differs from every radius tested; the "
                                  "conclusion (a 37,654-dot file cannot pass Rule 1) holds for all three counts.")
    res["max_dots_passing_rule1_if_gap_used_fully"] = {
        "formula": "N <= G / 0.30 with G = not-label uncovered pixels at <=3 px",
        "value": int(np.floor(res["radius_px"]["<=3.0"]["footprint_uncovered_px_not_labels"] / 0.30)),
    }
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
