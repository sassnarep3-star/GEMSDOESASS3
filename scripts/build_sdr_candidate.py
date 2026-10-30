#!/usr/bin/env python3
"""Build the SDR (Spaced-Density Retention) literal-rule candidate — lane H-SASS3-I (EXP1).

Mechanism (one paragraph, per protocol): the audited LWST-GeoConduit 37,654-dot evidence set is
retained, not rebuilt. Retention changes from farthest-point spread (which pushed dots onto isolated
low-evidence outliers) to spacing-constrained density-greedy: scan LWST dots in descending
10-px-disk evidence density and keep a dot only if no already-kept dot is within 3 px (Chebyshev-2
blocking guarantees Euclidean spacing >= 3.0 px), until K = floor(TAU * G / (1 - TAU)) dots are kept.
All G = footprint pixels more than 3 px from every 13GEMSDOE lattice dot (and not on a training
label) become gap dots, which caps the inside share at TAU = 0.69 < the 0.70 literal limit.
Output: float32 GeoTIFF, values in {1.0}, NaN outside the footprint (official rule).

Label-free and SGMC-free: the only inputs are the shipped LWST raster, the calibration lattice,
the training labels (used only to EXCLUDE label pixels from gap dots, as in build_literal_candidate.py),
and the organizer sample grid. No holdout field is touched during construction.

Usage: python scripts/build_sdr_candidate.py --out docs/downloads/<name>.tif --receipt <path.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
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
LWST_SHA = "bc9109d9dd22d2f7193bafca7366acdf9432bfda7a393eb96d8fd8b48c0ed84a"  # pinned input (matches evidence/literal_audit_lwst_baseline.json)
TAU = 0.69
DENSITY_RADIUS_PX = 10
BLOCK_CHEBYSHEV = 2  # keep-out half-width; guarantees Euclidean spacing >= 3.0 px between kept dots


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def disk(r: int) -> np.ndarray:
    yy, xx = np.ogrid[-r : r + 1, -r : r + 1]
    return (yy * yy + xx * xx) <= r * r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--surface-out", default=str(ROOT / "evidence/sdr1_surface_dens.npy"))
    args = ap.parse_args()
    t0 = time.time()

    in_sha = sha256_file(LWST)
    if in_sha != LWST_SHA:
        raise SystemExit(f"LWST input SHA mismatch: {in_sha}")

    with rasterio.open(TEMPLATE) as t:
        foot = np.isfinite(t.read(1))
        profile = t.profile.copy()
    labels = read_binary(LABELS) & foot
    lat_dots = read_binary(LATTICE) & foot
    lwst = read_binary(LWST) & foot

    dist_lat = ndi.distance_transform_edt(~lat_dots)
    covered = dist_lat <= 3.0
    gap = foot & ~covered & ~labels
    G = int(gap.sum())

    dens = ndi.convolve(lwst.astype(np.float32), disk(DENSITY_RADIUS_PX).astype(np.float32), mode="constant")

    inside_pool = np.flatnonzero((lwst & covered).ravel())
    K = int(np.floor(TAU * G / (1.0 - TAU)))

    # Spacing-constrained density-greedy retention (Chebyshev-2 blocking -> Euclidean spacing >= 3 px).
    pool_dens = dens.ravel()[inside_pool]
    order = np.lexsort((inside_pool, -pool_dens))  # descending density, stable by index
    blocked = np.zeros(foot.shape, dtype=bool)
    keep_inside: list[np.int64] = []
    n_spacing_reject = 0
    for idx in inside_pool[order]:
        if len(keep_inside) >= K:
            break
        y, x = divmod(int(idx), foot.shape[1])
        if blocked[y, x]:
            n_spacing_reject += 1
            continue
        keep_inside.append(np.int64(idx))
        y0, y1 = max(0, y - BLOCK_CHEBYSHEV), min(foot.shape[0], y + BLOCK_CHEBYSHEV + 1)
        x0, x1 = max(0, x - BLOCK_CHEBYSHEV), min(foot.shape[1], x + BLOCK_CHEBYSHEV + 1)
        blocked[y0:y1, x0:x1] = True
    n_inside = len(keep_inside)

    mask = np.zeros(foot.shape, dtype=bool)
    mask.ravel()[np.asarray(keep_inside, dtype=np.int64)] = True
    mask |= gap
    total = int(mask.sum())

    out = np.zeros(foot.shape, dtype=np.float32)
    out[mask] = np.float32(1.0)
    out[~foot] = np.nan  # official rule: data outside the bounds is null or nan

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile.update(driver="GTiff", dtype="float32", count=1, nodata=float("nan"), compress="deflate")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(out, 1)

    zip_path = out_path.with_suffix(".tif.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(out_path, arcname=out_path.name)

    np.save(args.surface_out, dens.astype(np.float32))

    # Self-audit against the shipped bytes.
    audit = audit_geotiff(out_path, foot, labels, mode="nan", template_tif=TEMPLATE)
    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "lane": "H-SASS3-I: SDR spaced-density retention of the audited LWST evidence set",
        "variant": "sdr1_spaced_dense",
        "inputs": {
            "lwst_raster": LWST.name,
            "lwst_sha256": in_sha,
            "lattice": LATTICE.name,
            "tau": TAU,
            "density_radius_px": DENSITY_RADIUS_PX,
            "block_chebyshev": BLOCK_CHEBYSHEV,
            "min_euclid_spacing_px": 3.0,
        },
        "counts": {
            "gap_pixels_G": G,
            "K_target_inside": K,
            "inside_dots_kept": n_inside,
            "spacing_rejections": n_spacing_reject,
            "gap_dots": G,
            "total_dots": total,
            "literal_cap_total": G / 0.30,
        },
        "output": {
            "tif": str(out_path.resolve().relative_to(ROOT)),
            "tif_sha256": sha256_file(out_path),
            "zip_sha256": sha256_file(zip_path),
            "bytes": out_path.stat().st_size,
        },
        "format_audit": audit,
        "label_free": True,
        "sgmc_free": True,
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("variant", "counts", "output")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
