"""Invariants for the 2026-10-31 block-inversion candidate (H-BLOCKINV).

Two failure modes matter, and both are pinned here:

1. the raster drifting away from what the receipt says (dot count, SHA-256, format, value
   discipline, zip identity, note length);
2. a number appearing on a page that the receipts do not support.  The estimator's own claims
   (leave-one-file-out error, the per-site table, the N ceiling) are re-derived from the tracked
   receipts, so a page edit that quietly changes a figure fails here.

The raster, the build receipt, the model receipt, the validator receipt and the per-site table are
all committed.  The block field and the reconstructed grid live in ``.cache`` (rebuildable), so the
tests that need them are skipped on a bare checkout.
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
MODEL = ROOT / "evidence" / "blockinversion_model_20261031.json"
# The candidate name is read from the receipt, so a re-emission does not silently skip these tests.
NAME = (json.loads(MODEL.read_text())["submission"]["submission_name"] if MODEL.exists()
        else "gemsdoesass3-blockinv3-missing")
TIF = ROOT / "docs" / "downloads" / f"{NAME}.tif"
ZIP = TIF.with_name(TIF.name + ".zip")
BUILD = TIF.with_name(TIF.stem + "-build.json")
VALID = ROOT / "evidence" / "validator_blockinv_20261031.json"
FOCUS = ROOT / "evidence" / "focus9_best_files_20261031.json"
FIELD = ROOT / ".cache" / "blockinv_field.npz"
ALPHA, BETA = 0.2, 0.8


def _receipt(p: Path) -> dict:
    return json.loads(p.read_text())


pytestmark = pytest.mark.skipif(
    not (TIF.exists() and BUILD.exists() and MODEL.exists()), reason="candidate artefacts not present"
)


# ------------------------------------------------------------------------------------ the raster
def test_raster_and_zip_are_the_bytes_the_receipt_claims():
    build = _receipt(BUILD)
    assert hashlib.sha256(TIF.read_bytes()).hexdigest() == build["raster_sha256"]
    assert ZIP.exists()
    assert hashlib.sha256(ZIP.read_bytes()).hexdigest() == build["zip_sha256"]
    with zipfile.ZipFile(ZIP) as zf:
        assert zf.namelist() == [TIF.name]
        assert zf.read(TIF.name) == TIF.read_bytes()


def test_format_gates_on_the_saved_bytes():
    build = _receipt(BUILD)
    with rasterio.open(TIF) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert ds.shape == (3730, 3292)
        assert abs(ds.transform.a - 100.0) < 1e-9 and abs(ds.transform.e + 100.0) < 1e-9
        a = ds.read(1)
        mask = ds.read_masks(1) > 0
        flags = ds.mask_flag_enums[0]
    # the portal's literal element-wise test on the *stored* array: NaN compares False, so a NaN
    # payload outside the footprint is what triggers "Predicted values must be in range [0, 1]"
    assert np.count_nonzero(~((a >= 0.0) & (a <= 1.0))) == 0
    assert not np.isnan(a).any()                                # nothing stored is NaN
    assert np.isin(np.unique(a), [0.0, 1.0]).all()              # binary, as priced
    assert int((a == 1.0).sum()) == build["n_dots"]
    # null-ness outside the footprint is carried by the mask band, and it must match the footprint
    from rasterio.enums import MaskFlags
    assert MaskFlags.per_dataset in flags
    assert 0 < int((~mask).sum()) < mask.size                   # something is declared null ...
    assert not mask[~mask].any()
    assert float(a[~mask].max()) == 0.0                         # ... and it is stored as finite 0
    assert (a[mask] == 1.0).sum() == build["n_dots"]             # every dot is in the valid area


def test_note_is_submittable():
    build = _receipt(BUILD)
    note = build["submission_note"]
    assert 1 <= len(note) <= 140
    assert "\n" not in note and "\r" not in note
    # the note must quote the receipt's own estimate, to 3 dp, and its dot count
    assert f"est {build['est_score']:.3f}" in note
    assert str(build["n_dots"]) in note


# --------------------------------------------------------------------------- the estimator's claims
def test_model_is_better_than_baseline_and_than_the_previous_release():
    m = _receipt(MODEL)
    chosen, base = m["chosen"], m["baseline_20261030_release"]
    assert chosen["loo_rmse"] < chosen["baseline_sd_of_scores"] / 3   # 0.0206 vs 0.0825
    assert chosen["loo_rmse"] < base["loo_rmse"]                      # beats the exact-dot design
    assert chosen["loo_rho"] > base["loo_rho"]
    assert chosen["block_px"] * 100 == 300                            # block = metric kernel radius


def test_estimate_respects_the_proven_N_ceiling():
    m = _receipt(MODEL)
    est = m["estimate"]
    ceiling = m["n_bound"]["N_upper_bound"]
    assert ceiling is not None and ceiling > 0
    assert m["chosen"]["N"] <= ceiling, "emission used an N the data forbid"
    # recompute the estimate from the components the receipt publishes
    recomputed = est["expected_tp"] / (ALPHA * est["n_dots"] + BETA * m["chosen"]["N"])
    assert abs(recomputed - est["est_score"]) < 1e-3
    # every admissible-N variant must be internally consistent too
    for row in est["band_over_admissible_N"]:
        assert abs(row["est_score_at_same_dots"]
                   - row["expected_tp_at_same_dots"] / (ALPHA * est["n_dots"] + BETA * row["N"])) < 1e-3
    assert min(r["N"] for r in est["band_over_admissible_N"]) >= 1000


def test_uniqueness_claim_is_under_the_cap_and_beats_random():
    m = _receipt(MODEL)
    u = m["uniqueness"]
    assert u["worst_submission_overlap"] <= u["cap"] <= 0.70
    assert u["cap_satisfied"] is True
    assert u["top10_submissions"][0]["overlap"] == u["worst_submission_overlap"]
    # a dense field would overlap anything at roughly its own coverage; the lift says we are not
    # merely reproducing the closest raster
    assert u["worst_submission_lift"] is not None


def test_selection_trials_are_self_consistent():
    m = _receipt(MODEL)
    trials = m["selection_trials"]
    assert len(trials) >= 3
    best = max(trials, key=lambda t: t["est_score"])
    est = m["estimate"]
    assert best["n_dots"] == est["n_dots"]
    assert abs(best["est_score"] - est["est_score"]) < 1e-3
    for t in trials:
        assert t["quota_per_raster"] == int(np.floor(m["uniqueness"]["cap"] * t["n_target"]))


def test_per_site_table_reproduces_every_published_focus_score():
    """The nine focus sites' best files are predicted out-of-sample to within 0.02 of their score."""
    m = _receipt(MODEL)
    by_site = {}
    for row in m["files"]:
        if not row["site"]:
            continue
        cur = by_site.get(row["site"])
        if cur is None or row["owner_reported_score"] > cur["owner_reported_score"]:
            by_site[row["site"]] = row
    focus = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
             "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
    assert set(focus) <= set(by_site)
    for site in focus:
        row = by_site[site]
        assert abs(row["loo_predicted_score"] - row["owner_reported_score"]) < 0.02, site
    assert abs(by_site["GEMSDOE32"]["owner_reported_score"] - 0.2778) < 1e-9
    assert abs(by_site["GEMSDOE32"]["loo_predicted_score"] - 0.2726) < 0.005


