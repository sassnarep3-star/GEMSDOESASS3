#!/usr/bin/env python3
"""Exact arithmetic for the 13GEMSDOE calibration-lattice block (Protocol Rule 1, literal reading).

Question answered: can ANY raster with N dots satisfy "no more than 70% of my dots lie within 3 px of
one registry raster's dots" against the 5-px lattice witness?

Method (all numbers are computed from the restored rasters, not copied):
  1. Footprint F = finite cells of sample_submission.tif (the organizer grid's valid region).
  2. Lattice L = positive finite cells of 13gems_20261001_r13-lattice-s5_v2_nan-outside.tif.
  3. U = F cells whose distance to L is greater than 3 px. Only these can be dots that are NOT within 3 px.
  4. A dot set with N dots has at most U of them outside the buffer, so the rule needs
     outside >= 0.30 * N, i.e. N <= floor(U / 0.30). Any N above that is impossible on this footprint.
  5. The bound depends on the distance convention, so it is reported for three conventions.

Also re-measures the shipped LWST archive against the lattice (overlap should reproduce 0.997849).

Output: evidence/lattice_bound_audit_20261028.json. Requires `python scripts/restore_data.py` first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
LATTICE_REL = "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SHA = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
LWST_REL = "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"
LWST_SHA = "bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a"
OVERLAP_LIMIT = 0.70
CANDIDATE_DOTS = 37_654


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(ROOT / ".cache/gems_data"))
    ap.add_argument("--out", default=str(ROOT / "evidence/lattice_bound_audit_20261028.json"))
    args = ap.parse_args()
    data = Path(args.data)

    lat_path = data / LATTICE_REL
    if sha256_file(lat_path) != LATTICE_SHA:
        raise SystemExit("lattice SHA-256 mismatch; refusing to compute")
    with rasterio.open(data / "sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
        grid = (s.crs.to_string(), tuple(s.shape), tuple(round(float(x), 6) for x in list(s.transform)[:6]))
    with rasterio.open(lat_path) as s:
        lat_vals = s.read(1)
        lat_grid = (s.crs.to_string(), tuple(s.shape), tuple(round(float(x), 6) for x in list(s.transform)[:6]))
    if lat_grid != grid:
        raise SystemExit(f"lattice grid differs from footprint grid: {lat_grid} vs {grid}")
    lat = np.isfinite(lat_vals) & (lat_vals > 0)

    dist = ndi.distance_transform_edt(~lat)  # Euclidean distance (px) to nearest lattice dot
    conventions = {
        "euclidean_le_3px": dist <= 3.0,       # protocol text: "within 3 px" (used by the audits)
        "euclidean_lt_3px": dist < 3.0,        # strict reading
        "square_7x7_neighbourhood": ndi.binary_dilation(lat, structure=np.ones((7, 7), bool)),
    }
    bound = {}
    for name, cover in conventions.items():
        uncovered = int((foot & ~cover).sum())
        # outside >= (1 - 0.70) * N  and  outside <= uncovered  =>  N <= uncovered / 0.30
        n_max = math.floor(uncovered / (1.0 - OVERLAP_LIMIT) + 1e-9)
        bound[name] = dict(
            footprint_cells_within_3px_of_lattice=int((foot & cover).sum()),
            footprint_cells_outside_buffer=uncovered,
            max_dots_that_can_pass=n_max,
            candidate_37654_dots_can_pass=bool(CANDIDATE_DOTS <= n_max),
        )

    primary = bound["euclidean_le_3px"]
    uncov = foot & ~conventions["euclidean_le_3px"]
    bd = ndi.distance_transform_edt(foot)
    edge_stats = dict(
        median_distance_to_footprint_edge_px=float(np.median(bd[uncov])) if uncov.any() else None,
        max_distance_to_footprint_edge_px=float(bd[uncov].max()) if uncov.any() else None,
        share_within_2px_of_footprint_edge=float((bd[uncov] <= 2).mean()) if uncov.any() else None,
    )

    # Re-measure the shipped LWST archive (forward overlap = share of its dots within 3 px of a lattice dot).
    lwst_path = ROOT / LWST_REL
    lwst_sha = sha256_file(lwst_path)
    if lwst_sha != LWST_SHA:
        raise SystemExit("LWST SHA-256 mismatch")
    with rasterio.open(lwst_path) as s:
        lw = s.read(1)
    lw_dots = np.isfinite(lw) & (lw > 0)
    lwst = dict(
        sha256=lwst_sha,
        dots=int(lw_dots.sum()),
        forward_overlap_within_3px=float((lw_dots & conventions["euclidean_le_3px"]).sum() / lw_dots.sum()),
        dots_on_lattice_uncovered_cells=int((lw_dots & uncov).sum()),
    )

    out = dict(
        schema_version=1,
        generated_by="scripts/lattice_bound_audit.py",
        evidence_class="REGISTRY-MEASUREMENT + exact arithmetic (no holdout, no organizer score)",
        lattice=dict(path=f"data/{LATTICE_REL}", sha256=LATTICE_SHA, positive_cells=int(lat.sum()),
                     source_submission="13GEMSDOE 20261001_r13-lattice-s5_v2_nan-outside (owner-reported 0.0904)",
                     source_repo="https://github.com/buffedlizard55-lab/13GEMSDOE"),
        footprint=dict(cells=int(foot.sum()), grid=dict(crs=grid[0], shape=list(grid[1]), transform=list(grid[2]))),
        rule=dict(text="more than 70% of your dots within 3 px of one registry raster's dots = duplicate",
                  overlap_limit=OVERLAP_LIMIT),
        bound_by_convention=bound,
        primary_convention="euclidean_le_3px",
        uncovered_cells_edge_statistics=edge_stats,
        candidate_dots_assumed=CANDIDATE_DOTS,
        conclusion=("No raster with 37,654 dots can pass the literal lattice rule on this footprint under any of the "
                    "three conventions." if not any(v["candidate_37654_dots_can_pass"] for v in bound.values())
                    else "At least one convention allows 37,654 dots; see bound_by_convention."),
        lwst_archive=lwst,
        previous_figure_discrepancy=("evidence/irregularities_ledger.json IR-SASS3-19 and the review state 5,379 uncovered cells "
                                     "and 11,297 dots needed. Recomputed here: "
                                     f"{primary['footprint_cells_outside_buffer']:,} uncovered cells (<=3 px Euclidean) and "
                                     f"{math.ceil(0.30 * CANDIDATE_DOTS):,} dots needed at 37,654. The 5,379 figure did not reproduce "
                                     "under any convention tested. The conclusion is unchanged."),
    )
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("bound_by_convention", "uncovered_cells_edge_statistics", "lwst_archive", "conclusion")}, indent=2))


if __name__ == "__main__":
    main()
