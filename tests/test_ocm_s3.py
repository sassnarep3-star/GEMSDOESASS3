"""Unit tests for the S3 orientation-consensus module (src/gemsdoesass3/ocm.py).

These pin the contracts the E1/E2/E3 experiments rely on: which official 19-band indices feed the edge
consensus, which external LiDAR bands (1-based) feed the scarp gain, that band 12 is treated as the
validity flag and never as signal, that the nodata sentinel is neutralised into NaN before any filter
sees it, and that the consensus machinery recovers the orientation of a synthetic ramp.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoesass3 import ocm  # noqa: E402


def test_edge_and_level_band_indices_are_disjoint_and_in_range() -> None:
    edge = set(ocm.EDGE_BANDS.values())
    level = set(ocm.LEVEL_BANDS.values())
    assert edge == {3, 4, 5, 7, 8, 9, 11, 19}
    assert level == {12, 13, 14, 15}
    assert not (edge & level), "a band cannot be both an edge proxy and a level field"
    assert all(1 <= v <= 19 for v in edge | level), "training_features.tif has 19 bands"


def test_lidar_band_map() -> None:
    assert ocm.LIDAR_BANDS["valid"] == 12, "band 12 is the validity flag, never a statistic"
    assert set(ocm.LIDAR_BANDS.values()) == {1, 3, 4, 6, 7, 9, 10, 12}
    assert len(set(ocm.LIDAR_BANDS.values())) == len(ocm.LIDAR_BANDS)


def test_sanitize_turns_nodata_sentinel_into_nan() -> None:
    """The float32 minimum sentinel must never be read as signal by a downstream filter."""
    nodata = np.float32(-3.4028235e38)
    a = np.full((5, 5), nodata, dtype=np.float32)
    a[2, 2] = 4.0
    out = ocm._sanitize(a, float(nodata))
    assert np.isnan(out).sum() == 24
    assert out[2, 2] == 4.0
    b = np.array([[np.inf, 1.0], [np.nan, 2.0]], dtype=np.float32)
    assert np.isnan(ocm._sanitize(b, None)).sum() == 2


def test_norm01_is_finite_safe_and_bounded() -> None:
    assert float(np.max(ocm._norm01(np.full((4, 4), np.nan, dtype=np.float32)))) == 0.0
    a = np.arange(16, dtype=np.float32).reshape(4, 4)
    a[0, 0] = 1e9  # a single wild outlier must not stretch the scale
    n = ocm._norm01(a)
    assert np.isfinite(n).all() and n.min() >= 0.0 and n.max() <= 1.0


def test_structure_tensor_recovers_a_diagonal_ramp() -> None:
    n = 64
    img = (np.mgrid[0:n, 0:n][1] + np.mgrid[0:n, 0:n][0]).astype(np.float32)
    a, b, c, mag2 = ocm.structure_tensor(img, sigma=2.0)
    sl = (slice(10, -10), slice(10, -10))
    assert np.allclose(a[sl], c[sl], rtol=1e-2) and b[sl].mean() > 0.5 * a[sl].mean()
    theta = 0.5 * np.arctan2(2.0 * b[sl], a[sl] - c[sl])
    assert abs(float(np.median(theta)) - np.pi / 4) < 0.02
    flat = np.zeros((16, 16), dtype=np.float32)
    *_, mflat = ocm.structure_tensor(flat, sigma=1.0)
    assert float(mflat.max()) == 0.0


def test_add_edge_support_is_monotone_in_edge_energy_and_clipped() -> None:
    base = np.zeros((4, 4), dtype=np.float32)
    base[1, 1] = 0.5
    f_off = {k: np.zeros((4, 4), dtype=np.float32) for k in ocm.EDGE_BANDS}
    low = ocm.add_edge_support(base.copy(), f_off, gain=0.35)
    ramp = np.arange(16, dtype=np.float32).reshape(4, 4)
    f_on = {k: ramp.copy() for k in ocm.EDGE_BANDS}
    high = ocm.add_edge_support(base.copy(), f_on, gain=0.35)
    assert high[1, 1] > low[1, 1] > 0.0
    assert np.isfinite(high).all() and high.min() >= 0.0 and high.max() <= 1.0
    # A spatially constant band carries no gradient information: percentile normalisation collapses it to
    # zero, so it must add no gain. Regression guard against a silent "all bands are strong" support bug.
    f_flat = {k: np.full((4, 4), 7.0, dtype=np.float32) for k in ocm.EDGE_BANDS}
    assert np.allclose(ocm.add_edge_support(base.copy(), f_flat, gain=0.35), low)
