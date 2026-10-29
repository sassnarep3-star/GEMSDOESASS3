#!/usr/bin/env python3
"""
Generate an ARCHIVE-ONLY diagnostic raster for GEMSDOESASS3.

This script creates a deterministic synthetic pattern for format and audit
exercises. It is not a trained prediction, does not establish uniqueness, and
must not be submitted. It does NOT require the login-walled competition rasters
(training_features.tif, labels.tif, sample_submission.tif); therefore it cannot
validate geological skill, holdout score, footprint correctness, or uniqueness.
It uses only the grid specification recorded in data/prepared_manifest.json.

Grid specification (EPSG:32611):
  height  = 3730 rows
  width   = 3292 columns
  transform = (100, 0, 243350, 0, -100, 4508550)  # 100 m pixels, north-up
  footprint = 5,167,373 valid pixels (of 12,279,160 total)
  positive catalogue labels = 60,988

Output: docs/downloads/<name>-zeros.tif  (float32, single band, [0,1], no NaN,
nodata=None, CRS EPSG:32611)

Diagnostic pattern only (not a uniqueness strategy):
  * The generator samples 10,000 centers along six hand-coded line equations
    and paints radius-2-pixel disks. Those disks yield many more positive cells
    than centers and do not represent a measured probability field.
  * The NNE orientation is a hand-coded regional motif, not a result inferred
    from official data in this checkout. It can coincide with faults, lithologic
    contacts, drainage, or arbitrary lineation.
  * No registry comparison is performed by this generator. A separate, complete
    surface-and-dot audit is mandatory before considering any submission.

No score estimate is produced. This artifact is archive-only and must not be
uploaded to the competition.
"""

from __future__ import annotations

import hashlib
import math
import os
import uuid
from datetime import datetime, timezone

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_DIR = os.path.join(REPO_ROOT, "docs", "downloads")

# ---- Grid specification from data/prepared_manifest.json ----
EPSG = 32611
HEIGHT = 3730
WIDTH = 3292
TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)  # (a, b, c, d, e, f)
DTYPE = np.float32
NODATA = None

# Georeferenced extent (meters, EPSG:32611)
X0 = TRANSFORM[2]          # 243350.0
Y_TOP = TRANSFORM[5]       # 4508550.0 (north edge)
PIXEL = 100.0
X_MAX = X0 + WIDTH * PIXEL          # 572550.0
Y_MIN = Y_TOP - HEIGHT * PIXEL      # 4471250.0

# ---- Submission parameters ----
N_DOTS = 10000          # sparse: well below prior 37,654 / 44,090 counts
DOT_RADIUS_PX = 2       # dots are ~200 m features (1-2 px at 100 m)
SEED = 0x5EED           # deterministic, reproducible


def world_to_pixel(x: float, y: float) -> tuple[int, int]:
    """Convert world coordinates (EPSG:32611 m) to (row, col) pixel indices."""
    col = int(math.floor((x - X0) / PIXEL))
    row = int(math.floor((Y_TOP - y) / PIXEL))
    return row, col


def pixel_to_world(row: int, col: int) -> tuple[float, float]:
    """Convert (row, col) pixel indices to world coordinates."""
    x = X0 + col * PIXEL + PIXEL / 2.0
    y = Y_TOP - row * PIXEL - PIXEL / 2.0
    return x, y


def in_bounds(row: int, col: int) -> bool:
    return 0 <= row < HEIGHT and 0 <= col < WIDTH


def add_dot(arr: np.ndarray, row: int, col: int, radius_px: int = DOT_RADIUS_PX, value: float = 1.0) -> None:
    """Burn a circular dot of `value` into arr at (row, col)."""
    r0, r1 = max(0, row - radius_px), min(HEIGHT, row + radius_px + 1)
    c0, c1 = max(0, col - radius_px), min(WIDTH, col + radius_px + 1)
    rr, cc = np.ogrid[r0:r1, c0:c1]
    dist = np.sqrt((rr - row) ** 2 + (cc - col) ** 2)
    mask = dist <= radius_px
    arr[r0:r1, c0:c1][mask] = value


def generate_structural_dots(rng: np.random.Generator, n_dots: int) -> list[tuple[int, int]]:
    """
    Place dots along NNE-trending structural corridors.

    The NW Nevada / Walker Lane region is dominated by NNE-SSW striking normal
    faults. We model several parallel corridors running NNE across the grid,
    place dots along them at regular intervals, and add a small off-corridor
    jitter so the pattern is not a regular lattice.
    """
    dots: list[tuple[int, int]] = []

    # Define NNE-trending corridors as lines y = m*x + b in world coords.
    # NNE strike ~ 30 deg east of north -> slope dy/dx = cot(30deg) ≈ 1.732
    # but in image coords (y goes down), we work in world coords and convert.
    m = math.tan(math.radians(60))   # corridor trend ~60 deg from east axis (NNE)
    corridor_intercepts = np.linspace(4_480_000.0, 4_500_000.0, num=6)

    dots_per_corridor = n_dots // len(corridor_intercepts)
    remainder = n_dots % len(corridor_intercepts)

    for i, b in enumerate(corridor_intercepts):
        n = dots_per_corridor + (1 if i < remainder else 0)

        # Sample along-corridor positions: x uniform across grid, y = m*x + b
        xs = rng.uniform(X0 + 2000, X_MAX - 2000, size=n)
        ys = m * xs + b

        # Clip to grid extent
        valid = (ys >= Y_MIN + 2000) & (ys <= Y_TOP - 2000)
        xs = xs[valid]
        ys = ys[valid]

        # Add perpendicular jitter (±400 m) so dots are not on a lattice
        jitter = rng.normal(0.0, 400.0, size=xs.size)
        # Perpendicular offset to line y = m*x + b: offset vector (-sin, cos) * jitter
        theta = math.atan(m)
        dx_off = -math.sin(theta) * jitter
        dy_off = math.cos(theta) * jitter
        xs_j = xs + dx_off
        ys_j = ys + dy_off

        # Clip again after jitter
        valid2 = (xs_j >= X0 + 500) & (xs_j <= X_MAX - 500) & (ys_j >= Y_MIN + 500) & (ys_j <= Y_TOP - 500)
        xs_j = xs_j[valid2]
        ys_j = ys_j[valid2]

        for xw, yw in zip(xs_j, ys_j):
            r, c = world_to_pixel(float(xw), float(yw))
            if in_bounds(r, c):
                dots.append((r, c))

    # If we fell short (clipping), fill remaining with in-bound random dots
    while len(dots) < n_dots:
        r = int(rng.integers(0, HEIGHT))
        c = int(rng.integers(0, WIDTH))
        dots.append((r, c))

    return dots[:n_dots]


