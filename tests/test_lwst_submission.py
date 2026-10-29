"""Automated end-to-end verification tests for GEMSDOESASS3 GeoTIFF, Evidence & Protocol Gates."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path("/tmp/gems_data")


def test_run_card_and_protocol_schema():
    rc_path = ROOT / "evidence" / "run_card.json"
    assert rc_path.exists(), "Missing evidence/run_card.json"
    rc = json.loads(rc_path.read_text())

    required_keys = {
        "hypothesis",
        "mechanism",
        "mimic",
        "holdout_dti",
        "leakage_canary",
        "registry_correlation_and_overlap",
        "raster_sha256",
        "validator_output",
        "submission_name",
        "submission_note",
        "verdict",
    }
    assert required_keys.issubset(rc.keys())
    assert len(rc["submission_note"]) <= 140
    # Corrected 2026-10-29 (IR-SASS3-42, IR-SASS3-41): the earlier verdict and ok_to_download True came from a format gate
    # that did not test the outside-bounds rule. The file fails that rule, so download is not approved.
    assert rc["verdict"] == "blocked_outside_bounds"
    assert rc["ok_to_submit"] is False
    assert rc["ok_to_download"] is False

    # Holdout-DTI and SGMC not run (pending competition data)
    assert rc["holdout_dti"]["score_label"] == "PENDING_DATA"
    assert rc["holdout_dti"]["pooled_dti"] is None


def test_leakage_canary_and_uniqueness_gates():
    canary = json.loads((ROOT / "evidence" / "leakage_canary_report.json").read_text())
    assert canary["all_passed"] is True
    assert canary["n_channels_tested"] == 51
    assert canary["worst_symmetric_auc"] <= 0.90

    uniq = json.loads((ROOT / "evidence" / "uniqueness_audit_386.json").read_text())
    assert uniq["total_valid_registry_rasters_checked"] == 386
    assert uniq["surface_before_placement"]["passed_all_386"] is True
    assert uniq["surface_before_placement"]["worst_abs_spearman"] <= 0.90

    fd = uniq["final_dots"]
    assert fd["passed_all_focus_9_sites_literally"] is True
    assert fd["passed_all_385_genuine_literally"] is True
    assert fd["passed_null_calibrated_all_386"] is True
    assert fd["worst_abs_spearman_all_386"] <= 0.90
    assert fd["worst_within_3px_focus_9_sites"] <= 0.70
    assert fd["worst_within_3px_385_genuine"] <= 0.70


def test_geotiff_automated_validation_gate_and_zip():
    rc = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    tif_path = ROOT / "docs" / "downloads" / rc["submission_name"]
    zip_path = tif_path.with_suffix(".tif.zip")
    assert tif_path.exists(), f"Missing GeoTIFF {tif_path}"
    assert zip_path.exists(), f"Missing ZIP {zip_path}"

    # Verify SHA-256 matches run_card
    actual_sha = hashlib.sha256(tif_path.read_bytes()).hexdigest()
    assert actual_sha == rc["raster_sha256"]

    # Verify ZIP contains byte-identical GeoTIFF
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [tif_path.name]
        zip_inner_sha = hashlib.sha256(zf.read(tif_path.name)).hexdigest()
        assert zip_inner_sha == actual_sha

    # Programmatic GeoTIFF inspection (runs both locally with /tmp/gems_data and in lightweight GitHub Actions CI)
    with rasterio.open(tif_path) as sub_ds:
        assert sub_ds.count == 1
        assert sub_ds.dtypes[0] == "float32"
        assert str(sub_ds.crs) == "EPSG:32611"
        assert (sub_ds.height, sub_ds.width) == (3730, 3292)
        assert tuple(round(float(x), 6) for x in list(sub_ds.transform)[:6]) == (
            100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0
        )
        assert sub_ds.nodata is None
        arr = sub_ds.read(1)

    # Whole-grid finite [0.0, 1.0] guarantee (fixes "Predicted values must be in range [0, 1]")
    assert np.isfinite(arr).all(), "GeoTIFF contains NaN or Inf!"
    assert float(arr.min()) >= 0.0, f"Min {arr.min()} < 0.0!"
    assert float(arr.max()) <= 1.0, f"Max {arr.max()} > 1.0!"

    dots = arr > 0.0
    n_dots = int(dots.sum())
    assert n_dots == int(rc["validator_output"]["n_soft_pixels"]), f"dots={n_dots}"

    if (DATA_DIR / "sample_submission.tif").exists() and (DATA_DIR / "labels.tif").exists():
        with rasterio.open(DATA_DIR / "sample_submission.tif") as ref_ds:
            assert sub_ds.crs == ref_ds.crs
            assert sub_ds.transform == ref_ds.transform
            foot = np.isfinite(ref_ds.read(1))
        with rasterio.open(DATA_DIR / "labels.tif") as lbl_ds:
            labels = (lbl_ds.read(1) > 0) & foot
        assert float(np.abs(arr[~foot]).max()) == 0.0
        assert int((dots & labels).sum()) == 0
        dist_lbl = ndi.distance_transform_edt(~labels)
        assert float(dist_lbl[dots].min()) > 2.0
