#!/usr/bin/env python3
"""Automated gate verifier for GEMSDOESASS3 (programmatic inspection, no human step).

Reads the CURRENT candidate's run card (evidence/run_card.json, identical copies in evidence/ and
docs/) and re-checks the shipped GeoTIFF byte-for-byte, the leakage canary, the holdout receipt, the
literal registry-uniqueness receipt, the archived and non-current cards, and the Pages sync.

Exit codes
  default          0 only if every gate passes (OK TO SUBMIT).
  --expect-blocked 0 when the candidate is downloadable and NOT submittable, and the ONLY failing
                   gates are the documented holdout blockers below. Any other failure is nonzero.

Documented blockers (holdout is measured, the file is below the 0.2778 champion):
  holdout_hide_recover_beats_02778_ci95_gt_0 - hide-and-recover not run for this file
  holdout_sgmc_beats_02778                   - SGMC-CAL below the champion, CIs do not separate
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
EXPECTED_BLOCKERS = {
    "holdout_hide_recover_beats_02778_ci95_gt_0",
    "holdout_sgmc_beats_02778",
}
ARCHIVE_LWST = ROOT / "evidence/archive/run_card_lwst_archived_20261027.json"
NON_CURRENT_CARDS = [
    ROOT / "evidence/run_card_bgk_pbe.json",
    ROOT / "evidence/run_card_unique_structural_20261029.json",
]
SIBLING_GSD = ROOT / "docs/downloads/gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros.tif"
LATTICE = ROOT / ".cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
SAMPLE = ROOT / ".cache/gems_data/sample_submission.tif"


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

    rc_ev = ROOT / "evidence/current_run_card.json"
    rc_doc = ROOT / "docs/data/current_run_card.json"
    rc_canon = ROOT / "evidence/run_card.json"
    record("run_card_exists", rc_ev.exists() and rc_doc.exists() and rc_canon.exists(), "Missing run_card.json")
    if not (rc_ev.exists() and rc_doc.exists() and rc_canon.exists()):
        return {"ok": False, "checks": checks, "problems": problems}

    card = json.loads(rc_ev.read_text())
    record("run_card_copies_identical", card == json.loads(rc_doc.read_text()) == json.loads(rc_canon.read_text()),
           "evidence/ and docs/data/ run cards diverge")

    required_keys = [
        "hypothesis", "mechanism", "mimic", "holdout_dti", "leakage_canary",
        "registry_correlation_and_overlap", "raster_sha256", "zip_sha256", "validator_output",
        "submission_name", "submission_note", "verdict", "download_path",
    ]
    record("run_card_required_fields", all(k in card and card[k] not in (None, "") for k in required_keys),
           "Missing required Run Card fields")
    record("submission_note_le_140_chars", 1 <= len(card["submission_note"]) <= 140,
           f"Submission note length {len(card['submission_note'])} outside [1, 140]")

    ledger = json.loads((ROOT / "evidence/lwst_experiment_ledger.json").read_text())
    record("lwst_ledger_budget_le_3_experiments_2h",
           int(ledger["experiment_count"]) <= 3 and float(ledger["elapsed_seconds"]) <= 7200.0,
           f"Budget exceeded: {ledger['experiment_count']} exps / {ledger['elapsed_seconds']}s")

    can = json.loads((ROOT / "evidence/leakage_canary_report.json").read_text())
    record("leakage_canary_51_channels_le_0p90",
           bool(can["all_passed"]) and can["n_channels_tested"] == 51 and float(can["worst_symmetric_auc"]) <= 0.90,
           f"Canary failed: {can.get('worst_symmetric_auc')}")

    # ---- Direct programmatic GeoTIFF inspection ----
    tif_path = ROOT / card["download_path"]
    zip_path = tif_path.with_suffix(".tif.zip")
    record("tif_and_zip_exist", tif_path.exists() and zip_path.exists(), f"Missing {tif_path} or {zip_path}")

    cand_dots = None
    if tif_path.exists():
        actual_sha = sha256_file(tif_path)
        record("tif_sha256_matches_run_card", actual_sha == card["raster_sha256"],
               f"{actual_sha} != {card['raster_sha256']}")
        with rasterio.open(tif_path) as src:
            arr = src.read(1)
            crs_str, shape, dtype_str = str(src.crs), src.shape, str(src.dtypes[0])
            count, nodata = src.count, src.nodata
            tr = tuple(round(float(x), 6) for x in list(src.transform)[:6])
        record("tif_single_band", count == 1, f"count={count}")
        record("tif_dtype_float32", dtype_str == "float32", f"dtype={dtype_str}")
        record("tif_shape_3730x3292", shape == EXPECTED_SHAPE, f"shape={shape}")
        record("tif_crs_epsg_32611", crs_str == EXPECTED_CRS, f"crs={crs_str}")
        record("tif_geotransform_exact", tr == EXPECTED_TRANSFORM, f"transform={tr}")
        record("tif_nodata_none", nodata is None, f"nodata={nodata}")
        record("tif_zero_nan", int(np.isnan(arr).sum()) == 0, "NaN pixels present")
        record("tif_zero_inf", int(np.isinf(arr).sum()) == 0, "Inf pixels present")
        record("tif_no_float32_sentinel", int((np.abs(arr) > 1e30).sum()) == 0, "Sentinel present")
        fmin, fmax = float(arr.min()), float(arr.max())
        record("tif_strict_range_0_1", 0.0 <= fmin and fmax <= 1.0 and fmax > 0.0, f"range=[{fmin}, {fmax}]")
        cand_dots = arr > 0.0
        n_pos = int(cand_dots.sum())
        expected_dots = int(card["validator_output"].get("emitted_positive_pixels", n_pos))
        record("tif_positive_dots_match_card", n_pos == expected_dots, f"positive_dots={n_pos} (card says {expected_dots})")
        if SAMPLE.exists():
            with rasterio.open(SAMPLE) as t:
                foot = np.isfinite(t.read(1))
            record("tif_zero_outside_footprint", int((arr[~foot] != 0).sum()) == 0,
                   f"{int((arr[~foot] != 0).sum())} non-zero values outside the organizer footprint")

    if zip_path.exists():
        record("zip_sha256_matches_run_card", sha256_file(zip_path) == card["zip_sha256"], "Zip SHA256 mismatch")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            record("zip_contains_valid_tif", names == [tif_path.name], f"zip contents={names}")
            record("zip_inner_matches_tif",
                   names == [tif_path.name] and hashlib.sha256(zf.read(tif_path.name)).hexdigest() == card["raster_sha256"],
                   "ZIP bytes differ from TIF")

    # ---- Holdout gates (HOLDOUT-DTI) ----
    hd = card.get("holdout_dti", {})
    if hd.get("score_label") == "HOLDOUT-DTI":
        hr = hd.get("primary_hide_and_recover", {})
        sg = hd.get("secondary_off_catalogue_sgmc", {})
        record(
            "holdout_hide_recover_beats_02778_ci95_gt_0",
            hr.get("score_label") == "HOLDOUT-DTI"
            and hr.get("pooled_dti", 0) > hr.get("champion_02778_baseline_dti", 0)
            and hr.get("paired_delta_ci95", [0, 0])[0] > 0.0,
            f"hide-and-recover: {hr.get('score_label', 'NOT RUN')}",
        )
        lit_lo = (sg.get("prevalence_calibrated_ci95") or [None, None])[0]
        champ_hi = (sg.get("champion_02778_calibrated_ci95") or [None, None])[1]
        record(
            "holdout_sgmc_beats_02778",
            sg.get("score_label") == "HOLDOUT-DTI"
            and sg.get("prevalence_calibrated_dti", 0) > sg.get("champion_02778_calibrated_dti", 0)
            and lit_lo is not None and champ_hi is not None and lit_lo > champ_hi,
            f"SGMC {sg.get('prevalence_calibrated_dti')} vs champion {sg.get('champion_02778_calibrated_dti')}; "
            f"CI lower {lit_lo} vs champion CI upper {champ_hi}",
        )
    else:
        record("holdout_hide_recover_beats_02778_ci95_gt_0", False, "Holdout-DTI not run")
        record("holdout_sgmc_beats_02778", False, "Holdout-DTI not run")

    # ---- Literal registry uniqueness (Protocol Rule 1; no exemption for the calibration lattice) ----
    uq = card.get("registry_correlation_and_overlap", {})
    rec_path = ROOT / uq.get("receipt", "__missing__")
    if rec_path.is_file():
        rec = json.loads(rec_path.read_text())
        record("literal_receipt_bound_to_raster", rec.get("candidate_sha256") == card["raster_sha256"],
               f"receipt {rec.get('candidate_sha256')} != raster {card['raster_sha256']}")
        record("literal_registry_overlap_all_rasters",
               rec["literal_rule_passed"] is True and rec["registry_rasters_compared"] == 386
               and rec["final_dots_stage"]["worst_within_3px_fraction"] <= 0.70,
               f"worst within-3px {rec['final_dots_stage']['worst_within_3px_fraction']:.6f} (limit 0.70)")
        record("literal_registry_rank_correlation_all_rasters",
               rec["surface_stage"]["passed"] is True and rec["final_dots_stage"]["worst_abs_spearman"] <= 0.90,
               "rank correlation above 0.90 on surface or final dots")
    else:
        record("literal_registry_overlap_all_rasters", False, f"receipt missing: {uq.get('receipt')}")
        record("literal_registry_rank_correlation_all_rasters", False, "receipt missing")

    if cand_dots is not None and SIBLING_GSD.exists():
        with rasterio.open(SIBLING_GSD) as s_ds:
            s_dots = s_ds.read(1) > 0.0
        ov_sib = float((ndi.distance_transform_edt(~s_dots)[cand_dots] <= 3.0).mean())
        record("uniqueness_vs_gsdhua3_sibling", ov_sib <= 0.70, f"ov_vs_gsdhua3={ov_sib:.4f}")

    # ---- Archived and non-current cards must not be downloadable under the literal rule ----
    if ARCHIVE_LWST.exists():
        arch = json.loads(ARCHIVE_LWST.read_text())
        record("archived_lwst_card_not_downloadable", arch.get("ok_to_download") is False
               and arch.get("ok_to_submit") is False, "archived LWST card must be ok_to_download=false")
    else:
        record("archived_lwst_card_not_downloadable", False, "archived LWST card missing")
    for p in NON_CURRENT_CARDS:
        if p.exists():
            c2 = json.loads(p.read_text())
            lit = c2.get("literal_audit_2026_10_29", {})
            record(f"non_current_{p.stem}_not_downloadable",
                   c2.get("ok_to_download") is False and c2.get("ok_to_submit") is False
                   and lit.get("literal_rule_passed") is False,
                   f"{p.name}: ok_to_download={c2.get('ok_to_download')}, literal={lit.get('literal_rule_passed')}")
        else:
            record(f"non_current_{p.stem}_not_downloadable", False, f"missing {p.name}")

    # ---- Pages synchronization across root / and /docs ----
    for doc_rel in ("README.md", "index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"):
        dp_file = ROOT / doc_rel
        txt = dp_file.read_text() if dp_file.exists() else ""
        key_slug = doc_rel.replace("/", "_").replace(".", "_")
        record(f"doc_synced_{key_slug}",
               (card["submission_name"] in txt) and (card["raster_sha256"][:12] in txt) and (card["submission_note"] in txt),
               f"{doc_rel} out of sync with current_run_card.json")

    # ---- Summary flags ----
    format_keys = [k for k in checks if k.startswith("tif_") or k.startswith("zip_")]
    format_ok = all(checks.get(k, False) for k in format_keys)
    literal_ok = checks.get("literal_registry_overlap_all_rasters", False) and checks.get("literal_registry_rank_correlation_all_rasters", False)
    ok = len(problems) == 0
    ok_download = format_ok and literal_ok and bool(card.get("ok_to_download"))
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
    expect_blocked = "--expect-blocked" in sys.argv
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
    print(f"  SUBMISSION FILE : {res['submission_name']}")
    print(f"  SUBMISSION NOTE : {res['submission_note']} ({len(res['submission_note'] or '')}/140 chars)")
    print(f"  OK TO DOWNLOAD  : {'YES' if res['ok_to_download'] else 'NO (BLOCKED)'}")
    print(f"  OK TO SUBMIT    : {'YES (VERDICT: PROMOTE)' if res['ok_to_submit'] else 'NO'}")
    print("=" * 78)
    failing = {p.split(":", 1)[0] for p in res["problems"]}
    blocked_only = bool(failing) and failing <= EXPECTED_BLOCKERS
    if expect_blocked:
        good = res["ok_to_download"] and not res["ok_to_submit"] and blocked_only
        return 0 if good else 1
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
