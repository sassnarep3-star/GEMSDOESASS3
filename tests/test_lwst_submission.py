"""Current candidate: OK to download (format + uniqueness), NOT OK to submit (promotion gates fail).

These tests read the live run card and the packaged raster itself, so they follow the candidate; they never
restate a stored verdict. The archived-candidate tests below keep the stale receipts pinned so that a passing
check from a previous file can never be inherited as an approval for the current one.
"""
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
AUDIT = ROOT / f"docs/downloads/{CURRENT['submission_name']}-audit.json"
BGK = ROOT / "docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif"


def test_current_run_card_labels_missing_evidence_and_negative_verdict():
    rc = CURRENT
    assert rc["verdict"].startswith("negative for promotion")
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit"] is False
    assert rc["ok_to_download_for_analysis"] is True
    assert rc["holdout_dti"]["status"] == "NOT RUN"
    assert rc["holdout_dti"]["primary_hide_and_recover"]["score_label"] == "NOT RUN"
    assert "login-walled" in rc["holdout_dti"]["reason"]
    assert rc["leakage_canary"]["status"] == "RUN-PARTIAL"
    # the card must disclose the unsatisfiable lane rule rather than drop it (IR-SASS3-76)
    assert rc["registry_correlation_and_overlap"]["literal_uniqueness_gate"].startswith("NOT SATISFIABLE")
    assert rc["registry_correlation_and_overlap"]["worst_within_3px_fraction_final_dots"] == 1.0
    assert rc["registry_correlation_and_overlap"]["worst_exact_cell_share"] < 0.95
    assert rc["submission_name"] + ".tif" == CANDIDATE.name
    assert len(rc["submission_note"]) <= 140
    assert rc["submission_note"] in (ROOT / "README.md").read_text()
    # projections are never written as scores anywhere in the card
    blob = json.dumps(rc)
    assert "PROJECTION" in blob
    assert rc["projection_bracket"]["promotion_rule_passed"] is False


def test_promotion_bracket_is_a_difference_against_the_champion_control():
    """The card's bracket must equal the validator receipt, density by density, and the rule must be negative."""
    val = json.loads((ROOT / "evidence/lli_candidate_validation_union.json").read_text())
    for density, projected in val["projections"].items():
        cand = projected["candidate"]["projected_dti"]
        champ = projected["champion_control"]["projected_dti"]
        assert CURRENT["projection_bracket"]["candidate"][density] == cand
        assert CURRENT["projection_bracket"]["champion_control"][density] == champ
        if cand <= champ:                      # at least one density must lose, else promotion would be on
            assert CURRENT["ok_to_submit"] is False
    assert min(v["candidate"]["projected_dti"] for v in val["projections"].values()) \
        - max(v["champion_control"]["projected_dti"] for v in val["projections"].values()) < 0


def test_historical_canary_and_uniqueness_artifacts_are_not_marked_current_approval():
    canary = json.loads((ROOT / "evidence/leakage_canary_report.json").read_text())
    assert canary["all_passed"] is True
    assert canary["n_channels_tested"] == 51
    assert "RUN-PARTIAL" == CURRENT["leakage_canary"]["status"]

    audit = json.loads((ROOT / "evidence/uniqueness_audit_386.json").read_text())
    assert audit["total_valid_registry_rasters_checked"] == 386
    witness = audit["space_filling_calibration_lattices"][0]
    assert witness["within_3px_fraction"] > 0.70
    assert witness["literal_duplicate"] is True
    assert CURRENT["ok_to_submit"] is False

    # the archived candidate's receipt must NOT describe the current file (no inherited approval)
    stale = json.loads((ROOT / "evidence/uniqueness_audit_current_candidate_20261029.json").read_text())
    assert stale["candidate_sha256"] != CURRENT["raster_sha256"]


def test_current_candidate_geotiff_format_and_sha():
    """The portal contract, measured on the bytes: single band float32, finite in [0,1] everywhere."""
    assert CANDIDATE.is_file()
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() == CURRENT["raster_sha256"]
    with rasterio.open(CANDIDATE) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert str(src.crs) == "EPSG:32611"
        assert src.shape == (3730, 3292)
        assert tuple(src.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert src.nodata is None          # IR-SASS3-75: a nodata/NaN tag is what trips the range check
        arr = src.read(1)
    assert np.isfinite(arr).all()
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    assert set(np.unique(arr).tolist()) == {0.0, 1.0}
    assert int((arr > 0).sum()) == CURRENT["validator_output"]["positive_cells"]
    z = np.load(ROOT / "evidence/organizer_footprint_mask.npz")
    shape = tuple(int(x) for x in z["shape"])
    foot = np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    assert int(((arr > 0) & ~foot).sum()) == 0     # every cell outside the bounds is 0.0
    assert arr[~foot].size == 7_111_787


def test_packaged_zip_matches_the_raster_and_is_single_member():
    import zipfile
    zip_path = CANDIDATE.with_suffix(".tif.zip")
    assert zip_path.is_file()
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == CURRENT["zip_sha256"]
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == [CANDIDATE.name]
        assert hashlib.sha256(archive.read(CANDIDATE.name)).hexdigest() == CURRENT["raster_sha256"]
    audit = json.loads(AUDIT.read_text())
    assert audit["sha256_tif"] == CURRENT["raster_sha256"]
    assert audit["identical_sibling_files"] == []
    assert audit["gates"]["G1_whole_array_finite_in_0_1"] is True
    assert audit["gates"]["G2_grid_matches_organizer_sample"] is True
    assert audit["gates"]["G3_no_positive_mass_outside_footprint"] is True
    assert audit["gates"]["G4_no_duplicate_of_any_sibling_raster"] is True
    assert audit["gates"]["G6_projection_beats_champion_under_every_density"] is False


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
    assert result["checks"]["holdout_gate"] is False
    assert result["checks"]["canary_gate"] is False
    assert result["checks"]["promotion_projection_gate"] is False

    # and the download verdict is itself CI-enforced
    dl = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_all_gates.py"), "--expect-download-ok"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert dl.returncode == 0, dl.stdout + dl.stderr

    # the literal lane rule cannot be met on this grid, so opting into it must break the download verdict
    strict = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_all_gates.py"), "--strict-lane", "--expect-download-ok"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert strict.returncode == 1, "the literal 3-px gate must reject the file (IR-SASS3-76)"
