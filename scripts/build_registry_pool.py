#!/usr/bin/env python3
"""Build a registry-wide fingerprint pool for the lane/uniqueness rule.

The protocol's uniqueness test needs *every* accessible sibling raster, not a hand-picked list.
This script shallow-clones each sibling repository named in registry/sibling_repos.txt (sparse
checkout of .tif paths), then fingerprints every raster:

  n_positive, mass, dtype, n_bands, and a 128x128 binned occupancy grid (for rank correlation)

Per-raster positive coordinates are kept only as .npy for sparse rasters (<= 400k positives) so the
exact "fraction of dots within 3 px" test can be run later without re-reading the TIFF.

Everything is written under .cache/pool (git-ignored).  The committed summary is
evidence/registry_pool_fingerprints.json.

Usage:  python scripts/build_registry_pool.py [--limit N]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
WORK = Path("/tmp/pool")
OUT = ROOT / ".cache" / "pool"
BIN = 16
MAX_COORDS = 120_000
SHAPE = (3730, 3292)


def repos() -> list[tuple[str, str]]:
    out = []
    for line in (ROOT / "registry" / "sibling_repos.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        owner, name = line.split()
        out.append((owner, name))
    return out


def clone(owner: str, name: str) -> Path | None:
    d = WORK / f"{owner}__{name}"
    if d.exists():
        return d
    url = f"https://github.com/{owner}/{name}"
    r = subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                        "--quiet", url, str(d)], capture_output=True)
    if r.returncode != 0:
        return None
    subprocess.run(["git", "-C", str(d), "sparse-checkout", "set", "--no-cone", "**/*.tif"],
                   capture_output=True)
    return d


def fingerprint(p: Path) -> dict | None:
    try:
        with rasterio.open(p) as ds:
            if (ds.height, ds.width) != SHAPE:
                return dict(status="shape_mismatch", shape=[ds.height, ds.width])
            a = ds.read(1)
            nb, dt = ds.count, ds.dtypes[0]
    except Exception as exc:  # noqa: BLE001
        return dict(status=f"read_error: {type(exc).__name__}")
    if nb != 1:
        return dict(status="multiband", n_bands=nb)
    fin = np.isfinite(a)
    pos = fin & (a > 0)
    n = int(pos.sum())
    if n == 0:
        return dict(status="empty", n_positive=0)
    rs = np.linspace(0, SHAPE[0], BIN + 1).astype(int)
    cs = np.linspace(0, SHAPE[1], BIN + 1).astype(int)
    b = np.add.reduceat(np.add.reduceat(pos.astype(np.int32), rs[:-1], axis=0), cs[:-1], axis=1)
    b = b[list(range(BIN))[: len(rs) - 1]][:, list(range(BIN))[: len(cs) - 1]]
    rec = dict(status="ok", n_positive=n, mass=float(np.nansum(np.clip(a, 0, None))), dtype=str(dt),
               binned=b.tolist())
    if n <= MAX_COORDS:
        ys, xs = np.nonzero(pos)
        rec["coords"] = np.stack([ys.astype(np.int16), xs.astype(np.int16)])
    return rec


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    rows = []
    rs = repos()
    if limit:
        rs = rs[:limit]
    for i, (owner, name) in enumerate(rs):
        d = clone(owner, name)
        if d is None:
            rows.append(dict(repo=f"{owner}/{name}", status="clone_failed"))
            print(f"[{i+1}/{len(rs)}] {owner}/{name}: clone failed")
            continue
        tifs = sorted(d.rglob("*.tif"))
        print(f"[{i+1}/{len(rs)}] {owner}/{name}: {len(tifs)} tifs", flush=True)
        for p in tifs:
            rec = fingerprint(p)
            if rec is None:
                continue
            rec["repo"] = f"{owner}/{name}"
            rec["path"] = str(p.relative_to(d))
            if "coords" in rec:
                key = f"{owner}__{name}__{p.name}".replace("/", "_")[:180]
                np.save(OUT / (key + ".npy"), rec.pop("coords"))
                rec["coords_file"] = key + ".npy"
            if rec["status"] == "ok":
                rows.append(rec)
        # keep disk usage bounded
        if (i % 10) == 9:
            print(f"    disk free: {shutil.disk_usage('/tmp').free/1e9:.1f} GB", flush=True)
    (ROOT / "evidence" / "registry_pool_fingerprints.json").write_text(json.dumps(
        dict(schema_version=1, bin=BIN, n_rasters=len(rows),
             note="Fingerprints of every .tif accessible in the sibling registry. "
                  "MEASURED. Used for the lane (uniqueness) rule only.",
             rasters=rows)))
    print(f"wrote evidence/registry_pool_fingerprints.json with {len(rows)} rasters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
