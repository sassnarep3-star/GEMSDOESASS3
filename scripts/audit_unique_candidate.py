#!/usr/bin/env python3
"""Full-registry uniqueness audit of the candidate raster.

Implements the protocol's lane rule against EVERY raster fingerprinted by
scripts/build_registry_pool.py (3,010 rasters across 104 sibling repositories):

  1. DOT RULE   fraction of the candidate's dots within 3 px of a reference's dots.
                Reported literally against all references, and again with halo-saturated
                references (their own 300 m band covering > HALO_MAX of the footprint)
                separated out, because for those the statistic cannot fall below ~coverage.
  2. SURFACE RULE   Spearman rank correlation of the 16x16 binned occupancy surfaces.

Also reports the footprint band coverage of every reference that exceeds the dot cap, so the
reader can see *why* it exceeds it.

Usage: python scripts/audit_unique_candidate.py docs/downloads/<file>.tif
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DATA = ROOT / ".cache" / "gems_data"
POOL = ROOT / ".cache" / "pool"
RADIUS_PX = 3.0
CAP = 0.70
HALO_MAX = 0.50
BIN = 16


def binned(mask: np.ndarray) -> np.ndarray:
    rs = np.linspace(0, mask.shape[0], BIN + 1).astype(int)
    cs = np.linspace(0, mask.shape[1], BIN + 1).astype(int)
    b = np.add.reduceat(np.add.reduceat(mask.astype(np.int32), rs[:-1], axis=0), cs[:-1], axis=1)
    return b[: len(rs) - 1, : len(cs) - 1].ravel().astype(float)


def main() -> int:
    tif = Path(sys.argv[1])
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
    with rasterio.open(DATA / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    mine = np.where(foot, arr, 0.0) > 0
    ys, xs = np.nonzero(mine)
    xy = np.stack([ys, xs], 1)
    mybin = binned(mine)
    print(f"candidate: {tif.name}  dots={xy.shape[0]}")

    pool = json.loads((ROOT / "evidence" / "registry_pool_fingerprints.json").read_text())["rasters"]
    print(f"pool: {len(pool)} rasters")

    rows = []
    over = []
    for i, r in enumerate(pool):
        if r["status"] != "ok":
            continue
        rec = dict(repo=r["repo"], path=r["path"], n_positive=r["n_positive"], score=None)
        b = np.array(r["binned"], float).ravel()
        if b.size == mybin.size and b.sum() > 0 and mybin.sum() > 0:
            rho = spearmanr(mybin, b).statistic
            rec["spearman_binned"] = float(rho) if np.isfinite(rho) else 0.0
        cf = r.get("coords_file")
        if cf and (POOL / cf).exists():
            pts = np.load(POOL / cf).astype(np.int32)
            tree = cKDTree(pts.T if pts.shape[0] == 2 else pts)
            d, _ = tree.query(xy, k=1, workers=-1)
            rec["frac_within_3px"] = float((d <= RADIUS_PX).mean())
            if rec["frac_within_3px"] > CAP:
                if len(over) < 40:
                    m = np.zeros(foot.shape, bool)
                    q = pts.T if pts.shape[0] == 2 else pts
                    m[q[:, 0], q[:, 1]] = True
                    rec["band_coverage"] = float((distance_transform_edt(~m) <= RADIUS_PX)[foot].mean())
        rows.append(rec)
        if (i % 500) == 0:
            print(f"  {i}/{len(pool)}", flush=True)

    dot = [r for r in rows if "frac_within_3px" in r]
    over = sorted([r for r in dot if r["frac_within_3px"] > CAP], key=lambda r: -r["frac_within_3px"])
    rho_over = sorted([r for r in rows if r.get("spearman_binned", 0) > 0.90],
                      key=lambda r: -r["spearman_binned"])
    print(f"\nrasters with exact dot test: {len(dot)}")
    print(f"literal: {len(over)} rasters above {CAP:.0%} within 3 px")
    for r in over[:12]:
        print(f"   {r['frac_within_3px']:.3f} cov={r.get('band_coverage', float('nan')):.3f} "
              f"{r['repo']}/{r['path'][-58:]}")
    halo = [r for r in over if r.get("band_coverage", 0) > HALO_MAX]
    non_halo = [r for r in over if r.get("band_coverage", 0) <= HALO_MAX]
    print(f"   of which halo-saturated (band coverage > {HALO_MAX:.0%}): {len(halo)}")
    print(f"   non-halo rasters above the cap: {len(non_halo)}")
    for r in non_halo[:10]:
        print(f"      {r['frac_within_3px']:.3f} {r['repo']}/{r['path'][-58:]}")
    print(f"surface rule: {len(rho_over)} rasters with binned Spearman > 0.90")
    for r in rho_over[:5]:
        print(f"   rho={r['spearman_binned']:.3f} {r['repo']}/{r['path'][-50:]}")

    max_dot = max([r["frac_within_3px"] for r in dot], default=0.0)
    max_rho = max([abs(r.get("spearman_binned", 0.0)) for r in rows], default=0.0)
    out = dict(
        schema_version=1, candidate=tif.name, n_dots=int(xy.shape[0]),
        pool_rasters=len(pool), tested=len(dot), cap=CAP, halo_max=HALO_MAX,
        max_frac_within_3px_literal=float(max_dot),
        n_over_cap_literal=len(over), n_over_cap_non_halo=len(non_halo),
        max_frac_within_3px_non_halo=float(max([r["frac_within_3px"] for r in non_halo], default=0.0)),
        max_abs_spearman_binned=float(max_rho), n_spearman_over_0p90=len(rho_over),
        over_cap=[dict(repo=r["repo"], path=r["path"], frac=r["frac_within_3px"],
                       band_coverage=r.get("band_coverage")) for r in over],
        top_by_spearman=[dict(repo=r["repo"], path=r["path"], rho=r["spearman_binned"])
                         for r in sorted(rows, key=lambda r: -abs(r.get("spearman_binned", 0)))[:10]],
        note=("MEASURED. Literal lane rule vs every accessible sibling raster. Halo-saturated "
              "references (band coverage > 50% of the footprint) are separated because no "
              "submission can score below their coverage on that statistic."),
    )
    p = ROOT / "evidence" / "uniqueness_audit_candidate_20261030.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
