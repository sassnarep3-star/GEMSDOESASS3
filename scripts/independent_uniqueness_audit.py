#!/usr/bin/env python3
"""Recompute the Protocol-Rule-1 uniqueness audit FROM THE RASTERS, not from stored JSON.

Why this exists
---------------
`scripts/verify_all_gates.py` and `evidence/uniqueness_audit_386.json` only *read* the
uniqueness numbers that an earlier pipeline wrote. This script recomputes them directly
from GeoTIFF files on disk, so the claim can be re-checked by anyone who has the sibling
rasters (for example, a checkout of the public GEMSDOE* sibling repositories).

Metrics (per sibling raster S, candidate raster C)
--------------------------------------------------
* ``within3_frac``   : fraction of C's dots (value > 0) lying within 3 px (300 m) of an S dot.
                       Protocol Rule 1 threshold: must be <= 0.70.
* ``rev_within3_frac``: the reverse fraction (S dots within 3 px of C dots).
* ``xor_dots``       : |dots(C) XOR dots(S)|; 0 means byte-identical dot sets.
* ``spearman_sampled``: Spearman rank correlation on a fixed uniform random sample of
                       ``--n-sample`` pixels (both finite). Protocol Rule 1 threshold:
                       |rho| must be <= 0.90. Sampling is an approximation of the full-grid rank
                       correlation and is recorded as such in the output.

Registry scope (fixed 2026-10-28)
---------------------------------
Each compared raster is tagged with a scope, and the protocol rule is applied only to
the registry scopes:

* ``submission``  : any raster under a ``docs/downloads/`` or ``archive/legacy_candidates/``
                    folder of a sibling repository (a previously published or archived submission).
* ``calibration`` : any raster under ``inputs/calibration/`` (the literal "any registry raster"
                    reading includes these; the calibration lattice is the case in point).
* ``other``       : everything else on the grid, e.g. ``data/external`` feature layers such as
                    distance-to-road or geology rasters. These are NOT submissions. Before this fix
                    the first audit counted them, which produced a false 100% overlap
                    (``tiger_road_distance_m.tif``). They are listed, not gated.

``passes_rule_1`` = the literal rule over ``submission`` + ``calibration``.
``passes_submission_scope_only`` = the rule over ``submission`` alone.

Only single-band rasters on the competition grid (3730 rows x 3292 cols, float32 or
float64-compatible) are compared, so unrelated feature layers (uint8 external layers,
calibration probes on other grids) are skipped and listed in the output.

Usage
-----
    python scripts/independent_uniqueness_audit.py CANDIDATE.tif SIBLING_DIR \
        --out evidence/independent_uniqueness_audit.json

The script never writes into SIBLING_DIR and never modifies the candidate.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

EXPECTED_SHAPE = (3730, 3292)
RADIUS_PX = 3.0
N_SAMPLE_DEFAULT = 300_000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_submission(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (values as float64 with NaN kept, dots mask) for a single-band raster."""
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float64)
        nodata = ds.nodata
    if nodata is not None:
        arr[arr == nodata] = np.nan
    arr[np.abs(arr) > 1e30] = np.nan  # float32 sentinels
    dots = np.isfinite(arr) & (arr > 0.0)
    return arr, dots


def within_radius_fraction(a_dots: np.ndarray, dist_to_b: np.ndarray, radius: float) -> float:
    """Fraction of a_dots lying within `radius` px of b's dots, given dist_to_b = EDT(~b_dots)."""
    if int(a_dots.sum()) == 0:
        return 0.0
    return float((dist_to_b[a_dots] <= radius).mean())


def scope_of(rel_path: str) -> str:
    """Classify a sibling raster path (relative to the sibling directory) into a registry scope."""
    p = "/" + rel_path.replace(os.sep, "/")
    if "/docs/downloads/" in p or "/archive/legacy_candidates/" in p:
        return "submission"
    if "/inputs/calibration/" in p:
        return "calibration"
    return "other"


def scope_summary(results: list[dict], scopes: tuple[str, ...]) -> dict:
    rs = [r for r in results if r["scope"] in scopes]
    if not rs:
        return {"n": 0, "max_within3": None, "max_abs_spearman": None, "n_over_70pct": 0, "passes": False}
    m = max(rs, key=lambda r: r["within3_frac"])
    sp = [r for r in rs if r["spearman_sampled"] is not None]
    s = max(sp, key=lambda r: abs(r["spearman_sampled"])) if sp else None
    return {
        "n": len(rs),
        "max_within3": {"path": m["path"], "frac": m["within3_frac"]},
        "max_abs_spearman": {"path": s["path"], "rho": s["spearman_sampled"]} if s else None,
        "n_over_70pct": sum(1 for r in rs if r["within3_frac"] > 0.70),
        "passes": bool(m["within3_frac"] <= 0.70 and (s is None or abs(s["spearman_sampled"]) <= 0.90)),
    }


