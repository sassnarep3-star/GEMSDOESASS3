"""Physical feature engineering & fold-safe structural propagation for H-GASS3-1 (GSD-HUA).

Every band of ``training_features.tif`` is mapped by its verified GDAL ``band_name`` metadata tag
(with Band 6 ``tc`` verified as GeoDAWN Radiometric Total Count per ``IR-DATA-B06``):
  B01: mag_anom             B08: geod_dilaterate      B15: depth_to_base_surf
  B02: rtp                  B09: tmi_vg               B16: ieq_n100a15
  B03: tmi_hg               B10: deq_n100a15          B17: cond_surf
  B04: geod_2ndinv          B11: iso_grav_anom_vg     B18: iso_grav_anom_hg
  B05: iso_grav_anom_slope  B12: det_elev             B19: det_elev_slope
  B06: tc (GeoDAWN Rad TC)  B13: iso_grav_anom
  B07: geod_shearrate       B14: tmi
"""
from __future__ import annotations

import csv
import gc
import json
import struct
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from scipy.ndimage import (
    convolve,
    distance_transform_edt,
    gaussian_filter,
    laplace,
    sobel,
)

BAND_NAMES_19 = [
    "b01_mag_anom",
    "b02_rtp",
    "b03_tmi_hg",
    "b04_geod_2ndinv",
    "b05_iso_grav_anom_slope",
    "b06_rad_tc",               # Verified GeoDAWN Radiometric Total Count (IR-DATA-B06)
    "b07_geod_shearrate",
    "b08_geod_dilaterate",
    "b09_tmi_vg",
    "b10_deq_n100a15",
    "b11_iso_grav_anom_vg",
    "b12_det_elev",
    "b13_iso_grav_anom",
    "b14_tmi",
    "b15_depth_to_base_surf",
    "b16_ieq_n100a15",
    "b17_cond_surf",
    "b18_iso_grav_anom_hg",
    "b19_det_elev_slope",
]

GSD_HUA_EXTRA_NAMES = [
    # Group B: Pure Subsurface Potential-Field, Basement-Throw, Alteration & MT Edges (cols 19..30)
    "true_mag_tilt",             # 19: atan2(b09_tmi_vg, b03_tmi_hg) fixing IR-DATA-B06
    "true_mag_tilt_hg",          # 20: |grad(true_mag_tilt)| depth-invariant contact edge
    "mag_destr_up150",           # 21: z(TMI_up150) - z(b02_rtp) hydrothermal magnetite destruction
    "geodawn_th_k",              # 22: GeoDAWN eTh/K alteration ratio
    "geodawn_u_k",               # 23: GeoDAWN eU/K ratio
    "geodawn_u_th",              # 24: GeoDAWN eU/eTh redox mobility ratio
    "clay_cap_edge",             # 25: |grad(b17_cond_surf)| lateral smectite clay-cap boundary
    "grav_tilt",                 # 26: atan2(b11_iso_grav_anom_vg, b05_iso_grav_anom_slope)
    "basin_fault_wall_grad",     # 27: |grad(b15_depth_to_base_surf)| buried basement fault throw!
    "basin_cover_log",           # 28: log1p(max(b15_depth_to_base_surf, 0))
    "subsurf_line_max_2p5km",    # 29: 2.5 km 12-angle line integral on PURE subsurface edges
    "subsurf_line_aniso_2p5km",  # 30: 2.5 km directional anisotropy on PURE subsurface edges
    # Group C: Mechano-Thermal Slip-Dilation & GDR #1391 Fluid-Upflow Plumes (cols 31..36)
    "subsurf_slip_dilation",     # 31: Morris-Ferrill-Henderson tendency on PURE subsurface strike * GPS dilatation
    "thermal_probe_2m_plume",    # 32: Coolbaugh/Kratt 3,800-station 2m temperature probe F2mDAB plume
    "geotherm_spring_plume",     # 33: GDR #1391 27,092-record thermal spring/well & quartz geothermometer plume
    "paleo_sinter_vent_plume",   # 34: GDR #1391 Quaternary sinter/travertine/tufa & volcanic vent plume
    "mechano_thermal_coupling",  # 35: subsurf_slip_dilation * thermal_plumes * subsurface_edge
    "seismic_strain_coupling",   # 36: log1p(b16_ieq) * z_pos(b04_geod_2ndinv) / log1p(b10_deq + 100)
    # Group D: Geomorphic Piedmont Toe, 3DEP Sub-100m Scarp, & Full-Sensor Line Integrals (cols 37..43)
    "piedmont_toe_inflection",   # 37: upslope-minus-local b19_det_elev_slope * concave -laplace(b12_det_elev)
    "det_elev_resid_500m",       # 38: 500 m high-pass detrended elevation residual
    "lidar_scarp_step",          # 39: 3DEP sub-100m scarp step + downface asymmetry
    "lidar_coh100",              # 40: 3DEP sub-100m 100 m linear scarp coherence
    "full_line_max_1p5km",       # 41: 1.5 km 12-angle line integral on combined scarp + subsurface
    "full_line_aniso_1p5km",     # 42: 1.5 km directional anisotropy on combined scarp + subsurface
    "multi_slip_dilation",       # 43: Slip-dilation tendency including det_elev + subsurface strike
    # Group E: Explicit Non-Fault Mimic Indicators (cols 44..45)
    "mimic_road_corridor",       # 44: TIGER road proximity lacking gravity/basement-throw support
    "mimic_lahontan_shoreline",  # 45: Basin-margin contour bench lacking gravity/basement-throw support
]

