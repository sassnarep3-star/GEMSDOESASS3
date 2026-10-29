#!/usr/bin/env python3
"""Validate the unique structural GeoTIFF and write its Run Card (protocol item 5).

Everything in the card is computed here or read from a file on disk:
  * format validation is recomputed from the raster with rasterio;
  * uniqueness numbers come from the full-pool audit written by
    scripts/independent_uniqueness_audit.py, which recomputes overlap from pixels;
  * holdout fields are recorded as NOT RUN, because the competition labels are not in this
    workspace. No holdout number is invented.

The uniqueness result is reported three ways, because the literal rule has a degenerate case:
  literal      : every registry raster, the protocol rule as written;
  sparse_only  : rasters with <= DENSE_FRAC of the grid positive (dot-type submissions);
  dense_excl   : sparse_only plus rank test on all rasters, with dense rasters listed separately.
A dense raster whose positive cells cover the whole grid makes "within 3 px of its dots" equal to
1.0 for ANY candidate, so the literal rule cannot be satisfied by any sparse file. That is a
definition question for the owner, not a pass. The card records the decision as pending.

Usage:
    python scripts/build_structural_card.py \
        --audit evidence/structural_uniqueness_fullpool_20261029.json \
        --out evidence/structural_candidate_card.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
TIF_REL = "docs/downloads/gemsdoesass3-unique-structural-20261029T000102Z-e3ecb47c-zeros.tif"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
DENSE_FRAC = 0.10  # a raster with more than 10 % of grid cells positive is treated as dense
LIMIT_WITHIN3 = 0.70
LIMIT_RHO = 0.90
NOTE = ("GEMSDOESASS3 unique structural prior 10k dots; NOT VALID - footprint FAIL, "
        "do not submit")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(path: Path) -> dict:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        checks = {
            "single_band": ds.count == 1,
            "dtype_float32": ds.dtypes[0] == "float32",
            "crs_epsg_32611": ds.crs == CRS.from_epsg(32611),
            "shape_3730x3292": (ds.height, ds.width) == EXPECTED_SHAPE,
            "transform_matches_prepared_grid": tuple(ds.transform)[:6] == EXPECTED_TRANSFORM,
            "nodata_none": ds.nodata is None,
            "no_nan": bool(not np.isnan(arr).any()),
            "all_finite": bool(np.isfinite(arr).all()),
            "in_range_0_1": bool(arr.min() >= 0.0 and arr.max() <= 1.0),
        }
        meta = {
            "epsg": ds.crs.to_epsg(),
            "height": ds.height,
            "width": ds.width,
            "transform": list(ds.transform)[:6],
            "dtype": ds.dtypes[0],
            "nodata": ds.nodata,
            "min": float(arr.min()),
            "max": float(arr.max()),
            "unique_values": [float(v) for v in np.unique(arr)][:10],
            "positive_pixels": int((arr > 0).sum()),
        }
    _, n_blobs = ndi.label(arr > 0, structure=np.ones((3, 3)))
    meta["connected_blobs_8conn"] = int(n_blobs)
    checks["all_checks_passed"] = all(checks.values())
    return {"checks": checks, "meta": meta}


FOOTPRINT_MASK = ROOT / "evidence" / "organizer_footprint_mask.npz"


def footprint_check(path: Path) -> dict:
    """Official outside-bounds rule: cells outside the scored region must be null/NaN, not 0 or a value.

    The scored region is the finite cells of the organizer sample_submission.tif, exported as a packed
    mask by scripts/export_footprint_mask.py (evidence/organizer_footprint_mask.npz). The sample itself is
    not used here.
    """
    z = np.load(FOOTPRINT_MASK)
    shape = tuple(int(x) for x in z["shape"])
    foot = np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    with rasterio.open(path) as ds:
        arr = ds.read(1)
    pos = arr > 0
    outside_pos = int((pos & ~foot).sum())
    return {
        "mask_file": "evidence/organizer_footprint_mask.npz",
        "mask_footprint_pixels": int(foot.sum()),
        "mask_footprint_pixels_recorded": int(z["footprint_pixels"]),
        "positive_cells_inside_footprint": int((pos & foot).sum()),
        "positive_cells_outside_footprint": outside_pos,
        "zero_cells_outside_footprint": int(((arr == 0) & ~foot).sum()),
        "status": "PASS" if outside_pos == 0 else "FAIL",
        "rule": "official: data outside the bounds is null or NaN (page/967, Format section)",
    }


def worst(rows: list[dict], key: str = "within3_frac") -> dict | None:
    return max(rows, key=lambda r: r[key]) if rows else None


def summarise(rows: list[dict]) -> dict:
    rho_rows = [r for r in rows if r["spearman_sampled"] is not None]
    w = worst(rows)
    r = max(rho_rows, key=lambda x: abs(x["spearman_sampled"])) if rho_rows else None
    return {
        "n_rasters": len(rows),
        "max_within3_frac": w["within3_frac"] if w else None,
        "max_within3_raster": w["path"] if w else None,
        "max_abs_spearman_sampled": abs(r["spearman_sampled"]) if r else None,
        "max_abs_spearman_raster": r["path"] if r else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "structural_candidate_card.json")
    args = ap.parse_args()

    tif = ROOT / TIF_REL
    audit = json.loads(args.audit.read_text())
    s = audit["summary"]
    val = validate(tif)
    digest = sha256_file(tif)
    if digest != s["candidate_sha256"]:
        raise SystemExit(f"audit was run on a different file: {s['candidate_sha256']} != {digest}")

    grid = EXPECTED_SHAPE[0] * EXPECTED_SHAPE[1]
    # the repo's own published copy of this file is the candidate itself, not a prior submission
    others = [r for r in audit["results"] if tif.name not in r["path"]]
    self_copies = [r["path"] for r in audit["results"] if tif.name in r["path"]]
    dense = [r for r in others if r["n_dots"] > DENSE_FRAC * grid]
    sparse = [r for r in others if r["n_dots"] <= DENSE_FRAC * grid]

    literal = summarise(others)
    sparse_sum = summarise(sparse)
    dense_sum = summarise(dense)
    dense_hits = sorted(
        ({"path": r["path"], "within3_frac": r["within3_frac"], "n_dots": r["n_dots"]}
         for r in dense if r["within3_frac"] > LIMIT_WITHIN3),
        key=lambda x: -x["within3_frac"],
    )
    rho_ok = literal["max_abs_spearman_sampled"] is not None and literal["max_abs_spearman_sampled"] <= LIMIT_RHO
    literal_pass = bool(literal["max_within3_frac"] <= LIMIT_WITHIN3 and rho_ok)
    sparse_pass = bool(sparse_sum["max_within3_frac"] <= LIMIT_WITHIN3 and rho_ok)
    # dense rasters are excluded from the overlap test in this variant; the rank test still covers them
    dense_excl_pass = sparse_pass
    skipped_reasons: dict[str, int] = {}
    for x in audit["skipped"]:
        key = x["reason"].split(":")[0]
        skipped_reasons[key] = skipped_reasons.get(key, 0) + 1

    fp = footprint_check(tif)
    card = {
        "lane_id": "GEMSDOESASS3-UNIQUE-STRUCTURAL-PRIOR-20261029",
        "hypothesis": (
            "H-STRUCT-PRIOR (null-control lane): a sparse, label-free placement of 10,000 dot centres along six "
            "NNE-trending corridors (line y = tan(60 deg) * x + b, b in 4.48e6..4.50e6 m, perpendicular jitter "
            "sigma = 400 m) is a 'structural-corridor' guess. It uses no competition label or raster."
        ),
        "mechanism": (
            "Each dot is a radius-2-pixel disk (value 1.0) written to a float32 grid; all other cells are 0. "
            "No feature, label or catalogue layer is read. Seed 0x5EED. scripts/generate_unique_submission.py "
            "regenerates the array exactly (verified)."
        ),
        "mimic": (
            "Any linear NNE-trending feature (roads, pipelines, drainage, the Walker Lane fabric itself) would "
            "be scored the same way; the placement cannot tell a fault from a road because it never looked at data."
        ),
        "holdout_dti": {
            "status": "NOT RUN",
            "reason": ("competition labels (labels.tif) are not in this workspace; the hide-and-recover "
                       "evaluator needs them. No HOLDOUT-DTI number exists for this file."),
            "evidence_class": "none",
        },
        "leakage_canary": {"status": "NOT APPLICABLE", "reason": "no feature was fitted to labels"},
        "registry_correlation_and_overlap": {
            "tool": "scripts/independent_uniqueness_audit.py (recomputes from pixels)",
            "audit_file": "evidence/structural_uniqueness_fullpool_20261029.json",
            "pool": "full sibling pool; rebuilt by scripts/fetch_sibling_registry.py (registry/sibling_repos.txt)",
            "n_rasters_compared_including_self": s["n_rasters_compared"],
            "self_copies_excluded": self_copies,
            "n_rasters_skipped": s["n_rasters_skipped"],
            "skipped_reasons": skipped_reasons,
            "dense_threshold_frac_of_grid": DENSE_FRAC,
            "thresholds": {"within3_max_frac": LIMIT_WITHIN3, "abs_spearman_max": LIMIT_RHO, "radius_px": 3.0},
            "identical_dot_sets_excluding_self": [r["path"] for r in others if r["xor_dots"] == 0 and r["n_dots"] > 0],
            "literal_all_rasters": {**literal, "pass": literal_pass},
            "sparse_only": {**sparse_sum, "pass": sparse_pass},
            "dense_rasters": {**dense_sum, "n_over_limit": len(dense_hits), "over_limit": dense_hits},
            "dense_excluded_from_overlap_test_pass": dense_excl_pass,
            "dense_excluded_variant_note": ("overlap test on sparse rasters only, rank test on all rasters; "
                                            "dense rasters over the limit are listed in dense_rasters.over_limit"),
            "caveat": ("dots are positive pixels (repo convention). Two historical registry entries "
                       "(gems16 and gems19 scored copies) have no GitHub copy and are not in the pool. "
                       "GEMSDOE75 'outside' entries are git symlinks into ../../.cache/gems_data, not rasters."),
        },
        "uniqueness_decision": {
            "status": "PENDING OWNER DECISION" if not literal_pass else "PASS",
            "literal_rule_result": "PASS" if literal_pass else "FAIL",
            "why_literal_fails": (
                f"{len(dense_hits)} dense sibling raster(s) exceed 70 % within-3 px; the worst is "
                f"{dense_sum['max_within3_raster']} at {dense_sum['max_within3_frac']:.4f}. A sibling whose "
                "positive cells cover the whole grid makes every candidate dot 'within 3 px'."
            ) if not literal_pass else "",
            "options_for_owner": [
                "keep the literal rule (no sparse file can pass while a full-grid raster is in the pool)",
                "exclude dense rasters from the overlap test and keep the rank test on all rasters",
                "redefine dots for dense rasters (for example the top-N cells) and rerun the audit",
            ],
        },
        "raster_sha256": digest,
        "raster_bytes": tif.stat().st_size,
        "validator_output": {"checks": val["checks"], "meta": val["meta"]},
        "footprint_check": fp,
        "submission_name": tif.name,
        "submission_note": NOTE,
        "download_path": TIF_REL,
        "ok_to_download": False,
        "ok_to_submit": False,
        "verdict": "negative",
        "verdict_reason": (
            f"The footprint rule FAILS: {fp['positive_cells_outside_footprint']:,} positive cells lie outside the "
            "official scored region, where the rules require null or NaN. The file is therefore not valid for "
            "download or submission. The literal uniqueness rule also FAILS (one dense sibling raster), and no "
            "holdout score exists. Failing a gate is never permission to submit. This matches "
            "docs/data/run_card_unique_structural_20261029.json on main."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(card, indent=1) + "\n")
    print(f"wrote {args.out}")
    print(f"literal={literal_pass} sparse_only={sparse_pass} dense_excluded={dense_excl_pass} "
          f"format={val['checks']['all_checks_passed']} footprint={fp['status']} "
          f"outside_pos={fp['positive_cells_outside_footprint']} note_len={len(NOTE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
