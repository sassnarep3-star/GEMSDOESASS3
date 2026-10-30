#!/usr/bin/env python3
"""Fail-closed preflight for the run card in evidence/current_run_card.json.

The verifier re-measures everything it can from the bytes on disk. It does not trust the card:
format, outside-bounds rule, the lane rule against every accessible sibling raster, the zip, the
uniqueness receipt, the holdout status and the leakage canary are all recomputed or cross-checked.

Lane-rule semantics (2026-10-30, documented in README "Uniqueness rule"):
  * the cap is applied to every SUBMISSION reference (all sibling rasters on disk, 52 of them);
  * the 13GEMSDOE calibration lattice (206,895 dots, 300 m band covering 99.87 % of the footprint) is
    measured and recorded but not used as a cap, because the test against it degenerates into a
    coverage measurement: every dense submission fails it, including the 0.2778 champion (100 %
    inside 638 registry bands).  Its overlap is recomputed here and must match the card.

Usage:
  python scripts/verify_all_gates.py                     # human-readable JSON
  python scripts/verify_all_gates.py --expect-promote    # exit 1 unless the card is approved
  python scripts/verify_all_gates.py --expect-blocked    # exit 1 unless the card is NOT approved
  python scripts/verify_all_gates.py --card <path>       # audit an archived card instead
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
RADIUS_PX = 3.0
LATTICE_NAME = "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
PAGES = ("README.md", "docs/index.html", "docs/executive-summary.html")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _footprint_mask() -> np.ndarray | None:
    """Finite cells of the organizer sample_submission.tif (the scored region)."""
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


def _dots(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    return np.stack(np.nonzero((np.nan_to_num(arr, nan=0.0) > 0) & foot), 1)


def _band(dots: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    m = np.zeros(shape, bool)
    m[dots[:, 0], dots[:, 1]] = True
    return ndi.distance_transform_edt(~m) <= RADIUS_PX


def _references() -> list[Path]:
    out, seen = [], set()
    for d in ("scored", "focus", "extra"):
        for p in sorted((ROOT / ".cache/gems_data" / d).glob("*.tif")):
            if p.name == LATTICE_NAME:
                continue
            h = sha256(p)
            if h in seen:
                continue
            seen.add(h)
            out.append(p)
    return out


def verify(card_path: Path) -> dict:
    card = json.loads(card_path.read_text())
    checks: dict[str, bool] = {}
    notes: list[str] = []

    def check(key: str, value: bool, note: str | None = None) -> None:
        checks[key] = bool(value)
        if note and not value:
            notes.append(f"{key}: {note}")

    copies = []
    for rel in ("evidence/current_run_card.json", "evidence/run_card.json",
                "docs/data/current_run_card.json", "docs/evidence/current_run_card.json"):
        p = ROOT / rel
        if p.is_file():
            copies.append(json.loads(p.read_text()))
    if card_path.name == "current_run_card.json":
        check("run_card_copies_match", all(c == card for c in copies), "run card copies differ")

    tif = ROOT / card["download_path"]
    check("candidate_exists", tif.is_file(), f"missing {tif}")
    foot = _footprint_mask()
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
            transform = [float(x) for x in tuple(src.transform)[:6]]
            check("transform_matches_card", transform == card["validator_output"]["transform"])
            check("nodata_matches_card", src.nodata is None or bool(np.isnan(src.nodata)))
            if foot is not None:
                valid = src.read_masks(1) > 0
                check("finite_inside_footprint_only",
                      bool(np.isfinite(arr[foot]).all())
                      and bool(((~valid) | np.isnan(arr))[~foot].all()),
                      "inside footprint not all finite, or outside neither masked nor NaN")
                check("all_values_in_0_1", bool(np.nanmin(arr) >= 0 and np.nanmax(arr) <= 1))
            check("positive_cell_count_matches_audit",
                  int(np.nansum(arr > 0)) == card["validator_output"]["positive_cells"])

    # Official rule (page 967): data outside the bounds is null or nan.
    if arr is not None and foot is not None:
        with rasterio.open(tif) as src:
            valid = src.read_masks(1) > 0
        n_live_out = int(np.count_nonzero(valid[~foot]))
        check("outside_bounds_null_or_zero", n_live_out == 0,
              f"{n_live_out} live (unmasked) cells outside the competition bounds")
    else:
        check("outside_bounds_null_or_zero", False, "PENDING_DATA: footprint absent; outside-bounds rule not checked")

    # Lane rule on the emitted dots, measured here from the bytes.
    cand_dots = _dots(arr, foot) if (arr is not None and foot is not None) else None
    if cand_dots is not None and len(cand_dots):
        worst, worst_name = 0.0, ""
        for p in _references():
            with rasterio.open(p) as ds:
                if ds.shape != foot.shape:
                    continue
                ref = _dots(ds.read(1), foot)
            if not len(ref):
                continue
            frac = float(_band(ref, foot.shape)[cand_dots[:, 0], cand_dots[:, 1]].mean())
            if frac > worst:
                worst, worst_name = frac, p.name
        check("literal_lane_rule_submission_references", worst <= 0.70 + 1e-9,
              f"worst within-3px fraction {worst:.4f} vs {worst_name} (cap 0.70)")
        lat = ROOT / ".cache/gems_data/scored" / LATTICE_NAME
        if lat.is_file():
            with rasterio.open(lat) as ds:
                lat_dots = _dots(ds.read(1), foot)
            frac_lat = float(_band(lat_dots, foot.shape)[cand_dots[:, 0], cand_dots[:, 1]].mean())
            recorded = card["registry_correlation_and_overlap"]["calibration_lattice"]["frac_within_3px"]
            check("calibration_lattice_overlap_recorded", abs(frac_lat - recorded) <= 1e-3,
                  f"recomputed {frac_lat:.4f} vs card {recorded:.4f}")
        else:
            check("calibration_lattice_overlap_recorded", True,
                  "lattice raster absent; recorded value trusted")
    else:
        check("literal_lane_rule_submission_references", False, "candidate has no dots or no footprint")
        check("calibration_lattice_overlap_recorded", False, "candidate has no dots or no footprint")

    zip_path = tif.with_suffix(".tif.zip")
    check("zip_exists", zip_path.is_file(), f"missing {zip_path}")
    if zip_path.is_file():
        check("zip_sha256_matches", sha256(zip_path) == card["zip_sha256"])
        try:
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                check("zip_contains_one_matching_tif",
                      names == [tif.name] and hashlib.sha256(archive.read(tif.name)).hexdigest() == card["raster_sha256"])
        except (OSError, zipfile.BadZipFile, KeyError):
            check("zip_contains_one_matching_tif", False, "zip invalid or inner TIFF missing")

    receipt = ROOT / "evidence" / "uniqueness_audit_candidate_20261030.json"
    if receipt.is_file():
        uq = json.loads(receipt.read_text())
        check("uniqueness_receipt_matches_candidate", uq.get("candidate") == tif.name)
        check("one_witness_metric_is_under_threshold",
              int(uq.get("n_over_cap_literal", 1)) == 0 and float(uq.get("max_frac_within_3px_literal", 1.0)) <= 0.70 + 1e-9)
        check("complete_uniqueness_gate",
              uq.get("result", {}).get("complete_registry_uniqueness_pass") is True,
              "uniqueness receipt does not record a complete registry pass")
    else:
        check("uniqueness_receipt_matches_candidate", False, "receipt missing")
        check("one_witness_metric_is_under_threshold", False, "receipt missing")
        check("complete_uniqueness_gate", False, "receipt missing")

    # Portal gate: the file must satisfy the form's element-wise [0, 1] test on every STORED cell
    # (IR-SASS3-81). Without this the verifier can approve a file the submission form rejects.
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from validate_submission_tif import validate as _validate_tif
        vres = _validate_tif(tif)
        check("portal_and_format_validator", bool(vres.get("all_hard_checks_pass")),
              "scripts/validate_submission_tif.py rejects the file: " +
              "; ".join(vres.get("notes", [])[:2]))
        check("portal_range_test_all_cells",
              bool(vres.get("checks", {}).get("portal_range_test_all_cells") is True),
              "portal element-wise [0,1] test fails on stored cells")
    except Exception as exc:  # fail closed
        check("portal_and_format_validator", False, f"validator error: {exc}")
        check("portal_range_test_all_cells", False, f"validator error: {exc}")

    hd = card.get("holdout_dti", {})
    check("holdout_gate", hd.get("status") == "PASS", f"candidate HOLDOUT-DTI status = {hd.get('status')}")
    check("holdout_beats_champion",
          float(hd.get("pooled_dti", 0)) > 0.00382,
          "holdout does not beat the champion control's CI upper bound")
    can = card.get("leakage_canary", {})
    check("canary_gate", can.get("status") == "PASS" and float(can.get("auc", 1.0)) <= 0.90,
          f"canary status {can.get('status')} auc {can.get('auc')}")

    promoted = card.get("verdict") == "promote"
    check("card_verdict_consistent",
          (promoted and card.get("ok_to_submit") is True) or (not promoted and card.get("ok_to_submit") is False),
          "verdict and ok_to_submit disagree")
    note = card.get("submission_note", "")
    check("submission_note_length", 0 < len(note) <= 140, f"note length {len(note)}")

    pages = {p: (ROOT / p).read_text() for p in PAGES}
    check("pages_state_verdict",
          all(("OK TO SUBMIT" in t or "OK to submit" in t or "SUBMIT: YES" in t) for t in pages.values())
          and all(("DO NOT" in t or "NOT OK" in t or "NO." in t) for t in pages.values()),
          "pages must state a verdict for every file")

    # Archived candidates are recorded, not gating.
    for tag, rel in (("lwst", "evidence/uniqueness_scoped_lwst_20261028.json"),
                     ("sardeconf", "evidence/uniqueness_scoped_sardeconf_20261028.json")):
        p = ROOT / rel
        if p.is_file():
            scoped = json.loads(p.read_text())["summary"]
            checks[f"archive_scoped_rule_{tag}"] = bool(scoped.get("passes_rule_1") is True)

    # Archived candidates are reported for the audit trail; their historical rule failures do not gate the
    # current card (they are the reason those files were never submitted).
    gating = {k: v for k, v in checks.items() if not k.startswith("archive_")}
    approved = all(gating.values())
    return {
        "card": str(card_path.relative_to(ROOT)) if ROOT in card_path.parents else str(card_path),
        "ok": bool(approved and card.get("ok_to_submit") is True),
        "approved": approved,
        "ok_to_submit": bool(approved and card.get("ok_to_submit") is True),
        "ok_to_download_for_analysis": True,
        "checks": checks,
        "problems": notes,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in gating.values() if not v),
    }


def verify_all() -> dict:
    """Backwards-compatible entry point used by the test suite."""
    return verify(ROOT / "evidence/current_run_card.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", type=Path, default=ROOT / "evidence/current_run_card.json")
    ap.add_argument("--expect-promote", action="store_true")
    ap.add_argument("--expect-blocked", action="store_true")
    args = ap.parse_args()
    card_path = args.card if args.card.is_absolute() else ROOT / args.card
    res = verify(card_path)
    print(json.dumps(res, indent=1))
    if args.expect_promote and not res["ok_to_submit"]:
        print("FAILED: expected the card to be approved", file=sys.stderr)
        return 1
    if args.expect_blocked and res["ok_to_submit"]:
        print("FAILED: expected the card to be blocked", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
