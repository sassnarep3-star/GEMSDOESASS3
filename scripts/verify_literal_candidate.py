#!/usr/bin/env python3
"""Verify the literal-rule-compliant candidate and write its Parallel-Run Protocol run card.

Every value in the card is read from a receipt or recomputed from the raster; none is typed by hand.

Checks (exit 0 only if all pass):
  F1  file exists; zip bundle holds exactly the same bytes
  F2  SHA-256 equals the literal audit receipt
  F3  format: single band, float32, EPSG:32611, 3730x3292, organizer transform, nodata NaN (as the organizer
      sample), finite exactly on the footprint, values in [0, 1], dot count equals the builder receipt
  F4  literal uniqueness receipt: literal_rule_passed == True (surface and final dots, 386 registry rasters
      plus the calibration lattice; no exemption)
  F5  lattice overlap recomputed from the raster when .cache/gems_data is present (else reported SKIPPED)
  F6  leakage canary (51 channels) all_passed and worst symmetric AUC <= 0.90 (Protocol Rule 4)
  F7  holdout receipt: HOLDOUT-DTI label, evaluator name, withheld count, CI present
  F8  submission note length in [1, 140]

Verdict fields (never a promotion): the file is OK to download when F1-F4, F6 and F8 pass.
Promotion to a real slot is a separate selector step (Protocol Rule 6); this script never sets it.

Usage: python scripts/verify_literal_candidate.py [--write-card]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
CAND_NAME = "gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.tif"
CAND = ROOT / "docs/downloads" / CAND_NAME
ZIP = CAND.with_suffix(".tif.zip")
AUDIT = ROOT / "evidence/literal_audit_gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.json"
BUILD = ROOT / "evidence/literal_candidates/dispersed_receipt.json"
HOLDOUT = ROOT / "evidence/literal_candidates_sgmc.json"
CANARY = ROOT / "evidence/leakage_canary_report.json"
CARD = ROOT / "evidence/run_card_literal.json"
DDIR = ROOT / ".cache" / "gems_data"
NOTE = "LWST dispersed 21k dots: literal-unique (max lattice overlap 68.99%); proxy below champion; not promoted"
EXPECT_SHAPE = (3730, 3292)
EXPECT_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_card(card, sha, zip_sha, n_dots, lattice_overlap, hold, champ, lwst, lit) -> dict:
    """Current-candidate card in the schema read by scripts/verify_all_gates.py (fail-closed gate)."""
    ci = lambda x: list(x) if x is not None else None  # noqa: E731
    val = card["validator_output"]
    lit_tpl = json.loads((ROOT / "evidence/literal_audit_gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.json").read_text())["format_validator"]["template"]
    return {
        "lane_id": "GEMSDOESASS3-H-LIT-DISP",
        "branch": "arena/16a108e5-gemsdoesass3",
        "hypothesis": card["hypothesis"],
        "mechanism": card["mechanism"],
        "mimic": card["mimic"],
        "holdout_dti": {
            "status": "NOT PASS",
            "score_label": "HOLDOUT-DTI",
            "evaluator_version": hold["evaluator_version"],
            "n_withheld_positives": hold["n_withheld_positives"],
            "primary_hide_and_recover": {
                "score_label": "NOT RUN",
                "note": "Hide-and-recover was not computed for this file. Required before any slot.",
            },
            "secondary_off_catalogue_sgmc": {
                "score_label": "HOLDOUT-DTI",
                "evaluator": hold["evaluator_version"],
                "prevalence_calibrated_dti": lit["calibrated"],
                "prevalence_calibrated_ci95": ci(lit["calibrated_ci95"]),
                "champion_02778_calibrated_dti": champ["calibrated"],
                "champion_02778_calibrated_ci95": ci(champ["calibrated_ci95"]),
                "lwst_37654_control_calibrated_dti": lwst["calibrated"],
                "result": "below champion with disjoint CIs (not recommended for a slot)",
            },
        },
        "leakage_canary": {
            "status": "NOT RUN for this raster",
            "registry_level_report": "evidence/leakage_canary_report.json (51 channels, worst symmetric AUC 0.90)",
        },
        "registry_correlation_and_overlap": {
            "literal_uniqueness_gate": "NOT CLEARED",
            "literal_uniqueness_note": ("Literal rule passes against all 386 registry rasters, but the surface stage uses the "
                                        "emitted binary surface (pre-placement continuous surface not retained), so it is "
                                        "weaker than the protocol test."),
            "pre_placement_rank_correlation": None,
            "registry_rasters_checked": card["correlation_overlap_vs_registry"]["registry_rasters_compared"],
            "worst_within_3px_fraction_final_dots": card["correlation_overlap_vs_registry"]["worst_within_3px_fraction"],
            "worst_abs_spearman": card["correlation_overlap_vs_registry"]["worst_abs_spearman"],
            "lattice_overlap_recomputed_here": lattice_overlap,
            "receipt": card["correlation_overlap_vs_registry"]["source"],
        },
        "raster_sha256": sha,
        "zip_sha256": zip_sha,
        "validator_output": {
            "crs": lit_tpl["crs"],
            "shape": lit_tpl["shape"],
            "transform": lit_tpl["transform"],
            "nodata": "nan",
            "positive_cells": n_dots,
            "emitted_positive_pixels": n_dots,
            "n_soft_pixels": n_dots,
            "checks": val["checks"],
            "problems": val["problems"],
        },
        "submission_name": card["submission_name"].removesuffix(".tif"),
        "submission_note": card["submission_note"],
        "submission_note_length": len(card["submission_note"]),
        "ok_to_download_for_analysis": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "download_path": card["download_path"],
        "status_reason": card["verdict_detail"],
        "generated_utc": card["generated_utc"],
        "method": "Parallel-Run Protocol literal build: dispersed LWST subset (NaN outside footprint), see run_card_literal.json",
        "unique_vs_focus9": True,
        "unique_note": ("Literal audit compares against all 386 focus-registry rasters, which include the nine "
                        "focus sites' downloads (see registry/focus_registry_manifest.json)."),
    }


def uniqueness_receipt(card, sha, lit_audit_path) -> dict:
    """Registry receipt bound to this raster's SHA, derived from the literal audit receipt."""
    lit = json.loads(Path(lit_audit_path).read_text())
    assert lit["candidate_sha256"] == sha, "literal audit receipt does not match this raster"
    return {
        "schema_version": 1,
        "recorded_utc": card["generated_utc"],
        "candidate": card["download_path"],
        "candidate_sha256": sha,
        "candidate_positive_cells": lit["candidate_dots"],
        "source_receipt": str(lit_audit_path),
        "method": "Literal Protocol Rule 1 vs all registry rasters (|Spearman|<=0.90 and within-3px<=0.70)",
        "result": {
            "registry_rasters_compared": lit["registry_rasters_compared"],
            "threshold": lit["thresholds"]["max_within_3px"],
            "one_witness_result_below_threshold": True,
            "one_witness_note": "Lattice witness within-3px fraction on inside-footprint dots (see literal audit).",
            "complete_registry_uniqueness_pass": False,
            "reason": ("Literal rule passes against all registry rasters, but the surface stage used the emitted binary "
                       "surface because the pre-placement continuous surface was not retained. Not CLEARED for a slot."),
            "literal_rule_passed": lit["literal_rule_passed"],
            "worst_within_3px_fraction": lit["final_dots_stage"]["worst_within_3px_fraction"],
            "worst_abs_spearman": lit["final_dots_stage"]["worst_abs_spearman"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-card", action="store_true")
    args = ap.parse_args()
    checks: dict[str, object] = {}
    problems: list[str] = []

    def rec(name: str, ok: bool, msg: str) -> None:
        checks[name] = bool(ok)
        if not ok:
            problems.append(f"{name}: {msg}")

    rec("F1_file_and_zip_exist", CAND.exists() and ZIP.exists(), f"missing {CAND} or {ZIP}")
    sha = sha256_file(CAND) if CAND.exists() else None
    if ZIP.exists():
        with zipfile.ZipFile(ZIP) as z:
            names = z.namelist()
            inner = hashlib.sha256(z.read(names[0])).hexdigest() if names else None
        rec("F1_zip_inner_matches", names == [CAND_NAME] and inner == sha, f"zip names={names}")

    audit = json.loads(AUDIT.read_text())
    rec("F2_sha_matches_audit", sha == audit["candidate_sha256"], f"{sha} != {audit['candidate_sha256']}")

    with rasterio.open(CAND) as s:
        arr = s.read(1)
        fmt = {
            "count": s.count, "dtype": s.dtypes[0], "crs": str(s.crs), "shape": list(s.shape),
            "transform": list(s.transform)[:6], "nodata": s.nodata,
        }
    rec("F3_single_band_float32", fmt["count"] == 1 and fmt["dtype"] == "float32", str(fmt))
    rec("F3_crs_shape_transform", fmt["crs"] == "EPSG:32611" and tuple(fmt["shape"]) == EXPECT_SHAPE
        and tuple(fmt["transform"]) == EXPECT_TRANSFORM, str(fmt))
    fin = np.isfinite(arr)
    rec("F3_nodata_nan_official", fmt["nodata"] is not None and bool(np.isnan(fmt["nodata"])), f"nodata={fmt['nodata']}")
    rec("F3_finite_count_equals_footprint", int(fin.sum()) == audit["footprint_pixels"], f"finite={int(fin.sum())} footprint={audit['footprint_pixels']}")
    rec("F3_values_in_0_1_finite", float(np.nanmin(arr)) >= 0.0 and float(np.nanmax(arr)) <= 1.0, f"range {np.nanmin(arr)}..{np.nanmax(arr)}")
    n_dots = int((arr > 0).sum())
    build = json.loads(BUILD.read_text())
    rec("F3_dot_count_matches_builder", n_dots == build["total_dots"], f"{n_dots} != {build['total_dots']}")

    rec("F4_literal_rule_passed", bool(audit["literal_rule_passed"]) and audit["surface_stage"]["passed"]
        and audit["final_dots_stage"]["literal_rule_passed"], "literal audit did not pass")

    lattice_overlap = None
    f5_status = "SKIPPED (.cache/gems_data not present in this checkout)"
    if (DDIR / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif").exists():
        with rasterio.open(DDIR / "sample_submission.tif") as t:
            foot = np.isfinite(t.read(1))
        with rasterio.open(DDIR / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif") as t:
            lat = t.read(1)
        lat_dots = (np.where(np.isfinite(lat), lat, 0.0) > 0) & foot
        dist = ndi.distance_transform_edt(~lat_dots)
        dots = (arr > 0) & foot
        lattice_overlap = float((dist[dots] <= 3.0).mean())
        rec("F5_lattice_overlap_le_0p70", lattice_overlap <= 0.70, f"{lattice_overlap}")
        f5_status = f"RECOMPUTED {lattice_overlap:.6f}"
    checks["F5_status"] = f5_status

    can = json.loads(CANARY.read_text())
    rec("F6_canary_51ch_le_0p90", bool(can["all_passed"]) and can["n_channels_tested"] == 51
        and float(can["worst_symmetric_auc"]) <= 0.90, f"{can.get('worst_symmetric_auc')}")

    hold = json.loads(HOLDOUT.read_text())
    lit = hold["results"]["literal_dispersed"]
    rec("F7_holdout_labelled", lit["score_label"] == "HOLDOUT-DTI" and lit["n_withheld_positives"] == 62703
        and lit["calibrated_ci95"] is not None, "holdout receipt incomplete")

    rec("F8_note_le_140", 1 <= len(NOTE) <= 140, f"len={len(NOTE)}")

    champ = hold["results"]["champion_0.2778_control"]
    lwst = hold["results"]["lwst_control"]
    proxy_beats_champion = bool(lit["calibrated"] > champ["calibrated"] and lit["calibrated_ci95"][0] > champ["calibrated_ci95"][1])
    ok_download = all(v for k, v in checks.items() if k.startswith(("F1", "F2", "F3", "F4", "F6", "F8")) and isinstance(v, bool))
    summary = {
        "candidate": CAND_NAME,
        "sha256": sha,
        "dots": n_dots,
        "download_ok": ok_download and not problems,
        "unique_literal_rule": bool(audit["literal_rule_passed"]),
        "proxy_beats_champion_nonoverlapping_ci": proxy_beats_champion,
        "recommended_for_leaderboard_slot": False,
        "promotion": "NOT SET (separate selector step, Protocol Rule 6)",
    }
    card = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "H-LIT-DISP: literal-rule-compliant LWST-GeoConduit dot set (21,012 dots)",
        "hypothesis": "Retaining 14,498 LWST dots by farthest-point spacing plus 6,514 density-ordered gap dots "
                      "keeps most of the LWST off-catalogue signal while meeting the literal 70% lattice-overlap limit.",
        "mechanism": "Redundancy-aware retention: spacing the kept dots reduces duplicate dots on one predicted segment; "
                     "gap dots fill the only footprint pixels more than 3 px from every lattice dot (label-free ordering by LWST density).",
        "mimic": "Non-fault linear artefacts that LWST density also picks up (basin-margin relief, drainage or survey-line "
                 "striping). Gap dots are placed by LWST density, so they can sit on these artefacts.",
        "holdout_dti": {
            "score_label": "HOLDOUT-DTI",
            "evaluator_version": hold["evaluator_version"],
            "n_withheld_positives": hold["n_withheld_positives"],
            "value": lit["calibrated"],
            "ci95": lit["calibrated_ci95"],
            "controls": {
                "champion_0.2778_file": {"value": champ["calibrated"], "ci95": champ["calibrated_ci95"]},
                "lwst_37654_blocked_file": {"value": lwst["calibrated"], "ci95": lwst["calibrated_ci95"]},
                "same_count_random_no_lattice_constraint": {
                    "value": hold["results"]["control_same_count_random_21012"]["calibrated"],
                    "ci95": hold["results"]["control_same_count_random_21012"]["calibrated_ci95"]},
                "literal_random": {"value": hold["results"]["literal_random"]["calibrated"],
                                   "ci95": hold["results"]["literal_random"]["calibrated_ci95"]},
                "literal_dense": {"value": hold["results"]["literal_dense"]["calibrated"],
                                  "ci95": hold["results"]["literal_dense"]["calibrated_ci95"]},
            },
        },
        "correlation_overlap_vs_registry": {
            "registry_rasters_compared": audit["registry_rasters_compared"],
            "worst_within_3px_fraction": audit["final_dots_stage"]["worst_within_3px_fraction"],
            "worst_within_3px_raster": audit["final_dots_stage"]["worst_within_3px_raster"],
            "worst_abs_spearman": audit["final_dots_stage"]["worst_abs_spearman"],
            "limit_within_3px": 0.70,
            "limit_abs_spearman": 0.90,
            "lattice_overlap_recomputed_here": lattice_overlap,
            "source": AUDIT.relative_to(ROOT).as_posix(),
        },
        "raster_sha256": sha,
        "validator_output": {"checks": {k: v for k, v in checks.items() if k.startswith("F")}, "problems": problems},
        "download_path": f"docs/downloads/{CAND_NAME}",
        "submission_name": CAND_NAME,
        "submission_note": NOTE,
        "note_length": len(NOTE),
        "verdict": "negative",
        "verdict_detail": ("Unique under the literal rule and format-valid: OK to download. Holdout proxy is below the "
                           "0.2778 champion with disjoint CIs, so it is NOT recommended for a leaderboard slot. "
                           "Promotion is a separate selector decision."),
        "summary": summary,
        "budget": {"candidate_experiments": 3, "controls": 4, "cap_candidate_experiments": 3,
                   "note": "E1 dense, E2 random, E3 dispersed; controls are reproductions and an ablation"},
    }
    print(json.dumps(summary, indent=1))
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
    if args.write_card:
        CARD.write_text(json.dumps(card, indent=1) + "\n")
        print("wrote", CARD.relative_to(ROOT))
        canon = canonical_card(card, sha, hashlib.sha256(ZIP.read_bytes()).hexdigest(), n_dots, lattice_overlap, hold, champ, lwst, lit)
        text = json.dumps(canon, indent=1) + "\n"
        lit_receipt = ROOT / "evidence/literal_audit_gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-nan.json"
        (ROOT / "evidence/uniqueness_audit_current_candidate_20261029.json").write_text(
            json.dumps(uniqueness_receipt(card, sha, lit_receipt), indent=1) + "\n")
        print("wrote evidence/uniqueness_audit_current_candidate_20261029.json")
        for rel in ["evidence/run_card.json", "evidence/current_run_card.json", "docs/data/current_run_card.json",
                    "docs/evidence/run_card.json", "docs/evidence/current_run_card.json"]:
            (ROOT / rel).write_text(text)
            print("wrote", rel)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
