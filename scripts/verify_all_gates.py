#!/usr/bin/env python3
"""Verify archived-raster integrity and fail-closed submission status.

A successful audit run means the local archive and its provenance/status records
are internally consistent. It does NOT mean the candidate is eligible to submit.
Current uniqueness remains blocked when the complete registry is unavailable or
the literal calibration-lattice rule fails.
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
EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_metric_record(record: object, *, score_key: str) -> bool:
    if not isinstance(record, dict):
        return False
    ci = record.get("ci95")
    return (
        record.get("score_label") == "HOLDOUT-DTI"
        and isinstance(record.get("evaluator_version"), str)
        and bool(record.get("evaluator_version"))
        and isinstance(record.get("withheld_positive_pixels"), int)
        and record["withheld_positive_pixels"] > 0
        and isinstance(record.get(score_key), (int, float))
        and isinstance(ci, list)
        and len(ci) == 2
        and all(isinstance(v, (int, float)) for v in ci)
    )


def verify_all() -> dict:
    checks: dict[str, bool] = {}
    problems: list[str] = []

    def record(name: str, condition: bool, failure: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            problems.append(f"{name}: {failure}")

    paths = {
        "current": ROOT / "evidence/current_run_card.json",
        "docs_current": ROOT / "docs/data/current_run_card.json",
        "canonical": ROOT / "evidence/run_card.json",
        "docs_canonical": ROOT / "docs/data/run_card.json",
    }
    cards_exist = all(path.exists() for path in paths.values())
    record("all_run_cards_exist", cards_exist, "One or more canonical run cards are missing")
    if not cards_exist:
        return {
            "ok": False,
            "ok_to_download": False,
            "ok_to_submit": False,
            "verdict": "negative",
            "checks_passed": sum(checks.values()),
            "checks_total": len(checks),
            "checks": checks,
            "problems": problems,
            "submission_blockers": ["Run-card files are incomplete"],
        }

    loaded = {key: json.loads(path.read_text(encoding="utf-8")) for key, path in paths.items()}
    card = loaded["current"]
    record("run_cards_synchronized", all(value == card for value in loaded.values()), "Run-card copies differ")

    required = [
        "hypothesis", "mechanism", "non_fault_mimic", "holdout_dti", "leakage_canary",
        "registry_correlation_and_overlap", "raster_sha256", "zip_sha256", "validator_output",
        "submission_name", "submission_note", "download_path", "verdict", "ok_to_download",
        "ok_to_submit", "budget", "official_data_availability",
    ]
    record("run_card_required_fields", all(key in card for key in required), "Missing required run-card fields")
    note = card.get("submission_note")
    record("note_length_le_140", isinstance(note, str) and 1 <= len(note) <= 140, "Submission/archive note exceeds 140 characters or is empty")
    record("current_lane_unresolved_is_explicit", card.get("assigned_lane_status", "").startswith("UNRESOLVED"), "Lane ambiguity is not disclosed")
    record("no_new_candidate_claim", card.get("new_candidate_generated_this_review") is False, "Run card incorrectly claims a new candidate was generated")
    record("slot_not_spent", card.get("slot_spent") is False and card.get("promote_to_real_slot") is False, "Slot/promotion status is not negative")

    # The prior lane used its allowed experiment budget. No new experiment is run here.
    budget = card.get("budget", {})
    record(
        "prior_lane_budget_recorded_and_not_exceeded",
        isinstance(budget.get("prior_lane_experiments"), int)
        and isinstance(budget.get("prior_lane_budget_cap"), int)
        and budget["prior_lane_experiments"] <= budget["prior_lane_budget_cap"]
        and budget.get("new_experiments_this_review") == 0,
        "Prior lane budget is missing/overrun or new experiments were not disclosed",
    )
    ledger_path = ROOT / "evidence/lwst_experiment_ledger.json"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        record(
            "historical_lane_ledger_within_3_experiments_2h",
            int(ledger.get("experiment_count", 999)) <= 3 and float(ledger.get("elapsed_seconds", float("inf"))) <= 7200.0,
            "Historical H-SASS3-A lane exceeds the recorded budget",
        )
    else:
        record("historical_lane_ledger_within_3_experiments_2h", False, "Experiment ledger is missing")

    # Verify the local archive itself; this is separate from submission eligibility.
    tif_path = ROOT / str(card.get("download_path", ""))
    zip_path = tif_path.with_suffix(".tif.zip")
    record("tif_and_zip_exist", tif_path.is_file() and zip_path.is_file(), "Archived TIF or ZIP is missing")
    format_ok = False
    if tif_path.is_file():
        actual_sha = sha256_file(tif_path)
        record("tif_sha256_matches_card", actual_sha == card.get("raster_sha256"), f"Archive SHA-256 mismatch: {actual_sha}")
        with rasterio.open(tif_path) as src:
            arr = src.read(1)
            transform = tuple(round(float(value), 6) for value in list(src.transform)[:6])
            structural_checks = {
                "single_band": src.count == 1,
                "float32": src.dtypes[0] == "float32",
                "shape": src.shape == EXPECTED_SHAPE,
                "crs": str(src.crs) == EXPECTED_CRS,
                "transform": transform == EXPECTED_TRANSFORM,
                "no_nodata_sentinel": src.nodata is None,
                "finite": bool(np.isfinite(arr).all()),
                "range_0_1": bool(np.isfinite(arr).all() and float(arr.min()) >= 0 and float(arr.max()) <= 1),
                "binary": bool(np.isin(arr, [0.0, 1.0]).all()),
                "positive_pixels": int((arr == 1).sum()) == 37_654,
            }
        for name, condition in structural_checks.items():
            record(f"tif_{name}", condition, f"Local GeoTIFF check failed: {name}")
        format_ok = all(structural_checks.values())
    else:
        arr = None

    if zip_path.is_file():
        record("zip_sha256_matches_card", sha256_file(zip_path) == card.get("zip_sha256"), "Archive ZIP SHA-256 mismatch")
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                names = archive.namelist()
                record("zip_contains_only_named_tif", names == [tif_path.name], f"Unexpected archive contents: {names}")
                member_ok = names == [tif_path.name] and hashlib.sha256(archive.read(tif_path.name)).hexdigest() == card.get("raster_sha256")
                record("zip_tif_matches_archive", member_ok, "TIF inside ZIP does not match the reviewed raster")
        except (OSError, zipfile.BadZipFile) as exc:
            record("zip_contains_only_named_tif", False, f"Cannot read ZIP: {exc}")
            record("zip_tif_matches_archive", False, f"Cannot read ZIP: {exc}")

    validator = card.get("validator_output", {})
    record("official_sample_absence_disclosed", validator.get("organizer_sample_comparison_available") is False, "Official-sample comparison status missing or misleading")
    record("archive_download_is_research_only", card.get("ok_to_download") is True and card.get("ok_to_submit") is False, "Download/submission status is not explicit")

    # HOLDOUT metrics are checked for provenance completeness, not for a win.
    hold = card.get("holdout_dti", {})
    metric_records = [
        (hold.get("archived_lwst_hide_and_recover"), "pooled_dti"),
        (hold.get("archived_lwst_sgmc_cal"), "prevalence_calibrated_dti"),
        (hold.get("experiment_E1_hide_and_recover"), "pooled_dti"),
        (hold.get("experiment_E1_sgmc_cal"), "prevalence_calibrated_dti"),
    ]
    record(
        "holdout_metrics_have_evaluator_n_and_ci",
        all(_is_metric_record(item, score_key=key) for item, key in metric_records),
        "One or more archived HOLDOUT-DTI records lack evaluator, withheld count, or 95% CI",
    )
    record("organizer_score_not_claimed_without_receipt", hold.get("organizer_score") is None, "An organizer score is asserted without a receipt")

    canary = card.get("leakage_canary", {})
    e1_canary = canary.get("E1_single_feature", {})
    old_canary = canary.get("historical_51_channel_report", {})
    record(
        "archived_single_feature_canary_status_disclosed",
        e1_canary.get("evidence_status", "").startswith("ARCHIVED")
        and isinstance(e1_canary.get("symmetric_auc"), (int, float))
        and e1_canary.get("passed") is True,
        "The historical single-feature canary is missing or mislabeled as fresh",
    )
    record(
        "archived_51_channel_canary_status_disclosed",
        old_canary.get("channels_tested") == 51
        and isinstance(old_canary.get("worst_symmetric_auc"), (int, float))
        and old_canary.get("all_passed") is True
        and old_canary.get("evidence_status", "").startswith("ARCHIVED"),
        "The prior 51-channel canary is missing or mislabeled as fresh",
    )

    # Fail closed on incomplete current uniqueness. Archived pass flags are not current passes.
    uniq = card.get("registry_correlation_and_overlap", {})
    lattice = uniq.get("archived_literal_lattice_result", {})
    archived_dots = uniq.get("archived_final_dot_scan_451_downloads", {})
    surface = uniq.get("archived_preplacement_surface_scan", {})
    record(
        "literal_lattice_failure_correctly_recorded",
        isinstance(lattice.get("within3_fraction"), (int, float))
        and lattice["within3_fraction"] > 0.70
        and lattice.get("pass") is False,
        "The archived lattice overlap does not demonstrate the literal-rule failure",
    )
    record(
        "historical_download_subset_is_labeled_archived",
        archived_dots.get("evidence_status", "").startswith("ARCHIVED")
        and archived_dots.get("archived_subset_pass") is True
        and isinstance(archived_dots.get("max_within3_fraction"), (int, float))
        and archived_dots["max_within3_fraction"] <= 0.70,
        "Historical subset statistics are missing or presented as current clearance",
    )
    record(
        "surface_scan_is_labeled_archived",
        surface.get("evidence_status", "").startswith("ARCHIVED")
        and isinstance(surface.get("max_abs_spearman"), (int, float)),
        "Historical surface scan is missing or presented as current clearance",
    )
    record(
        "current_registry_uniqueness_fails_closed",
        uniq.get("recomputed_this_run") is False
        and uniq.get("current_registry_clearance") is False
        and uniq.get("preplacement_surface_currently_cleared") is False
        and uniq.get("final_dots_currently_cleared") is False,
        "Unavailable current registry evidence was not failed closed",
    )
    record(
        "run_card_submission_status_is_blocked",
        card.get("verdict") == "negative"
        and card.get("ok_to_submit") is False
        and card.get("promote_to_real_slot") is False,
        "Candidate is not marked blocked despite incomplete/failing uniqueness evidence",
    )

    # Public files should expose archive identity and the truthful archive-only note.
    pages = [ROOT / rel for rel in ["README.md", "index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"]]
    for page in pages:
        text = page.read_text(encoding="utf-8") if page.exists() else ""
        slug = page.relative_to(ROOT).as_posix().replace("/", "_").replace(".", "_")
        record(
            f"page_sync_{slug}",
            page.exists()
            and card.get("submission_name", "") in text
            and str(card.get("raster_sha256", ""))[:12] in text
            and str(card.get("submission_note", "")) in text,
            f"{page.relative_to(ROOT)} does not identify the archived candidate and its status note",
        )

    ok = not problems
    blockers = []
    if not card.get("ok_to_submit"):
        blockers.append("Candidate is not approved for submission")
    if lattice.get("pass") is False:
        blockers.append("Archived literal calibration-lattice comparison exceeds the 70% limit")
    if not uniq.get("current_registry_clearance"):
        blockers.append("Current full-registry surface/dot comparisons are unavailable")
    if not card.get("budget", {}).get("current_lane_resolved"):
        blockers.append("Method lane is unresolved and the prior lane budget is exhausted")

    return {
        "ok": ok,
        "ok_to_download": bool(ok and format_ok and card.get("ok_to_download")),
        "ok_to_submit": bool(ok and card.get("ok_to_submit")),
        "verdict": card.get("verdict"),
        "submission_name": card.get("submission_name"),
        "submission_note": card.get("submission_note"),
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "checks": checks,
        "problems": problems,
        "submission_blockers": blockers,
    }


def main() -> int:
    result = verify_all()
    print("=" * 78)
    print(f"GEMSDOESASS3 ARCHIVE & SUBMISSION-STATUS AUDIT ({result['checks_passed']}/{result['checks_total']} checks consistent)")
    print("=" * 78)
    for name, passed in result["checks"].items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    if result["problems"]:
        print("\nAUDIT PROBLEMS:")
        for problem in result["problems"]:
            print(f"  - {problem}")
    if result["submission_blockers"]:
        print("\nSUBMISSION BLOCKERS (expected for this archive):")
        for blocker in result["submission_blockers"]:
            print(f"  - {blocker}")
    print("-" * 78)
    print(f"  ARCHIVE FILE    : {result['submission_name']}")
    print(f"  ARCHIVE NOTE    : {result['submission_note']} ({len(result['submission_note'] or '')}/140 chars)")
    print(f"  DOWNLOAD (ANALYSIS ONLY): {'YES' if result['ok_to_download'] else 'NO'}")
    print(f"  SUBMIT          : {'YES' if result['ok_to_submit'] else 'NO — BLOCKED'}")
    print("=" * 78)
    if not result["ok"]:
        return 1
    return 0 if "--expect-blocked" in sys.argv or result["ok_to_submit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
