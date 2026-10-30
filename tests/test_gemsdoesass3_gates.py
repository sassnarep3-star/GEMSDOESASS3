"""Automated pytest suite verifying GEMSDOESASS3 invariants, template patches, feature schema,
leakage canary, 9-site H19-5 set algebra, and emitted [0, 1] GeoTIFF submission gates.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems57.uniqueness import HALO_SATURATION_FRACTION, two_phase_summary  # noqa: E402
from gemsdoesass3.features import ALL_STATIC_NAMES, PURE_SUBSURF_COLS  # noqa: E402
from verify_all_gates import verify_all  # noqa: E402


def test_verified_gdal_band_order_and_pure_subsurf_isolation() -> None:
    """Verify IR-DATA-BAND-ORDER & IR-DATA-B06 fixes in features.py."""
    assert len(ALL_STATIC_NAMES) == 46
    assert ALL_STATIC_NAMES[4] == "b05_iso_grav_anom_slope"
    assert ALL_STATIC_NAMES[5] == "b06_rad_tc"
    assert ALL_STATIC_NAMES[11] == "b12_det_elev"
    assert ALL_STATIC_NAMES[14] == "b15_depth_to_base_surf"
    assert ALL_STATIC_NAMES[18] == "b19_det_elev_slope"
    assert ALL_STATIC_NAMES[19] == "true_mag_tilt"

    # Strictly zero DEM/slope/LiDAR features inside PURE_SUBSURF_COLS
    forbidden_topo = {
        "b12_det_elev",
        "b19_det_elev_slope",
        "piedmont_toe_inflection",
        "det_elev_resid_500m",
        "lidar_scarp_step",
        "lidar_coh100",
        "full_line_max_1p5km",
        "full_line_aniso_1p5km",
        "multi_slip_dilation",
        "mimic_lahontan_shoreline",
    }
    subsurf_names = {ALL_STATIC_NAMES[i] for i in PURE_SUBSURF_COLS}
    assert subsurf_names.isdisjoint(forbidden_topo)
    assert len(PURE_SUBSURF_COLS) == 36


def test_halo_saturated_lattice_uniqueness_patch() -> None:
    """Verify IR-REG-LATTICE-S5 fix in vendor/gems57/uniqueness.py."""
    assert HALO_SATURATION_FRACTION == 0.90
    synthetic_rows = [
        {
            "repo": "historical",
            "submission": "r13-lattice-s5.tif",
            "their_dots": 206_895,
            "their_halo_fraction": 0.998724,
            "my_dots_within_3px_of_theirs": 0.9997,
            "their_dots_within_3px_of_mine": 0.09,
            "spearman_full_footprint": 0.01,
            "jaccard_dot_sets": 0.008,
            "representation": "halo_saturated_lattice",
        },
        {
            "repo": "historical",
            "submission": "gems10-h25-ctx-ridge.tif",
            "their_dots": 174_232,
            "their_halo_fraction": 0.2631,
            "my_dots_within_3px_of_theirs": 0.6745,
            "their_dots_within_3px_of_mine": 0.2032,
            "spearman_full_footprint": 0.0294,
            "jaccard_dot_sets": 0.0173,
            "representation": "dot_field",
        },
    ]
    tp = two_phase_summary(synthetic_rows, footprint_cells=5_167_373, expected_rasters=2)
    assert tp["literal_reading"]["duplicate"] is True
    assert tp["like_for_like_reading"]["dot_field_rasters"] == 1
    assert tp["like_for_like_reading"]["duplicate"] is False
    assert tp["like_for_like_reading"]["forward_overlap_firings"] == 0


def test_nine_sites_h19_5_set_algebra_invariants() -> None:
    """Verify exact 0-pixel symmetric difference proofs across the 9 focus sites."""
    audit = json.loads((ROOT / "evidence/nine_sites_executive_audit.json").read_text())
    lp = audit["lineage_proof"]
    assert lp["h19_5_dots"] == 121_131
    assert lp["d28_outside_h19_5_pixels"] == 0
    assert lp["gemsdoe25_equals_gemsdoe30_symdiff"] == 0
    assert lp["gemsdoe28_solo_equals_gemsdoe31_symdiff"] == 0
    assert lp["b1_equals_d28_minus_dcat_le_1_symdiff"] == 0
    assert lp["b2_champion_equals_d28_minus_dcat_le_2_symdiff"] == 0
    assert lp["gemsdoe36_contains_100pct_of_b2_champion"] is True
    assert lp["gemsdoe36_extra_dots_over_b2_champion"] == 1200
    assert len(audit["sites"]) == 9


def test_current_candidate_is_download_ok_and_not_promoted() -> None:
    """The packaged candidate passes every format/record gate, and is deliberately NOT promoted.

    ok_to_download  = the bytes match the run card and the portal contract (finite [0,1] everywhere,
                      zeros outside the scored footprint, no nodata tag) and the file is not a duplicate.
    ok_to_submit    = additionally needs a cleared holdout, a passed canary, and a projection that beats
                      the 0.2778 champion under EVERY truth density. It does not, so it must stay false.
    """
    res = verify_all()
    assert res["ok"] is False
    assert res["format_and_record_integrity"] is True
    assert res["competition_rules_outside_bounds_range_and_grid"] is True
    assert res["ok_to_download"] is True
    assert res["ok_to_download_for_analysis"] is True
    assert res["ok_to_submit"] is False
    assert res["problems"] and set(res["problems"]) >= {
        "holdout_gate", "canary_gate", "promotion_projection_gate"}
    assert res["verdict"].startswith("negative for promotion")

    # the exact numbers the download verdict rests on, recomputed from the receipt
    assert res["measured"]["pool_rasters_checked"] >= 126
    assert res["measured"]["worst_exact_cell_share"] < 0.95
    assert res["measured"]["delta_worst_case_unpaired"] < 0
    assert res["measured"]["delta_worst_case_paired"] < 0
    assert res["projections"]["promotion_rule_passed"] is False

    # the literal 3-px lane rule is unsatisfiable on this grid (IR-SASS3-76): gating on it must flip the
    # download verdict, which is exactly why we report the number instead of dropping the rule.
    assert verify_all(strict_lane=True)["ok_to_download"] is False

    card = json.loads((ROOT / "evidence/current_run_card.json").read_text())
    assert card["ok_to_download"] is True and card["ok_to_submit"] is False
    tif_path = ROOT / card["download_path"]
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.shape == (3730, 3292)
        assert str(src.crs) == "EPSG:32611"
        assert [float(x) for x in tuple(src.transform)[:6]] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
        assert src.nodata is None                       # portal-safe: nothing masked out of the range check
        assert np.isfinite(arr).all()                   # no NaN anywhere: the [0,1] predicate sees every cell
        assert set(np.unique(arr).tolist()) == {0.0, 1.0}
        assert int((arr > 0).sum()) == 20_416
    z = np.load(ROOT / "evidence/organizer_footprint_mask.npz")
    shape = tuple(int(x) for x in z["shape"])
    foot = np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    assert int(((arr > 0) & ~foot).sum()) == 0           # no positive mass outside the scored footprint
    assert int((~foot).sum()) == 7_111_787                # footprint itself unchanged from the sample


def test_space_filling_witness_does_not_get_a_protocol_exemption():
    """A registry lattice is still a registry raster under the literal rule."""
    audit = json.loads((ROOT / "evidence/uniqueness_audit_386.json").read_text())
    witness = audit["space_filling_calibration_lattices"][0]
    assert witness["within_3px_fraction"] > 0.70
    assert witness["literal_duplicate"] is True
    assert verify_all()["ok_to_submit"] is False
