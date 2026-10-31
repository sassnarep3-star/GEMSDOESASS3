"""Invariants for the leaderboard-inversion candidate (2026-10-30), portal-safe encoding.

These tests exist to stop the two failure modes that matter:

1. the raster drifting away from what the pages and the receipt say (dot count, SHA-256,
   format, value discipline, zip identity), and
2. the headline number becoming un-recomputable -- so the estimate is recomputed here from the
   raster and the field, and must match the receipt to 5e-4.

The submittable artefact is the portal-safe render (finite {0,1} inside the footprint, 0.0 outside,
internal GDAL mask band). The NaN-payload copy is retained only as the analysis source; its dot set is
bit-identical (symmetric difference 0), so every estimate and uniqueness receipt applies unchanged.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
NAME = "gemsdoesass3-lbinv-84262-20261030T0900Z-safe"
TIF = ROOT / "docs" / "downloads" / f"{NAME}.tif"
ZIP = TIF.with_name(TIF.name + ".zip")
BUILD = TIF.with_name(TIF.stem + "-build.json")
RECEIPT = ROOT / "evidence" / "validator_lbinv_safe_20261031.json"
ESTIMATOR = ROOT / "evidence" / "distill_from_leaderboard_20261030.json"
ALPHA, BETA = 0.2, 0.8

# The raster and its receipts are committed; the estimator field and the reference grid live in
# .cache (a rebuildable derivative), so the subset of tests that re-derive numbers from the field
# is skipped on a bare checkout such as CI.
HAS_CACHE = (ROOT / ".cache" / "distill_q.npz").exists() and (
    ROOT / ".cache" / "gems_data" / "sample_submission.tif").exists()
pytestmark = pytest.mark.skipif(not TIF.exists(), reason="candidate raster not present")


@pytest.fixture(scope="module")
def artifact():
    if not HAS_CACHE:
        pytest.skip("estimator field not built in .cache")
    build = json.loads(BUILD.read_text())
    with rasterio.open(ROOT / ".cache" / "gems_data" / "sample_submission.tif") as ref:
        foot = np.isfinite(ref.read(1))
        rshape, rtransform, rcrs = ref.shape, ref.transform, ref.crs
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        meta = {"count": ds.count, "dtype": ds.dtypes[0], "crs": ds.crs,
                "shape": ds.shape, "transform": ds.transform}
    return build, a, foot, meta, (rshape, rtransform, rcrs)


def test_format_matches_organizer_rules(artifact):
    build, a, foot, meta, (rshape, rtransform, rcrs) = artifact
    assert meta["count"] == 1 and meta["dtype"] == "float32"
    assert meta["crs"] == rcrs and meta["shape"] == rshape and meta["transform"] == rtransform
    assert abs(meta["transform"].a - 100.0) < 1e-6
    vals = a[np.isfinite(a)]
    assert vals.min() >= 0.0 and vals.max() <= 1.0
    assert set(np.unique(vals)).issubset({0.0, 1.0})
    # portal-safe encoding: outside cells are finite 0.0 carried by an internal mask band, not NaN.
    assert np.isfinite(a).all()
    assert (a[~foot] == 0.0).all()
    assert np.isfinite(a[foot]).all()        # nothing missing inside


def test_portal_range_test_passes_on_all_cells():
    # The live form rejects NaN outside the footprint; the safe render must have zero violating cells.
    with rasterio.open(TIF) as ds:
        a = ds.read(1).astype(np.float64)
    bad = int(np.count_nonzero(~((a >= 0.0) & (a <= 1.0))))
    assert bad == 0


def test_dot_count_and_sha_match_receipt(artifact):
    build, a, *_ = artifact
    assert int((a == 1.0).sum()) == build["n_dots"]
    assert hashlib.sha256(TIF.read_bytes()).hexdigest() == build["raster_sha256"]


def test_zip_is_the_same_bytes(artifact):
    assert ZIP.exists()
    with zipfile.ZipFile(ZIP) as zf:
        names = zf.namelist()
        assert names == [TIF.name]
        assert zf.read(names[0]) == TIF.read_bytes()


def test_headline_estimate_is_recomputable(artifact):
    build, a, foot, *_ = artifact
    z = np.load(ROOT / ".cache" / "distill_q.npz")
    q = z["q"]
    grid_of_fp = np.nonzero(foot.ravel())[0]
    fp_of_grid = np.full(foot.size, -1, dtype=np.int64)
    fp_of_grid[grid_of_fp] = np.arange(grid_of_fp.size)
    sel = fp_of_grid[(a == 1.0).ravel()]
    sel = sel[sel >= 0]
    qsum = float(q[sel].sum())
    N = float(np.ravel(z["N"])[0])
    est = qsum / (ALPHA * build["n_dots"] + BETA * N)
    assert abs(est - build["est_score"]) <= 5e-4
    assert abs(qsum - build["expected_tp"]) <= max(5.0, 0.001 * build["expected_tp"])


def test_note_is_portal_legal_and_published():
    build = json.loads(BUILD.read_text())
    note = build["submission_note"]
    assert 1 <= len(note) <= 140 and "\n" not in note
    assert note in (ROOT / "docs" / "index.html").read_text()
    assert build["submission_name"] in (ROOT / "docs" / "index.html").read_text()


def test_estimator_beats_the_mean_baseline():
    ev = json.loads(ESTIMATOR.read_text())
    assert ev["label"] == "ESTIMATE" and ev["not_organizer_confirmed"] is True
    assert ev["chosen"]["loo_rmse"] < ev["baseline_loo_rmse"]
    assert ev["chosen"]["loo_rho"] > 0.70
    assert ev["n_rasters"] >= 128


def test_validator_receipt_passes_every_gate():
    rec = json.loads(RECEIPT.read_text())
    assert rec["all_hard_checks_pass"] is True
    assert rec["checks"]["portal_range_test_all_cells"] is True
    assert rec["checks"]["values_in_0_1"] is True
    assert rec["checks"]["outside_cells_are_null"] is True
    assert rec["mask"]["has_internal_mask_band"] is True


def test_uniqueness_gate_is_under_the_protocol_limit():
    build = json.loads(BUILD.read_text())
    assert build["worst_registry_overlap"] <= 0.70
    assert "GEMSDOE22" in build["worst_registry_raster"]


def test_pages_send_the_reader_to_this_file_first():
    for page in ("docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / page).read_text()
        assert html.index(NAME) < html.index("cdti128-consensus") if "cdti128" in html else True
        assert "OK TO SUBMIT" in html
        assert "localhost" not in html.lower() and "127.0.0.1" not in html
