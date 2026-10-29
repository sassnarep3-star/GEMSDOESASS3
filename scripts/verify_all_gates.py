#!/usr/bin/env python3
"""Fail-closed preflight for the active candidate recorded in current_run_card.json.

This verifier checks file bytes and format independently. It does not treat a passed
format check, a one-raster overlap receipt, or a historical HOLDOUT-DTI as promotion.
Use --expect-blocked in CI to require the current documented negative verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _footprint_mask():
    """Finite cells of the organizer sample_submission.tif (the scored region), or None if the data is absent."""
    for cand in (ROOT / ".cache/gems_data/sample_submission.tif", Path("/tmp/gems_data/sample_submission.tif")):
        if cand.is_file():
            with rasterio.open(cand) as src:
                return np.isfinite(src.read(1))
    return None


def verify() -> dict:
    card_path = ROOT / "evidence/current_run_card.json"
    card = json.loads(card_path.read_text())
    tif = ROOT / card["download_path"]
    checks: dict[str, bool] = {}
    notes: list[str] = []

    def check(key: str, value: bool, note: str | None = None) -> None:
        checks[key] = bool(value)
        if note and not value:
            notes.append(f"{key}: {note}")

    copies = [
        json.loads((ROOT / "evidence/run_card.json").read_text()),
        json.loads((ROOT / "docs/data/current_run_card.json").read_text()),
        json.loads((ROOT / "docs/evidence/current_run_card.json").read_text()),
        json.loads((ROOT / "docs/evidence/run_card.json").read_text()),
    ]
    check("run_card_copies_match", all(copy == card for copy in copies), "run card copies differ")
    check("candidate_exists", tif.is_file(), f"missing {tif}")
    if tif.is_file():
        digest = sha256(tif)
        check("sha256_matches", digest == card["raster_sha256"], f"actual digest {digest}")
        with rasterio.open(tif) as src:
            arr = src.read(1)
            check("single_band", src.count == 1)
            check("float32", src.dtypes[0] == "float32")
            check("crs_matches_card", str(src.crs) == card["validator_output"]["crs"])
            check("shape_matches_card", list(src.shape) == card["validator_output"]["shape"])
            transform = [float(x) for x in tuple(src.transform)[:6]]
            check("transform_matches_card", transform == card["validator_output"]["transform"])
            check("nodata_matches_card", src.nodata is None)
            check("all_values_finite", bool(np.isfinite(arr).all()))
            check("all_values_in_0_1", bool(arr.min() >= 0 and arr.max() <= 1))
            check("positive_cell_count_matches_audit", int((arr > 0).sum()) == card["validator_output"]["positive_cells"])
    # Competition rules (page 967): "data outside the bounds is null or nan". Zeros outside are the convention of the
    # owner-scored files (IR-SASS3-27), so only NON-ZERO finite cells outside the footprint fail. Pending without data.
    # Added 2026-10-29 (IR-SASS3-42, 44): the format checks above do not test this rule, so it gates approval below.
    footprint = _footprint_mask() if tif.is_file() else None
    if tif.is_file() and footprint is not None:
        with rasterio.open(tif) as src:
            raw = src.read(1)
        outside = raw[~footprint]
        n_nonzero_out = int(np.count_nonzero(np.isfinite(outside) & (outside != 0)))
        check("outside_bounds_null_or_zero", n_nonzero_out == 0, f"{n_nonzero_out} non-zero cells outside the competition bounds")
    else:
        check("outside_bounds_null_or_zero", False, "PENDING_DATA: competition footprint absent; outside-bounds rule not checked")

    # Literal lattice rule measured on THIS file (<= 70% of its positive cells inside the footprint within 3 px of the
    # pinned 13GEMSDOE calibration lattice). Pending without the data.
    lattice_path = ROOT / ".cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
    if tif.is_file() and footprint is not None and lattice_path.is_file():
        with rasterio.open(tif) as src:
            cand_pos = src.read(1) > 0.0
        with rasterio.open(lattice_path) as lat_ds:
            lat = np.nan_to_num(lat_ds.read(1), nan=0.0) > 0.0
        inside = cand_pos & footprint
        n_inside = int(inside.sum())
        frac = float((ndi.distance_transform_edt(~lat)[inside] <= 3.0).mean()) if n_inside else 1.0
        check("literal_lattice_inside_footprint", frac <= 0.70, f"within-3px fraction inside footprint = {frac:.4f} (limit 0.70)")
    else:
        check("literal_lattice_inside_footprint", False, "PENDING_DATA: lattice or footprint absent; literal lattice rule not measured")

    zip_path = tif.with_suffix(".tif.zip")
    check("zip_exists", zip_path.is_file(), f"missing {zip_path}")
    if zip_path.is_file():
        check("zip_sha256_matches", sha256(zip_path) == card["zip_sha256"])
        try:
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                check("zip_contains_one_matching_tif", names == [tif.name] and hashlib.sha256(archive.read(tif.name)).hexdigest() == card["raster_sha256"])
        except (OSError, zipfile.BadZipFile, KeyError):
            check("zip_contains_one_matching_tif", False, "zip invalid or inner TIFF missing")
    uq = json.loads((ROOT / "evidence/uniqueness_audit_current_candidate_20261029.json").read_text())
    check("uniqueness_receipt_matches_candidate", uq["candidate_sha256"] == card["raster_sha256"])
    check("one_witness_metric_is_under_threshold", uq["result"]["one_witness_result_below_threshold"] is True)
    complete_unique = (
        uq["result"]["complete_registry_uniqueness_pass"] is True
        and card["registry_correlation_and_overlap"]["literal_uniqueness_gate"] == "CLEARED"
        and card["registry_correlation_and_overlap"]["pre_placement_rank_correlation"] is not None
    )
    check("complete_uniqueness_gate", complete_unique, "full registry / surface gate is not cleared")
    check("holdout_gate", card["holdout_dti"]["status"] == "PASS", "candidate HOLDOUT-DTI not run")
    check("canary_gate", card["leakage_canary"]["status"] == "PASS", "candidate leakage canary not run")
    check("candidate_not_promoted", card["verdict"] == "negative" and card["ok_to_submit"] is False)
    note_len = len(card["submission_note"])
    check("submission_note_length", 0 < note_len <= 140, f"note length {note_len}")
    check("archive_only_ui", all("NOT approved" in (ROOT / p).read_text() or "NOT OK to submit" in (ROOT / p).read_text() for p in ("README.md", "docs/index.html", "docs/executive-summary.html")), "UI must visibly block download as a submission")

    format_ok = all(checks[k] for k in (
        "run_card_copies_match", "candidate_exists", "sha256_matches", "single_band", "float32",
        "crs_matches_card", "shape_matches_card", "transform_matches_card", "nodata_matches_card",
        "all_values_finite", "all_values_in_0_1", "positive_cell_count_matches_audit",
        "zip_exists", "zip_sha256_matches", "zip_contains_one_matching_tif",
        "uniqueness_receipt_matches_candidate", "one_witness_metric_is_under_threshold",
        "submission_note_length", "archive_only_ui", "candidate_not_promoted"))
    competition_rules_ok = checks["outside_bounds_null_or_zero"] and checks["literal_lattice_inside_footprint"]
    approved = (format_ok and competition_rules_ok and checks["complete_uniqueness_gate"]
                and checks["holdout_gate"] and checks["canary_gate"])
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "ok": bool(approved and card.get("ok_to_submit") is True),
        "format_and_record_integrity": format_ok,
        "competition_rules_outside_bounds_and_literal_lattice": competition_rules_ok,
        "ok_to_download": False,
        "ok_to_download_for_analysis": bool(card.get("ok_to_download_for_analysis")),
        "ok_to_submit": approved and card.get("ok_to_submit") is True,
        "verdict": card["verdict"],
        "submission_name": card["submission_name"],
        "submission_note": card["submission_note"],
        "positive_pixels": card["validator_output"]["positive_cells"],
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "checks": checks,
        "problems": sorted(set(notes + failed)),
    }


# Backward-compatible test/import name; semantics are now fail-closed for the active card.
verify_all = verify


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-blocked", action="store_true", help="CI mode: success means format is intact and candidate remains fail-closed")
    args = parser.parse_args()
    result = verify()
    print(json.dumps(result, indent=2))
    if args.expect_blocked:
        return 0 if result["format_and_record_integrity"] and not result["ok_to_submit"] else 1
    return 0 if result["ok_to_submit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
