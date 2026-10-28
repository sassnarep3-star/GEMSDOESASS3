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


def test_uniqueness_audit_passes_on_submitted_rasters():
    d = json.loads((ROOT / "evidence/independent_uniqueness_lwst_20261028.json").read_text())
    subs = [r for r in d["results"] if "/docs/downloads/" in r["path"]]
    assert len(subs) >= 400, "audit should cover the submitted rasters"
    assert max(r["within3_frac"] for r in subs) <= 0.70
    assert max(abs(r["spearman_sampled"]) for r in subs) <= 0.90


def test_experiment_e1_is_negative_and_spends_no_slot():
    e1 = json.loads((ROOT / "evidence/hypothesis_h_sass3_e_experiment.json").read_text())
    assert e1["verdict"] == "negative"
    assert e1["slot_spent"] is False
    assert all(v is False for k, v in e1["pre_registered_criteria"].items() if k != "canary_symmetric_auc_le_090")
    assert e1["leakage_canary_single_feature"]["pass_le_090"] is True


def test_review_json_verdict_is_conservative():
    r = json.loads((ROOT / "evidence/independent_review_20261028.json").read_text())
    v = r["verdict"]
    assert v["ok_to_download_and_upload_as_valid_unique_file"] is True
    assert v["beats_0_2778_champion_demonstrated"] is False
    assert v["beats_0_4544_leader_demonstrated"] is False
    assert v["promote_to_real_slot"] is False
    assert r["link_gate"]["all_resolved"] is True
    assert len(r["per_site_table"]) == 9


def test_banner_present_on_all_pages_and_claims_are_withdrawn():
    for rel in PAGES:
        txt = (ROOT / rel).read_text()
        assert "Independent review (2026-10-28)" in txt, rel
        assert "NOT DEMONSTRATED" in txt, rel


def test_ledger_copies_identical_and_retractions_recorded():
    a = (ROOT / "evidence/irregularities_ledger.json").read_text()
    b = (ROOT / "docs/data/irregularities_ledger.json").read_text()
    assert a == b
    ids = {x["id"]: x for x in json.loads(a)["irregularities"]}
    assert "RETRACTED" in ids["IR-SASS3-05"]["resolution"]
    assert "CORRECTED" in ids["IR-SASS3-03"]["resolution"]
    assert "IR-SASS3-18" in ids


def test_lwst_baseline_is_true_champion_not_d28_parent():
    src = (ROOT / "scripts/run_lwst_experiments.py").read_text()
    assert "d28_path" not in src
    assert "e5eb6e7e" in src
    assert "base_hr = holdout.evaluate_hide_and_recover(b2_champ_mask" in src


def test_independent_review_markdown_has_run_card_and_sources():
    md = (ROOT / "docs/research/independent-review-20261028.md").read_text()
    assert "```json" in md
    assert "NOT DEMONSTRATED" in md
    assert "docs.nlr.gov/docs/fy26osti/96647.pdf" in md
    assert md.count("| GEMSDOE") == 9