def audit(candidate: Path, sibling_dir: Path, n_sample: int, seed: int) -> dict:
    t0 = time.time()
    cand_arr, cand_dots = load_submission(candidate)
    if cand_arr.shape != EXPECTED_SHAPE:
        raise SystemExit(f"candidate shape {cand_arr.shape} != {EXPECTED_SHAPE}")

    dist_to_cand = ndi.distance_transform_edt(~cand_dots)  # computed once, reused for every sibling
    rng = np.random.default_rng(seed)
    flat_n = EXPECTED_SHAPE[0] * EXPECTED_SHAPE[1]
    sample_idx = rng.choice(flat_n, size=min(n_sample, flat_n), replace=False)
    cand_sample = cand_arr.ravel()[sample_idx]

    files = sorted(
        f for f in glob.glob(str(sibling_dir / "**" / "*.tif"), recursive=True)
        if Path(f).resolve() != candidate.resolve()
    )
    results = []
    skipped = []
    for f in files:
        p = Path(f)
        try:
            with rasterio.open(p) as ds:
                if (ds.height, ds.width) != EXPECTED_SHAPE or ds.count != 1:
                    skipped.append({"path": str(p.relative_to(sibling_dir)), "reason": "grid_or_band_mismatch"})
                    continue
                if str(ds.dtypes[0]) not in ("float32", "float64"):
                    skipped.append({"path": str(p.relative_to(sibling_dir)), "reason": f"dtype={ds.dtypes[0]}"})
                    continue
        except Exception as exc:  # unreadable file
            skipped.append({"path": str(p.relative_to(sibling_dir)), "reason": f"unreadable: {exc}"[:120]})
            continue

        sib_arr, sib_dots = load_submission(p)
        if int(sib_dots.sum()) == 0:
            skipped.append({"path": str(p.relative_to(sibling_dir)), "reason": "no_positive_dots"})
            continue
        dist_to_sib = ndi.distance_transform_edt(~sib_dots)  # one EDT per sibling
        within = within_radius_fraction(cand_dots, dist_to_sib, RADIUS_PX)
        rev = within_radius_fraction(sib_dots, dist_to_cand, RADIUS_PX)
        xor = int(np.logical_xor(cand_dots, sib_dots).sum())

        s_sample = sib_arr.ravel()[sample_idx]
        ok = np.isfinite(cand_sample) & np.isfinite(s_sample)
        if ok.sum() > 100 and np.std(cand_sample[ok]) > 0 and np.std(s_sample[ok]) > 0:
            rho = float(spearmanr(cand_sample[ok], s_sample[ok]).statistic)
        else:
            rho = float("nan")

        if len(results) % 25 == 0:
            print(f"[audit] {len(results)} rasters compared ({time.time() - t0:.0f}s)", flush=True)
        results.append({
            "path": str(p.relative_to(sibling_dir)),
            "scope": scope_of(str(p.relative_to(sibling_dir))),
            "sha256": sha256_file(p),
            "n_dots": int(sib_dots.sum()),
            "within3_frac": round(within, 6),
            "rev_within3_frac": round(rev, 6),
            "xor_dots": xor,
            "spearman_sampled": None if np.isnan(rho) else round(rho, 6),
        })

    results.sort(key=lambda r: -r["within3_frac"])
    max_w = results[0] if results else None
    max_rho = max(results, key=lambda r: abs(r["spearman_sampled"] or 0.0)) if results else None
    summary = {
        "candidate": str(candidate),
        "candidate_sha256": sha256_file(candidate),
        "candidate_n_dots": int(cand_dots.sum()),
        "sibling_dir": str(sibling_dir),
        "n_rasters_compared": len(results),
        "n_rasters_skipped": len(skipped),
        "thresholds": {"within3_max_frac": 0.70, "abs_spearman_max": 0.90, "radius_px": RADIUS_PX},
        "max_within3": {"path": max_w["path"], "frac": max_w["within3_frac"]} if max_w else None,
        "max_abs_spearman": {"path": max_rho["path"], "rho": max_rho["spearman_sampled"]} if max_rho else None,
        "identical_dot_sets": [r["path"] for r in results if r["xor_dots"] == 0 and r["n_dots"] > 0],
        "by_scope": {
            "submission": scope_summary(results, ("submission",)),
            "calibration": scope_summary(results, ("calibration",)),
            "other_not_gated": {"n": sum(1 for r in results if r["scope"] == "other")},
        },
        "literal_registry_scope": ["submission", "calibration"],
        "passes_submission_scope_only": scope_summary(results, ("submission",))["passes"],
        # Protocol Rule 1 applies to the literal registry (submission + calibration) only.
        "passes_rule_1": scope_summary(results, ("submission", "calibration"))["passes"],
        "spearman_note": f"sampled on {min(n_sample, flat_n)} uniform random pixels (seed={seed}); approximation of full-grid rank correlation",
        "runtime_s": round(time.time() - t0, 1),
    }
    return {"summary": summary, "results": results, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("sibling_dir", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--n-sample", type=int, default=N_SAMPLE_DEFAULT)
    ap.add_argument("--seed", type=int, default=20261028)
    args = ap.parse_args(argv)

    out = audit(args.candidate, args.sibling_dir, args.n_sample, args.seed)
    s = out["summary"]
    print(json.dumps(s, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2) + "\n")
        print(f"wrote {args.out}")
    return 0 if s["passes_rule_1"] else 1


if __name__ == "__main__":
    sys.exit(main())
