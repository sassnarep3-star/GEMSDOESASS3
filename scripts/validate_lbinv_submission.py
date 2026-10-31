#!/usr/bin/env python3
"""Verify the emitted candidate against the organizer format rules and against its own claims.

This is the "line by line" check: every number the site publishes about this file is recomputed
here from the raster and the field, and nothing is taken on trust -- including the headline
estimated score, which is recomputed as ``sum(q at the dots) / (0.2*dots + 0.8*N)``.

Exit codes: 0 = all gates pass, 1 = at least one gate failed.

Usage
-----
    python scripts/validate_lbinv_submission.py --tif docs/downloads/<name>.tif
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tif", type=Path, required=True)
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "distill_q.npz")
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "validator_lbinv_20261030.json")
    args = ap.parse_args()

    checks: dict[str, object] = {}
    detail: dict[str, object] = {}

    tif = args.tif if args.tif.is_absolute() else (ROOT / args.tif)
    build_path = tif.with_name(tif.stem + "-build.json")
    build = json.loads(build_path.read_text())
    checks["build_receipt_exists"] = True

    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    checks["sha256_matches_receipt"] = sha == build["raster_sha256"]
    detail["raster_sha256"] = sha

    zp = tif.with_name(tif.name + ".zip")
    checks["zip_exists"] = zp.exists()
    if zp.exists():
        checks["zip_sha256_matches_receipt"] = hashlib.sha256(zp.read_bytes()).hexdigest() == build["zip_sha256"]
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
            checks["zip_single_member"] = len(names) == 1
            checks["zip_member_is_the_tif"] = names == [tif.name]
            checks["zip_bytes_identical"] = zf.read(names[0]) == tif.read_bytes() if names else False

    with rasterio.open(args.data_dir / "sample_submission.tif") as ref:
        rshape, rtransform, rcrs = ref.shape, ref.transform, ref.crs
        foot = np.isfinite(ref.read(1))
    with rasterio.open(tif) as ds:
        checks["single_band"] = ds.count == 1
        checks["float32"] = ds.dtypes[0] == "float32"
        checks["crs_matches"] = ds.crs == rcrs
        checks["shape_matches"] = ds.shape == rshape
        checks["transform_matches"] = ds.transform == rtransform
        checks["pixel_size_100m"] = (abs(ds.transform.a - 100.0) < 1e-6 and abs(ds.transform.e + 100.0) < 1e-6)
        a = ds.read(1)

    vals = a[np.isfinite(a)]
    checks["all_values_in_0_1"] = bool(vals.min() >= 0.0 and vals.max() <= 1.0)
    checks["values_are_binary"] = bool(np.isin(np.unique(vals), [0.0, 1.0]).all())
    checks["nan_only_outside_footprint"] = bool(np.isnan(a[~foot]).all())
    checks["no_nan_inside_footprint"] = bool(np.isfinite(a[foot]).all())
    dots = a == 1.0
    n_dots = int(dots.sum())
    checks["dot_count_matches_receipt"] = n_dots == build["n_dots"]
    detail["n_dots"] = n_dots

    # ---- the headline number, recomputed ----
    z = np.load(args.field)
    q = z["q"]
    with rasterio.open(args.data_dir / "sample_submission.tif") as ds:
        ref_foot = np.isfinite(ds.read(1))
    grid_of_fp = np.nonzero(ref_foot.ravel())[0]
    fp_of_grid = np.full(ref_foot.size, -1, dtype=np.int64)
    fp_of_grid[grid_of_fp] = np.arange(grid_of_fp.size)
    sel = fp_of_grid[dots.ravel()]
    sel = sel[sel >= 0]
    qsum = float(q[sel].sum())
    N = float(np.ravel(z["N"])[0])
    est = qsum / (ALPHA * n_dots + BETA * N)
    detail.update({"expected_tp_recomputed": round(qsum, 1), "est_score_recomputed": round(est, 4),
                   "N": N, "means_q_on_dots": round(qsum / n_dots, 4)})
    checks["est_score_reproduced"] = abs(est - build["est_score"]) <= 5e-4
    checks["expected_tp_reproduced"] = abs(qsum - build["expected_tp"]) <= max(5.0, 0.001 * build["expected_tp"])

    note = build["submission_note"]
    checks["note_length_1_to_140"] = 1 <= len(note) <= 140
    detail["note_length"] = len(note)
    checks["note_has_no_newline"] = "\n" not in note

    ok = all(bool(v) for v in checks.values())
    receipt = {"schema_version": 1,
               "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
               "tif": str(tif.relative_to(ROOT)),
               "label": "ESTIMATE", "not_organizer_confirmed": True,
               "ok": ok, "n_gates": len(checks), "n_passed": int(sum(bool(v) for v in checks.values())),
               "checks": checks, "detail": detail,
               "note": note}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=1) + "\n")
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(json.dumps(detail, indent=1))
    print(f"{int(sum(bool(v) for v in checks.values()))}/{len(checks)} gates pass -> {'ok' if ok else 'BLOCKED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
