"""Tests for the 2026-10-28 independent review: recomputed gates, E1 experiment, banners, ledger, baseline fix."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

PAGES = ["README.md", "index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"]


def test_current_archive_candidate_format_recomputed_from_raster():
    import numpy as np
    import rasterio

    path = ROOT / "docs/downloads/gemsdoesass3-bgk-pbe-gravity-k-dilatation-blind-fault-20261029T000321Z-af121062-zeros.tif"
    with rasterio.open(path) as src:
        data = src.read(1)
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert str(src.crs) == "EPSG:32611"
        assert src.shape == (3730, 3292)
        assert tuple(src.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert src.nodata is None
    assert np.isfinite(data).all()
    assert data.min() >= 0.0 and data.max() <= 1.0
    # Synthetic BGK diagnostic has 8,794 positive cells, including soft halo pixels.
    assert int((data > 0).sum()) == 8794


def test_historical_lwst_format_gate_is_not_current_candidate():
    import independent_review

    fmt = independent_review.format_gate()
    assert fmt["all_pass"]
    assert fmt["meta"]["dots"] == 37654
    assert fmt["meta"]["crs"] == "EPSG:32611"


def test_uniqueness_audit_passes_on_submitted_rasters():
    d = json.loads((ROOT / "evidence/independent_uniqueness_lwst_20261028.json").read_text())
    subs = [r for r in d["results"] if "/docs/downloads/" in r["path"]]
    assert len(subs) >= 400, "audit should cover the submitted rasters"
    assert max(r["within3_frac"] for r in subs) <= 0.70
    assert max(abs(r["spearman_sampled"]) for r in subs) <= 0.90


def test_current_candidate_is_fail_closed_and_not_a_score_claim():
    card = json.loads((ROOT / "evidence/current_run_card.json").read_text())
    audit = json.loads((ROOT / "evidence/uniqueness_audit_current_candidate_20261029.json").read_text())
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["holdout_dti"]["status"] in ("NOT RUN", "NOT PASS")  # fail-closed: never PASS here
    assert card["registry_correlation_and_overlap"]["literal_uniqueness_gate"] == "NOT CLEARED"
    assert audit["candidate_sha256"] == card["raster_sha256"]
    assert audit["result"]["one_witness_result_below_threshold"] is True
    assert audit["result"]["complete_registry_uniqueness_pass"] is False
    assert 0 < len(card["submission_note"]) <= 140


def test_fail_closed_verifier_reports_format_integrity_but_no_approval():
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_all_gates.py"), "--expect-blocked"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["format_and_record_integrity"] is True
    assert result["ok_to_submit"] is False
    assert result["checks"]["complete_uniqueness_gate"] is False
    assert result["checks"]["holdout_gate"] is False


def test_experiment_e1_is_negative_and_spends_no_slot():
    e1 = json.loads((ROOT / "evidence/hypothesis_h_sass3_e_experiment.json").read_text())
    assert e1["verdict"] == "negative"
    assert e1["slot_spent"] is False
    assert all(v is False for k, v in e1["pre_registered_criteria"].items() if k != "canary_symmetric_auc_le_090")
    assert e1["leakage_canary_single_feature"]["pass_le_090"] is True


def test_review_json_verdict_is_conservative():
    r = json.loads((ROOT / "evidence/independent_review_20261028.json").read_text())
    v = r["verdict"]
    # Literal registry rule (incl. calibration lattice) blocks the file: NOT OK to submit.
    assert v["unique_on_downloads_programmatic"] is True
    assert v["unique_literal_incl_calibration_lattice"] is False
    assert v["ok_to_download_and_upload_as_valid_unique_file"] is False
    assert v["ok_to_download_as_format_valid_archive_only"] is True
    assert v["beats_0_2778_champion_demonstrated"] is False
    assert v["beats_0_4544_leader_demonstrated"] is False
    assert v["promote_to_real_slot"] is False
    assert r["lattice_gate_literal"]["within3_frac"] > 0.70
    assert r["link_gate"]["all_resolved"] is True
    assert len(r["per_site_table"]) == 9


def test_lattice_gate_reproduces_main_pin_when_witness_present():
    import os

    import pytest

    import independent_review as ir

    if not (Path(os.environ.get("GEMS_SIB_ROOT", "/tmp/sib")) / ir.LATTICE_REL).exists():
        pytest.skip("lattice witness not present; set GEMS_SIB_ROOT")
    lat = ir.lattice_gate()
    assert lat["witness_sha256_matches_main_pin"] is True
    assert lat["same_grid_crs_shape_transform"] is True
    assert abs(lat["within3_frac"] - 0.997849) < 1e-5
    assert lat["pass"] is False


def test_pages_state_block_and_link_review():
    for rel in ["README.md"]:
        txt = (ROOT / rel).read_text()
        assert "NOT OK to submit" in txt
        assert "independent-review-20261028.md" in txt
    for rel in ["index.html", "docs/index.html"]:
        txt = (ROOT / rel).read_text()
        assert "Independent review (2026-10-28)" in txt, rel
    for rel in ["executive-summary.html", "docs/executive-summary.html"]:
        assert "BLOCKED" in (ROOT / rel).read_text(), rel


def test_ledger_copies_identical_and_retractions_recorded():
    a = (ROOT / "evidence/irregularities_ledger.json").read_text()
    b = (ROOT / "docs/data/irregularities_ledger.json").read_text()
    assert a == b
    ids = {x["id"]: x for x in json.loads(a)["irregularities"]}
    assert "RETRACTED" in ids["IR-SASS3-05"]["resolution"]
    assert "CORRECTED" in ids["IR-SASS3-03"]["resolution"]
    assert "IR-SASS3-18" in ids
    assert "IR-SASS3-19" in ids


def test_lwst_baseline_is_true_champion_not_d28_parent():
    src = (ROOT / "scripts/run_lwst_experiments.py").read_text()
    assert "d28_path" not in src
    assert "e5eb6e7e" in src
    assert "base_hr = holdout.evaluate_hide_and_recover(b2_champ_mask" in src


def test_independent_review_markdown_has_run_card_and_sources():
    md = (ROOT / "docs/research/independent-review-20261028.md").read_text()
    assert "```json" in md
    assert "NOT DEMONSTRATED" in md
    assert "**NO**" in md
    assert "99.78%" in md
    assert "docs.nlr.gov/docs/fy26osti/96647.pdf" in md
    assert md.count("| GEMSDOE") == 9
