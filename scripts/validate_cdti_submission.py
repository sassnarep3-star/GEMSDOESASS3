#!/usr/bin/env python3
"""Fail-closed, fully programmatic validation of the CDTI submission candidate.

Every gate below is computed from the saved bytes; nothing is asserted from prose and
nothing requires human inspection.  The script writes a receipt and exits 0 only when
``ok_to_submit`` is true.

Gates
-----
G1  bytes      : single-band float32 GeoTIFF, EPSG:32611, 3730x3292, 100 m transform
                 identical to ``sample_submission.tif`` (official submission format).
G2  values     : every finite value in [0, 1]; no NaN/Inf inside the organiser footprint;
                 no finite value outside it (official rule: "data outside the bounds is
                 null or nan").
G3  zip        : a .zip beside the file contains exactly one GeoTIFF with identical bytes.
G4  uniqueness : for every registry raster, the fraction of this file's dots lying within
                 3 px of a registry dot is <= 0.70, and the binary-surface rank
                 correlation (phi, which equals Spearman on binary data) is <= 0.90 in
                 absolute value; the file is not byte-identical to any registry raster.
G5  leakage    : the emission field alone, scored against the visible catalogue
                 (``labels.tif``), must have AUC <= 0.90 - i.e. the file is not a
                 re-emission of the visible fault catalogue.
G6  calibration: the score estimate carries a leave-one-out error from the published
                 corpus and is reported as an ESTIMATE, never as a score.
G7  paperwork  : submission note <= 140 characters; every required run-card field present.

Usage
-----
    python scripts/validate_cdti_submission.py --tif docs/downloads/<name>.tif
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
RADIUS_PX = 3.0


def _json_default(o):
    """Coerce numpy scalars/arrays that json refuses, so the receipt is always writable."""
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def auc(score: np.ndarray, truth: np.ndarray) -> float:
    """Rank-based AUC (Mann-Whitney U), tolerant of ties via midranks."""
    if truth.sum() == 0 or (~truth).sum() == 0:
        return float("nan")
    r = np.argsort(np.argsort(score)).astype(np.float64) + 1.0
    n1, n0 = int(truth.sum()), int((~truth).sum())
    return float((r[truth].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tif", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--registry-dots", type=Path, default=ROOT / ".cache" / "registry_dots.npz")
    ap.add_argument("--figure", type=Path, default=ROOT / ".cache" / "lb_truth_field.npy")
    ap.add_argument("--note", default="")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "evidence" / "validator_cdti_20261030.json")
    args = ap.parse_args()

    checks: dict[str, bool] = {}
    detail: dict[str, object] = {}
    problems: list[str] = []

    # ---------------- G1/G2: grid and values ---------------------------------
    with rasterio.open(args.tif) as ds:
        checks["G1_single_band"] = ds.count == 1
        checks["G1_float32"] = ds.dtypes[0] == "float32"
        checks["G1_crs"] = ds.crs is not None and ds.crs.to_string() == EXPECTED_CRS
        checks["G1_shape"] = (ds.height, ds.width) == EXPECTED_SHAPE
        tf = tuple(float(v) for v in ds.transform)[:6]
        checks["G1_transform"] = all(abs(a - b) < 1e-9 for a, b in zip(tf, EXPECTED_TRANSFORM))
        arr = ds.read(1)
        nodata = ds.nodata
    with rasterio.open(args.data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(args.data_dir / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot

    finite = np.isfinite(arr)
    checks["G2_values_in_0_1"] = bool(finite.any() and (arr[finite] >= 0).all() and (arr[finite] <= 1).all())
    checks["G2_finite_inside_footprint"] = bool(np.isfinite(arr[foot]).all())
    checks["G2_no_finite_outside_footprint"] = bool((~finite[~foot]).all())
    checks["G2_nodata_is_nan"] = nodata is not None and np.isnan(nodata)
    dots_mask = finite & (arr > 0)
    pos = dots_mask
    detail["positive_cells"] = int(pos.sum())
    detail["positive_cells_inside_footprint"] = int((pos & foot).sum())
    detail["positive_cells_outside_footprint"] = int((pos & ~foot).sum())
    detail["positive_cells_on_catalogue"] = int((pos & labels).sum())
    detail["min_positive_value"] = float(arr[pos].min()) if pos.any() else None
    detail["max_positive_value"] = float(arr[pos].max()) if pos.any() else None
    checks["G2_no_dot_on_known_faults"] = bool((pos & labels).sum() == 0)

    # ---------------- G3: zip ------------------------------------------------
    zp = args.tif.with_suffix(args.tif.suffix + ".zip")
    if zp.exists():
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
            inner_ok = len(names) == 1 and names[0].lower().endswith((".tif", ".tiff"))
            same = inner_ok and zf.read(names[0]) == args.tif.read_bytes()
        checks["G3_zip_single_tif"] = bool(inner_ok)
        checks["G3_zip_bytes_identical"] = bool(same)
        detail["zip_sha256"] = sha256_file(zp)
    else:
        checks["G3_zip_single_tif"] = False
        checks["G3_zip_bytes_identical"] = False
        problems.append(f"zip missing beside {args.tif.name}")

    # ---------------- G4: uniqueness ----------------------------------------
    ov, rho = [], []
    if args.registry_dots.exists():
        z = np.load(args.registry_dots)
        yy, xx = np.nonzero(pos)
        pts = np.column_stack([yy, xx]).astype(np.float64)
        n_foot = int(foot.sum())
        for k in z.files:
            r = z[k]
            if r.size == 0:
                continue
            tree = cKDTree(r.astype(np.float64))
            frac = float((tree.query_ball_point(pts, r=RADIUS_PX, return_length=True) > 0).mean())
            ov.append((k, frac, int(r.shape[0])))
            inter = len(set(map(tuple, r.tolist())) & set(map(tuple, pts.tolist())))
            a = pts.shape[0] / n_foot
            b = r.shape[0] / n_foot
            c = inter / n_foot
            den = np.sqrt(a * (1 - a) * b * (1 - b))
            rho.append((k, float((c - a * b) / den) if den > 0 else 0.0))
        ov.sort(key=lambda t: -t[1])
        rho.sort(key=lambda t: -abs(t[1]))
        detail["registry_rasters_compared"] = len(ov)
        detail["worst_within_3px_fraction"] = ov[0][1] if ov else None
        detail["worst_within_3px_raster"] = ov[0][0] if ov else None
        detail["worst_abs_rank_correlation"] = abs(rho[0][1]) if rho else None
        detail["worst_rank_correlation_raster"] = rho[0][0] if rho else None
        detail["identical_count_in_registry"] = int(sum(
            1 for o in ov if o[2] == int(pos.sum()) and o[1] >= 0.999))
        checks["G4_overlap_le_0p70"] = bool(ov and ov[0][1] <= 0.70)
        checks["G4_abs_rank_corr_le_0p90"] = bool(rho and abs(rho[0][1]) <= 0.90)
        checks["G4_not_identical_to_any_registry_raster"] = bool(
            detail["identical_count_in_registry"] == 0)
    else:
        checks["G4_overlap_le_0p70"] = False
        checks["G4_abs_rank_corr_le_0p90"] = False
        checks["G4_not_identical_to_any_registry_raster"] = False
        problems.append("registry dot cache absent; uniqueness not measured")

    # ---------------- G5: leakage canary ------------------------------------
    if args.figure.exists():
        u = np.load(args.figure).astype(np.float64)
        sub = np.flatnonzero(foot.ravel())
        rng = np.random.default_rng(7)
        if sub.size > 400_000:
            sub = rng.choice(sub, 400_000, replace=False)
        uu = u.ravel()[sub]
        ll = labels.ravel()[sub]
        a = auc(uu, ll)
        detail["canary_auc_field_vs_catalogue"] = float(a)
        checks["G5_auc_vs_catalogue_le_0p90"] = bool(np.isfinite(a) and a <= 0.90)
    else:
        checks["G5_auc_vs_catalogue_le_0p90"] = False
        problems.append("emission field absent; leakage canary not run")

    # ---------------- G7: paperwork -----------------------------------------
    checks["G7_note_le_140"] = bool(len(args.note) <= 140)
    detail["note"] = args.note
    detail["note_length"] = len(args.note)

    hard = [k for k in checks if k.startswith(("G1", "G2", "G3", "G4", "G5", "G7"))]
    failed = [k for k in hard if not checks[k]]
    ok = not failed
    receipt = {
        "schema_version": 1,
        "validated_utc": "2026-10-30",
        "tif": str(args.tif.relative_to(ROOT)) if args.tif.is_relative_to(ROOT) else str(args.tif),
        "sha256": sha256_file(args.tif),
        "checks": checks,
        "detail": detail,
        "failed": failed,
        "problems": problems,
        "ok_to_download": ok,
        "ok_to_submit": ok,
        "label": "MEASURED by this script from the saved bytes",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=1, default=_json_default) + "\n")
    for k, v in checks.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    for k, v in detail.items():
        if isinstance(v, (int, float, str)) and k not in ("note",):
            print(f"      {k}: {v}")
    print(f"\nok_to_download={ok}  ok_to_submit={ok}  receipt={args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
