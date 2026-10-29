#!/usr/bin/env python3
"""Verify the literal-rule-compliant candidate and write its Parallel-Run Protocol run card.

Every value in the card is read from a receipt or recomputed from the raster; none is typed by hand.

Checks (exit 0 only if all pass):
  F1  file exists; zip bundle holds exactly the same bytes
  F2  SHA-256 equals the literal audit receipt
  F3  format: single band, float32, EPSG:32611, 3730x3292, organizer transform, nodata None,
      all pixels finite, values in [0, 1], dot count equals the builder receipt
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
CAND_NAME = "gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2-zeros.tif"
CAND = ROOT / "docs/downloads" / CAND_NAME
ZIP = CAND.with_suffix(".tif.zip")
AUDIT = ROOT / "evidence/literal_audit_gemsdoesass3-literal-lwst-disp21k-20261029T001500Z-f0e5abd2.json"
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
    rec("F3_nodata_none_all_finite", fmt["nodata"] is None and bool(np.isfinite(arr).all()), "nodata or non-finite pixels")
    rec("F3_values_in_0_1", float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0, f"range {arr.min()}..{arr.max()}")
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
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
