"""Pre-registered H1 displaced-magnetic-texture surface, no catalogue input.

This is an exploratory proxy, not an inversion or proof of fault displacement.
All offsets use raster pixels; the competition mirror has 100 m cells.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

# Normals and perpendicular tangents. Diagonals are intentionally discrete.
FRAMES = (((0, 3), (2, 0)), ((3, 0), (0, 2)),
          ((3, 3), (2, -2)), ((3, -3), (2, 2)))


def sample_offset(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """out[y, x] = a[y + dy, x + dx], with zeros rather than wraparound."""
    a = np.asarray(a)
    if a.ndim != 2:
        raise ValueError("expected a 2-D raster")
    h, w = a.shape
    out = np.zeros_like(a)
    if abs(dy) >= h or abs(dx) >= w:
        return out
    yd0, yd1 = max(0, -dy), min(h, h - dy)
    xd0, xd1 = max(0, -dx), min(w, w - dx)
    out[yd0:yd1, xd0:xd1] = a[yd0 + dy:yd1 + dy, xd0 + dx:xd1 + dx]
    return out


def make_fields(rtp: np.ndarray, elevation: np.ndarray, footprint: np.ndarray) -> tuple[dict, np.ndarray]:
    """Return bounded feature maps and strict support, using no fault labels.

    Four directional hypotheses compare locally averaged squared differences
    of magnetic windows across a trace, with and without a tangential shift.
    Positive advantage requires the shifted comparison to improve on zero shift.
    The corresponding cross-line elevation break gates that advantage.
    Physical units are those in the mirrored bands; no temperature is inferred.
    """
    rtp = np.asarray(rtp, dtype=np.float32)
    elevation = np.asarray(elevation, dtype=np.float32)
    footprint = np.asarray(footprint, dtype=bool)
    if rtp.ndim != 2 or rtp.shape != elevation.shape or rtp.shape != footprint.shape:
        raise ValueError("feature bands and footprint must share a 2-D grid")
    # Reject nodata sentinels and extreme values whose squared differences can
    # overflow float32. These are not physical observations in the pinned data.
    observed = (footprint & np.isfinite(rtp) & np.isfinite(elevation)
                & (np.abs(rtp) < 1e18) & (np.abs(elevation) < 1e18))
    # Padded beyond the maximal offset plus the Gaussian's truncated radius.
    support = ndi.binary_erosion(observed, structure=np.ones((3, 3), bool),
                                 iterations=12, border_value=0)
    if not support.any():
        raise ValueError("no fully supported feature cells after edge erosion")
    r = np.where(observed, rtp, 0).astype(np.float32)
    z = np.where(observed, elevation, 0).astype(np.float32)
    features = {}
    combined = np.zeros(r.shape, dtype=np.float32)
    terrain_max = np.zeros(r.shape, dtype=np.float32)
    for i, ((ny, nx), (ty, tx)) in enumerate(FRAMES):
        a = sample_offset(r, ny, nx)
        b0 = sample_offset(r, -ny, -nx)
        bp = sample_offset(r, -ny + ty, -nx + tx)
        bm = sample_offset(r, -ny - ty, -nx - tx)
        d0 = ndi.gaussian_filter(np.square(a - b0), sigma=2.0, mode="nearest", truncate=3.0)
        dp = ndi.gaussian_filter(np.square(a - bp), sigma=2.0, mode="nearest", truncate=3.0)
        dm = ndi.gaussian_filter(np.square(a - bm), sigma=2.0, mode="nearest", truncate=3.0)
        best = np.minimum(dp, dm)
        advantage = np.clip((d0 - best) / (d0 + best + np.float32(1.0)), 0, 1).astype(np.float32)
        dz = np.abs(sample_offset(z, ny, nx) - sample_offset(z, -ny, -nx))
        terrain = (dz / (dz + np.float32(100.0))).astype(np.float32)
        advantage[~support] = 0
        terrain[~support] = 0
        features[f"shift_advantage_{i}"] = advantage
        features[f"elevation_break_{i}"] = terrain
        np.maximum(combined, advantage * terrain, out=combined)
        np.maximum(terrain_max, terrain, out=terrain_max)
    features["combined_surface"] = combined
    features["terrain_control"] = terrain_max
    return features, support