ALL_STATIC_NAMES = BAND_NAMES_19 + GSD_HUA_EXTRA_NAMES  # 46 total static features

# Pure Subsurface + Geodetic + Seismic + Radiometric + Geothermal Tower (ZERO DEM / slope / LiDAR columns!)
PURE_SUBSURF_COLS = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17,  # All 17 non-topographic bands (excludes 11=det_elev, 18=det_elev_slope)
    19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,            # Subsurface potential-field, basement throw, MT & subsurface line integrals
    31, 32, 33, 34, 35, 36,                                    # Pure-subsurface slip-dilation, 2m probes, geothermometers, sinter, seismic-strain
    44,                                                        # Road mimic control
]


def impute_footprint_2d(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    out = np.asarray(arr, dtype=np.float32).copy()
    bad = (~np.isfinite(out)) | (np.abs(out) > 1e30) | (~fp)
    if bad.any():
        if (~bad).any():
            idx = distance_transform_edt(bad, return_distances=False, return_indices=True)
            out = out[tuple(idx)]
        else:
            out.fill(0.0)
    return out.astype(np.float32, copy=False)


def robust_z(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    vals = arr[fp]
    med = float(np.median(vals))
    iqr = float(np.percentile(vals, 75) - np.percentile(vals, 25))
    scale = max(iqr / 1.3489795, 1e-6)
    return np.clip((arr - med) / scale, -8.0, 8.0).astype(np.float32)


def grad_mag(arr: np.ndarray) -> np.ndarray:
    gx = sobel(arr, axis=1, mode="nearest") / 8.0
    gy = sobel(arr, axis=0, mode="nearest") / 8.0
    return np.hypot(gx, gy).astype(np.float32)


def _oriented_line_kernels(length_px: int, n_angles: int = 12) -> list[np.ndarray]:
    half = length_px // 2
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1].astype(np.float32)
    kernels = []
    for k in range(n_angles):
        theta = np.pi * k / n_angles
        d_perp = np.abs(-xx * np.sin(theta) + yy * np.cos(theta))
        d_para = np.abs(xx * np.cos(theta) + yy * np.sin(theta))
        w = np.maximum(1.25 - d_perp, 0.0) * (d_para <= half + 0.25)
        w /= max(float(w.sum()), 1e-6)
        kernels.append(w.astype(np.float32))
    return kernels


def _slip_dilation_from_potential(U: np.ndarray, dilate_z: np.ndarray, shear_z: np.ndarray) -> np.ndarray:
    ux = sobel(U, axis=1, mode="nearest") / 8.0
    uy = -sobel(U, axis=0, mode="nearest") / 8.0  # Northing upward
    jxx = gaussian_filter(ux * ux, sigma=6.0)
    jyy = gaussian_filter(uy * uy, sigma=6.0)
    jxy = gaussian_filter(ux * uy, sigma=6.0)
    alpha_n = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    psi_ext_math = np.deg2rad(-24.0)  # N114E WNW-ESE regional extension
    delta_ang = alpha_n - psi_ext_math
    td = np.cos(delta_ang) ** 2
    ts = np.abs(np.sin(2.0 * delta_ang))
    lam_diff = np.hypot(jxx - jyy, 2.0 * jxy)
    aniso = lam_diff / (jxx + jyy + 1e-5)
    strain_amp = 0.50 + 0.30 * np.maximum(dilate_z, 0.0) + 0.20 * np.maximum(shear_z, 0.0)
    return ((0.65 * td + 0.35 * ts) * aniso * strain_amp).astype(np.float32)


def _read_2m_probes(zip_path: Path, grid_transform, H: int, W: int) -> np.ndarray:
    impulse = np.zeros((H, W), dtype=np.float32)
    with zipfile.ZipFile(zip_path) as z:
        dbf = z.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    num_rec, hdr_len, rec_len = struct.unpack("<IHH", dbf[4:12])
    fields = []
    off = 32
    while dbf[off] != 0x0D:
        name = dbf[off:off + 11].split(b"\x00", 1)[0].decode("ascii", "replace")
        flen = dbf[off + 16]
        fields.append((name, flen))
        off += 32

    lons, lats, weights = [], [], []
    pos = hdr_len
    for _ in range(num_rec):
        if dbf[pos] == 0x2A:
            pos += rec_len
            continue
        rec = dbf[pos + 1:pos + rec_len]
        fo = 0
        row = {}
        for fn, fl in fields:
            if fn in ("LatDegreeN", "LongDegree", "T2m", "F2mDAB"):
                row[fn] = rec[fo:fo + fl].decode("ascii", "replace").strip()
            fo += fl
        pos += rec_len
        try:
            lon = float(row["LongDegree"])
            lat = float(row["LatDegreeN"])
        except (KeyError, ValueError):
            continue
        if not (-122.0 <= lon <= -114.0 and 37.0 <= lat <= 43.0):
            continue
        dab = t2m = 0.0
        try:
            dab = float(row.get("F2mDAB", "0") or 0.0)
        except ValueError:
            pass
        try:
            t2m = float(row.get("T2m", "0") or 0.0)
        except ValueError:
            pass
        w = max(dab, 0.0) + 0.15 * max(t2m - 18.0, 0.0) + 0.20
        lons.append(lon)
        lats.append(lat)
        weights.append(min(w, 25.0))

    if lons:
        xs, ys = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
        for x, y, w in zip(xs, ys, weights):
            r = int((grid_transform.f - y) / 100.0)
            c = int((x - grid_transform.c) / 100.0)
            if 0 <= r < H and 0 <= c < W:
                impulse[r, c] += float(w)
    plume = 0.65 * gaussian_filter(impulse, sigma=15.0) + 0.35 * gaussian_filter(impulse, sigma=40.0)
    return np.log1p(plume * 50.0).astype(np.float32)


def _read_wellspring_plume(csv_path: Path, H: int, W: int) -> np.ndarray:
    impulse = np.zeros((H, W), dtype=np.float32)
    with csv_path.open("r", errors="replace") as f:
        for row in csv.DictReader(f):
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError):
                continue
            if not (0 <= r < H and 0 <= c < W):
                continue
            tclass = row.get("thermalclass", "")
            w = 1.5 if tclass == "Hot" else (0.75 if tclass == "Warm" else 0.0)
            for col_name, thresh, scale in [
                ("temp_c", 22.0, 0.08),
                ("geothermquartz_c", 80.0, 0.03),
                ("geothermchalc_c", 65.0, 0.025),
            ]:
                val_s = row.get(col_name, "")
                if val_s and val_s.lower() != "nan":
                    try:
                        v = float(val_s)
                        if np.isfinite(v) and v > thresh and v < 360.0:
                            w += scale * (v - thresh)
                    except ValueError:
                        pass
            if w > 0.0:
                impulse[r, c] = max(impulse[r, c], min(w, 15.0))
    plume = 0.60 * gaussian_filter(impulse, sigma=20.0) + 0.40 * gaussian_filter(impulse, sigma=50.0)
    return np.log1p(plume * 40.0).astype(np.float32)


