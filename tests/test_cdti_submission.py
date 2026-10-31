"""Invariants for the CDTI-128 candidate (2026-10-30) and for its score estimator.

These tests read only shipped files, so they run in CI without the competition data.
Anything that needs `.cache/` (the interview rasters, the registry dot cache) skips with a
visible reason rather than passing silently.
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
NAME = "gemsdoesass3-cdti128-consensus-40533-20261030T041500Z-nanoutside"
TIF = ROOT / "docs/downloads" / f"{NAME}.tif"
ZIP = TIF.with_suffix(".tif.zip")
CARD = ROOT / "evidence/run_card_cdti_20261030.json"
VALIDATOR = ROOT / "evidence/validator_cdti_20261030.json"
LOO = ROOT / "evidence/cdti_estimator_loo_20261030.json"
FOCUS9 = ROOT / "evidence/cdti_focus9_estimates_20261030.json"
SAMPLE = ROOT / ".cache/gems_data/sample_submission.tif"

EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_candidate_and_zip_exist_byte_identical():
    assert TIF.is_file() and TIF.stat().st_size > 100_000
    assert ZIP.is_file()
    with zipfile.ZipFile(ZIP) as zf:
        names = zf.namelist()
        assert len(names) == 1 and names[0].endswith(".tif")
        assert zf.read(names[0]) == TIF.read_bytes()


def test_grid_crs_shape_transform_dtype():
    with rasterio.open(TIF) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.crs.to_string() == EXPECTED_CRS
        assert (ds.height, ds.width) == EXPECTED_SHAPE
        assert all(abs(a - b) < 1e-9 for a, b in zip(tuple(ds.transform)[:6], EXPECTED_TRANSFORM))


def test_values_are_zero_or_one_and_nan_only_outside_footprint():
    with rasterio.open(TIF) as ds:
        arr = ds.read(1)
        nodata = ds.nodata
    assert nodata is not None and np.isnan(nodata)
    finite = np.isfinite(arr)
    assert set(np.unique(arr[finite]).tolist()) <= {0.0, 1.0}
    assert int((arr[finite] == 1.0).sum()) == 40_533
    if SAMPLE.is_file():
        with rasterio.open(SAMPLE) as ds:
            foot = np.isfinite(ds.read(1))
        assert bool(np.isfinite(arr[foot]).all()), "NaN inside the organiser footprint"
        assert bool((~finite[~foot]).all()), "finite value outside the organiser footprint"
    else:
        pytest.skip("sample_submission.tif absent; footprint containment not re-checked here")


def test_run_card_matches_bytes_and_note_length():
    card = json.loads(CARD.read_text())
    assert card["raster"]["sha256"] == _sha(TIF)
    assert card["raster"]["positive_cells"] == 40_533
    assert card["raster"]["positive_cells_outside_footprint"] == 0
    assert card["raster"]["positive_cells_on_known_faults"] == 0
    assert card["validator_output"]["failed_gates"] == []
    assert card["verdict"] == "promote"
    note = card["submission_note"]
    assert len(note) <= 140 and len(note) == card["submission_note_length"]
    assert card["score_estimate"]["label"].startswith("ESTIMATE")


def test_validator_receipt_all_gates_pass():
    rec = json.loads(VALIDATOR.read_text())
    assert rec["failed"] == []
    assert rec["ok_to_download"] is True and rec["ok_to_submit"] is True
    assert all(rec["checks"].values())
    assert rec["sha256"] == _sha(TIF)
    # the 70% / 0.90 lane thresholds are hard
    assert rec["detail"]["worst_within_3px_fraction"] <= 0.70
    assert abs(rec["detail"]["worst_abs_rank_correlation"]) <= 0.90
    assert rec["detail"]["identical_count_in_registry"] == 0
    # leakage canary
    assert rec["detail"]["canary_auc_field_vs_catalogue"] <= 0.90


def test_estimator_is_validated_out_of_sample():
    loo = json.loads(LOO.read_text())
    assert loo["n_files"] >= 100
    assert loo["loo"]["spearman"] > 0.80
    assert 0.0 < loo["loo"]["rmse"] < 0.08
    # the nine focus sites must all be present and predicted within 0.05
    focus = json.loads(FOCUS9.read_text())
    assert len(focus) == 9
    for row in focus:
        assert abs(row["loo_estimate"] - row["owner_reported_score"]) < 0.05


def test_estimate_beats_the_champion_point_estimate():
    card = json.loads(CARD.read_text())
    champ = 0.2778  # OWNER-REPORT
    assert card["score_estimate"]["central"] > champ
    assert card["score_estimate"]["optimism_corrected"] > champ


def test_site_pages_do_not_promote_the_superseded_file():
    for page in ("index.html", "executive-summary.html"):
        txt = (ROOT / "docs" / page).read_text()
        assert "NO-GO" in txt or "NO APPROVED TIFF" in txt
        assert "DO NOT SUBMIT" in txt
        assert "run_card_20261031_review.json" in txt or "repo-review-20261031.md" in txt
        assert "OK TO SUBMIT" not in txt
