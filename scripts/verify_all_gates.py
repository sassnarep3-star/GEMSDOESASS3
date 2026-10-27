#!/usr/bin/env python3
"""Automated zero-human-intervention programmatic inspector & gate verifier for GEMSDOESASS3.

Runs in both:
  - Full workspace mode (when .cache/gems_data/sample_submission.tif is present), and
  - Lightweight CI mode (GitHub Actions checkout without ignored .cache/ rasters), inspecting
    the actual emitted GeoTIFF in docs/downloads/, its .zip/.json receipt, and all committed
    evidence ledgers.

Exits 0 ONLY if every portal format/range gate, leakage canary, uniqueness gate, and Run Card
contract passes. Prints unmistakable OK TO DOWNLOAD / OK TO SUBMIT banners.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_all() -> dict:
    checks: dict[str, bool] = {}
    problems: list[str] = []

    def record(name: str, cond: bool, msg_if_fail: str) -> None:
        checks[name] = bool(cond)
        if not cond:
            problems.append(f"{name}: {msg_if_fail}")

    # 1. Run card existence & parity
    rc_ev = ROOT / "evidence/current_run_card.json"
    rc_doc = ROOT / "docs/data/current_run_card.json"
    record("run_card_exists", rc_ev.exists() and rc_doc.exists(), "Missing current_run_card.json")
    if not (rc_ev.exists() and rc_doc.exists()):
        return {"ok": False, "checks": checks, "problems": problems}

    card = json.loads(rc_ev.read_text())
    card_doc = json.loads(rc_doc.read_text())
    record("run_card_docs_identical", card == card_doc, "evidence/ and docs/data/ run cards diverge")

    required_card_keys = [
        "hypothesis", "mechanism", "mimic", "holdout_dti",
        "registry_correlation_overlap", "raster_sha256", "validator_output",
        "submission_name", "submission_note", "verdict",
    ]
    record(
        "run_card_required_fields",
        all(k in card and card[k] not in (None, "") for k in required_card_keys),
        "Missing required Run Card fields",
    )
    record(
        "submission_note_le_140_chars",
        1 <= len(card["submission_note"]) <= 140,
        f"Submission note length {len(card['submission_note'])} outside [1, 140]",
    )
    record(
        "budget_cap_le_3_experiments_2h",
        int(card["experiments_executed"]) <= 3 and float(card["wall_clock_seconds"]) <= 7200.0,
        f"Budget exceeded: {card['experiments_executed']} exps / {card['wall_clock_seconds']}s",
    )

    # 2. Leakage canary gate
    canary_p = ROOT / "evidence/leakage_canary.json"
    record("leakage_canary_exists", canary_p.exists(), "Missing evidence/leakage_canary.json")
    if canary_p.exists():
        can = json.loads(canary_p.read_text())
        record(
            "leakage_canary_all_le_0p90",
            bool(can.get("all_passed")) and float(can.get("max_symmetric_auc", 1.0)) <= 0.90,
            f"Leakage canary failed: max_symmetric_auc={can.get('max_symmetric_auc')}",
        )
        feats = can.get("features", [])
        record(
            "leakage_canary_48_features_passed",
            len(feats) == 48 and all(bool(r.get("pass_le_0p90")) for r in feats) and len(can.get("quarantined_features", [1])) == 0,
            "Expected 48 passed features in v2 canary",
        )

    # 3. Direct programmatic GeoTIFF inspection (NO human inspector!)
    tif_path = ROOT / card["download_path"]
    zip_path = tif_path.with_suffix(".zip")
    sidecar_path = tif_path.with_suffix(".json")
    record("tif_and_zip_exist", tif_path.exists() and zip_path.exists() and sidecar_path.exists(), f"Missing {tif_path}")

    if tif_path.exists():
        actual_sha = sha256_file(tif_path)
        record("tif_sha256_matches_run_card", actual_sha == card["raster_sha256"], f"{actual_sha} != {card['raster_sha256']}")

        with rasterio.open(tif_path) as src:
            arr = src.read(1)
            crs_str = str(src.crs)
            shape = src.shape
            dtype_str = str(src.dtypes[0])
            count = src.count
            nodata = src.nodata
            tr = tuple(round(float(x), 6) for x in list(src.transform)[:6])

        record("tif_single_band", count == 1, f"count={count}")
        record("tif_dtype_float32", dtype_str == "float32", f"dtype={dtype_str}")
        record("tif_shape_3730x3292", shape == EXPECTED_SHAPE, f"shape={shape}")
        record("tif_crs_epsg_32611", crs_str == EXPECTED_CRS, f"crs={crs_str}")
        record("tif_geotransform_exact", tr == EXPECTED_TRANSFORM, f"transform={tr}")
        record("tif_nodata_none", nodata is None, f"nodata={nodata}")
        record("tif_zero_nan", int(np.isnan(arr).sum()) == 0, "NaN pixels present!")
        record("tif_zero_inf", int(np.isinf(arr).sum()) == 0, "Inf pixels present!")
        record("tif_no_float32_sentinel", int((np.abs(arr) > 1e30).sum()) == 0, "-3.4e38 sentinel present!")
        fmin, fmax = float(arr.min()), float(arr.max())
        record("tif_strict_range_0_1", 0.0 <= fmin and fmax <= 1.0 and fmax > 0.0, f"range=[{fmin}, {fmax}]")
        n_pos = int((arr > 0).sum())
        record("tif_positive_dots_match_card", n_pos == 37_654, f"positive_dots={n_pos}")

        # Optional full-grid footprint & catalogue check when .cache/gems_data is present
        sample_p = ROOT / ".cache/gems_data/sample_submission.tif"
        labels_p = ROOT / ".cache/gems_data/labels.tif"
        if sample_p.exists() and labels_p.exists():
            with rasterio.open(sample_p) as s_src:
                fp = np.isfinite(s_src.read(1))
            with rasterio.open(labels_p) as l_src:
                cat = (l_src.read(1) > 0) & fp
            record("tif_zero_outside_footprint", float(np.abs(arr[~fp]).sum()) == 0.0, "Nonzero outside footprint")
            record("tif_zero_on_catalogue", int((arr[cat] > 0).sum()) == 0, "Dots placed on mapped catalogue")

    if zip_path.exists():
        record("zip_sha256_matches_run_card", sha256_file(zip_path) == card["zip_sha256"], "Zip SHA256 mismatch")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            record("zip_contains_valid_tif", tif_path.name in names or "submission.tif" in names, f"zip contents={names}")

    # 4. Holdout & Labeling gates
    hd = card["holdout_dti"]
    c0 = hd["controls_same_split"]["CTRL-0_H19_5_B2"]["dti"]
    c1 = hd["controls_same_split"]["CTRL-1_19BAND_HGB"]["dti"]
    record("holdout_labeled_correctly", hd["evidence_class"] == "HOLDOUT-DTI" and hd["withheld_positive_pixels"] == 22893, "Bad holdout label")
    record("holdout_beats_both_controls", float(hd["dti"]) > float(c0) and float(hd["dti"]) > float(c1), f"dti={hd['dti']} vs {c0}, {c1}")
    record(
        "lli_marked_not_a_score",
        "NOT A SCORE" in card["lli_projection_not_a_score"]["evidence_class"],
        "LLI projection must be marked NOT A SCORE",
    )

    # 5. Dual-phase uniqueness across all 43 registry rasters
    uo = card["registry_correlation_overlap"]
    sp = uo["surface_phase"]
    dp = uo["dots_phase"]
    record("registry_checked_all_43_shas", uo["registry_unique_sha256_count"] == 43 and uo["complete_accessible_scan"] is True, "Incomplete registry scan")
    record(
        "surface_phase_unique",
        sp["unique"] is True and sp["max_abs_spearman_all_43"] <= 0.90 and sp["max_3px_overlap_dot_fields_42"] <= 0.70,
        f"Surface duplicate: {sp}",
    )
    record(
        "dots_phase_unique",
        dp["unique"] is True and dp["max_abs_spearman_all_43"] <= 0.90 and dp["max_3px_overlap_dot_fields_42"] <= 0.70 and uo["byte_unique"] and uo["pixel_unique"],
        f"Dots duplicate: {dp}",
    )

    # 6. 9-Site Executive Audit completeness
    nine_p = ROOT / "evidence/nine_sites_executive_audit.json"
    record("nine_sites_audit_complete", nine_p.exists() and len(json.loads(nine_p.read_text()).get("sites", [])) == 9, "Incomplete 9-site audit")

    # 7. Documentation & GitHub Pages synchronization
    for doc_rel in ("README.md", "docs/index.html", "docs/executive-summary.html"):
        dp_file = ROOT / doc_rel
        txt = dp_file.read_text() if dp_file.exists() else ""
        key_slug = doc_rel.replace("/", "_").replace(".", "_")
        record(
            f"doc_synced_{key_slug}",
            (card["submission_name"] in txt) and (card["raster_sha256"] in txt) and (card["submission_note"] in txt),
            f"{doc_rel} out of sync with current_run_card.json",
        )
    record(
        "preregistration_and_irregularities_exist",
        (ROOT / "docs/hypotheses.md").exists() and (ROOT / "docs/irregularities.md").exists(),
        "Missing docs/hypotheses.md or docs/irregularities.md",
    )

    ok = len(problems) == 0
    ok_download = ok and bool(card.get("ok_to_download"))
    ok_submit = ok and bool(card.get("ok_to_submit")) and card.get("verdict") == "promote"
    return {
        "ok": ok,
        "ok_to_download": ok_download,
        "ok_to_submit": ok_submit,
        "verdict": card.get("verdict"),
        "submission_name": card.get("submission_name"),
        "submission_note": card.get("submission_note"),
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "checks": checks,
        "problems": problems,
    }


def main() -> int:
    res = verify_all()
    print("=" * 78)
    print(f"GEMSDOESASS3 AUTOMATED GATE INSPECTOR ({res['checks_passed']}/{res['checks_total']} CHECKS PASSED)")
    print("=" * 78)
    for k, v in res["checks"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    if res["problems"]:
        print("\nPROBLEMS:")
        for p in res["problems"]:
            print(f"  - {p}")
    print("-" * 78)
    print(f"  SUBMISSION FILE : docs/downloads/{res['submission_name']}")
    print(f"  SUBMISSION NOTE : {res['submission_note']} ({len(res['submission_note'] or '')}/140 chars)")
    print(f"  OK TO DOWNLOAD  : {'YES (APPROVED)' if res['ok_to_download'] else 'NO (BLOCKED)'}")
    print(f"  OK TO SUBMIT    : {'YES (VERDICT: PROMOTE)' if res['ok_to_submit'] else 'NO'}")
    print("=" * 78)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