def _read_paleo_and_vents_plume(paleo_zip: Path, vents_csv: Path, grid_transform, H: int, W: int) -> np.ndarray:
    impulse = np.zeros((H, W), dtype=np.float32)
    with zipfile.ZipFile(paleo_zip) as z:
        with z.open("Paleo_geothermal_final.csv") as f:
            prows = list(csv.DictReader(line.decode("utf-8", "replace") for line in f))
    lons, lats, ws = [], [], []
    for row in prows:
        try:
            lon = float(row["Long_deg_NAD83"])
            lat = float(row["Lat_deg_NAD83"])
        except (KeyError, ValueError):
            continue
        dtype = (row.get("Deposit_type") or "").lower()
        w = 3.0 if "sinter" in dtype else (2.0 if "travertine" in dtype else 1.5)
        lons.append(lon)
        lats.append(lat)
        ws.append(w)
    if lons:
        xs, ys = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
        for x, y, w in zip(xs, ys, ws):
            r = int((grid_transform.f - y) / 100.0)
            c = int((x - grid_transform.c) / 100.0)
            if 0 <= r < H and 0 <= c < W:
                impulse[r, c] += float(w)

    with vents_csv.open("r", errors="replace") as f:
        for row in csv.DictReader(f):
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError):
                continue
            if 0 <= r < H and 0 <= c < W:
                impulse[r, c] += 1.0

    plume = 0.60 * gaussian_filter(impulse, sigma=18.0) + 0.40 * gaussian_filter(impulse, sigma=45.0)
    return np.log1p(plume * 40.0).astype(np.float32)


