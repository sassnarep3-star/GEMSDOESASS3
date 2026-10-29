"""Current candidate: OK to download (format and competition rules), NOT OK to submit (gates still failing)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CURRENT = json.loads((ROOT / "evidence/current_run_card.json").read_text())
CANDIDATE = ROOT / CURRENT["download_path"]
BGK = ROOT / "docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif"


def test_current_run_card_labels_missing_evidence_and_negative_verdict():
    rc = CURRENT
    assert rc["verdict"] == "negative"
    assert rc["ok_to_submit"] is False
    assert rc["ok_to_download_for_analysis"] is True
    assert rc["holdout_dti"]["status"] == "NOT PASS"
    assert rc["holdout_dti"]["primary_hide_and_recover"]["score_label"] == "NOT RUN"
    assert rc["leakage_canary"]["status"] == "NOT RUN for this raster"
    assert rc["registry_correlation_and_overlap"]["literal_uniqueness_gate"] == "NOT CLEARED"
    assert rc["submission_name"] + ".tif" == CANDIDATE.name
    assert len(rc["submission_note"]) <= 140
    assert rc["submission_note"] in (ROOT / "README.md").read_text()


def test_historical_canary_and_uniqueness_artifacts_are_not_marked_current_approval():
    canary = json.loads((ROOT / "evidence/leakage_canary_report.json").read_text())
    assert canary["all_passed"] is True
    assert canary["n_channels_tested"] == 51
    assert "NOT RUN for this raster" in CURRENT["leakage_canary"]["status"]

    audit = json.loads((ROOT / "evidence/uniqueness_audit_386.json").read_text())
    assert audit["total_valid_registry_rasters_checked"] == 386
    witness = audit["space_filling_calibration_lattices"][0]
    assert witness["within_3px_fraction"] > 0.70
    assert witness["literal_duplicate"] is True
    assert CURRENT["ok_to_submit"] is False


def test_current_candidate_geotiff_format_and_sha():
    assert CANDIDATE.is_file()
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() == CURRENT["raster_sha256"]
    with rasterio.open(CANDIDATE) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert str(src.crs) == "EPSG:32611"
        assert src.shape == (3730, 3292)
        assert tuple(src.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert np.isnan(src.nodata)
        arr = src.read(1)
    finite = np.isfinite(arr)
    assert int(finite.sum()) == 5_167_373
    assert np.isnan(arr[~finite]).all()
    assert float(np.nanmin(arr)) >= 0.0 and float(np.nanmax(arr)) <= 1.0
    assert int((arr > 0).sum()) == 21_012


def test_current_candidate_uniqueness_receipt_is_not_a_complete_certificate():
    audit = json.loads((ROOT / "evidence/uniqueness_audit_current_candidate_20261029.json").read_text())
    assert audit["candidate_sha256"] == CURRENT["raster_sha256"]
    assert audit["result"]["one_witness_result_below_threshold"] is True
    assert audit["result"]["complete_registry_uniqueness_pass"] is False


def test_bgk_one_lattice_witness_is_not_a_complete_uniqueness_certificate():
    audit = json.loads((ROOT / "evidence/uniqueness_audit_bgk_pbe_20261029.json").read_text())
    assert audit["result"]["all_positive_cells"]["fraction"] == 0.444053
    assert audit["result"]["one_witness_result_below_threshold"] is True
    assert audit["result"]["complete_registry_uniqueness_pass"] is False
    assert BGK.is_file()


def test_fail_closed_cli():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_all_gates.py"), "--expect-blocked"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["format_and_record_integrity"] is True
    assert result["ok_to_download"] is True
    assert result["ok_to_download_for_analysis"] is True
    assert result["ok_to_submit"] is False
    assert result["checks"]["complete_uniqueness_gate"] is False
    assert result["checks"]["holdout_gate"] is False
    assert result["checks"]["canary_gate"] is False
