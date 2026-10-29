"""Current candidate must remain an archive-only negative until all gates exist."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif"


def test_current_run_card_labels_missing_evidence_and_negative_verdict():
    rc = json.loads((ROOT / "evidence/current_run_card.json").read_text())
    assert rc["verdict"] == "negative"
    assert rc["ok_to_submit"] is False
    assert rc["holdout_dti"]["status"] == "NOT RUN"
    assert rc["holdout_dti"]["pooled_dti"] is None
    assert rc["leakage_canary"]["status"] == "NOT RUN for this raster"
    assert rc["registry_correlation_and_overlap"]["literal_uniqueness_gate"] == "NOT CLEARED"
    assert rc["submission_name"] + ".tif" == CANDIDATE.name
    assert len(rc["submission_note"]) <= 140
    assert rc["submission_note"] in (ROOT / "README.md").read_text()


def test_historical_canary_and_uniqueness_artifacts_are_not_marked_current_approval():
    canary = json.loads((ROOT / "evidence/leakage_canary_report.json").read_text())
    assert canary["all_passed"] is True
    assert canary["n_channels_tested"] == 51
    assert "NOT RUN for this raster" in json.loads((ROOT / "evidence/current_run_card.json").read_text())["leakage_canary"]["status"]

    audit = json.loads((ROOT / "evidence/uniqueness_audit_386.json").read_text())
    assert audit["total_valid_registry_rasters_checked"] == 386
    witness = audit["space_filling_calibration_lattices"][0]
    assert witness["within_3px_fraction"] > 0.70
    assert witness["literal_duplicate"] is True
    assert json.loads((ROOT / "evidence/current_run_card.json").read_text())["ok_to_submit"] is False


def test_current_archive_geotiff_format_and_sha():
    card = json.loads((ROOT / "evidence/current_run_card.json").read_text())
    assert CANDIDATE.is_file()
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() == card["raster_sha256"]
    with rasterio.open(CANDIDATE) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert str(src.crs) == "EPSG:32611"
        assert src.shape == (3730, 3292)
        assert tuple(src.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert src.nodata is None
        arr = src.read(1)
    assert np.isfinite(arr).all()
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    assert int((arr > 0).sum()) == 8794


def test_one_lattice_witness_is_not_a_complete_uniqueness_certificate():
    audit = json.loads((ROOT / "evidence/uniqueness_audit_current_candidate_20261029.json").read_text())
    assert audit["result"]["all_positive_cells"]["fraction"] == 0.444053
    assert audit["result"]["one_witness_result_below_threshold"] is True
    assert audit["result"]["complete_registry_uniqueness_pass"] is False
    assert audit["verdict"] == "negative; archive only; do not submit"


def test_fail_closed_cli():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_all_gates.py"), "--expect-blocked"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["format_and_record_integrity"] is True
    assert result["ok_to_download"] is False
    assert result["ok_to_download_for_analysis"] is True
    assert result["ok_to_submit"] is False
    assert result["checks"]["complete_uniqueness_gate"] is False
    assert result["checks"]["holdout_gate"] is False
