#!/usr/bin/env python3
"""Re-render an existing submission raster in the portal-safe encoding, with the dots unchanged.

Why this exists: on 2026-10-30 the live DrivenData form rejected a raster that satisfies the official
sentence "data outside the bounds is null or nan", because the form compares every *stored* cell against
[0, 1] element-wise and NaN compares False (IR-SASS3-81). The portal-safe encoding keeps the in-footprint
payload byte-for-byte identical, writes 0.0 outside the footprint, and carries the null-ness in an internal
GDAL per-dataset mask band, so it satisfies both the sentence (GDAL/rasterio read those cells as nodata) and
the portal test. The emission - the thing every score depends on - does not change, so uniqueness, holdout
and projection receipts measured on the source file apply to the output unchanged (this script proves that by
reporting the symmetric difference of the two positive sets, which must be 0).

Usage:
  python scripts/make_portal_safe_render.py docs/downloads/<file>.tif [--suffix -safe] [--zip]
Writes <stem><suffix>.tif beside it, an optional .zip, and a JSON receipt naming both SHAs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_submission_tif import EXPECTED_SHAPE, _footprint, portal_range_gate  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tif", type=Path)
    ap.add_argument("--suffix", default="-safe")
    ap.add_argument("--zip", dest="do_zip", action="store_true", default=True)
    ap.add_argument("--out-receipt", type=Path, default=None)
    args = ap.parse_args()

    src = args.tif if args.tif.is_absolute() else ROOT / args.tif
    if not src.is_file():
        raise SystemExit(f"no such raster: {src}")
    with rasterio.open(src) as ds:
        prof = ds.profile.copy()
        arr = ds.read(1).astype(np.float32)
        src_nodata, src_crs, src_transform = ds.nodata, ds.crs, ds.transform
        src_mask_flags = sorted({f"{int(f.value)}:{f.name}" for grp in ds.mask_flag_enums for f in grp})
    if arr.shape != EXPECTED_SHAPE:
        raise SystemExit(f"unexpected shape {arr.shape}; expected {EXPECTED_SHAPE}")
    footprint = _footprint(arr.shape)
    if footprint is None:
        raise SystemExit("footprint unavailable: restore data/sample_submission.tif or evidence/organizer_footprint_mask.npz")

    out = arr.copy()
    out[~footprint] = 0.0                       # finite, legal for the element-wise range test
    positive_source = np.isfinite(arr) & (arr != 0.0) & footprint
    positive_out = out != 0.0
    symdiff = int(np.count_nonzero(positive_source ^ positive_out))
    if symdiff:
        raise SystemExit(f"refusing to emit: re-render changed the dot set (symdiff {symdiff})")

    stem = src.name[: -len(".tif")] if src.name.endswith(".tif") else src.name
    for cut in ("-nan", "-zeros", "-allfinite", "-safe"):
        if stem.endswith(cut):
            stem = stem[: -len(cut)]
            break
    dst = src.with_name(f"{stem}{args.suffix}.tif")
    prof.update(count=1, dtype="float32", driver="GTiff", tiled=True, compress="deflate", predictor=2)
    prof.pop("nodata", None)                    # do NOT declare 0 as nodata: legal zeros would vanish
    with rasterio.open(dst, "w", **prof) as ds:
        ds.crs = src_crs
        ds.transform = src_transform
        ds.write(out, 1)
        ds.write_mask(np.where(footprint, 1, 0).astype(np.uint8))  # per-dataset band: outside == null
    with rasterio.open(dst) as chk_ds:
        chk = chk_ds.read(1)
        flags = sorted({f"{int(f.value)}:{f.name}" for grp in chk_ds.mask_flag_enums for f in grp})
        masked = np.ma.getmaskarray(chk_ds.read(1, masked=True)).astype(bool)
        out_crs = chk_ds.crs.to_string() if chk_ds.crs else None
        out_tf = [float(v) for v in chk_ds.transform][:6]
    ok_gate, n_bad = portal_range_gate(chk)
    if not ok_gate:
        raise SystemExit(f"re-render still violates the portal range test ({n_bad} cells)")

    zip_path = None
    if args.do_zip:
        zip_path = dst.with_suffix(dst.suffix + ".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(dst, dst.name)

    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "scripts/make_portal_safe_render.py",
        "source": {"file": src.name, "sha256": sha(src), "bytes": src.stat().st_size,
                   "declared_nodata": None if src_nodata is None or not np.isfinite(src_nodata) else float(src_nodata),
                   "mask_flags": src_mask_flags},
        "output": {"file": dst.name, "sha256": sha(dst), "bytes": dst.stat().st_size,
                   "zip": zip_path.name if zip_path else None,
                   "zip_sha256": sha(zip_path) if zip_path else None,
                   "mask_flags": flags, "declared_nodata": None,
                   "transform": out_tf,
                   "crs": out_crs},
        "proof": {
            "dot_set_symmetric_difference": symdiff,
            "positive_cells": int(positive_out.sum()),
            "unique_values_in": sorted(set(np.unique(chk[footprint]).tolist()))[:6],
            "portal_range_test_all_cells": bool(ok_gate),
            "non_finite_cells_stored": int(np.count_nonzero(~np.isfinite(chk))),
            "masked_fraction_output": round(float(masked.mean()), 6),
            "masked_fraction_source": round(float(np.count_nonzero(~footprint) / footprint.size), 6),
            "note": ("the emission is bit-identical inside the footprint, so every uniqueness, holdout and "
                     "projection receipt measured on the source file applies to this file unchanged"),
        },
        "reproduced_by": f"python scripts/make_portal_safe_render.py {src.relative_to(ROOT) if src.is_relative_to(ROOT) else src}",
    }
    out_path = args.out_receipt or ROOT / "evidence" / f"portal_safe_render_{dst.stem}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt["proof"], indent=1))
    print(f"wrote {dst}  ({dst.stat().st_size:,} bytes)  sha256={receipt['output']['sha256'][:16]}…")
    print(f"receipt {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
