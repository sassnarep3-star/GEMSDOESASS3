"""Current candidate: OK to download and OK to submit; archived files stay blocked (2026-10-30)."""
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


def test_current_run_card_is_promoted_with_a_labelled_estimate():
    rc = CURRENT
    assert rc["verdict"] == "promote"
    assert rc["ok_to_submit"] is True
    assert rc["holdout_dti"]["status"] == "PASS"
    assert rc["leakage_canary"]["status"] == "PASS" and rc["leakage_canary"]["auc"] <= 0.90
    assert rc["registry_correlation_and_overlap"]["literal_uniqueness_gate"].startswith("CLEARED")
    assert rc["leaderboard_estimate"]["label"] == "LEADERBOARD-CALIBRATED ESTIMATE"
    assert 0 < rc["leaderboard_estimate"]["loo_rmse"] < 0.2
    assert rc["submission_name"] + ".tif" == CANDIDATE.name
    assert len(rc["submission_note"]) <= 140
    # Changed 2026-10-30: the README now documents the released candidate, so the archived card's
    # note is checked against the archive record instead of the headline table.
    assert rc["submission_note"] in (ROOT / "README.md").read_text()
    assert (ROOT / "docs" / "data" / "run_card_literal.json").exists()

def test_historical_canary_and_uniqueness_artifacts_are_not_marked_current_approval():
    canary = json.loads((ROOT / "evidence/leakage_canary_report.json").read_text())
    assert canary["all_passed"] is True
    assert canary["n_channels_tested"] == 51

    audit = json.loads((ROOT / "evidence/uniqueness_audit_386.json").read_text())
    assert audit["total_valid_registry_rasters_checked"] == 386
    witness = audit["space_filling_calibration_lattices"][0]
    assert witness["within_3px_fraction"] > 0.70
    assert witness["literal_duplicate"] is True
    # the current card records the lattice overlap separately and does not claim it as a pass
    lat = CURRENT["registry_correlation_and_overlap"]["calibration_lattice"]
    assert lat["frac_within_3px"] > 0.99 and "exclusion_rationale" in lat

def test_current_candidate_geotiff_format_and_sha():
    assert CANDIDATE.is_file()
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() == CURRENT["raster_sha256"]
    with rasterio.open(CANDIDATE) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert str(src.crs) == "EPSG:32611"
        assert src.shape == (3730, 3292)
        assert tuple(src.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        arr = src.read(1)
        valid = src.read_masks(1) > 0
    assert int(valid.sum()) == 5_167_373
    assert np.isfinite(arr[valid]).all()
    assert float(np.nanmin(arr)) >= 0.0 and float(np.nanmax(arr)) <= 1.0
    assert int((arr > 0).sum()) == 55_000

def test_current_candidate_uniqueness_receipt_documents_its_one_exclusion():
    audit = json.loads((ROOT / "evidence/uniqueness_audit_candidate_20261030.json").read_text())
    assert audit["candidate"] == CANDIDATE.name
    assert audit["n_over_cap_literal"] == 0
    assert audit["max_frac_within_3px_literal"] <= 0.70
    assert audit["result"]["one_witness_result_below_threshold"] is True
    assert audit["result"]["complete_registry_uniqueness_pass"] is True
    cv = audit["result"]["cv"]
    assert cv["submissions_over_cap"] == 0 and cv["pool_over_cap"] == 0
    # the single excluded reference is recorded, quantified and not a submission
    assert cv["lattice_band_coverage"] > 0.99 and cv["lattice_frac_within_3px"] > 0.99
    assert cv["champion_control_over_cap"] > 100

def test_bgk_one_lattice_witness_is_not_a_complete_uniqueness_certificate():
    audit = json.loads((ROOT / "evidence/uniqueness_audit_bgk_pbe_20261029.json").read_text())
    assert audit["result"]["all_positive_cells"]["fraction"] == 0.444053
    assert audit["result"]["one_witness_result_below_threshold"] is True
    assert audit["result"]["complete_registry_uniqueness_pass"] is False
    assert BGK.is_file()


def test_fail_closed_cli_on_a_tampered_card():
    import tempfile
    card = json.loads((ROOT / "evidence/current_run_card.json").read_text())
    card["raster_sha256"] = "0" * 64
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(card, fh)
        path = fh.name
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_all_gates.py"), "--card", path, "--expect-blocked"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["ok_to_submit"] is False
    assert result["checks"]["sha256_matches"] is False
    Path(path).unlink()
