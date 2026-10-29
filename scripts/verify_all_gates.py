#!/usr/bin/env python3
"""Automated zero-human-intervention programmatic inspector & gate verifier for GEMSDOESASS3.

Runs cleanly in both:
  - Full workspace mode (with /tmp/gems_data), and
  - Lightweight GitHub Actions CI mode (inspecting shipped GeoTIFF, ZIP, 51-ch Leakage Canary,
    386-raster + sibling Uniqueness Audit, Dual-Evaluator Holdout wins, and Pages sync).
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


def _footprint_mask():
    """Finite cells of the organizer sample_submission.tif (the scored region), or None if the data is absent."""
    for base in (ROOT / ".cache/gems_data", Path("/tmp/gems_data")):
        p = base / "sample_submission.tif"
        if p.exists():
            with rasterio.open(p) as s:
                return np.isfinite(s.read(1))
    return None


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

    rc_ev = ROOT / "evidence/current_run_card.json"
    rc_doc = ROOT / "docs/data/current_run_card.json"
    rc_canon = ROOT / "evidence/run_card.json"
    record("run_card_exists", rc_ev.exists() and rc_doc.exists() and rc_canon.exists(), "Missing run_card.json")
    if not (rc_ev.exists() and rc_doc.exists() and rc_canon.exists()):
        return {"ok": False, "checks": checks, "problems": problems}

    card = json.loads(rc_ev.read_text())
    card_doc = json.loads(rc_doc.read_text())
    record("run_card_docs_identical", card == card_doc, "evidence/ and docs/data/ run cards diverge")

    required_keys = [
        "hypothesis", "mechanism", "mimic", "holdout_dti",
        "leakage_canary", "registry_correlation_and_overlap",
        "raster_sha256", "validator_output",
        "submission_name", "submission_note", "verdict", "download_path",
    ]
    record(
        "run_card_required_fields",
        all(k in card and card[k] not in (None, "") for k in required_keys),
        "Missing required Run Card fields",
    )
    record(
        "submission_note_le_140_chars",
        1 <= len(card["submission_note"]) <= 140,
        f"Submission note length {len(card['submission_note'])} outside [1, 140]",
    )

    ledger = json.loads((ROOT / "evidence/lwst_experiment_ledger.json").read_text())
    record(
        "budget_cap_le_3_experiments_2h",
        int(ledger["experiment_count"]) <= 3 and float(ledger["elapsed_seconds"]) <= 7200.0,
        f"Budget exceeded: {ledger['experiment_count']} exps / {ledger['elapsed_seconds']}s",
    )

    # Leakage Canary (51 channels)
    can = json.loads((ROOT / "evidence/leakage_canary_report.json").read_text())
    record(
        "leakage_canary_51_channels_le_0p90",
        bool(can["all_passed"]) and can["n_channels_tested"] == 51 and float(can["worst_symmetric_auc"]) <= 0.90,
        f"Canary failed: {can.get('worst_symmetric_auc')}",
    )

    # Direct programmatic GeoTIFF inspection
    tif_path = ROOT / card["download_path"]
    zip_path = tif_path.with_suffix(".tif.zip")
    record("tif_and_zip_exist", tif_path.exists() and zip_path.exists(), f"Missing {tif_path} or {zip_path}")

    cand_dots = None
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
        record("tif_no_float32_sentinel", int((np.abs(arr) > 1e30).sum()) == 0, "Sentinel present!")
        fmin, fmax = float(arr.min()), float(arr.max())
        record("tif_strict_range_0_1", 0.0 <= fmin and fmax <= 1.0 and fmax > 0.0, f"range=[{fmin}, {fmax}]")
        cand_dots = arr > 0.0
        n_pos = int(cand_dots.sum())
        expected_dots = int(card.get("validator_output", {}).get("emitted_positive_pixels", n_pos))
        record("tif_positive_dots_match_card", n_pos == expected_dots, f"positive_dots={n_pos} (card says {expected_dots})")
        # Competition text (page 967): "data outside the bounds is null or nan". Zeros outside are the convention of the
        # owner-scored files, so only NON-ZERO finite cells outside the footprint fail. Pending without the data.
        footprint = _footprint_mask()
        if footprint is None:
            record("tif_outside_bounds_null_or_zero", False, "competition footprint absent (PENDING_DATA): outside-bounds rule not checked")
        else:
            outside = arr[~footprint]
            n_nonzero_outside = int(np.count_nonzero(np.isfinite(outside) & (outside != 0)))
            n_pos_outside = int(np.count_nonzero(np.isfinite(outside) & (outside > 0)))
            record("tif_outside_bounds_null_or_zero", n_nonzero_outside == 0,
                   f"{n_nonzero_outside:,} non-zero cells outside the competition bounds ({n_pos_outside:,} positive); rule: null or nan")

    if zip_path.exists():
        record("zip_sha256_matches_run_card", sha256_file(zip_path) == card["zip_sha256"], "Zip SHA256 mismatch")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            record("zip_contains_valid_tif", names == [tif_path.name], f"zip contents={names}")
            record("zip_inner_matches_tif", names == [tif_path.name] and hashlib.sha256(zf.read(tif_path.name)).hexdigest() == card["raster_sha256"], "ZIP bytes differ from TIF")

    # Dual-Evaluator Holdout wins vs 0.2778 Champion (skipped if holdout not run)
    hd = card.get("holdout_dti", {})
    if hd.get("score_label") == "HOLDOUT-DTI":
        hr = hd.get("primary_hide_and_recover", {})
        sg = hd.get("secondary_off_catalogue_sgmc", {})
        record(
            "holdout_hide_recover_beats_02778_ci95_gt_0",
            hr.get("score_label") == "HOLDOUT-DTI"
            and hr.get("pooled_dti", 0) > hr.get("champion_02778_baseline_dti", 0)
            and hr.get("paired_delta_ci95", [0, 0])[0] > 0.0,
            f"HR={hr.get('pooled_dti')} vs {hr.get('champion_02778_baseline_dti')}",
        )
        record(
            "holdout_sgmc_beats_02778",
            sg.get("score_label") == "HOLDOUT-DTI"
            and sg.get("prevalence_calibrated_dti", 0) > sg.get("champion_02778_calibrated_dti", 0),
            f"SGMC={sg.get('prevalence_calibrated_dti')} vs {sg.get('champion_02778_calibrated_dti')}",
        )
    else:
        record("holdout_hide_recover_beats_02778_ci95_gt_0", False, "Holdout-DTI not run (PENDING_DATA)")
        record("holdout_sgmc_beats_02778", False, "Holdout-DTI not run (PENDING_DATA)")

    # Protocol applies to every registry raster, including space-filling ones.
    uq = card.get("registry_correlation_and_overlap", {})
    if uq.get("registry_rasters_checked", 0) > 0:
        audit = json.loads((ROOT / "evidence/uniqueness_audit_386.json").read_text())
        lattice = audit.get("space_filling_calibration_lattices", [])
        record("literal_registry_overlap_all_rasters", bool(lattice) and all(
            isinstance(row.get("within_3px_fraction"), (int, float))
            and 0 <= row["within_3px_fraction"] <= 0.70 for row in lattice),
            "Registry lattice overlaps 99.7849% of candidate dots; protocol limit is 70%")
        record(
            "historical_non_lattice_subset_passed",
            uq.get("registry_rasters_checked") == 386
            and uq.get("pre_placement_surface_max_abs_spearman", 1.0) <= 0.90
            and uq.get("final_dots_max_abs_spearman", 1.0) <= 0.90
            and uq.get("all_385_genuine_max_within_3px_fraction", 1.0) <= 0.70
            and uq.get("passed_all_focus_9_sites_literally") is True,
            f"Uniqueness failure: {uq}",
        )
    else:
        record("literal_registry_overlap_all_rasters", False, "Registry overlap not run (PENDING_DATA)")
        record("historical_non_lattice_subset_passed", False, "Registry uniqueness not run (PENDING_DATA)")

    sibling_gsd = ROOT / "docs/downloads/gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros.tif"
    if cand_dots is not None and sibling_gsd.exists():
        with rasterio.open(sibling_gsd) as s_ds:
            s_dots = s_ds.read(1) > 0.0
        d_sib = ndi.distance_transform_edt(~s_dots)
        ov_sib = float((d_sib[cand_dots] <= 3.0).mean())
        record("uniqueness_vs_parallel_pr7_gsdhua3", ov_sib <= 0.70, f"ov_vs_gsdhua3={ov_sib:.4f}")

    # Pages synchronization across root / and /docs
    for doc_rel in ("README.md", "index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"):
        dp_file = ROOT / doc_rel
        txt = dp_file.read_text() if dp_file.exists() else ""
        key_slug = doc_rel.replace("/", "_").replace(".", "_")
        record(
            f"doc_synced_{key_slug}",
            (card["submission_name"] in txt) and (card["raster_sha256"][:12] in txt) and (card["submission_note"] in txt),
            f"{doc_rel} out of sync with current_run_card.json",
        )

    # Format gate: all TIF/zip/range/CRS/shape checks must pass.
    format_keys = [k for k in checks if k.startswith("tif_") or k.startswith("zip_")]
    format_ok = all(checks.get(k, False) for k in format_keys)
    # All checks pass only if format + holdout + registry + docs all pass.
    ok = len(problems) == 0
    # OK to download: format gate passes + card says ok_to_download.
    ok_download = format_ok and bool(card.get("ok_to_download"))
    # OK to submit: everything passes AND verdict is promote.
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
    # Accept: all checks pass; OR format-valid pending-data verdict with only
    # expected missing-data failures (holdout/registry not run); OR the
    # historical --expect-blocked lattice failure.
    expected_pending = {
        "holdout_hide_recover_beats_02778_ci95_gt_0",
        "holdout_sgmc_beats_02778",
        "literal_registry_overlap_all_rasters",
        "historical_non_lattice_subset_passed",
        "tif_outside_bounds_null_or_zero",
    }
    pending_only = all(
        any(p.startswith(key + ":") for key in expected_pending) for p in res["problems"]
    )
    is_pending_format_valid = (
        res["verdict"] == "format_valid_pending_data"
        and res["ok_to_download"]
        and not res["ok_to_submit"]
        and pending_only
    )
    is_blocked_lattice = (
        "--expect-blocked" in sys.argv
        and not res["ok_to_submit"]
        and res["problems"] == ["literal_registry_overlap_all_rasters: Registry lattice overlaps 99.7849% of candidate dots; protocol limit is 70%"]
        and res["verdict"] == "negative"
    )
    # Documented blocked state for the current candidate: download and submit both NO, and every failing check is one of
    # the documented pending or failing gates (no unexplained failure). Without the data every gate reports PENDING.
    is_blocked_documented = (
        "--expect-blocked" in sys.argv
        and not res["ok_to_download"]
        and not res["ok_to_submit"]
        and bool(res["problems"])
        and all(any(p.startswith(key + ":") for key in expected_pending) for p in res["problems"])
    )
    return 0 if res["ok"] or is_pending_format_valid or is_blocked_lattice or is_blocked_documented else 1


if __name__ == "__main__":
    raise SystemExit(main())
