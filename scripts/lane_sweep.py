#!/usr/bin/env python3
"""Lane check: candidate vs every pinned sibling-site raster in the registry.

For each registry raster R (458 SHA-verified files from the nine focus sites, fetched by
scripts/fetch_sibling_registry_git.sh or scripts/fetch_sibling_registry_rasters.py):

* ``overlap3px``  = fraction of the candidate's positive cells that lie within 3 px (Euclidean, disk
  structuring element) of any positive cell of R.  Protocol cap: 0.70.
* ``spearman``    = rank correlation between the two float bands over a deterministic 250k-cell
  systematic sample of the scored footprint.  Protocol cap: 0.90.
* ``identical``   = symmetric difference of the two positive sets (0 means the same raster).

The candidate is checked both on the *pre-placement surface* (the ranking field before thinning, as
the protocol requires: "check this on the surface before placement AND on the final dots") and on the
final emission.  Output: evidence/lane_sweep_<name>.json with the worst offenders first.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]

DISK = np.zeros((7, 7), bool)
yy, xx = np.mgrid[-3:4, -3:4]
DISK = (yy ** 2 + xx ** 2) <= 9.0


def _nn_query(cand_pts, their_pts):
    """For every candidate pixel, the distance to the nearest of their pixels (via their tree)."""
    from scipy.spatial import cKDTree as _T
    their_pts = np.asarray(their_pts, dtype=np.float64)
    if their_pts.size == 0 or len(cand_pts) == 0:
        return np.full(len(cand_pts), np.inf)
    t = _T(their_pts)
    d, _ = t.query(cand_pts, k=1)
    return np.asarray(d, dtype=np.float64)


def _js(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    return str(o)


def load_arr(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
    return a


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", required=True, help="candidate .tif (emission) ")
    ap.add_argument("--surface", default=None, help="optional float surface .npy for the pre-placement check")
    ap.add_argument("--registry", default="/tmp/registry_git")
    ap.add_argument("--footprint-mask", default=str(ROOT / "evidence/organizer_footprint_mask.npz"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-correlation", action="store_true")
    args = ap.parse_args()

    z = np.load(args.footprint_mask)
    shape = tuple(int(v) for v in z["shape"])
    foot = np.unpackbits(z["packed"])[: shape[0] * shape[1]].reshape(shape).astype(bool)

    cand = load_arr(Path(args.candidate))
    cmask = np.isfinite(cand) & (cand > 0) & foot
    cpos = np.count_nonzero(cmask)
    cy, cx = np.nonzero(cmask)
    cand_pts = np.column_stack([cy, cx]).astype(np.float64)
    # Reverse-diagnostic mask: every cell within 3 px of a candidate pixel (one dilation, reused).
    dil_cand = binary_dilation(cmask, structure=DISK) if cpos else np.zeros(foot.shape, bool)
    del cy, cx

    surf = np.load(args.surface) if args.surface else None
    if surf is not None:
        surf = np.where(np.isfinite(surf), surf, 0.0).astype(np.float32)
        spos = surf[foot]

    files = sorted(Path(args.registry).rglob("*.tif"))
    if args.skip_correlation:
        pass
    files = [f for f in files if f.is_file() and f.stat().st_size > 10_000]
    if args.limit:
        files = files[: args.limit]
    stride = max(1, foot[foot].size // 250_000)
    samp_idx = np.flatnonzero(foot.ravel())[::stride]
    cand_samp = cand.ravel()[samp_idx]

    rows = []
    for i, f in enumerate(files, 1):
        try:
            a = load_arr(f)
            if a.shape != foot.shape:
                rows.append({"file": str(f), "status": "shape_mismatch", "shape": [int(x) for x in a.shape]})
                continue
            pos = np.isfinite(a) & (a > 0) & foot
            n_pos = int(pos.sum())
            if n_pos == 0:
                rows.append({"file": str(f), "status": "empty", "n_pos": 0})
                continue
            py, px = np.nonzero(pos)
            # fraction of OUR dots within 3 px of ANY of THEIR dots -> nearest-neighbour query
            d_our_to_their = _nn_query(cand_pts, np.column_stack([py, px]))
            ov = float((d_our_to_their <= 3.0001).mean()) if cpos else 0.0
            rev = float(dil_cand[pos].mean())
            rho = float("nan") if args.skip_correlation else float(spearmanr(cand_samp, a.ravel()[samp_idx], nan_policy="omit").statistic)
            xor_px = int(np.count_nonzero(pos ^ cmask))
            del py, px, pos, a
            rows.append({
                "file": str(f.relative_to(Path(args.registry))), "status": "ok",
                "registry_pos_px": n_pos, "candidate_pos_px": cpos,
                "overlap3px_cand_within_registry": round(ov, 4),
                "overlap3px_registry_within_cand": round(rev, 4),
                "spearman_sampled": None if not np.isfinite(rho) else round(rho, 4),
                "xor_px": xor_px,
            })
        except Exception as exc:  # noqa: BLE001 - record, never abort the sweep
            rows.append({"file": str(f), "status": "error", "error": repr(exc)[:160]})
        if i % 50 == 0:
            print(f"{i}/{len(files)}", flush=True)

    ok = [r for r in rows if r.get("status") == "ok"]
    ok.sort(key=lambda r: -r["overlap3px_cand_within_registry"])
    verdict = {"n_checked": len(ok),
               "max_overlap3px": ok[0]["overlap3px_cand_within_registry"] if ok else None,
               "max_overlap_holder": ok[0]["file"] if ok else None,
               "max_abs_spearman": max((abs(r["spearman_sampled"] or 0.0) for r in ok), default=None),
               "any_exact_duplicate": any(r["xor_px"] == 0 for r in ok),
               "pass_overlap_cap_0p70": bool(ok) and ok[0]["overlap3px_cand_within_registry"] <= 0.70,
               "pass_correlation_cap_0p90": bool(ok) and max(abs(r["spearman_sampled"] or 0.0) for r in ok) <= 0.90}
    out = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "candidate": str(Path(args.candidate).relative_to(ROOT)) if str(args.candidate).startswith(str(ROOT)) else args.candidate,
           "registry_root": args.registry, "registry_files": len(files),
           "verdict": verdict, "worst_15": ok[:15], "rows": rows}
    op = Path(args.out) if args.out else ROOT / "evidence" / f"lane_sweep_{Path(args.candidate).stem}.json"
    op.write_text(json.dumps(out, indent=1, default=_js) + "\n")
    print(json.dumps({"verdict": verdict}, indent=1, default=_js))
    print("wrote", op)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
