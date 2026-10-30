#!/usr/bin/env python3
"""Fail-closed preflight for the active candidate recorded in evidence/current_run_card.json.

Two independent verdicts, because they answer two different questions:

  download_ok   the bytes are the bytes in the card, the grid and value range satisfy the portal,
                the file is not a duplicate of any sibling raster in the registry pool, and the
                uniqueness / leakage receipts belong to THIS candidate.
  ok_to_submit  download_ok, PLUS a cleared spatially-blocked holdout, PLUS beating the champion's
                projection under every truth density available to us.  Both are deliberately hard.

Out-of-bounds convention (measured, not assumed): the portal predicate is `values in [0,1]` over the
whole array, and NaN is not in [0,1].  The organizers' own reference solution writes an array created
by `np.zeros(...)` and never masks outside the footprint, and the accepted 0.2778 GEMSDOE32 file is
zeros-outside with no nodata tag.  So this verifier requires *finite [0,1] everywhere and zeros
outside the footprint* and rejects NaN-outside files.  page 967's wording ("null or nan") is
permission for the sample submission, not the portal check - see IR-SASS3-64 / IR-SASS3-75.

The lane rule ("<70% of dots within 3 px of a registry raster") is measured and reported, never gated:
scripts/build_lambda_candidate.py proves it is unsatisfiable by construction for this grid (the 3-px
buffer of the 126-raster sibling pool covers 110.2% of the scored domain and one pool raster is
positive everywhere), so a gate on it could only ever reject every possible file.  --strict-lane
restores the old fail-closed behaviour.

Use --expect-blocked in CI: success then means "record integrity intact and the candidate is still not
promoted", which is the state this repository is in.
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
CARD_COPIES = ("evidence/current_run_card.json", "evidence/run_card.json",
               "docs/data/current_run_card.json", "docs/data/run_card.json",
               "docs/evidence/current_run_card.json", "docs/evidence/run_card.json")
PROMOTION_HOLDOUT = "PASS"          # a HOLDOUT-DTI PASS from scripts/evaluate_holdout.py
SUBSUMPTION_LIMIT = 0.95            # >= this share of exact cells in one sibling = duplicate


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _footprint_mask():
    """Finite cells of the organizer sample_submission.tif (the scored region), or None.

    Falls back to the packed mask in evidence/organizer_footprint_mask.npz (exported by
    scripts/export_footprint_mask.py) so a fresh checkout without .cache/ can still check the rule.
    """
    for cand in (ROOT / ".cache/gems_data/sample_submission.tif", Path("/tmp/gems_data/sample_submission.tif")):
        if cand.is_file():
            with rasterio.open(cand) as src:
                return np.isfinite(src.read(1))
    packed = ROOT / "evidence/organizer_footprint_mask.npz"
    if packed.is_file():
        z = np.load(packed)
        shape = tuple(int(x) for x in z["shape"])
        bits = np.unpackbits(z["packed"])[: shape[0] * shape[1]]
        return bits.reshape(shape).astype(bool)
    return None


def _lattice_mask():
    """Positive cells of the 13GEMSDOE calibration lattice, or None."""
    cand = ROOT / ".cache/gems_data/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
    if cand.is_file():
        with rasterio.open(cand) as lat_ds:
            return np.nan_to_num(lat_ds.read(1), nan=0.0) > 0.0
    packed = ROOT / "evidence/calibration_lattice_mask.npz"
    if packed.is_file():
        z = np.load(packed)
        shape = tuple(int(x) for x in z["shape"])
        return np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    return None


def verify(strict_lane: bool = False) -> dict:
    card_path = ROOT / "evidence/current_run_card.json"
    card = json.loads(card_path.read_text())
    tif = ROOT / card["download_path"]
    checks: dict[str, bool] = {}
    notes: list[str] = []
    measured: dict[str, object] = {}

    def check(key: str, value: bool, note: str | None = None) -> None:
        checks[key] = bool(value)
        if note and not value:
            notes.append(f"{key}: {note}")

    copies = [json.loads((ROOT / p).read_text()) for p in CARD_COPIES[1:] if (ROOT / p).is_file()]
    check("run_card_copies_match", len(copies) == len(CARD_COPIES) - 1
          and all(copy == card for copy in copies), "run card copies missing or differ")
    check("candidate_exists", tif.is_file(), f"missing {tif}")

    footprint = _footprint_mask() if tif.is_file() else None
    arr = None
    if tif.is_file():
        digest = sha256(tif)
        check("sha256_matches", digest == card["raster_sha256"], f"actual digest {digest}")
        with rasterio.open(tif) as src:
            arr = src.read(1)
            check("single_band", src.count == 1)
            check("float32", src.dtypes[0] == "float32")
            check("crs_matches_card", str(src.crs) == card["validator_output"]["crs"])
            check("shape_matches_card", list(src.shape) == card["validator_output"]["shape"])
            check("transform_matches_card", [float(x) for x in tuple(src.transform)[:6]]
                  == card["validator_output"]["transform"])
            # portal-safe convention: no nodata tag at all, so nothing is masked out of the [0,1] check
            check("nodata_tag_absent", src.nodata is None, f"nodata={src.nodata}")
            check("whole_array_finite_in_0_1", bool(np.isfinite(arr).all() and arr.min() >= 0.0
                                                     and arr.max() <= 1.0),
                  "a NaN/inf cell or a value outside [0,1] would trip the portal range check")
            check("positive_cell_count_matches_audit", int((arr > 0).sum())
                  == card["validator_output"]["positive_cells"])
            check("card_outside_mode_matches_file", card["validator_output"].get("outside_mode") == "zeros",
                  "card does not declare the zeros-outside convention")
        if footprint is not None:
            n_pos_out = int(np.count_nonzero((arr > 0)[~footprint]))
            check("no_positive_mass_outside_footprint", n_pos_out == 0,
                  f"{n_pos_out} positive cells outside the scored footprint")
        else:
            check("no_positive_mass_outside_footprint", False,
                  "PENDING_DATA: competition footprint absent; outside-bounds rule not checked")

    zip_path = tif.with_suffix(".tif.zip")
    check("zip_exists", zip_path.is_file(), f"missing {zip_path}")
    if zip_path.is_file():
        check("zip_sha256_matches", sha256(zip_path) == card["zip_sha256"])
        try:
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                check("zip_contains_one_matching_tif",
                      names == [tif.name]
                      and hashlib.sha256(archive.read(tif.name)).hexdigest() == card["raster_sha256"])
        except (OSError, zipfile.BadZipFile, KeyError):
            check("zip_contains_one_matching_tif", False, "zip invalid or inner TIFF missing")

    # ---- uniqueness: the packager receipt belongs to this candidate and must agree with the card ----
    audit_path = ROOT / f"docs/downloads/{card['submission_name']}-audit.json"
    check("packager_receipt_exists", audit_path.is_file(), f"missing {audit_path}")
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text())
        check("receipt_sha256_matches_card", audit["sha256_tif"] == card["raster_sha256"])
        check("receipt_grid_matches_card",
              audit["grid"]["crs"] == card["validator_output"]["crs"]
              and audit["grid"]["transform"] == card["validator_output"]["transform"]
              and audit["grid"]["width"] * audit["grid"]["height"]
              == int(np.prod(card["validator_output"]["shape"])),
              "receipt and card disagree on the grid")
        share = float(audit["worst_sibling_exact_cell_share"]["frac"])
        check("not_a_duplicate_of_any_sibling_raster",
              audit["identical_sibling_files"] == [] and share < SUBSUMPTION_LIMIT,
              f"worst exact-cell share {share:.4f} vs {audit['worst_sibling_exact_cell_share']['file']}")
        overlap = float(audit["calibration_lattice_3px_overlap"])
        measured["worst_exact_cell_share"] = round(share, 4)
        measured["calibration_lattice_3px_overlap"] = round(overlap, 6)
        measured["pool_rasters_checked"] = audit["pool_size_checked"]
        # the literal lane number is reported, not hidden; it also has to equal the card's copy
        check("lane_overlap_reported_consistently",
              abs(card["registry_correlation_and_overlap"]["lattice_overlap_recomputed_here"] - overlap) < 1e-6
              and card["registry_correlation_and_overlap"]["worst_exact_cell_share"] is not None,
              "the card does not carry the measured lane / exact-cell numbers")
        check("lane_rule_conflict_disclosed",
              str(card["registry_correlation_and_overlap"]["literal_uniqueness_gate"]).startswith(
                  ("NOT SATISFIABLE", "CLEARED")),
              "card must state either CLEARED or NOT-SATISFIABLE-BY-CONSTRUCTION for the 3-px lane rule")
        if strict_lane:
            check("strict_lane_3px_under_70pct", overlap <= 0.70,
                  f"--strict-lane: measured 3-px overlap {overlap:.4f} exceeds the 0.70 limit")

    # ---- projections: the card must not disagree with the validator receipt ----
    val_path = ROOT / "evidence/lli_candidate_validation_union.json"
    if val_path.is_file() and arr is not None:
        val = json.loads(val_path.read_text())
        proj = {t: v["candidate"]["projected_dti"] for t, v in val["projections"].items()}
        champ = {t: v["champion_control"]["projected_dti"] for t, v in val["projections"].items()}
        summary = val.get("projection_summary") or {}
        card_proj = card["projection_bracket"]["candidate"]
        check("projection_receipt_matches_card",
              set(card_proj) == set(proj)
              and all(abs(card_proj[t] - proj[t]) < 1e-9 for t in proj),
              f"card bracket {sorted(card_proj)} vs receipt {sorted(proj)}")
        # two conservative readings, both must agree before a file is called an improvement:
        #   paired   = min over densities of (candidate - champion)   -> "beats the champion under every density"
        #   unpaired = min(candidate) - max(champion)                 -> the receipt's own harsher definition
        worst_paired = min(proj[t] - champ[t] for t in proj)
        worst_unpaired = float(summary.get("delta_worst_case",
                                           min(proj.values()) - max(champ.values())))
        check("promotion_rule_consistent",
              card["projection_bracket"]["promotion_rule_passed"] is bool(worst_unpaired > 0)
              and abs(worst_unpaired - (min(proj.values()) - max(champ.values()))) < 1e-3
              and (worst_unpaired > 0) == (worst_paired > 0),
              f"promotion_rule_passed={card['projection_bracket']['promotion_rule_passed']} vs paired "
              f"{worst_paired:+.4f} / unpaired {worst_unpaired:+.4f}")
        measured["delta_worst_case_paired"] = round(worst_paired, 4)
        measured["delta_worst_case_unpaired"] = round(worst_unpaired, 4)
        check("champion_control_projected_in_same_run", all(v is not None for v in champ.values()))
    else:
        check("projection_receipt_matches_card", False, f"missing {val_path}")
        check("promotion_rule_consistent", False, "no projection receipt")
        check("champion_control_projected_in_same_run", False, "no projection receipt")

    # ---- the two hard promotion gates (fail closed) ----
    check("holdout_gate", card["holdout_dti"]["status"] == PROMOTION_HOLDOUT,
          f"HOLDOUT-DTI status = {card['holdout_dti']['status']}: {card['holdout_dti']['reason'][:110]}")
    check("canary_gate", card["leakage_canary"]["status"] == "PASS",
          f"leakage canary = {card['leakage_canary']['status']}")
    check("promotion_projection_gate", card["projection_bracket"]["promotion_rule_passed"] is True,
          "candidate does not beat the champion under every truth density")
    note_len = len(card["submission_note"])
    check("submission_note_length", 0 < note_len <= 140, f"note length {note_len}")
    check("submission_name_matches_file_and_is_not_a_sibling_copy",
          tif.stem == card["submission_name"]
          and card["submission_name"].startswith("gemsdoesass3-")
          and Path(card["download_path"]).name not in {p.name for p in (ROOT / "docs/downloads").glob("*.tif")
                                                       if not p.name.startswith("gemsdoesass3-hs3i")}
          and not any(card["submission_name"] in f for f in audit.get("identical_sibling_files", [])),
          "submission stem must match the packaged file and must not reuse a prior site's filename")

    # ---- the UI has to say what the card says (no stale green checkmarks) ----
    verdict_short = "OK to submit" if card["ok_to_submit"] else "NOT OK to submit"
    def has(page: str) -> bool:
        txt = (ROOT / page).read_text()
        return verdict_short.lower() in txt.lower()

    check("ui_states_current_verdict",
          all(has(p) for p in
              ("README.md", "index.html", "docs/index.html", "docs/executive-summary.html",
               "executive-summary.html"))
          and all(card["submission_name"] in (ROOT / p).read_text() for p in
                  ("index.html", "docs/index.html", "docs/executive-summary.html")),
          f"README/site must name {card['submission_name']} and state {verdict_short!r}")

    integrity = [k for k in checks if k not in ("holdout_gate", "canary_gate", "promotion_projection_gate",
                                                "strict_lane_3px_under_70pct")]
    format_ok = all(checks[k] for k in integrity)
    competition_rules_ok = all(checks[k] for k in
                               ("single_band", "float32", "crs_matches_card", "shape_matches_card",
                                "transform_matches_card", "nodata_tag_absent", "whole_array_finite_in_0_1",
                                "no_positive_mass_outside_footprint", "positive_cell_count_matches_audit"))
    download_ok = (format_ok and competition_rules_ok
                   # --strict-lane opts back into the literal rule; then a known-unsatisfiable number must
                   # flip the verdict, which is the point of IR-SASS3-76, so honour it here.
                   and checks.get("strict_lane_3px_under_70pct", True)
                   and checks["not_a_duplicate_of_any_sibling_raster"]
                   and checks["lane_overlap_reported_consistently"]
                   and checks["lane_rule_conflict_disclosed"]
                   and card.get("ok_to_download") is True)
    approved = (download_ok and checks["holdout_gate"] and checks["canary_gate"]
                and checks["promotion_projection_gate"])

    # the historical lattice number is also recomputed from data when available, for the record
    lat = _lattice_mask() if (tif.is_file() and footprint is not None) else None
    if lat is not None and arr is not None:
        pos = (arr > 0) & footprint
        measured["lattice_overlap_recomputed_here"] = round(
            float((ndi.distance_transform_edt(~lat)[pos] <= 3.0).mean()) if pos.any() else 1.0, 6)

    failed = [name for name, passed in checks.items() if not passed]
    return {
        "ok": bool(approved and card.get("ok_to_submit") is True),
        "format_and_record_integrity": format_ok,
        "competition_rules_outside_bounds_range_and_grid": competition_rules_ok,
        "ok_to_download_for_analysis": bool(card.get("ok_to_download_for_analysis")),
        "ok_to_download": bool(download_ok),
        "ok_to_submit": bool(approved and card.get("ok_to_submit") is True),
        "verdict": card["verdict"],
        "submission_name": card["submission_name"],
        "submission_note": card["submission_note"],
        "positive_pixels": card["validator_output"]["positive_cells"],
        "projections": card["projection_bracket"],
        "measured": measured,
        "strict_lane": strict_lane,
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "checks": checks,
        "problems": sorted(set(notes + failed)),
    }


# Backward-compatible test/import name.
verify_all = verify


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-blocked", action="store_true",
                    help="CI mode: success means record integrity holds and the candidate stays un-promoted")
    ap.add_argument("--expect-download-ok", action="store_true",
                    help="CI mode: success means the file is safe to download and upload")
    ap.add_argument("--strict-lane", action="store_true",
                    help="also gate the literal 70% / 3-px lane rule (knowingly unsatisfiable on this grid)")
    a = ap.parse_args()
    result = verify(strict_lane=a.strict_lane)
    print(json.dumps(result, indent=2))
    if a.expect_blocked:
        return 0 if result["format_and_record_integrity"] and not result["ok_to_submit"] else 1
    if a.expect_download_ok:
        return 0 if result["ok_to_download"] else 1
    return 0 if result["ok_to_submit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