def test_focus_files_are_duplicates_of_each_other_but_not_of_the_candidate():
    if not FOCUS.exists():
        pytest.skip("per-site table not present")
    t = _receipt(FOCUS)["sites"]
    for site, row in t.items():
        assert row["worst_overlap_other_focus"] >= 0.97, f"{site} unexpectedly distinct"
        # the constrained direction: our dots near theirs must stay well inside the cap
        assert row["new_dots_within_this_file"] < 0.45, f"{site} too close to the new candidate"
        # the reverse direction is large by construction and must not be read as a duplicate
        assert row["this_files_dots_within_new"] > row["new_dots_within_this_file"]


def test_validator_receipt_says_every_gate_passes():
    if not VALID.exists():
        pytest.skip("validator receipt not present")
    v = _receipt(VALID)
    assert v["ok"] is True
    assert v["n_passed"] == v["n_gates"]
    assert not [k for k, ok in v["checks"].items() if not ok]
    build = _receipt(BUILD)
    d = v["detail"]
    assert d["n_dots"] == build["n_dots"]
    assert abs(d["est_score_recomputed"] - build["est_score"]) < 1e-3
    assert d["raster_sha256"] == build["raster_sha256"]
    assert d["worst_overlap"]["overlap"] <= 0.70


# ------------------------------------------------------------------- recompute the estimate itself
@pytest.mark.skipif(not FIELD.exists(), reason="block field lives in .cache (rebuildable)")
def test_estimate_is_recomputed_from_the_raster_and_the_field():
    build = _receipt(BUILD)
    z = np.load(FIELD)
    u, key, N = z["u"].astype(np.float64), z["key"].astype(np.int64), float(z["N"][0])
    mask = np.load(ROOT / "evidence" / "organizer_footprint_mask.npz")
    shape = tuple(int(v) for v in mask["shape"])
    bits = np.unpackbits(mask["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    cid = np.full(bits.size, -1, np.int64)
    cid[bits.ravel()] = np.arange(int(bits.sum()))
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
    dots = a == 1.0
    fp = cid[np.flatnonzero(dots.ravel())]
    assert (fp >= 0).all()
    tp = float(u[key[fp]].sum())
    est = tp / (ALPHA * int(dots.sum()) + BETA * N)
    assert abs(tp - build["expected_tp"]) < 0.5
    assert abs(est - build["est_score"]) < 1e-3
