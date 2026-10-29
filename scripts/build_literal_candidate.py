#!/usr/bin/env python3
"""Build a literal-rule-compliant variant of the LWST-GeoConduit dot set (Protocol Rule 1).

Problem (verified in docs/research/independent-review-20261028.md and re-derived in
evidence/literal_lattice_gap.json): the 37,654-dot LWST file has 99.78% of its dots within 3 px of
the 13GEMSDOE calibration lattice, which is a registry raster. The literal rule allows at most 70%.
Only G footprint pixels lie more than 3 px from every lattice dot (and not on a catalogue label), so
at least 30% of the dots must sit on those G pixels. That caps the total dot count at about G/0.30.

Construction (label-free, no holdout use):
  1. G = footprint & not within 3 px of any lattice dot & not a catalogue label.
  2. Gap dots: ALL G pixels (needed to reach the 30% floor), ordered by the density of LWST dots within
     a 10 px disk, so the gap dots that sit beside the predicted structure are the ones that matter.
  3. Inside dots: K = floor(TAU * |G| / (1 - TAU)) of the LWST dots that already sit within 3 px of a
     lattice dot. TAU = 0.69 leaves a 1-point margin below the 70% limit.
     Variant "dense": keep the K highest-density LWST dots.
     Variant "random": keep K LWST dots chosen uniformly at random (seed 20261028).
  4. Write float32 GeoTIFF on the organizer grid, zeros outside the footprint, values in {0,1}.

Usage: python scripts/build_literal_candidate.py --variant dense --out <path.tif>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32.holdout import read_binary  # noqa: E402
from gems32.submission import audit_geotiff  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
TEMPLATE = DATA / "sample_submission.tif"
LABELS = DATA / "labels.tif"
LATTICE = DATA / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LWST = ROOT / "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"
TAU = 0.69
DENSITY_RADIUS_PX = 10
SEED = 20261028


def disk(r: int) -> np.ndarray:
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    return (yy * yy + xx * xx) <= r * r


def farthest_point_subset(pool_flat: np.ndarray, k: int, shape: tuple, seed: int) -> np.ndarray:
    """Greedy max-min spacing: repeatedly keep the pool dot farthest from everything already kept.

    Redundancy-aware retention: dots that duplicate the same predicted segment add little DTI
    coverage, so spreading the retained dots over the pool targets unique coverage.
    """
    yy, xx = np.unravel_index(pool_flat, shape)
    py = yy.astype(np.float64)
    px = xx.astype(np.float64)
    rng = np.random.default_rng(seed)
    first = int(rng.integers(0, pool_flat.size))
    chosen = np.empty(k, dtype=np.int64)
    chosen[0] = first
    min_d2 = (py - py[first]) ** 2 + (px - px[first]) ** 2
    for i in range(1, k):
        j = int(np.argmax(min_d2))
        chosen[i] = j
        d2 = (py - py[j]) ** 2 + (px - px[j]) ** 2
        np.minimum(min_d2, d2, out=min_d2)
    return pool_flat[chosen]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["dense", "random", "dispersed"], required=True)
    ap.add_argument("--no-gap", action="store_true",
                    help="CONTROL ONLY: random same-count subset of all LWST dots, no lattice constraint")
    ap.add_argument("--out", required=True)
    ap.add_argument("--outside", choices=["nan", "zeros"], default="nan",
                    help="value outside the footprint: nan (official rule: data outside the bounds is null or nan; default) or zeros (owner-variant convention)")
    ap.add_argument("--receipt", default=None)
    args = ap.parse_args()

    with rasterio.open(TEMPLATE) as t:
        foot = np.isfinite(t.read(1))
        tpl_profile = t.profile.copy()
    labels = read_binary(LABELS) & foot
    lat_dots = read_binary(LATTICE) & foot
    lwst = read_binary(LWST) & foot

    dist_lat = ndi.distance_transform_edt(~lat_dots)
    covered = dist_lat <= 3.0
    gap = foot & ~covered & ~labels
    G = int(gap.sum())

    # Density of LWST dots in a 10 px disk (label-free: uses only the LWST output).
    dens = ndi.convolve(lwst.astype(np.float32), disk(DENSITY_RADIUS_PX).astype(np.float32), mode="constant")

    inside_pool = np.flatnonzero((lwst & covered).ravel())
    K = int(np.floor(TAU * G / (1.0 - TAU)))
    if inside_pool.size < K:
        raise SystemExit(f"not enough inside LWST dots: pool={inside_pool.size} K={K}")
    if args.variant == "dense":
        pool_dens = dens.ravel()[inside_pool]
        order = np.argsort(-pool_dens, kind="stable")
        keep_inside = inside_pool[order[:K]]
    elif args.variant == "random":
        rng = np.random.default_rng(SEED)
        keep_inside = rng.choice(inside_pool, size=K, replace=False)
    else:
        keep_inside = farthest_point_subset(inside_pool, K, foot.shape, SEED)

    gap_idx = np.flatnonzero(gap.ravel())
    if args.no_gap:
        # SAME-COUNT CONTROL: random subset of ALL LWST dots, total = K + |G|, no lattice constraint.
        # Not literal-compliant. Isolates the score effect of the dot cap from the forced gap dots.
        rng = np.random.default_rng(SEED)
        all_lwst = np.flatnonzero(lwst.ravel())
        keep_inside = rng.choice(all_lwst, size=min(all_lwst.size, K + G), replace=False)
        K = int(keep_inside.size)
        gap_idx = np.array([], dtype=np.int64)
    out = np.zeros(foot.shape, dtype=np.float32)
    out.ravel()[keep_inside] = 1.0
    out.ravel()[gap_idx] = 1.0

    n_dots = int((out > 0).sum())
    within = float(covered[out > 0].mean())
    if not args.no_gap:
        # Literal construction: the inside-dot share must equal the within-3px share exactly.
        frac_inside = K / n_dots
        assert abs(frac_inside - within) < 1e-9, (frac_inside, within)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile = tpl_profile.copy()
    profile.update(driver="GTiff", dtype="float32", count=1, nodata=(np.nan if args.outside == "nan" else None), compress="deflate",
                   predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256)
    fill = np.nan if args.outside == "nan" else 0.0
    arr = np.where(foot, out, fill).astype(np.float32)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
    audit = audit_geotiff(out_path, foot, labels, mode=args.outside, template_tif=TEMPLATE)

    receipt = {
        "variant": args.variant,
        "tau_within_3px_target": TAU,
        "density_radius_px": DENSITY_RADIUS_PX,
        "seed": SEED if args.variant in ("random", "dispersed") or args.no_gap else None,
        "footprint_pixels": int(foot.sum()),
        "lattice_dots": int(lat_dots.sum()),
        "lattice_covered_footprint_px": int((foot & covered).sum()),
        "gap_pixels_G": G,
        "lwst_dots_input": int(lwst.sum()),
        "inside_pool_lwst_dots": int(inside_pool.size),
        "K_inside_kept": K,
        "gap_dots_kept": int(gap_idx.size),
        "total_dots": n_dots,
        "within_3px_of_lattice_fraction": within,
        "output": str(out_path.relative_to(ROOT)) if out_path.is_relative_to(ROOT) else str(out_path),
        "format_audit_all_checks_passed": bool(audit["all_checks_passed"]),
        "format_audit_sha256": audit["sha256"],
    }
    if args.receipt:
        Path(args.receipt).write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(receipt, indent=1))
    return 0 if audit["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
