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
EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
# Only this verdict permits submission. It requires every blocking gate, including the
# literal registry-overlap rule (which currently FAILS; see IR-SASS3-19). Score claims are
# reported as WARN and never establish a score.
SUBMIT_VERDICT = "promote"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_all() -> dict:
    checks: dict[str, bool] = {}
    problems: list[str] = []
    # name -> (passed, detail). Failing items are WARNINGS: reported, never CI-blocking.
    warn_items: dict[str, tuple[bool, str]] = {}

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
        record("tif_positive_dots_match_card", n_pos == 37_654, f"positive_dots={n_pos}")

    if zip_path.exists():
        record("zip_sha256_matches_run_card", sha256_file(zip_path) == card["zip_sha256"], "Zip SHA256 mismatch")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            record("zip_contains_valid_tif", names == [tif_path.name], f"zip contents={names}")
            record("zip_inner_matches_tif", names == [tif_path.name] and hashlib.sha256(zf.read(tif_path.name)).hexdigest() == card["raster_sha256"], "ZIP bytes differ from TIF")

    # Score claims. Blocking: the independent recomputation receipt exists and is for the
    # shipped raster bytes. NOT blocking (reported as WARN): whether the claimed holdout
    # comparisons reproduce. A claim that does not reproduce must not turn CI red, but it
    # must not be reported as a PASS either.
    indep_p = ROOT / "evidence/independent_verification_20261028.json"
    record("independent_verification_receipt_present", indep_p.exists(), "Missing recomputed verification receipt")
    if indep_p.exists():
        indep = json.loads(indep_p.read_text())
        record(
            "independent_receipt_is_for_shipped_raster",
            indep["shipped_proxies"]["sha256"] == card["raster_sha256"],
            "independent receipt SHA != shipped raster SHA",
        )
        comp = indep["comparisons"]
        warn_items["HR_0p111062_reproduced_from_shipped_raster"] = (
            comp["hide_recover_claimed_for_shipped"]["status"] == "REPRODUCED",
            f"claimed {comp['hide_recover_claimed_for_shipped']['claimed']} vs recomputed static "
            f"{comp['hide_recover_claimed_for_shipped']['recomputed_static']:.6f}",
        )
        warn_items["HR_0p099202_is_champion_baseline"] = (
            comp["champion_hide_recover_baseline_claimed_0p099202"]["status"] == "REPRODUCED",
            "0.099202 equals GEMSDOE25 D2.8 static HR, not the 0.2778 champion",
        )
        delta_lo = comp["sgmc_paired_delta_ci_includes_zero"]["claimed_delta_ci95"][0]
        warn_items["SGMC_paired_delta_vs_champion_CI_excludes_zero"] = (
            delta_lo > 0.0,
            f"paired delta CI lower bound {delta_lo:+.6f} (claimed CI spans zero)",
        )
        warn_items["SGMC_shipped_reproduced"] = (
            comp["sgmc_cal_claimed_for_shipped"]["status"] == "REPRODUCED",
            "SGMC-CAL recomputed",
        )

    # Protocol applies to every registry raster, including space-filling ones.
    # Historical receipt has a literal failing row; no null-calibration exemption.
    audit = json.loads((ROOT / "evidence/uniqueness_audit_386.json").read_text())
    lattice = audit.get("space_filling_calibration_lattices", [])
    record("literal_registry_overlap_all_rasters", bool(lattice) and all(
        isinstance(row.get("within_3px_fraction"), (int, float))
        and 0 <= row["within_3px_fraction"] <= 0.70 for row in lattice),
        "Registry lattice overlaps 99.7849% of candidate dots; protocol limit is 70%")

    # 386-Raster Uniqueness + Parallel Sibling GeoTIFF check
    uq = card["registry_correlation_and_overlap"]
    record(
        "historical_non_lattice_subset_passed",
        uq["registry_rasters_checked"] == 386
        and uq["pre_placement_surface_max_abs_spearman"] <= 0.90
        and uq["final_dots_max_abs_spearman"] <= 0.90
        and uq["all_385_genuine_max_within_3px_fraction"] <= 0.70
        and uq["passed_all_focus_9_sites_literally"] is True,
        f"Uniqueness failure: {uq}",
    )

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

    ok = len(problems) == 0
    ok_download = ok and bool(card.get("ok_to_download"))
    # ok_to_submit requires all blocking gates AND verdict == promote. Score claims are
    # reported separately in `warnings` and do not gate submission.
    ok_submit = ok and bool(card.get("ok_to_submit")) and card.get("verdict") == SUBMIT_VERDICT
    warnings = {k: {"reproduced": bool(v[0]), "detail": v[1]} for k, v in warn_items.items()}
    return {
        "ok": ok,
        "ok_to_download": ok_download,
        "ok_to_submit": ok_submit,
        "score_claims_established": all(v[0] for v in warn_items.values()) if warn_items else False,
        "warnings": warnings,
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
        print("\nPROBLEMS (blocking):")
        for p in res["problems"]:
            print(f"  - {p}")
    if res["warnings"]:
        print("\nWARNINGS (non-blocking; score claims):")
        for k, v in res["warnings"].items():
            print(f"  [{'OK  ' if v['reproduced'] else 'WARN'}] {k}: {v['detail']}")
    print("-" * 78)
    print(f"  SUBMISSION FILE : docs/downloads/{res['submission_name']}")
    print(f"  SUBMISSION NOTE : {res['submission_note']} ({len(res['submission_note'] or '')}/140 chars)")
    print(f"  OK TO DOWNLOAD  : {'YES (format + uniqueness gates pass)' if res['ok_to_download'] else 'NO (BLOCKED)'}")
    print(f"  OK TO SUBMIT    : {'YES (format-valid & unique; score NOT established)' if res['ok_to_submit'] else 'NO'}")
    print(f"  SCORE CLAIMS    : {'reproduced' if res['score_claims_established'] else 'NOT ESTABLISHED (see WARN lines)'}")
    print("=" * 78)
    return 0 if res["ok"] or ("--expect-blocked" in sys.argv and not res["ok_to_submit"] and res["problems"] == ["literal_registry_overlap_all_rasters: Registry lattice overlaps 99.7849% of candidate dots; protocol limit is 70%"] and res["verdict"] == "negative") else 1


if __name__ == "__main__":
    raise SystemExit(main())