def build_or_load_static_stack(data_root: Path, feat_dir: Path, fp: np.ndarray) -> tuple[np.memmap, list[str]]:
    """Build or open the (5_167_373, 46) float32 memory-mapped static feature matrix."""
    feat_dir.mkdir(parents=True, exist_ok=True)
    mmap_path = feat_dir / "gsd_hua_static_v2.npy"
    meta_path = feat_dir / "gsd_hua_static_v2.json"
    n_fp = int(fp.sum())
    n_cols = len(ALL_STATIC_NAMES)

    if mmap_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("shape") == [n_fp, n_cols] and meta.get("feature_names") == ALL_STATIC_NAMES:
            mm = np.lib.format.open_memmap(mmap_path, mode="r", dtype=np.float32)
            return mm, ALL_STATIC_NAMES

    H, W = fp.shape
    with rasterio.open(data_root / "sample_submission.tif") as s:
        grid_transform = s.transform

    mm = np.lib.format.open_memmap(mmap_path, mode="w+", dtype=np.float32, shape=(n_fp, n_cols))

    keep = {}
    needed = {2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 19}
    for b in range(1, 20):
        raw = np.load(feat_dir / f"band-{b:02d}.npy")
        clean = impute_footprint_2d(raw, fp)
        mm[:, b - 1] = clean[fp]
        if b in needed:
            keep[b] = clean
        del raw

    rtp = keep[2]
    tmi_hg = keep[3]
    geod_2nd = keep[4]
    grav_slope = keep[5]
    geod_shear = keep[7]
    geod_dilate = keep[8]
    tmi_vg = keep[9]
    deq = keep[10]
    grav_vg = keep[11]
    det_elev = keep[12]
    grav_iso = keep[13]
    depth_base = keep[15]
    ieq = keep[16]
    cond_surf = keep[17]
    elev_slope = keep[19]

    # Group B: Pure Subsurface Potential-Field, Basement-Throw, Alteration & MT Edges
    true_mag_tilt = np.arctan2(tmi_vg, np.hypot(tmi_hg, 1e-3)).astype(np.float32)
    true_mag_tilt_hg = grad_mag(gaussian_filter(true_mag_tilt, sigma=1.2))
    mm[:, 19] = true_mag_tilt[fp]
    mm[:, 20] = true_mag_tilt_hg[fp]

    with rasterio.open(data_root / "external/geodawn_extensions_u8.tif") as src:
        th_k = impute_footprint_2d(src.read(1).astype(np.float32), fp)
        u_k = impute_footprint_2d(src.read(2).astype(np.float32), fp)
        u_th = impute_footprint_2d(src.read(3).astype(np.float32), fp)
        tmi_up150 = impute_footprint_2d(src.read(4).astype(np.float32), fp)

    mag_destr = (robust_z(tmi_up150, fp) - robust_z(rtp, fp)).astype(np.float32)
    mm[:, 21] = mag_destr[fp]
    mm[:, 22] = th_k[fp]
    mm[:, 23] = u_k[fp]
    mm[:, 24] = u_th[fp]
    del th_k, u_k, u_th, tmi_up150, mag_destr

    clay_cap_edge = grad_mag(gaussian_filter(cond_surf, sigma=1.5))
    grav_tilt = np.arctan2(grav_vg, np.hypot(grav_slope, 1e-4)).astype(np.float32)
    basin_wall_grad = grad_mag(gaussian_filter(depth_base, sigma=2.0))
    basin_cover_log = np.log1p(np.maximum(depth_base, 0.0)).astype(np.float32)
    mm[:, 25] = clay_cap_edge[fp]
    mm[:, 26] = grav_tilt[fp]
    mm[:, 27] = basin_wall_grad[fp]
    mm[:, 28] = basin_cover_log[fp]
    del grav_tilt, basin_cover_log

    # Pure subsurface 2.5 km (25 px) 12-azimuth oriented line integral (ZERO DEM/slope!)
    z_grav_pos = np.maximum(robust_z(grav_slope, fp), 0.0)
    z_bwall_pos = np.maximum(robust_z(basin_wall_grad, fp), 0.0)
    z_maghg_pos = np.maximum(robust_z(true_mag_tilt_hg, fp), 0.0)
    z_clay_pos = np.maximum(robust_z(clay_cap_edge, fp), 0.0)
    subsurf_edge = (0.34 * z_bwall_pos + 0.30 * z_grav_pos + 0.22 * z_maghg_pos + 0.14 * z_clay_pos).astype(np.float32)

    ks_25 = _oriented_line_kernels(25, n_angles=12)
    s_lmax = np.full((H, W), -1e9, dtype=np.float32)
    s_lsum = np.zeros((H, W), dtype=np.float32)
    for k in ks_25:
        resp = convolve(subsurf_edge, k, mode="nearest")
        np.maximum(s_lmax, resp, out=s_lmax)
        s_lsum += resp
    mm[:, 29] = s_lmax[fp]
    mm[:, 30] = (s_lmax - s_lsum / float(len(ks_25)))[fp]
    del s_lmax, s_lsum

    # Group C: Mechano-Thermal Slip-Dilation & GDR #1391 Fluid-Upflow Plumes
    dilate_z = robust_z(geod_dilate, fp)
    shear_z = robust_z(geod_shear, fp)
    U_sub = (0.40 * robust_z(depth_base, fp) + 0.35 * robust_z(grav_iso, fp) + 0.25 * robust_z(true_mag_tilt, fp)).astype(np.float32)
    sub_slip_dil = _slip_dilation_from_potential(U_sub, dilate_z, shear_z)
    mm[:, 31] = sub_slip_dil[fp]
    del U_sub

    probe_2m = _read_2m_probes(
        data_root / "external/2m_temperature_probe_INGENIOUS_regional_data.zip",
        grid_transform, H, W,
    )
    spring_plume = _read_wellspring_plume(data_root / "external/gdr_wellspring_in_footprint.csv", H, W)
    paleo_plume = _read_paleo_and_vents_plume(
        data_root / "external/paleo_geothermal_regional.zip",
        data_root / "external/gdr_volcanic_vents_in_footprint.csv",
        grid_transform, H, W,
    )
    mm[:, 32] = probe_2m[fp]
    mm[:, 33] = spring_plume[fp]
    mm[:, 34] = paleo_plume[fp]

    thermal_sum = 0.45 * spring_plume + 0.35 * probe_2m + 0.20 * paleo_plume
    mech_therm = (sub_slip_dil * thermal_sum * (subsurf_edge + 0.25)).astype(np.float32)
    seis_strain = (
        np.log1p(np.maximum(ieq, 0.0)) * (np.maximum(robust_z(geod_2nd, fp), 0.0) + 0.5)
        / np.log1p(np.maximum(deq, 0.0) + 200.0)
    ).astype(np.float32)
    mm[:, 35] = mech_therm[fp]
    mm[:, 36] = seis_strain[fp]
    del probe_2m, spring_plume, paleo_plume, thermal_sum, mech_therm, seis_strain, sub_slip_dil

    # Group D: Geomorphic Piedmont Toe, 3DEP Sub-100m Scarp, & Full-Sensor Line Integrals
    slope_up = gaussian_filter(elev_slope, sigma=8.0) - gaussian_filter(elev_slope, sigma=1.5)
    concav = np.maximum(-laplace(gaussian_filter(det_elev, sigma=2.0)), 0.0)
    piedmont_toe = (np.maximum(slope_up, 0.0) * np.log1p(concav)).astype(np.float32)
    elev_r500 = (det_elev - gaussian_filter(det_elev, sigma=5.0)).astype(np.float32)
    mm[:, 37] = piedmont_toe[fp]
    mm[:, 38] = elev_r500[fp]
    del slope_up, concav, elev_r500

    with rasterio.open(data_root / "external/lidar_scarp_features_u8.tif") as src:
        step_max = src.read(3).astype(np.float32)
        down_max = src.read(6).astype(np.float32)
        coh100 = src.read(10).astype(np.float32)
        lvalid = (src.read(12) > 0).astype(np.float32)
    mm[:, 39] = ((0.5 * step_max + 0.5 * down_max) * lvalid)[fp]
    mm[:, 40] = (coh100 * lvalid)[fp]
    del step_max, down_max, coh100, lvalid

    full_edge = (
        0.30 * np.maximum(robust_z(elev_slope, fp), 0.0)
        + 0.25 * np.maximum(robust_z(piedmont_toe, fp), 0.0)
        + 0.45 * subsurf_edge
    ).astype(np.float32)
    ks_15 = _oriented_line_kernels(15, n_angles=12)
    f_lmax = np.full((H, W), -1e9, dtype=np.float32)
    f_lsum = np.zeros((H, W), dtype=np.float32)
    for k in ks_15:
        resp = convolve(full_edge, k, mode="nearest")
        np.maximum(f_lmax, resp, out=f_lmax)
        f_lsum += resp
    mm[:, 41] = f_lmax[fp]
    mm[:, 42] = (f_lmax - f_lsum / float(len(ks_15)))[fp]
    del full_edge, f_lmax, f_lsum, piedmont_toe, subsurf_edge

    U_full = (0.40 * robust_z(det_elev, fp) + 0.35 * robust_z(grav_iso, fp) + 0.25 * robust_z(true_mag_tilt, fp)).astype(np.float32)
    mm[:, 43] = _slip_dilation_from_potential(U_full, dilate_z, shear_z)[fp]
    del U_full, dilate_z, shear_z

    # Group E: Explicit Non-Fault Mimic Indicators
    with rasterio.open(data_root / "external/tiger_road_distance_m.tif") as src:
        road_d = impute_footprint_2d(src.read(1).astype(np.float32), fp)
    sig_grav = 1.0 / (1.0 + np.exp(-robust_z(grav_slope, fp)))
    sig_bwall = 1.0 / (1.0 + np.exp(-robust_z(basin_wall_grad, fp)))
    mimic_road = (np.exp(-np.maximum(road_d, 0.0) / 150.0) * (1.0 - sig_grav) * (1.0 - sig_bwall)).astype(np.float32)
    mimic_shore = (
        np.exp(-(((det_elev - (-140.0)) / 45.0) ** 2))
        * np.exp(-(((elev_slope - 3.0) / 2.2) ** 2))
        * (1.0 - sig_grav)
        * (1.0 - sig_bwall)
    ).astype(np.float32)
    mm[:, 44] = mimic_road[fp]
    mm[:, 45] = mimic_shore[fp]

    del road_d, sig_grav, sig_bwall, mimic_road, mimic_shore, keep, basin_wall_grad, clay_cap_edge, true_mag_tilt, true_mag_tilt_hg
    mm.flush()
    gc.collect()

    meta_path.write_text(json.dumps({
        "schema_version": 2,
        "shape": [n_fp, n_cols],
        "feature_names": ALL_STATIC_NAMES,
    }, indent=2) + "\n")

    mm_ro = np.lib.format.open_memmap(mmap_path, mode="r", dtype=np.float32)
    return mm_ro, ALL_STATIC_NAMES


