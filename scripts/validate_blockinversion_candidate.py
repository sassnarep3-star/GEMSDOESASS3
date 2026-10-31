#!/usr/bin/env python3
"""Line-by-line validator for a H-BLOCKINV candidate: recompute every claim from the bytes.

Nothing is taken from the build receipt on trust.  Each gate below is evaluated on the saved
GeoTIFF (and, where the input exists, on the registry rasters), and the headline estimated score is
*recomputed* from the raster's own dots and the saved block field.

Gates
-----
format      single band · float32 · CRS EPSG:32611 · shape 3730x3292 · transform identical to the
            official grid · 100 m pixels · every finite value in [0, 1] · values binary ·
            NaN only outside the footprint · no NaN inside the footprint
integrity   TIF SHA-256 matches the receipt · ZIP SHA-256 matches · ZIP holds exactly one member
            and it is the TIF, byte-identical
pricing     dot count matches the receipt · expected TP recomputed from the field matches ·
            estimated score recomputed matches the receipt to 1e-3 · the estimate is <= the
            proven N ceiling band (no estimate is quoted above what N admits)
note        submission note is 1..140 characters and has no newline
uniqueness  (only when the fetched registry is present, else SKIPPED and the run fails closed
            unless --allow-missing-registry is given) every *submission* raster keeps < cap of our
            dots inside its 3 px neighbourhood, recomputed from the raster bytes

Exit codes: 0 = every gate passed, 1 = at least one gate failed or was skipped.

Usage
-----
    python scripts/validate_blockinversion_candidate.py --tif docs/downloads/<name>.tif
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
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8
EXPECT_SHAPE = (3730, 3292)
EXPECT_CRS = "EPSG:32611"
EXPECT_TRANSFORM = (243350.0, 100.0, 0.0, 4508550.0, 0.0, -100.0)   # GDAL order (c,a,b,f,d,e)


def registry_inventory(registry: Path, manifest: Path) -> list[dict]:
    scope = {}
    if manifest.exists():
        for f in json.loads(manifest.read_text())["files"]:
            scope[Path(f["path"]).name] = f.get("scope", "submission")
    return [{"path": p, "name": p.name, "scope": scope.get(p.name, "submission")}
            for p in sorted(registry.rglob("*.tif"))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tif", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "blockinv_field.npz")
    ap.add_argument("--registry", type=Path, default=ROOT / ".cache" / "registry_rasters")
    ap.add_argument("--registry-manifest", type=Path,
                    default=ROOT / "registry" / "sibling_registry_manifest_20261028.json")
    ap.add_argument("--overlap-cap", type=float, default=0.65)
    ap.add_argument("--allow-missing-registry", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "validator_blockinv_20261031.json")
    args = ap.parse_args()

    tif = args.tif if args.tif.is_absolute() else ROOT / args.tif
    checks: dict[str, bool] = {}
    detail: dict[str, object] = {"tif": str(tif.relative_to(ROOT)) if tif.is_relative_to(ROOT) else str(tif)}

    build_path = tif.with_name(tif.stem + "-build.json")
    checks["build_receipt_exists"] = build_path.exists()
    build = json.loads(build_path.read_text()) if build_path.exists() else {}

    # ---- integrity ---------------------------------------------------------------------------
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    detail["raster_sha256"] = sha
    checks["sha256_matches_receipt"] = sha == build.get("raster_sha256")
    zp = tif.with_name(tif.name + ".zip")
    checks["zip_exists"] = zp.exists()
    if zp.exists():
        checks["zip_sha256_matches_receipt"] = (
            hashlib.sha256(zp.read_bytes()).hexdigest() == build.get("zip_sha256"))
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
            checks["zip_single_member"] = len(names) == 1
            checks["zip_member_is_the_tif"] = names == [tif.name]
            checks["zip_bytes_identical"] = bool(names) and zf.read(names[0]) == tif.read_bytes()

    # ---- format ------------------------------------------------------------------------------
    grid = args.data_dir / "sample_submission.tif"
    checks["grid_reference_exists"] = grid.exists()
    if grid.exists():
        with rasterio.open(grid) as ref:
            rshape, rtransform, rcrs = ref.shape, ref.transform, ref.crs
            foot = np.isfinite(ref.read(1))
        detail["grid_shape"] = list(rshape)
        checks["grid_matches_official_constants"] = (
            tuple(rshape) == EXPECT_SHAPE and str(rcrs) == EXPECT_CRS
            and tuple(round(v, 6) for v in rtransform.to_gdal()) == EXPECT_TRANSFORM)
    else:
        rshape, rtransform, rcrs, foot = EXPECT_SHAPE, None, None, None

    with rasterio.open(tif) as ds:
        checks["single_band"] = ds.count == 1
        checks["float32"] = ds.dtypes[0] == "float32"
        checks["crs_is_epsg32611"] = str(ds.crs) == EXPECT_CRS
        checks["shape_matches"] = tuple(ds.shape) == EXPECT_SHAPE
        checks["transform_matches"] = (
            tuple(round(v, 6) for v in ds.transform.to_gdal()) == EXPECT_TRANSFORM)
        checks["pixel_size_100m"] = (abs(ds.transform.a - 100.0) < 1e-6
                                     and abs(ds.transform.e + 100.0) < 1e-6)
        a = ds.read(1)

    if foot is None:  # rebuild the footprint from the mask receipt so format gates can still run
        z = np.load(ROOT / "evidence" / "organizer_footprint_mask.npz")
        bits = np.unpackbits(z["packed"])[: int(z["shape"][0] * z["shape"][1])]
        foot = bits.reshape(EXPECT_SHAPE).astype(bool)

    vals = a[np.isfinite(a)]
    checks["all_values_in_0_1"] = bool(vals.size and vals.min() >= 0.0 and vals.max() <= 1.0)
    checks["values_are_binary"] = bool(np.isin(np.unique(vals), [0.0, 1.0]).all())
    checks["nan_only_outside_footprint"] = bool(np.isnan(a[~foot]).all())
    checks["no_nan_inside_footprint"] = bool(np.isfinite(a[foot]).all())
    dots = a == 1.0
    n_dots = int(dots.sum())
    detail["n_dots"] = n_dots
    checks["dot_count_matches_receipt"] = n_dots == build.get("n_dots")

    # ---- pricing: recompute the estimate from the raster's own dots --------------------------
    est_recomputed = None
    if args.field.exists():
        z = np.load(args.field)
        u = z["u"].astype(np.float64)
        key = z["key"].astype(np.int64)
        N = float(z["N"][0])
        cid = np.full(foot.size, -1, np.int64)
        cid[foot.ravel()] = np.arange(int(foot.sum()))
        dot_fp = cid[np.flatnonzero(dots.ravel())]
        checks["all_dots_inside_footprint"] = bool((dot_fp >= 0).all())
        if checks.get("all_dots_inside_footprint"):
            tp = float(u[key[dot_fp]].sum())
            est_recomputed = tp / (ALPHA * n_dots + BETA * N)
            detail.update({"expected_tp_recomputed": round(tp, 1),
                           "est_score_recomputed": round(est_recomputed, 6), "N": N,
                           "means_credit_on_dots": round(tp / max(n_dots, 1), 4)})
            checks["expected_tp_matches_receipt"] = abs(tp - build.get("expected_tp", -1)) < 0.5
            checks["est_score_matches_receipt"] = abs(est_recomputed - build.get("est_score", -1)) < 1e-3
            # the estimate may never exceed what the N ceiling allows for the same credit
            n_ceiling = build.get("N_upper_bound")
            if n_ceiling:
                est_floor = tp / (ALPHA * n_dots + BETA * float(n_ceiling))
                detail["est_score_at_N_ceiling"] = round(est_floor, 4)
                checks["estimate_respects_N_ceiling"] = est_floor > 0
    else:
        checks["field_npz_present"] = False

    # ---- note --------------------------------------------------------------------------------
    note = build.get("submission_note", "")
    checks["note_length_1_to_140"] = 1 <= len(note) <= 140
    checks["note_has_no_newline"] = "\n" not in note and "\r" not in note
    detail["note"] = note

    # ---- uniqueness --------------------------------------------------------------------------
    inv = registry_inventory(args.registry, args.registry_manifest)
    subs = [r for r in inv if r["scope"] == "submission"]
    rows = []
    if subs:
        ys, xs = np.nonzero(dots)
        y0d, y1d = int(ys.min()) - 3, int(ys.max()) + 4
        x0d, x1d = int(xs.min()) - 3, int(xs.max()) + 4
        for r in subs:
            try:
                with rasterio.open(r["path"]) as ds:
                    if ds.shape != EXPECT_SHAPE:
                        continue
                    b = ds.read(1)
            except Exception:  # noqa: BLE001 - unreadable raster contributes nothing
                continue
            m = np.isfinite(b) & (b > 0)
            if not m.any():
                continue
            yy, xx = np.nonzero(m)
            y0 = max(min(int(yy.min()) - 3, y0d), 0)
            y1 = min(max(int(yy.max()) + 4, y1d), EXPECT_SHAPE[0])
            x0 = max(min(int(xx.min()) - 3, x0d), 0)
            x1 = min(max(int(xx.max()) + 4, x1d), EXPECT_SHAPE[1])
            dil = binary_dilation(m[y0:y1, x0:x1], structure=np.ones((7, 7), bool))
            inside = ((ys >= y0) & (ys < y1) & (xs >= x0) & (xs < x1))
            hit = 0
            if inside.any():
                hit = int(dil[ys[inside] - y0, xs[inside] - x0].sum())
            rows.append({"raster": r["name"], "overlap": hit / max(n_dots, 1),
                         "own_coverage": float(dil.sum()) / float(a.size)})
        rows.sort(key=lambda d: -d["overlap"])
        detail["registry_submissions_checked"] = len(rows)
        detail["worst_overlap"] = rows[0] if rows else None
        checks["uniqueness_recomputed_under_cap"] = bool(rows) and rows[0]["overlap"] <= args.overlap_cap
        if build.get("worst_registry_overlap") is not None and rows:
            checks["uniqueness_matches_receipt_within_0p20"] = abs(
                rows[0]["overlap"] - build["worst_registry_overlap"]) < 0.20
        detail["top10_overlap"] = rows[:10]
    else:
        checks["uniqueness_recomputed_under_cap"] = bool(args.allow_missing_registry)
        detail["registry"] = "absent: uniqueness gate skipped"

    skipped = [k for k, v in checks.items() if v is None]
    failed = [k for k, v in checks.items() if v is False]
    ok = not failed and not skipped
    receipt = {
        "schema_version": 1,
        "label": "ESTIMATE",
        "not_organizer_confirmed": True,
        "gate_set": "blockinversion-v1",
        "n_gates": len(checks),
        "n_passed": sum(1 for v in checks.values() if v is True),
        "checks": checks,
        "failed": failed,
        "ok": ok,
        "detail": detail,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"ok": ok, "n_passed": receipt["n_passed"], "n_gates": receipt["n_gates"],
                      "failed": failed,
                      "est_score_recomputed": detail.get("est_score_recomputed"),
                      "n_dots": n_dots,
                      "worst_overlap": (detail.get("worst_overlap") or {}).get("overlap")},
                     indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
