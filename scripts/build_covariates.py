#!/usr/bin/env python3
"""Build the covariate stack used by the leaderboard-calibrated belief model.

Every covariate is a physical or geometric field on the official 100 m EPSG:32611 grid.
Nothing here is derived from the scored truth (the hidden faults); the only catalogue-derived
covariates are explicit distances to the PUBLIC catalogue and to the independent SGMC compilation,
which the submission is allowed to use and which the competition expects you to use.

Output: a float32 memmap .cache/gems_data/covariates.npy with shape (n_cov, 3730, 3292),
plus .cache/gems_data/covariates.json describing names and scaling.

Usage:  python scripts/build_covariates.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DATA = ROOT / ".cache" / "gems_data"
SHAPE = (3730, 3292)

# feature-band index -> (name, transform)
BANDS = [
    (1, "mag_anom", "z"), (2, "rtp", "z"), (3, "tmi_hg", "logz"), (4, "geod_2ndinv", "z"),
    (5, "grav_slope", "logz"), (6, "tc", "z"), (7, "geod_shear", "z"), (8, "geod_dilate", "z"),
    (9, "tmi_vg", "logz"), (10, "deq_n100", "z"), (11, "grav_vg", "z"), (12, "det_elev", "z"),
    (13, "grav_iso", "z"), (14, "tmi", "z"), (15, "depth_base", "z"), (16, "ieq_n100", "z"),
    (17, "cond_surf", "z"), (18, "grav_hg", "logz"), (19, "det_elev_slope", "z"),
]
LIDAR = [(3, "lidar_step"), (4, "lidar_lapneg"), (8, "lidar_cross"), (9, "lidar_relief"),
         (10, "lidar_coh100"), (11, "lidar_strike_sin"), (11, "lidar_strike_cos")]
RAD = [(1, "rad_K"), (2, "rad_Th"), (4, "rad_TC")]
EXT = [(4, "mag_up150")]


def read_band(path: Path, idx: int) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(idx).astype(np.float32)


def robust_scale(a: np.ndarray, foot: np.ndarray, mode: str, clip: float = 3.0) -> np.ndarray:
    v = a[foot]
    v = v[np.isfinite(v)]
    lo, hi = np.percentile(v, [0.5, 99.5])
    x = np.clip(a, lo, hi)
    if mode in ("logz", "log"):
        x = np.log1p(np.maximum(x - min(lo, 0.0), 0.0))
        vv = x[foot]
        lo2, hi2 = np.percentile(vv[np.isfinite(vv)], [0.5, 99.5])
        x = np.clip(x, lo2, hi2)
    mu, sd = np.nanmean(x[foot]), np.nanstd(x[foot])
    z = (x - mu) / (sd if sd > 0 else 1.0)
    return np.clip(z, -clip, clip).astype(np.float32)


def main() -> int:
    with rasterio.open(DATA / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    names: list[str] = []
    arrays: list[np.ndarray] = []
    tf = DATA / "training_features.tif"
    for idx, nm, mode in BANDS:
        a = read_band(tf, idx)
        a[~foot] = np.nan
        arrays.append(robust_scale(a, foot, mode))
        names.append(nm)
        print("band", nm, "ok")
    lp = DATA / "external" / "lidar_scarp_features_u8.tif"
    for idx, nm in LIDAR:
        a = read_band(lp, idx)
        a[~foot] = np.nan
        if nm.endswith("strike"):
            a = np.deg2rad(a)  # degrees -> radians
            a = np.sin(a) if nm.endswith("sin") else np.cos(a)
        arrays.append(robust_scale(np.nan_to_num(a, nan=np.nanmedian(a)), foot, "z"))
        names.append(nm)
        print("lidar", nm, "ok")
    rp = DATA / "external" / "geodawn_rad_u8.tif"
    for idx, nm in RAD:
        a = read_band(rp, idx)
        a[a == 0] = np.nan
        arrays.append(robust_scale(a, foot, "z"))
        names.append(nm)
        print("rad", nm, "ok")
    ep = DATA / "external" / "geodawn_extensions_u8.tif"
    for idx, nm in EXT:
        a = read_band(ep, idx)
        a[a == 0] = np.nan
        arrays.append(robust_scale(a, foot, "z"))
        names.append(nm)
        print("ext", nm, "ok")

    # ---- distance fields (in pixels; -1 = inside a mapped trace) ----
    with rasterio.open(DATA / "labels.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    arrays.append(np.clip(d_cat, 0, 60).astype(np.float32)); names.append("d_catalogue_px")

    with rasterio.open(DATA / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0) & foot
    d_sgmc = distance_transform_edt(~sgmc).astype(np.float32)
    arrays.append(np.clip(d_sgmc, 0, 60).astype(np.float32)); names.append("d_sgmc_px")

    # geothermal surface manifestations -> distance fields
    def points_from_csv(path: Path, col: str = "row", col2: str = "col") -> np.ndarray:
        import csv

        m = np.zeros(SHAPE, bool)
        with path.open() as f:
            for row in csv.DictReader(f):
                try:
                    r, c = int(float(row[col])), int(float(row[col2]))
                except (KeyError, ValueError, TypeError):
                    continue
                if 0 <= r < SHAPE[0] and 0 <= c < SHAPE[1]:
                    m[r, c] = True
        return m

    springs = points_from_csv(DATA / "external" / "gdr_wellspring_in_footprint.csv")
    d_spr = distance_transform_edt(~springs.astype(bool)).astype(np.float32)
    arrays.append(np.clip(d_spr, 0, 80).astype(np.float32)); names.append("d_spring_px")

    vents = points_from_csv(DATA / "external" / "gdr_volcanic_vents_in_footprint.csv")
    if vents.any():
        d_ven = distance_transform_edt(~vents).astype(np.float32)
        arrays.append(np.clip(d_ven, 0, 100).astype(np.float32)); names.append("d_vent_px")
        print("vents ok")

    with rasterio.open(DATA / "external" / "tiger_road_distance_m.tif") as ds:
        d_road = ds.read(1).astype(np.float32) / 100.0
    arrays.append(np.clip(np.nan_to_num(d_road, nan=200.0), 0, 40).astype(np.float32))
    names.append("d_road_px")

    n = len(arrays)
    mm = np.lib.format.open_memmap(DATA / "covariates.npy", mode="w+", dtype=np.float32,
                                   shape=(n, SHAPE[0], SHAPE[1]))
    for i, a in enumerate(arrays):
        mm[i] = a
    mm.flush()
    (DATA / "covariates.json").write_text(json.dumps(
        dict(names=names, n=n, shape=list(SHAPE), scaling="robust z-score, clipped to +-3; "
             "distances in pixels (100 m) clipped as stated", footprint_cells=int(foot.sum())), indent=1))
    print(f"wrote {n} covariates -> covariates.npy ({mm.nbytes/1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
