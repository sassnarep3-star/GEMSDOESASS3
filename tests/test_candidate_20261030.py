"""Invariants for the 2026-10-30 release (E1/E2, the estimator, and the emitted candidate).

Each test pins one claim that the executive summary makes, so the page cannot drift from the
receipts. Nothing here re-downloads anything: the receipts and the released raster are in the repo.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32.metric import ALPHA, BETA, RADIUS_PX, dti_binary, kernel  # noqa: E402

CARD = json.loads((ROOT / "evidence" / "run_card_tipcont_20261030.json").read_text())
RELEASED = ROOT / CARD["validator"]["file"] if False else ROOT / "docs" / "downloads" / f"{CARD['submission_name']}.tif"


def test_fetch_receipt_is_sha_verified_for_all_nine_sites():
    rec = json.loads((ROOT / "evidence" / "focus9_fetch_receipt_20261030.json").read_text())
    assert rec["all_match"] is True
    assert len(rec["rows"]) == 9
    assert {r["site"] for r in rec["rows"]} == {
        "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
    }
    for r in rec["rows"]:
        assert r["sha256"] == r["expected_sha256"], r["site"]
        assert r["expected_sha256_source"] in (
            "registry/focus_registry_manifest.json",
            "evidence/focus_site_candidate_audit_20261028.json:references",
        )


def test_holdout_receipt_is_labelled_and_has_intervals():
    h = json.loads((ROOT / "evidence" / "holdout_catalogue_20261030.json").read_text())
    assert h["label"] == "HOLDOUT-DTI (catalogue-recovery surrogate v1)"
    assert h["withheld_positive_cells"] > 0
    assert len(h["rows"]) == 5
    for r in h["rows"]:
        lo, hi = r["dti_ci95"]
        assert lo <= r["holdout_dti"] <= hi
    # the decision must follow the measured maximum, not a narrative preference
    best = max(h["rows"], key=lambda r: r["holdout_dti"])
    assert h["decision"]["best_strategy"] == best["strategy"]


def test_candidate_card_verdict_matches_its_own_gates():
    assert CARD["verdict"] == "promote"
    assert CARD["ok_to_submit"] is True
    assert CARD["validator"]["all_pass"] is True
    assert CARD["registry"]["submission_scope"]["pass"] is True
    assert CARD["registry"]["submission_scope"]["worst_forward_overlap"] <= 0.70
    assert CARD["registry"]["spearman_pass"] is True
    assert all(abs(v) <= 0.90 for v in CARD["registry"]["spearman_subsample"].values())
    assert len(CARD["submission_note"]) <= 140
    assert CARD["holdout"]["label"].startswith("HOLDOUT-DTI")


def test_released_raster_matches_card_and_is_format_clean():
    assert RELEASED.exists(), RELEASED
    assert hashlib.sha256(RELEASED.read_bytes()).hexdigest() == CARD["raster_sha256"]
    with rasterio.open(RELEASED) as ds:
        arr = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.crs.to_string() == "EPSG:32611"
        assert ds.nodata is None or (isinstance(ds.nodata, float) and np.isnan(ds.nodata))
    fp = np.load(ROOT / "evidence" / "organizer_footprint_mask.npz")
    n = int(fp["shape"][0]) * int(fp["shape"][1])
    footprint = np.unpackbits(fp["packed"])[:n].reshape(tuple(fp["shape"])).astype(bool)
    # IR-SASS3-78: outside the footprint the file must be null (NaN), never a finite zero.
    assert int(np.isfinite(arr[~footprint]).sum()) == 0
    assert np.isnan(arr[~footprint]).all()
    inside = arr[footprint]
    assert np.isfinite(inside).all()
    assert inside.min() >= 0.0 and inside.max() <= 1.0
    assert int((arr > 0).sum()) == CARD["validator"]["stats"]["positive_cells"] == 44_923
    assert int((arr > 0).sum()) == int(((arr > 0) & footprint).sum())


def test_estimator_inversion_identity():
    """S = x/(x + aN/M + b(1-x)) inverted for x must reproduce S exactly."""
    alpha, beta = ALPHA, BETA
    for s, n, m in [(0.2778, 37_654, 60_988), (0.1, 24_000, 30_494), (0.4, 50_000, 300_000)]:
        v = alpha * n / m
        x = s * (v + beta) / (1.0 - alpha * s)
        assert x == pytest.approx(s * (v + beta) / (1.0 - alpha * s))
        assert x / (x + v + beta * (1 - x)) == pytest.approx(s)


def test_blind_field_ceiling_is_reported_and_low():
    est = json.loads((ROOT / "evidence" / "score_estimate_20261030.json").read_text())
    blind = [r["score_eps1"] for r in est["blind_ceiling"]]
    assert max(blind) < 0.06, "an unenriched field must not be projected anywhere near 0.2778"
    proj = est["candidate_projection"]
    assert 0.0 < proj["central_skill_hypothesis"] < 0.2
    assert proj["range_selection_hypothesis"][0] > proj["central_skill_hypothesis"]


def test_kernel_and_metric_constants_are_the_official_ones():
    assert (ALPHA, BETA, RADIUS_PX) == (0.2, 0.8, 3.0)
    assert float(kernel(0.0)) == 1.0 and float(kernel(3.0)) == 0.0
    # One truth cell, one dot one pixel away. Official formulae give
    #   TP_w = p*k(1) = 2/3, FN_w = 1 - 2/3 = 1/3, FP_w = p*(1 - k(1)) = 1/3
    # because the false-positive term is weighted by the distance to the nearest truth cell.
    truth = np.zeros((9, 9), bool); truth[4, 4] = True
    pred = np.zeros((9, 9), bool); pred[4, 5] = True
    out = dti_binary(pred, truth)
    assert out["tp"] == pytest.approx(2 / 3)
    assert out["fn"] == pytest.approx(1 / 3)
    assert out["fp"] == pytest.approx(1 / 3)
    assert out["dti"] == pytest.approx((2 / 3) / ((2 / 3) + 0.2 * (1 / 3) + 0.8 * (1 / 3)), rel=1e-6)


def test_placement_helpers_are_deterministic():
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_candidate_20261030 as B  # noqa: E402

    pool = np.array([[10, 10], [10, 11], [12, 12], [14, 14], [16, 16], [20, 20], [25, 25]], dtype=np.int32)
    a = B.thin_to(pool, 3, np.random.default_rng(7))
    b = B.thin_to(pool, 3, np.random.default_rng(7))
    assert np.array_equal(a, b)
    # the released file's dot count and the generator's seed are recorded in the run card
    assert CARD["provenance"]["seed"] == 20261101
    assert CARD["provenance"]["no_registry_dots_used_to_build"] is True
    assert CARD["provenance"]["no_competition_labels_used"] is True


def test_density_sweep_shows_mass_cannot_substitute_for_skill():
    d = json.loads((ROOT / "evidence" / "density_sweep_20261030.json").read_text())
    assert d["label"].startswith("HOLDOUT-DTI")
    budgets = [r["budget"] for r in d["rows"]]
    assert min(budgets) == 45_000 and max(budgets) == 250_000
    best = max(d["rows"], key=lambda r: r["holdout_dti"])
    assert best["budget"] == 45_000, "the release budget is the measured optimum of this mechanism"
    eps = {(r["step_px"], r["budget"]): r["enrichment_eps"] for r in d["rows"]}
    assert eps[(4.0, 45_000)] > eps[(4.0, 180_000)] > 1.0
    assert all(r["enrichment_eps"] < 2.0 for r in d["rows"]), "no blind mechanism is 2x enriched"
