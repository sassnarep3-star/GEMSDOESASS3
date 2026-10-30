"""Regression tests for the official DTI metric and the shared submission validator.

Sources (verified 2026-10-30):
  * Official metric and submission rules: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  * Known-fault masking clarification (DrivenData staff): https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516
"""
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32 import metric  # noqa: E402
import validate_submission_tif as v  # noqa: E402

CANDIDATE = ROOT / "docs/downloads/gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif"


# ---------- official metric -------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 2])
def test_exact_matches_literal_equations(seed):
    rng = np.random.default_rng(seed)
    truth = rng.random((24, 24)) < 0.03
    truth[5, 2:20] = True  # a line-like fault
    pred = np.where(rng.random((24, 24)) < 0.1, rng.random((24, 24)), 0.0)
    a = metric.dti_exact(pred, truth)
    b = metric.dti_bruteforce(pred, truth)
    assert a["tp"] == pytest.approx(b["tp"], rel=1e-9, abs=1e-9)
    assert a["fp"] == pytest.approx(b["fp"], rel=1e-9, abs=1e-9)
    assert a["fn"] == pytest.approx(b["fn"], rel=1e-9, abs=1e-9)
    assert a["dti"] == pytest.approx(b["dti"], rel=1e-9, abs=1e-9)


def test_binary_fast_path_matches_exact():
    rng = np.random.default_rng(7)
    truth = rng.random((30, 30)) < 0.05
    pred = rng.random((30, 30)) < 0.15
    a = metric.dti_exact(pred.astype(float), truth)
    b = metric.dti_binary(pred, truth)
    assert a["dti"] == pytest.approx(b["dti"], rel=1e-9, abs=1e-9)


def test_known_faults_are_excluded():
    truth = np.zeros((10, 10), bool)
    truth[5, 5] = True
    known = np.zeros((10, 10), bool)
    known[5, 5] = True
    pred = np.zeros((10, 10))
    pred[0, 0] = 1.0
    r = metric.dti_exact(pred, truth, known=known)
    assert r["n_truth"] == 0  # the only truth pixel is masked as a known fault


def test_rejects_values_outside_unit_interval():
    truth = np.zeros((4, 4), bool)
    pred = np.zeros((4, 4))
    pred[0, 0] = 1.5
    with pytest.raises(ValueError):
        metric.dti_exact(pred, truth)


# ---------- shared validator (footprint rule) --------------------------------------------------

@pytest.mark.skipif(not CANDIDATE.exists(), reason="candidate raster not present")
def test_validator_passes_committed_candidate():
    rec = v.validate(CANDIDATE)
    assert rec["checks"]["nan_outside_and_finite_inside_footprint"] is True
    assert rec["checks"]["values_in_0_1"] is True
    assert rec["all_hard_checks_pass"] is True


def _copy_with_edit(tmp_path, edit):
    dst = tmp_path / "edited.tif"
    shutil.copy(CANDIDATE, dst)
    with rasterio.open(dst, "r+") as ds:
        arr = ds.read(1)
        edit(arr)
        ds.write(arr, 1)
    return dst


@pytest.mark.skipif(not CANDIDATE.exists(), reason="candidate raster not present")
def test_validator_rejects_zero_outside_footprint(tmp_path):
    fp = v._footprint((3730, 3292))
    outside = np.argwhere(~fp)
    def edit(a):
        a[outside[0][0], outside[0][1]] = 0.0  # finite zero outside bounds is NOT null/nan
    rec = v.validate(_copy_with_edit(tmp_path, edit))
    assert rec["checks"]["nan_outside_and_finite_inside_footprint"] is False
    assert rec["all_hard_checks_pass"] is False


@pytest.mark.skipif(not CANDIDATE.exists(), reason="candidate raster not present")
def test_validator_rejects_nan_inside_footprint(tmp_path):
    fp = v._footprint((3730, 3292))
    inside = np.argwhere(fp)
    def edit(a):
        a[inside[0][0], inside[0][1]] = np.nan
    rec = v.validate(_copy_with_edit(tmp_path, edit))
    assert rec["checks"]["nan_outside_and_finite_inside_footprint"] is False
    assert rec["all_hard_checks_pass"] is False


def test_footprint_from_committed_mask_has_recorded_pixel_count():
    fp = v._footprint((3730, 3292))
    assert fp is not None
    assert int(fp.sum()) == 5167373