def compute_fold_visible_tip_and_relay(visible_mask: np.ndarray, fp: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    vis = np.asarray(visible_mask, dtype=bool) & fp
    d_vis = distance_transform_edt(~vis).astype(np.float32)
    d_vis_clamped_log = np.log1p(np.clip(d_vis, 3.5, 120.0)).astype(np.float32)

    nb_count = convolve(vis.astype(np.int16), np.ones((3, 3), dtype=np.int16), mode="constant", cval=0) - 1
    tips = vis & (nb_count >= 1) & (nb_count <= 1)
    ty, tx = np.nonzero(tips)
    H, W = fp.shape
    beam = np.zeros((H, W), dtype=np.float32)

    if ty.size > 0:
        for r0, c0 in zip(ty.tolist(), tx.tolist()):
            y0, y1 = max(0, r0 - 8), min(H, r0 + 9)
            x0, x1 = max(0, c0 - 8), min(W, c0 + 9)
            sub = vis[y0:y1, x0:x1]
            ry, rx = np.nonzero(sub)
            dy_in = (ry.astype(np.float32) + y0) - float(r0)
            dx_in = (rx.astype(np.float32) + x0) - float(c0)
            dist_in = np.hypot(dy_in, dx_in)
            sel = (dist_in >= 2.0) & (dist_in <= 8.5)
            if int(sel.sum()) < 2:
                continue
            vy = -float(dy_in[sel].mean())
            vx = -float(dx_in[sel].mean())
            norm = float(np.hypot(vy, vx))
            if norm < 0.5:
                continue
            vy /= norm
            vx /= norm

            R = 38
            by0, by1 = max(0, r0 - R), min(H, r0 + R + 1)
            bx0, bx1 = max(0, c0 - R), min(W, c0 + R + 1)
            gy, gx = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
            oy = gy - float(r0)
            ox = gx - float(c0)
            s_along = oy * vy + ox * vx
            s_perp = np.abs(-oy * vx + ox * vy)
            in_cone = (s_along >= 3.0) & (s_along <= float(R))
            if not in_cone.any():
                continue
            sigma_perp = 1.6 + 0.14 * np.maximum(s_along, 0.0)
            lobe = (
                in_cone.astype(np.float32)
                * np.exp(-0.5 * ((s_perp / sigma_perp) ** 2))
                * np.exp(-np.maximum(s_along - 3.0, 0.0) / 16.0)
            )
            lobe *= (d_vis[by0:by1, bx0:bx1] >= 3.0).astype(np.float32)
            cur = beam[by0:by1, bx0:bx1]
            beam[by0:by1, bx0:bx1] = cur + lobe + 0.65 * np.minimum(cur, lobe)

    beam = np.tanh(beam * 0.85).astype(np.float32)
    return beam[fp], d_vis_clamped_log[fp]
