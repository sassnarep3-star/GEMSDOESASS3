"""Gate tests for the live portal rejection "Predicted values must be in range [0, 1]".

Root cause, measured on the previously promoted file on 2026-10-30: the raster stored float32 NaN in
the 7,111,787 outside-footprint cells. Its values inside the footprint were all legal, but the portal
compares the *stored* array with [0, 1] element-wise and every NaN comparison is False, so the file was
rejected with a range error. These tests pin the reproduction, the fix (finite payload outside the
footprint plus a GDAL mask band carrying the null-ness), and the two metric-algebra facts the emitter
design depends on.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from validate_submission_tif import portal_range_gate  # noqa: E402
from gems32.metric import dti_exact  # noqa: E402


def test_nan_outside_footprint_fails_the_literal_portal_test() -> None:
    """A raster whose only non-conforming cells are NaN must be rejected by the element-wise test."""
    arr = np.full((8, 8), np.nan, dtype=np.float32)
    arr[3:5, 3:5] = 1.0
    ok, n_bad = portal_range_gate(arr)
    assert ok is False
    assert n_bad == 64 - 4
    # and the "values_in_0_1" reading that passes on the finite subset is exactly the trap
    finite = arr[np.isfinite(arr)]
    assert bool(np.all((finite >= 0) & (finite <= 1)))


def test_zero_outside_footprint_passes_and_mask_band_carries_the_null_requirement(tmp_path: Path) -> None:
    """The shipped rendering: 0.0 stored outside, null-ness declared through an internal mask band."""
    arr = np.zeros((64, 64), dtype=np.float32)
    arr[10:20, 10:20] = 1.0
    assert portal_range_gate(arr)[0] is True
    prof = {
        "driver": "GTiff", "dtype": "float32", "width": 64, "height": 64, "count": 1,
        "crs": "EPSG:32611", "transform": rasterio.transform.from_origin(0.0, 6400.0, 100.0, 100.0),
        "tiled": True, "predictor": 2, "compress": "deflate",
    }
    out = tmp_path / "probe-safe.tif"
    with rasterio.open(out, "w", **prof) as ds:
        ds.write(arr, 1)
        ds.write_mask(np.ones((64, 64), dtype=np.uint8))  # per-dataset mask band; 1 = valid
    with rasterio.open(out) as ds:
        assert ds.count == 1
        assert not ds.nodatavals[0]  # no NODATA tag: 0.0 must stay readable, not be masked away
        assert any(ds.mask_flag_enums[0]), "expected a per-dataset mask band for the null-outside rule"
        again = ds.read(1)
    assert np.isfinite(again).all()
    assert portal_range_gate(again)[0] is True


@pytest.mark.parametrize("scale", [0.9, 0.6, 0.3, 0.05])
def test_binary_emission_is_optimal_on_a_fixed_support(scale: float) -> None:
    """DTI is linear-fractional and monotone in each pixel, so rescaling a fixed support cannot help.

    This is why the candidate writes p = 1 on the selected dots instead of a soft probability field.
    """
    truth = np.zeros((32, 32), dtype=np.uint8)
    truth[16, 16] = 1
    truth[17, 17] = 1
    support = np.zeros((32, 32), dtype=bool)
    support[16, 16] = True
    support[17, 17] = True
    support[25, 6] = True  # a false-positive pixel the selector also picked
    binary = np.where(support, 1.0, 0.0).astype(np.float32)
    soft = (binary * scale).astype(np.float32)
    d_bin = dti_exact(binary, truth)["dti"]
    d_soft = dti_exact(soft, truth)["dti"]
    assert d_bin >= d_soft - 1e-12, (scale, d_bin, d_soft)


def test_dilation_beyond_the_kernel_radius_is_pure_false_positive() -> None:
    """Adding predicted pixels farther than 300 m from every truth pixel can only lower DTI."""
    truth = np.zeros((40, 40), dtype=np.uint8)
    truth[20, 20] = 1
    near = np.zeros((40, 40), dtype=np.float32)
    near[20, 20] = 1.0
    wide = near.copy()
    wide[20 - 5, 20] = 1.0  # 500 m away: outside the triangular kernel, so no credit at all
    assert dti_exact(near, truth)["dti"] > dti_exact(wide, truth)["dti"]
