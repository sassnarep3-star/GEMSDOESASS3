"""Invariants for the literal-rule-compliant candidate (H-LIT-DISP), NaN outside the footprint.

These tests read only shipped files, so they run in CI. The lattice recomputation needs the
restored competition data and skips with a visible reason when it is absent.
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
CAND_NAME = "gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif"
CAND = ROOT / "docs/downloads" / CAND_NAME
ZIP = CAND.with_suffix(".tif.zip")
AUDIT = ROOT / "evidence/literal_audit_gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.json"
CARD = ROOT / "evidence/run_card_literal.json"
HOLD = ROOT / "evidence/literal_candidates_sgmc.json"
LATTICE = ROOT / ".cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
SAMPLE = ROOT / ".cache/gems_data/sample_submission.tif"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_candidate_and_zip_present_and_identical():
    assert CAND.exists() and ZIP.exists()
    with zipfile.ZipFile(ZIP) as z:
        assert z.namelist() == [CAND_NAME]
        assert hashlib.sha256(z.read(CAND_NAME)).hexdigest() == _sha(CAND)


def test_candidate_format_matches_organizer_grid():
    with rasterio.open(CAND) as s:
        assert s.count == 1
        assert s.dtypes[0] == "float32"
        assert str(s.crs) == "EPSG:32611"
        assert s.shape == (3730, 3292)
        assert tuple(s.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert s.nodata is not None and np.isnan(s.nodata)
        arr = s.read(1)
    # Official rule (page 967): data outside the bounds is null or nan. Finite cells are the footprint.
    finite = np.isfinite(arr)
    assert int(finite.sum()) == 5_167_373, "finite cells must equal the footprint"
    assert np.isnan(arr[~finite]).all(), "outside the footprint must be NaN, not zero"
    assert not np.isinf(arr).any()
    vals = np.unique(arr[finite])
    assert float(vals.min()) >= 0.0 and float(vals.max()) <= 1.0
    assert set(vals.tolist()) <= {0.0, 1.0}
    assert int((arr > 0).sum()) == 21012


def test_receipts_bind_to_the_shipped_bytes():
    audit = json.loads(AUDIT.read_text())
    assert audit["candidate_sha256"] == _sha(CAND)
    assert audit["literal_rule_passed"] is True
    assert audit["surface_stage"]["passed"] is True
    assert audit["final_dots_stage"]["literal_rule_passed"] is True
    assert audit["final_dots_stage"]["worst_within_3px_fraction"] < 0.70
    assert audit["final_dots_stage"]["worst_abs_spearman"] <= 0.90
    assert audit["registry_rasters_compared"] == 386
    assert audit["format_validator"]["checks"]["all_passed"] is True


def test_run_card_is_negative_not_promoted_and_note_fits():
    card = json.loads(CARD.read_text())
    assert card["raster_sha256"] == _sha(CAND)
    assert card["verdict"] == "negative"
    assert card["summary"]["recommended_for_leaderboard_slot"] is False
    assert card["summary"]["download_ok"] is True
    assert 1 <= len(card["submission_note"]) <= 140
    assert card["holdout_dti"]["score_label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["n_withheld_positives"] == 62703


def test_holdout_numbers_are_labelled_and_reproduce_controls():
    hold = json.loads(HOLD.read_text())
    assert hold["evaluator_version"] == "GEMSDOE32-SGMC-CAL-v3.0"
    champ = hold["results"]["champion_0.2778_control"]
    assert abs(champ["calibrated"] - 0.064121) < 1e-5  # matches the review's control value
    lwst = hold["results"]["lwst_control"]
    assert abs(lwst["calibrated"] - 0.065702) < 1e-5
    lit = hold["results"]["literal_dispersed"]
    # The literal-compliant file is expected to be BELOW the champion. Assert the recorded fact.
    assert lit["calibrated_ci95"][1] < champ["calibrated_ci95"][0]


@pytest.mark.skipif(not LATTICE.exists() or not SAMPLE.exists(),
                    reason="restored competition data not present (.cache/gems_data); run scripts/download_competition_data.sh")
def test_lattice_overlap_recomputed_from_raster():
    from scipy import ndimage as ndi

    with rasterio.open(SAMPLE) as t:
        foot = np.isfinite(t.read(1))
    with rasterio.open(LATTICE) as t:
        lat = t.read(1)
    lat_dots = (np.where(np.isfinite(lat), lat, 0.0) > 0) & foot
    with rasterio.open(CAND) as s:
        dots = (s.read(1) > 0) & foot
    d = ndi.distance_transform_edt(~lat_dots)
    assert float((d[dots] <= 3.0).mean()) <= 0.70
