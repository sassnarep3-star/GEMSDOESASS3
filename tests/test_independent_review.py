"""Tests for the 2026-10-28 independent review: recomputed gates, E1 experiment, banners, ledger, baseline fix."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

PAGES = ["README.md", "index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"]


def test_format_gate_recomputed_from_raster_passes():
    import independent_review

    fmt = independent_review.format_gate()
    failed = [k for k, v in fmt["checks"].items() if not v]
    assert fmt["all_pass"], f"format checks failed: {failed}"
    assert fmt["meta"]["dots"] == 37654
    assert fmt["meta"]["crs"] == "EPSG:32611"
    assert fmt["meta"]["min"] >= 0.0 and fmt["meta"]["max"] <= 1.0


def test_uniqueness_audit_is_labeled_as_archived_subset_only():
    import independent_review

    uq = independent_review.uniqueness_gate()
    assert uq["n_submitted_rasters_compared"] >= 400
    assert uq["archived_pass"] is True
    assert uq["recomputed_this_run"] is False
    assert uq["pass"] is False  # fail closed without source rasters and surface scan


def test_experiment_e1_is_negative_and_spends_no_slot():
    e1 = json.loads((ROOT / "evidence/hypothesis_h_sass3_e_experiment.json").read_text())
    assert e1["verdict"] == "negative"
    assert e1["slot_spent"] is False
    assert all(v is False for k, v in e1["pre_registered_criteria"].items() if k != "canary_symmetric_auc_le_090")
    assert e1["leakage_canary_single_feature"]["pass_le_090"] is True


def test_review_json_verdict_is_conservative():
    r = json.loads((ROOT / "evidence/independent_review_20261028.json").read_text())
    v = r["verdict"]
    # Historical subset results are retained, but current uniqueness fails closed.
    assert v["unique_on_downloads_programmatic"] is False
    assert v["unique_on_downloads_archived_pass"] is True
    assert v["uniqueness_recomputed_this_run"] is False
    assert v["unique_literal_incl_calibration_lattice"] is False
    assert v["ok_to_download_and_upload_as_valid_unique_file"] is False
    assert v["ok_to_download_as_format_valid_archive_only"] is True
    assert v["beats_0_2778_champion_demonstrated"] is False
    assert v["beats_current_leaderboard_demonstrated"] is False
    assert v["promote_to_real_slot"] is False
    assert r["lattice_gate_literal"]["within3_frac"] > 0.70
    assert r["lattice_gate_literal"]["available"] is False
    assert r["lattice_gate_literal"]["recomputed_this_run"] is False
    assert r["link_gate"]["verification_complete"] is True
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


def test_missing_lattice_witness_preserves_archive_and_fails_closed(tmp_path, monkeypatch):
    import independent_review as ir

    monkeypatch.setattr(ir, "SIB", tmp_path / "no_siblings")
    monkeypatch.setattr(ir, "OUT_JSON", tmp_path / "no_archived_review.json")
    lat = ir.lattice_gate()
    assert lat["available"] is False
    assert lat["recomputed_this_run"] is False
    assert lat["pass"] is False
    assert lat["within3_frac"] is None
    assert "unavailable" in ir._safe_block_reason(lat).lower()


def test_missing_lattice_witness_reuses_only_archived_measurement(tmp_path, monkeypatch):
    import independent_review as ir

    monkeypatch.setattr(ir, "SIB", tmp_path / "no_siblings")
    # The checked-in prior report is input evidence only; it must not be presented as a fresh pass.
    monkeypatch.setattr(ir, "OUT_JSON", ROOT / "evidence/independent_review_20261028.json")
    lat = ir.lattice_gate()
    assert lat["available"] is False
    assert lat["recomputed_this_run"] is False
    assert lat["pass"] is False
    assert abs(lat["within3_frac"] - 0.997849) < 1e-5
    assert "archived" in lat["evidence_status"]
    assert "witness unavailable" in ir._safe_block_reason(lat)


def test_pages_state_block_and_link_review():
    for rel in ["README.md"]:
        txt = (ROOT / rel).read_text()
        assert "Do not submit" in txt
        assert "independent-review-20261028.md" in txt
        assert "Maximize P(Win)" in txt and "Own the Outcome" in txt
    for rel in ["index.html", "docs/index.html"]:
        txt = (ROOT / rel).read_text()
        assert "Do not submit the archived LWST GeoTIFF" in txt, rel
        assert "ARCHIVED ONLY" in txt, rel
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
    assert "IR-SASS3-20" in ids
    assert "current uniqueness gate closed" in ids["IR-SASS3-19"]["resolution"]
    assert "do not use either value" in ids["IR-SASS3-18"]["resolution"].lower()


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
