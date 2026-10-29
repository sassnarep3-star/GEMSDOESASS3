#!/usr/bin/env python3
"""Literal Parallel-Run Protocol uniqueness audit on freshly fetched registry bytes.

Protocol Rule 1 (user prompt, verbatim intent): a candidate fails if its rank correlation with any
registry raster exceeds 0.90, OR if more than 70% of its dots lie within 3 px of one registry
raster's dots. Checked on the surface (before placement) and on the final dots. No
space-filling exemption is applied (``space_filling_coverage=None``).

Inputs
  * registry/focus_registry_manifest.json  - 386 rasters (378 fetched by
    scripts/fetch_registry_rasters.py and SHA-verified; 8 historical rasters from the restored
    .cache/gems_data/scored set, which restore_data.py also SHA-verifies).
  * .cache/gems_data/sample_submission.tif - organizer grid template (CRS, shape, transform, footprint).
  * the candidate GeoTIFF.

Usage: python scripts/literal_registry_audit.py <candidate.tif> <receipt.json>
Writes a compact JSON receipt (summary + worst rows). Exit 0 only if the literal rule passes.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import registry_audit as ra  # noqa: E402

MANIFEST = ROOT / "registry" / "focus_registry_manifest.json"
TEMPLATE = ROOT / ".cache" / "gems_data" / "sample_submission.tif"
LOCAL_MANIFEST = ROOT / ".cache" / "registry_manifest_local.json"
MAX_WITHIN3 = 0.70
MAX_RHO = 0.90


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_local_manifest() -> dict:
    m = json.loads(MANIFEST.read_text())
    rows = []
    missing = []
    for e in m["rasters"]:
        if e["repo"] == "HISTORICAL_SCORED":
            local = Path(".cache/gems_data") / e["path"]
        else:
            local = Path(".cache/registry_rasters") / e["repo"] / Path(e["path"]).name
        if not (ROOT / local).is_file():
            missing.append(str(local))
        rows.append(dict(e, local=str(local)))
    if missing:
        raise SystemExit(f"missing registry files: {missing[:5]} (n={len(missing)})")
    out = dict(m, rasters=rows)
    LOCAL_MANIFEST.write_text(json.dumps(out) + "\n")
    return out


def format_checks(cand: Path) -> dict:
    with rasterio.open(TEMPLATE) as t:
        tpl_foot = np.isfinite(t.read(1))
        tpl = {"crs": str(t.crs), "shape": list(t.shape), "transform": list(t.transform)[:6], "dtype": str(t.dtypes[0])}
    with rasterio.open(cand) as s:
        arr = s.read(1)
        got = {
            "count": s.count,
            "crs": str(s.crs),
            "shape": list(s.shape),
            "transform": list(s.transform)[:6],
            "dtype": str(s.dtypes[0]),
            "nodata": s.nodata,
        }
    foot = tpl_foot
    inside = arr[foot]
    checks = {
        "single_band": got["count"] == 1,
        "dtype_float32": got["dtype"] == "float32",
        "crs_match": got["crs"] == tpl["crs"],
        "shape_match": got["shape"] == tpl["shape"],
        "transform_match": got["transform"] == tpl["transform"],
        "no_nan_inside_footprint": bool(np.isfinite(inside).all()),
        "values_in_0_1_inside_footprint": bool(inside.size and inside.min() >= 0.0 and inside.max() <= 1.0),
        "outside_null_or_nan_official": bool(np.all(np.isnan(arr[~foot]))),
        "no_inf": bool(np.isfinite(arr).all() or np.isnan(arr).any()) and not bool(np.isinf(arr).any()),
    }
    # Informational only (not a pass criterion): owner-variant convention with zeros outside the footprint.
    info = {"outside_zero_or_nan_owner_variant": bool(np.all((arr[~foot] == 0.0) | np.isnan(arr[~foot])))}
    checks["all_passed"] = all(checks.values())
    checks.update(info)
    return {"checks": checks, "template": tpl, "candidate": got}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    cand = Path(sys.argv[1]).resolve()
    receipt_path = Path(sys.argv[2])
    manifest = build_local_manifest()
    with rasterio.open(TEMPLATE) as t:
        foot = np.isfinite(t.read(1))
    with rasterio.open(cand) as s:
        surf = s.read(1).astype(np.float32)
    dots = (surf > 0.0) & foot
    fmt = format_checks(cand)

    surface_audit = ra.audit_surface(surf, foot, manifest, root=ROOT, template_tif=TEMPLATE, max_abs_spearman=MAX_RHO)
    final_audit = ra.audit_final_dots(
        surf, dots, foot, manifest, root=ROOT, template_tif=TEMPLATE,
        max_abs_spearman=MAX_RHO, max_within_3px=MAX_WITHIN3, space_filling_coverage=None,
    )

    worst = sorted(
        [r for r in final_audit["comparisons"] if r.get("within_3px_fraction") is not None],
        key=lambda r: -r["within_3px_fraction"],
    )[:10]
    worst_surface = sorted(
        [r for r in surface_audit["comparisons"] if r.get("spearman") is not None],
        key=lambda r: -abs(r["spearman"]),
    )[:5]
    literal_pass = bool(surface_audit["passed"] and final_audit["literal_rule_passed"])
    n_dots = int(dots.sum())
    n_inside_foot = int(foot.sum())
    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": str(cand.relative_to(ROOT)) if cand.is_relative_to(ROOT) else str(cand),
        "candidate_sha256": sha256_file(cand),
        "candidate_dots": n_dots,
        "footprint_pixels": n_inside_foot,
        "rule": "literal Protocol Rule 1: |Spearman|<=0.90 AND within-3px<=0.70 vs EVERY registry raster; no exemption",
        "thresholds": {"max_within_3px": MAX_WITHIN3, "max_abs_spearman": MAX_RHO, "radius_px": 3},
        "registry_rasters_compared": len(final_audit["comparisons"]),
        "registry_malformed_or_missing": final_audit["malformed_or_missing"],
        "surface_stage": {
            "passed": surface_audit["passed"],
            "note": "pre-placement continuous surface not retained; the emitted binary surface is used (weaker test)",
            "worst_abs_spearman": surface_audit["worst_abs_spearman"],
            "worst_raster": surface_audit["worst_raster"],
            "worst_rows": [{k: r.get(k) for k in ("repo", "path", "spearman")} for r in worst_surface],
        },
        "final_dots_stage": {
            "literal_rule_passed": final_audit["literal_rule_passed"],
            "worst_within_3px_fraction": final_audit["worst_within_3px_fraction"],
            "worst_within_3px_raster": final_audit["worst_overlap_raster"],
            "worst_abs_spearman": final_audit["worst_abs_spearman"],
            "worst_spearman_raster": final_audit["worst_spearman_raster"],
            "literal_duplicates": final_audit["literal_duplicates"],
            "worst_rows": [{k: r.get(k) for k in ("repo", "path", "within_3px_fraction", "spearman", "footprint_coverage_3px")} for r in worst],
        },
        "format_validator": fmt,
        "literal_rule_passed": literal_pass,
        "verdict_uniqueness": "PASS (literal)" if literal_pass else "FAIL (literal)",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({
        "candidate": receipt["candidate"],
        "dots": n_dots,
        "literal_rule_passed": literal_pass,
        "worst_within_3px": final_audit["worst_within_3px_fraction"],
        "worst_within_3px_raster": final_audit["worst_overlap_raster"],
        "worst_abs_spearman": final_audit["worst_abs_spearman"],
        "format_all_passed": fmt["checks"]["all_passed"],
    }, indent=1))
    return 0 if (literal_pass and fmt["checks"]["all_passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
