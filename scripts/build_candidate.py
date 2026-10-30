#!/usr/bin/env python3
"""Build the SASS3 submission candidate(s) and write portal-safe GeoTIFFs.

Format decision (verified, see docs/research/submission-format-20261030.md)
---------------------------------------------------------------------------
Official problem description (page 967) requires: EPSG:32611, 100 m, same bounds as the training
data, **data outside the bounds null or nan**, single band float32, values in [0, 1].
The DrivenData submission form additionally evaluates the range test on the stored array, so a file
that stores NaN outside the footprint fails with "Predicted values must be in range [0, 1]" - which
is exactly what the owner observed with the previous `-nan` download (measured here: 7,111,787 NaN
cells; `np.all((a>=0)&(a<=1))` is False for NaN).  The fix is to carry the null-ness in a GDAL
*mask band* instead of in the payload:

  safe    : float32, every stored value in [0, 1], outside-footprint cells stored as 0.0 and
            flagged invalid by an internal per-dataset mask band  -> passes both readings.
  literal : outside-footprint cells stored as NaN, as the page text words it, no mask band
            -> passes the literal text, fails the portal's range test (kept for reference only).

The emission itself is binary p = 1 on the selected support: DTI is linear-fractional in each pixel
value on every region where the argmax assignment is fixed, so an optimum exists at a vertex of the
[0, 1]^N box - a binary emission (proved and unit-tested in tests/test_portal_range_gate.py).
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from scipy.ndimage import distance_transform_edt, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir, downloads_dir  # noqa: E402
from gemsdoesass3 import lli, ocm  # noqa: E402

CRS = "EPSG:32611"


def rank_norm(a: np.ndarray) -> np.ndarray:
    v = a[::37]
    v = v[np.isfinite(v)]
    qs = np.quantile(v, np.linspace(0.0, 1.0, 1025))
    idx = np.searchsorted(qs, np.nan_to_num(a, nan=-np.inf), side="right") - 1
    return (np.clip(idx, 0, 1023) / 1023.0).astype(np.float32)


def thin_to(m: np.ndarray, score: np.ndarray, n: int, block: int = 3) -> np.ndarray:
    s = np.where(m, np.nan_to_num(score, nan=0.0), -np.inf)
    out = np.zeros(m.shape, bool)
    idx = np.flatnonzero(s.ravel() > -np.inf)
    if n <= 0 or idx.size == 0:
        return out
    order = idx[np.argsort(-s.ravel()[idx], kind="stable")]
    H, W = m.shape
    yy, xx = np.unravel_index(order, (H, W))
    occupied: set[tuple[int, int]] = set()
    kept = 0
    for i in range(order.size):
        by, bx = int(yy[i]) // block, int(xx[i]) // block
        if any(((by + dy, bx + dx) in occupied) for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
            continue
        occupied.add((by, bx))
        out[int(yy[i]), int(xx[i])] = True
        kept += 1
        if kept >= n:
            return out
    rest = np.flatnonzero(m.ravel())
    rest = rest[~out.ravel()[rest]][: max(0, n - kept)]
    if rest.size:
        out.ravel()[rest] = True
    return out


def write_tif(arr: np.ndarray, path: Path, like: rasterio.Projection, mask: np.ndarray | None = None) -> dict:
    """Write a single-band float32 GeoTIFF matching the organizer grid; optional internal mask band."""
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff", "height": arr.shape[0], "width": arr.shape[1], "count": 1,
        "dtype": "float32", "crs": CRS, "transform": like["transform"],
        "compress": "deflate", "tiled": True, "blockxsize": 256, "blockysize": 256,
    }
    if mask is not None:
        profile["masked"] = True
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(arr, 1)
        if mask is not None:
            ds.write_mask(mask)
    with rasterio.open(path) as ds:
        tf = tuple(float(v) for v in ds.transform)[:6]
        hdr = {"crs": str(ds.crs), "shape": [ds.height, ds.width], "transform": tf, "dtype": ds.dtypes[0],
               "count": ds.count, "nodata": ds.nodata,
        "mask_flags": sorted({str(f) for grp in ds.mask_flag_enums for f in grp})}
    zpath = Path(str(path) + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(path, path.name)
    return {"tif": path.name, "tif_bytes": path.stat().st_size,
            "tif_sha256": _sha(path), "zip": zpath.name, "zip_bytes": zpath.stat().st_size,
            "zip_sha256": _sha(zpath), "header": hdr}


def _sha(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(ddir: Path, mass: int, mode: str) -> dict:
    ctx = holdout.load_holdout_context(ddir)
    foot, labels = ctx.foot, ctx.labels
    active = foot & ~labels
    spec, lam = lli.build_s0_spec(ddir)
    cat_lv, h_lv = spec.levels
    h195_path = ddir / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"
    with rasterio.open(h195_path) as ds:
        h_raw = ds.read(1)
    h195 = (np.isfinite(h_raw) & (h_raw > 0)) & foot
    d_cat = distance_transform_edt(~labels)
    d_h = distance_transform_edt(~h195)

    fields = ocm.load_fields(ddir)
    E = np.zeros(foot.shape, np.float32)
    for name in ocm.EDGE_BANDS:
        E += rank_norm(np.abs(np.nan_to_num(fields[name], nan=0.0)))
    for name in ("lidar_step_max", "lidar_ex_max", "lidar_relief"):
        E += rank_norm(fields[name])
    E /= (len(ocm.EDGE_BANDS) + 3)
    E[~active] = 0.0
    prom = E - maximum_filter(E, size=5)

    # LANE-COMPLIANT SUPPORT (mode "wide"): >=2.2 px off the H19-5 trace family, 3-50 px from the
    # catalogue.  This is the part of the live-calibrated intensity field that the sibling dot
    # families never occupied (their dots sit 1-2 px off their own trace), so it is the only region
    # where a projection improvement would be evidence of *discovery* rather than of re-thinning.
    # mode "band" is the intensity-optimal support (1.4-2 px off trace) kept for the lane record.
    if mode == "band":
        base = active & (h_lv == 3) & np.isin(cat_lv, [5, 6, 7])
    else:
        base = active & np.isin(h_lv, [3, 4]) & np.isin(cat_lv, [4, 5, 6, 7])
    sel = thin_to(base, E * np.maximum(0.0, 1.0 + prom), mass) & active
    return {"ctx": ctx, "sel": sel, "active": active, "spec": spec, "lam": lam,
            "d_cat": d_cat, "d_h": d_h, "foot": foot, "base_px": int(base.sum())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mass", type=int, default=44090)
    ap.add_argument("--mode", default="wide", choices=["wide", "band"])
    ap.add_argument("--stamp", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--tag", default="gemsdoesass3-s3-ocm")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--receipt", default=str(ROOT / "evidence/candidate_build_receipt.json"))
    args = ap.parse_args()
    ddir = data_dir()
    b = build(ddir, args.mass, args.mode)
    sel, foot = b["sel"], b["foot"]
    ctx = b["ctx"]

    with rasterio.open(ddir / "sample_submission.tif") as ds:
        like = {"transform": ds.transform}
        nod = ds.read(1)
        nan_out = ~np.isfinite(nod)

    inside = np.where(foot, sel.astype(np.float32), np.float32(0.0))
    safe = np.where(foot, inside, np.float32(0.0)).astype(np.float32)
    literal = np.where(foot, sel.astype(np.float32), np.float32(np.nan)).astype(np.float32)

    out_dir = Path(args.out_dir) if args.out_dir else downloads_dir()
    stem = f"{args.tag}-{args.mode}{args.mass}-{args.stamp}-s3hash"
    rec = {"schema_version": 1, "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "mode": args.mode, "mass_target": args.mass, "emitted_px": int(sel.sum()),
           "support_pool_px": b["base_px"]}
    rec["safe"] = write_tif(safe, out_dir / f"{stem}-safe.tif", like, mask=foot)
    rec["literal"] = write_tif(literal, out_dir / f"{stem}-nan.tif", like)

    proj = lli.project_lli(np.where(foot, sel, 0).astype(np.float32), b["spec"], b["lam"])
    off = holdout.evaluate_sgmc_with_ci(sel, ctx, n_boot=1000)
    hr = holdout.evaluate_hide_and_recover(sel, ctx, b_visible_px=2.0, name=stem)
    d_fam = distance_transform_edt(~(read_ctl(ddir) & ctx.foot))
    rec["projections"] = {
        "lli": proj,
        "holdout_sgmc_cal": {"evaluator": holdout.SGMC_EVALUATOR_VERSION,
                             "n_withheld_positives": off["n_withheld_positives"],
                             "dti": off["sgmc_prevalence_calibrated_dti"], "ci95": off["sgmc_calibrated_ci95"]},
        "holdout_hide_recover": {"evaluator": holdout.HIDE_RECOVER_EVALUATOR_VERSION,
                                 "n_withheld_positives": hr["n_withheld_positives"],
                                 "dti": hr["pooled_dti"], "ci95": hr["ci95_cluster_bootstrap"]},
        "lane_overlap_vs_gems25_family_3px": round(float((d_fam[sel] <= 3.0).mean()), 4),
        "median_d_catalogue_px": float(np.median(b["d_cat"][sel])),
        "median_d_H19_5_px": float(np.median(b["d_h"][sel])),
    }
    Path(args.receipt).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))
    return 0


def read_ctl(ddir: Path) -> np.ndarray:
    p = ddir / "scored/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
    with rasterio.open(p) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


if __name__ == "__main__":
    raise SystemExit(main())