def build_array(dots: list[tuple[int, int]]) -> np.ndarray:
    arr = np.zeros((HEIGHT, WIDTH), dtype=DTYPE)
    for r, c in dots:
        add_dot(arr, r, c, radius_px=DOT_RADIUS_PX, value=1.0)
    return arr


def validate_array(arr: np.ndarray) -> dict:
    """Run the structural gates that CAN be verified without organizer data."""
    checks = {}
    checks["shape"] = arr.shape == (HEIGHT, WIDTH)
    checks["dtype_float32"] = arr.dtype == np.float32
    checks["finite"] = bool(np.isfinite(arr).all())
    checks["no_nan"] = bool(~np.isnan(arr).any())
    checks["in_range_0_1"] = bool((arr >= 0.0).all() and (arr <= 1.0).all())
    checks["n_positive_pixels"] = int((arr > 0).sum())
    checks["n_unique_values"] = int(len(np.unique(arr)))
    checks["mean_value"] = float(arr.mean())
    return checks


def write_geotiff(arr: np.ndarray, path: str) -> None:
    crs = CRS.from_epsg(EPSG)
    # Build transform from the 6-parameter form: (a, b, c, d, e, f)
    # rasterio Affine: | a  b  c |
    #                  | d  e  f |
    #                  | 0  0  1 |
    from rasterio.transform import Affine
    affine = Affine(TRANSFORM[0], TRANSFORM[1], TRANSFORM[2],
                    TRANSFORM[3], TRANSFORM[4], TRANSFORM[5])

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=HEIGHT,
        width=WIDTH,
        count=1,
        dtype="float32",
        crs=crs,
        transform=affine,
        nodata=NODATA,
        compress="deflate",
        tiled=True,
        blockxsize=256,
        blockysize=256,
    ) as dst:
        dst.write(arr, 1)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)

    run_id = uuid.uuid4().hex[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_name = f"gemsdoesass3-diagnostic-pattern-{stamp}-{run_id}"
    tif_path = os.path.join(DOWNLOADS_DIR, f"{base_name}-zeros.tif")

    print(f"[generate] SEED={SEED:#x} N_DOTS={N_DOTS}")
    dots = generate_structural_dots(rng, N_DOTS)
    print(f"[generate] placed {len(dots)} dots in bounds")

    arr = build_array(dots)
    checks = validate_array(arr)
    print("[validate] structural gates:")
    for k, v in checks.items():
        print(f"  {k}: {v}")

    if not all(
        checks[k] for k in ("shape", "dtype_float32", "finite", "no_nan", "in_range_0_1")
    ):
        raise SystemExit("Structural validation failed -- not writing TIF.")

    write_geotiff(arr, tif_path)
    digest = sha256_file(tif_path)
    size_bytes = os.path.getsize(tif_path)

    print(f"[write] {tif_path}")
    print(f"[write] bytes={size_bytes} sha256={digest}")

    # Write a sidecar audit JSON
    audit = {
        "schema_version": 1,
        "generated_utc": stamp,
        "file": os.path.basename(tif_path),
        "sha256": digest,
        "bytes": size_bytes,
        "grid": {
            "epsg": EPSG,
            "height": HEIGHT,
            "width": WIDTH,
            "transform": list(TRANSFORM),
            "dtype": "float32",
            "nodata": NODATA,
        },
        "generation": {
            "seed": SEED,
            "n_dots": N_DOTS,
            "dot_radius_px": DOT_RADIUS_PX,
            "method": "NNE structural corridors + perpendicular jitter (deterministic)",
        },
        "validation": checks,
        "notes": [
            "ARCHIVE ONLY: synthetic corridor pattern, not a data-derived prediction.",
            "10,000 centers painted as radius-2 disks; positive cell count is recorded separately.",
            "No holdout score, leakage test, or complete registry uniqueness audit was run.",
            "Grid metadata comes from the checked-in prepared manifest, not a fresh organizer-sample comparison.",
            "Local format checks do not mean organizer acceptance or permission to submit.",
        ],
    }
    audit_path = os.path.join(DOWNLOADS_DIR, f"{base_name}-audit.json")
    with open(audit_path, "w") as f:
        import json as _json
        _json.dump(audit, f, indent=2)
    print(f"[write] {audit_path}")


if __name__ == "__main__":
    main()
