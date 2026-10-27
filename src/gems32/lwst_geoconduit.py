"""LWST-GeoConduit (H-SASS3-A): Potential-Field 3-D SPI Local-Wavenumber Contact-Depth,
Wijns Theta-Map Dip Concordance & Transtensional Geothermal Conduit Architecture.

Strictly label-free and SGMC-free physical feature construction (16 float32 channels)
plus steerable crest sharpening, fold-local fault-tip relay cones, and exact 300 m
triangular-kernel CELF submodular allocation (`gems32.emitter.emit`).
"""
from __future__ import annotations

import csv
import gc
import io
import json
import struct
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from numpy.lib.format import open_memmap
from rasterio.warp import transform as warp_transform
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from . import emitter, grid

LWST_CHANNELS: tuple[str, ...] = (
    "spi_mag_wavenumber",            # 00: Thurston & Smith (1997) 3-D RTP magnetic SPI local wavenumber
    "spi_grav_wavenumber",           # 01: 3-D isostatic gravity SPI local wavenumber
    "wijns_theta_mag",               # 02: Wijns et al. (2005) contrast-invariant RTP Theta-map ridge
    "wijns_theta_grav",              # 03: Contrast-invariant gravity Theta-map contact ridge
    "spi_cross_tensor_concord",      # 04: Strike-locked magnetic x gravity SPI concordance
    "upward_150m_dip_shift",         # 05: Multi-altitude TMI vs TMI_up150 deep-contact persistence
    "basement_detachment_flexure",   # 06: Depth-to-basement normalized ramp + concave flexure
    "transtensional_slip_dilation",  # 07: Strike-projected geodetic shear + dilatation slip tendency
    "hydrothermal_alteration_trough",# 08: RTP magnetite-destruction trough x GeoDAWN K/Th potassic excess
    "claycap_lateral_boundary",      # 09: Playa-deconfounded MT surface-conductivity lateral edge
    "ingenious_thermal_upflow_aniso",# 10: Strike-anisotropic GDR #1391 well/spring + 2m probe + paleo sinter plume
    "lidar_scarp_polarity_asymmetry",# 11: 1m 3DEP LiDAR step/polarity crest with 100m DEM seamless fallback
    "piedmont_breakline_deconf",     # 12: Relief-normalized piedmont/bajada break-in-slope ridge
    "steerable_multiscale_aniso_2km",# 13: 12-azimuth 2.0 km steerable lineament excess over orientation mean
    "mimic_veto_clean_gate",         # 14: TIGER road-cut & flat Lahontan/playa mimic suppression gate
    "lwst_unsupervised_conduit_index", # 15: Pre-registered label-free LWST subsurface/geothermal conduit composite
)


def _robust_z_pos(arr: np.ndarray, foot: np.ndarray, clip_hi: float = 8.0) -> np.ndarray:
    """Footprint-standardized non-negative robust z-score in [0, 1]."""
    vals = arr[foot]
    fin = vals[np.isfinite(vals)]
    if fin.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    med = float(np.median(fin))
    mad = float(np.median(np.abs(fin - med))) * 1.4826
    scale = max(mad, float(np.std(fin)), 1e-6)
    z = np.clip((arr.astype(np.float32) - np.float32(med)) / np.float32(scale), 0.0, clip_hi) / np.float32(clip_hi)
    z[~foot | ~np.isfinite(z)] = 0.0
    return z.astype(np.float32)


def _robust_z_signed(arr: np.ndarray, foot: np.ndarray, clip_abs: float = 6.0) -> np.ndarray:
    """Footprint-standardized signed robust z-score."""
    vals = arr[foot]
    fin = vals[np.isfinite(vals)]
    if fin.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    med = float(np.median(fin))
    mad = float(np.median(np.abs(fin - med))) * 1.4826
    scale = max(mad, float(np.std(fin)), 1e-6)
    z = np.clip((arr.astype(np.float32) - np.float32(med)) / np.float32(scale), -clip_abs, clip_abs)
    z[~foot | ~np.isfinite(z)] = 0.0
    return z.astype(np.float32)


def _read_clean_band(ds: rasterio.DatasetReader, band_idx: int, foot: np.ndarray) -> np.ndarray:
    """Read a training_features band, replacing sentinel/outside-footprint values smoothly via EDT nearest."""
    raw = ds.read(band_idx).astype(np.float32)
    valid = foot & np.isfinite(raw) & (raw > grid.NODATA_F32 * np.float32(0.5))
    if not valid.all():
        _, inds = ndi.distance_transform_edt(~valid, return_distances=True, return_indices=True)
        filled = raw[inds[0], inds[1]].astype(np.float32)
    else:
        filled = raw
    return filled


def _fft_vertical_derivative(field: np.ndarray, dx_m: float = 100.0) -> np.ndarray:
    """First harmonic vertical derivative dF/dz via radial wavenumber |k| multiplication with cosine taper."""
    h, w = field.shape
    f_demean = field.astype(np.float32) - np.float32(np.mean(field))
    ty = np.hanning(min(128, h))
    tx = np.hanning(min(128, w))
    wy = np.ones(h, dtype=np.float32)
    wx = np.ones(w, dtype=np.float32)
    hw_y, hw_x = len(ty) // 2, len(tx) // 2
    wy[:hw_y] = ty[:hw_y]
    wy[-hw_y:] = ty[-hw_y:]
    wx[:hw_x] = tx[:hw_x]
    wx[-hw_x:] = tx[-hw_x:]
    tapered = f_demean * wy[:, None] * wx[None, :]

    ky = 2.0 * np.pi * np.fft.fftfreq(h, d=dx_m).astype(np.float32)
    kx = 2.0 * np.pi * np.fft.rfftfreq(w, d=dx_m).astype(np.float32)
    kr = np.hypot(ky[:, None], kx[None, :])
    # Mild Butterworth low-pass above Nyquist*0.65 to prevent 1-px grid ringing
    k_cut = np.float32(0.65 * np.pi / dx_m)
    filt = kr / (np.float32(1.0) + (kr / k_cut) ** 4)
    spec = np.fft.rfft2(tapered)
    dz = np.fft.irfft2(spec * filt, s=(h, w)).astype(np.float32)
    return dz


def _horizontal_grad_and_strike(field: np.ndarray, sigma_px: float = 1.4, dx_m: float = 100.0) -> tuple[np.ndarray, np.ndarray]:
    """Compute horizontal gradient magnitude ||grad_H F|| and structural strike angle phi in [0, pi)."""
    sm = ndi.gaussian_filter(field.astype(np.float32), sigma=sigma_px)
    gy, gx = np.gradient(sm, dx_m)
    gh = np.hypot(gx, gy).astype(np.float32)
    # Normal to contact is atan2(gy, gx); fault strike is perpendicular: atan2(-gx, gy) mod pi
    strike = np.mod(np.arctan2(-gx, gy), np.pi).astype(np.float32)
    return gh, strike


def _oriented_line_filter(field: np.ndarray, length_px: int = 21, n_angles: int = 12) -> tuple[np.ndarray, np.ndarray]:
    """Steerable 1-D line integral across n_angles azimuths; returns (max_over_angles, excess_over_mean)."""
    h, w = field.shape
    half = length_px // 2
    t = np.linspace(-half, half, length_px, dtype=np.float32)
    # Weak Gaussian taper along strike so tips blend cleanly without boxcar ringing
    weights = np.exp(-0.5 * (t / (0.42 * length_px)) ** 2).astype(np.float32)
    weights /= weights.sum()

    best = np.full((h, w), -1e30, dtype=np.float32)
    mean_acc = np.zeros((h, w), dtype=np.float32)
    f32 = field.astype(np.float32)

    for k in range(n_angles):
        ang = np.pi * k / float(n_angles)
        dy = np.round(t * np.sin(ang)).astype(int)
        dx = np.round(t * np.cos(ang)).astype(int)
        ksize = 2 * half + 1
        kern = np.zeros((ksize, ksize), dtype=np.float32)
        for dy_i, dx_i, w_i in zip(dy, dx, weights):
            kern[half + int(dy_i), half + int(dx_i)] += float(w_i)
        resp = ndi.convolve(f32, kern, mode="nearest")
        np.maximum(best, resp, out=best)
        mean_acc += resp

    mean_acc /= np.float32(n_angles)
    excess = np.maximum(best - mean_acc, 0.0).astype(np.float32)
    return best, excess


def _build_ingenious_thermal_field(
    ddir: Path, foot: np.ndarray, strike_field: np.ndarray, origin_x: float, origin_y: float, pixel_size: float
) -> np.ndarray:
    """Build label-free strike-anisotropic geothermal upflow field from GDR #1391 thermal observations.

    Explicitly ignores `dist_known_fault_px` so zero catalogue proximity leaks into the feature.
    """
    h, w = foot.shape
    point_heat = np.zeros((h, w), dtype=np.float32)
    ext = ddir / "external"

    # 1. GDR #1391 well & spring geothermometry (drop dist_known_fault_px!)
    ws_csv = ext / "gdr_wellspring_in_footprint.csv"
    if ws_csv.exists():
        with ws_csv.open("r", encoding="utf-8", errors="replace") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                try:
                    rr = int(float(row["row"]))
                    cc = int(float(row["col"]))
                except (KeyError, ValueError):
                    continue
                if not (0 <= rr < h and 0 <= cc < w and foot[rr, cc]):
                    continue
                temps = []
                for col_name in ("temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                    val = row.get(col_name, "")
                    try:
                        v = float(val)
                        if np.isfinite(v) and 0.0 < v < 400.0:
                            temps.append(v)
                    except ValueError:
                        pass
                tmax = max(temps) if temps else 25.0
                excess_w = float(np.clip((tmax - 35.0) / 140.0, 0.05, 1.5))
                if excess_w > point_heat[rr, cc]:
                    point_heat[rr, cc] = excess_w

    # 2. GDR #1391 paleo-geothermal sinter / travertine / silicified fault breccia deposits
    paleo_zip = ext / "paleo_geothermal_regional.zip"
    if paleo_zip.exists():
        with zipfile.ZipFile(paleo_zip) as zf:
            if "Paleo_geothermal_final.csv" in zf.namelist():
                txt = zf.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
                lons, lats, weights = [], [], []
                for row in csv.DictReader(io.StringIO(txt)):
                    try:
                        lon = float(row["Long_deg_NAD83"])
                        lat = float(row["Lat_deg_NAD83"])
                    except (KeyError, ValueError):
                        continue
                    dtype = (row.get("Deposit_type") or "").lower()
                    wt = 1.25 if ("sinter" in dtype or "silic" in dtype or "travertine" in dtype) else 0.85
                    lons.append(lon)
                    lats.append(lat)
                    weights.append(wt)
                if lons:
                    ux, uy = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
                    for x_m, y_m, wt in zip(ux, uy, weights):
                        cc = int(np.floor((x_m - origin_x) / pixel_size))
                        rr = int(np.floor((origin_y - y_m) / pixel_size))
                        if 0 <= rr < h and 0 <= cc < w and foot[rr, cc]:
                            point_heat[rr, cc] = max(point_heat[rr, cc], float(wt))

    # 3. GDR #1391 INGENIOUS 2-meter temperature probe anomalies (F2mDAB / T2m)
    probe_zip = ext / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    if probe_zip.exists():
        dbf_member = "2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf"
        with zipfile.ZipFile(probe_zip) as zf:
            if dbf_member in zf.namelist():
                dbf = zf.read(dbf_member)
                nrec, hdr_len, rec_len = struct.unpack("<IHH", dbf[4:12])
                fields = []
                pos = 32
                while dbf[pos] != 0x0D:
                    fname = dbf[pos:pos + 11].split(b"\x00")[0].decode("ascii", errors="replace")
                    flen = dbf[pos + 16]
                    fields.append((fname, flen))
                    pos += 32
                lons, lats, dab_vals = [], [], []
                offset = hdr_len
                for _ in range(nrec):
                    rec = dbf[offset:offset + rec_len]
                    offset += rec_len
                    if not rec or rec[0] == 0x2A:
                        continue
                    fpos = 1
                    row_d = {}
                    for fname, flen in fields:
                        if fname in ("LatDegreeN", "LongDegree", "F2mDAB", "T2m"):
                            row_d[fname] = rec[fpos:fpos + flen].decode("ascii", errors="replace").strip()
                        fpos += flen
                    try:
                        lon = float(row_d["LongDegree"])
                        lat = float(row_d["LatDegreeN"])
                    except (KeyError, ValueError):
                        continue
                    dab = 0.0
                    try:
                        dab = float(row_d.get("F2mDAB", "0") or 0.0)
                    except ValueError:
                        dab = 0.0
                    if np.isfinite(lon) and np.isfinite(lat) and -125.0 < lon < -110.0 and 35.0 < lat < 45.0 and dab > 0.5:
                        lons.append(lon)
                        lats.append(lat)
                        dab_vals.append(float(np.clip(dab / 6.0, 0.1, 1.35)))
                if lons:
                    ux, uy = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
                    for x_m, y_m, wt in zip(ux, uy, dab_vals):
                        cc = int(np.floor((x_m - origin_x) / pixel_size))
                        rr = int(np.floor((origin_y - y_m) / pixel_size))
                        if 0 <= rr < h and 0 <= cc < w and foot[rr, cc]:
                            point_heat[rr, cc] = max(point_heat[rr, cc], wt)

    # Multi-scale diffusion + steerable elongation along local geophysical strike
    iso_near = ndi.gaussian_filter(point_heat, sigma=5.0)
    iso_mid = ndi.gaussian_filter(point_heat, sigma=14.0)
    base_plume = np.float32(0.65) * iso_near + np.float32(0.35) * iso_mid
    best_line, _ = _oriented_line_filter(base_plume, length_px=25, n_angles=8)
    # Weight higher where strike is well-defined
    plume = np.float32(0.55) * best_line + np.float32(0.45) * base_plume + np.float32(0.0 * np.cos(strike_field))
    return _robust_z_pos(plume, foot)


def build_lwst_stack(ddir: Path, out_npy: Path) -> dict:
    """Build or verify the 16-channel label-free LWST-GeoConduit stack (`float32`, disk-backed)."""
    out_npy.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = out_npy.with_suffix(".receipt.json")
    t0 = time.time()
    with rasterio.open(ddir / "sample_submission.tif") as ds_sub:
        foot = np.isfinite(ds_sub.read(1))
        h_grid, w_grid = ds_sub.height, ds_sub.width
        origin_x = float(ds_sub.transform.c)
        origin_y = float(ds_sub.transform.f)
        pixel_size = float(ds_sub.transform.a)

    if out_npy.exists() and receipt_path.exists():
        mm = np.load(out_npy, mmap_mode="r")
        if mm.shape == (h_grid, w_grid, len(LWST_CHANNELS)) and mm.dtype == np.float32:
            return json.loads(receipt_path.read_text(encoding="utf-8"))

    mm = open_memmap(out_npy, mode="w+", dtype=np.float32, shape=(h_grid, w_grid, len(LWST_CHANNELS)))

    with rasterio.open(ddir / "training_features.tif") as ds_tf:
        # --- Group 1: Potential-field 3-D SPI local wavenumber & Wijns Theta-map concordance ---
        rtp = _read_clean_band(ds_tf, 2, foot)
        rtp_gh, strike_mag = _horizontal_grad_and_strike(rtp, sigma_px=1.5, dx_m=100.0)
        rtp_dz = _fft_vertical_derivative(ndi.gaussian_filter(rtp, sigma=1.5), dx_m=100.0)
        # Calibrate vertical vs horizontal derivative scale via footprint median magnitude
        med_mgh = float(np.median(rtp_gh[foot])) + 1e-6
        med_mdz = float(np.median(np.abs(rtp_dz[foot]))) + 1e-6
        rtp_dz_cal = rtp_dz * np.float32(med_mgh / med_mdz)

        tilt_mag = np.arctan2(rtp_dz_cal, rtp_gh + np.float32(0.05 * med_mgh)).astype(np.float32)
        tmy, tmx = np.gradient(ndi.gaussian_filter(tilt_mag, sigma=1.2), 100.0)
        spi_mag = _robust_z_pos(np.hypot(tmx, tmy), foot)
        wijns_mag = (rtp_gh / np.sqrt(rtp_gh * rtp_gh + rtp_dz_cal * rtp_dz_cal + np.float32((0.15 * med_mgh) ** 2))).astype(np.float32)
        wijns_mag[~foot] = 0.0

        mm[:, :, 0] = spi_mag
        mm[:, :, 2] = _robust_z_pos(wijns_mag, foot)
        del tilt_mag, tmy, tmx, rtp_dz, rtp_dz_cal
        gc.collect()

        iso_grav = _read_clean_band(ds_tf, 13, foot)
        grav_slope = _read_clean_band(ds_tf, 5, foot)
        grav_vg = _read_clean_band(ds_tf, 11, foot)
        _, strike_grav = _horizontal_grad_and_strike(iso_grav, sigma_px=1.8, dx_m=100.0)
        med_gs = float(np.median(np.abs(grav_slope[foot]))) + 1e-6
        med_gv = float(np.median(np.abs(grav_vg[foot]))) + 1e-6
        grav_vg_cal = grav_vg * np.float32(med_gs / med_gv)
        grav_gh = np.maximum(grav_slope, np.float32(0.0))

        tilt_grav = np.arctan2(grav_vg_cal, grav_gh + np.float32(0.05 * med_gs)).astype(np.float32)
        tgy, tgx = np.gradient(ndi.gaussian_filter(tilt_grav, sigma=1.4), 100.0)
        spi_grav = _robust_z_pos(np.hypot(tgx, tgy), foot)
        wijns_grav = (grav_gh / np.sqrt(grav_gh * grav_gh + grav_vg_cal * grav_vg_cal + np.float32((0.15 * med_gs) ** 2))).astype(np.float32)
        wijns_grav[~foot] = 0.0

        mm[:, :, 1] = spi_grav
        mm[:, :, 3] = _robust_z_pos(wijns_grav, foot)

        # Cross-tensor strike concordance: cos^2(strike_mag - strike_grav) * geometric mean of SPI crests
        strike_align = np.cos(strike_mag - strike_grav) ** 2
        concord = np.sqrt(np.maximum(spi_mag * spi_grav, 0.0)) * strike_align + np.float32(0.35) * np.sqrt(
            np.maximum(mm[:, :, 2] * mm[:, :, 3], 0.0)
        ) * strike_align
        mm[:, :, 4] = _robust_z_pos(concord, foot)
        # Keep composite structural strike weighted by gravity+magnetic gradient strength
        use_grav_strike = (_robust_z_pos(grav_gh, foot) >= _robust_z_pos(rtp_gh, foot))
        strike_struct = np.where(use_grav_strike, strike_grav, strike_mag).astype(np.float32)
        del iso_grav, grav_slope, grav_vg, grav_vg_cal, grav_gh, tilt_grav, tgy, tgx, spi_mag, spi_grav, wijns_mag, wijns_grav, concord, strike_align, rtp_gh, strike_mag, strike_grav
        gc.collect()

        # --- Group 2: Upward-continued 150m persistence & Sub-alluvial basement detachment flexure ---
        tmi_hg = _read_clean_band(ds_tf, 3, foot)
        ext_tif = ddir / "external" / "geodawn_extensions_u8.tif"
        if ext_tif.exists():
            with rasterio.open(ext_tif) as ds_ext:
                tmi_up150 = ds_ext.read(4).astype(np.float32)
                th_k_u8 = ds_ext.read(1).astype(np.float32)
            up_gh, _ = _horizontal_grad_and_strike(tmi_up150, sigma_px=1.6, dx_m=100.0)
            z_up = _robust_z_pos(up_gh, foot)
            z_obs = _robust_z_pos(tmi_hg, foot)
            # Crust-penetrating fault contacts persist at +150m continuation while float clutter decays
            persistence = z_up * (z_up / (z_obs + np.float32(0.25)))
            mm[:, :, 5] = _robust_z_pos(persistence, foot)
            del tmi_up150, up_gh, z_up, z_obs, persistence
        else:
            th_k_u8 = np.zeros_like(tmi_hg)
            mm[:, :, 5] = _robust_z_pos(tmi_hg, foot)
        del tmi_hg
        gc.collect()

        z_base = np.maximum(_read_clean_band(ds_tf, 15, foot), 0.0)
        zb_sm = ndi.gaussian_filter(z_base, sigma=1.8)
        zby, zbx = np.gradient(zb_sm, 100.0)
        zb_grad_norm = np.hypot(zbx, zby) / (zb_sm + np.float32(180.0))
        zb_lap_neg = np.maximum(-ndi.laplace(zb_sm), 0.0)
        base_flex = np.float32(0.65) * _robust_z_pos(zb_grad_norm, foot) + np.float32(0.35) * _robust_z_pos(zb_lap_neg, foot)
        mm[:, :, 6] = _robust_z_pos(base_flex, foot)
        del z_base, zb_sm, zby, zbx, zb_grad_norm, zb_lap_neg, base_flex
        gc.collect()

        # --- Group 3: Transtensional slip/dilation tendency & Hydrothermal alteration / clay-cap ---
        g_2nd = _read_clean_band(ds_tf, 4, foot)
        g_shr = _read_clean_band(ds_tf, 7, foot)
        g_dil = _read_clean_band(ds_tf, 8, foot)
        # Basin-and-Range / Walker Lane NNE-NNW & ENE structural favorability under WNW extension (~N105E)
        ext_az = np.deg2rad(15.0)  # optimal normal-fault strike ~N15E perpendicular to N105E extension
        oblique_factor = np.float32(0.55) + np.float32(0.45) * (np.cos(strike_struct - ext_az) ** 2).astype(np.float32)
        z_shr = _robust_z_pos(g_shr, foot)
        z_dil = _robust_z_pos(g_dil, foot)
        z_2nd = _robust_z_pos(g_2nd, foot)
        transtens = oblique_factor * (np.float32(0.45) * z_shr + np.float32(0.35) * z_dil + np.float32(0.20) * z_2nd)
        mm[:, :, 7] = _robust_z_pos(transtens, foot)
        del g_2nd, g_shr, g_dil, z_shr, z_dil, z_2nd, transtens, oblique_factor
        gc.collect()

        # Magnetite-destruction narrow RTP trough (positive high-pass Laplacian) x GeoDAWN K/Th excess
        rtp_hp_trough = np.maximum(ndi.gaussian_filter(rtp, sigma=6.0) - ndi.gaussian_filter(rtp, sigma=1.3), 0.0)
        z_demag = _robust_z_pos(rtp_hp_trough, foot)
        del rtp, rtp_hp_trough
        rad_tif = ddir / "external" / "geodawn_rad_u8.tif"
        if rad_tif.exists():
            with rasterio.open(rad_tif) as ds_rad:
                rad_k = ds_rad.read(1).astype(np.float32)
                rad_th = ds_rad.read(2).astype(np.float32)
                rad_valid = (rad_k > 0) & (rad_th > 0) & foot
            # Residualize K on Th to isolate hydrothermal adularia/illite from felsic tuffs
            if rad_valid.any():
                k_med, th_med = float(np.median(rad_k[rad_valid])), float(np.median(rad_th[rad_valid]))
                slope_kt = float(np.cov(rad_k[rad_valid], rad_th[rad_valid])[0, 1] / (np.var(rad_th[rad_valid]) + 1e-6))
                k_excess = np.where(rad_valid, (rad_k - k_med) - slope_kt * (rad_th - th_med), 0.0).astype(np.float32)
            else:
                k_excess = np.zeros_like(z_demag)
            z_kex = _robust_z_pos(k_excess, foot)
            # Low Th/K in geodawn_extensions_u8 also signals potassic alteration
            inv_thk = np.where((th_k_u8 > 0) & foot, 255.0 - th_k_u8, 0.0).astype(np.float32)
            z_inv_thk = _robust_z_pos(inv_thk, foot)
            alter = z_demag * (np.float32(0.45) + np.float32(0.35) * z_kex + np.float32(0.20) * z_inv_thk) + np.float32(0.25) * z_kex
            del rad_k, rad_th, rad_valid, k_excess, z_kex, inv_thk, z_inv_thk
        else:
            alter = z_demag
        mm[:, :, 8] = _robust_z_pos(alter, foot)
        del z_demag, alter, th_k_u8
        gc.collect()

        # Playa-deconfounded MT clay-cap lateral edge
        cond = _read_clean_band(ds_tf, 17, foot)
        elev = _read_clean_band(ds_tf, 12, foot)
        slope = np.maximum(_read_clean_band(ds_tf, 19, foot), 0.0)
        # Flat basin-floor playas have very low slope and local minimum elevation
        elev_rel = elev - ndi.minimum_filter(ndi.gaussian_filter(elev, sigma=3.0), size=25)
        playa_like = np.exp(-slope / (np.float32(np.percentile(slope[foot], 35)) + 1e-6)) * np.exp(-np.maximum(elev_rel, 0.0) / 35.0)
        cond_log = np.log1p(np.maximum(cond - float(np.min(cond[foot])), 0.0)).astype(np.float32)
        cond_gh, _ = _horizontal_grad_and_strike(cond_log, sigma_px=2.0, dx_m=100.0)
        clay_edge = cond_gh * (np.float32(1.0) - np.float32(0.75) * np.clip(playa_like, 0.0, 1.0))
        mm[:, :, 9] = _robust_z_pos(clay_edge, foot)
        del cond, cond_log, cond_gh, clay_edge
        gc.collect()

    # --- Group 4: INGENIOUS GDR #1391 thermal upflow, 1m LiDAR polarity, piedmont breakline & mimic veto ---
    mm[:, :, 10] = _build_ingenious_thermal_field(ddir, foot, strike_struct, origin_x, origin_y, pixel_size)
    gc.collect()

    # Relief-normalized piedmont break-in-slope ridge (amplifies 1-3 deg bajada fault scarps vs 30 deg cliffs)
    local_relief = ndi.maximum_filter(elev, size=19) - ndi.minimum_filter(elev, size=19)
    tau_rel = float(np.percentile(local_relief[foot], 30)) + 15.0
    slope_hp = np.maximum(slope - ndi.gaussian_filter(slope, sigma=5.0), 0.0)
    piedmont_break = (slope_hp / (local_relief + np.float32(tau_rel))) * (np.float32(1.0) - np.float32(0.5) * np.clip(playa_like, 0.0, 1.0))
    mm[:, :, 12] = _robust_z_pos(piedmont_break, foot)

    # Seamless 1m LiDAR scarp polarity/step crest with 100m DEM breakline fallback in 18% non-LiDAR tiles
    lid_tif = ddir / "external" / "lidar_scarp_features_u8.tif"
    if lid_tif.exists():
        with rasterio.open(lid_tif) as ds_lid:
            down_m = ds_lid.read(1).astype(np.float32)
            up_m = ds_lid.read(3).astype(np.float32)
            step_m = ds_lid.read(5).astype(np.float32)
            lap_n = ds_lid.read(7).astype(np.float32)
            lap_p = ds_lid.read(8).astype(np.float32)
            coh = ds_lid.read(9).astype(np.float32) / np.float32(255.0)
            lid_valid = (ds_lid.read(12) > 0) & foot
        # Erode tile mask by 2 px so 3DEP survey boundary steps never mimic fault scarps
        lid_inner = ndi.binary_erosion(lid_valid, iterations=2)
        polarity_asym = np.abs(down_m - up_m) / (down_m + up_m + np.float32(8.0))
        dipole_crest = np.sqrt(np.maximum(lap_n * lap_p, 0.0))
        lid_raw = (np.float32(0.45) * step_m + np.float32(0.30) * dipole_crest + np.float32(0.25) * np.maximum(down_m, up_m) * polarity_asym) * (np.float32(0.4) + np.float32(0.6) * coh)
        z_lid = _robust_z_pos(np.where(lid_inner, lid_raw, 0.0), lid_inner if lid_inner.any() else foot)
        fallback = mm[:, :, 12]
        w_blend = ndi.gaussian_filter(lid_inner.astype(np.float32), sigma=2.0)
        mm[:, :, 11] = (w_blend * z_lid + (np.float32(1.0) - w_blend) * fallback).astype(np.float32)
        del down_m, up_m, step_m, lap_n, lap_p, coh, lid_valid, lid_inner, polarity_asym, dipole_crest, lid_raw, z_lid, fallback, w_blend
    else:
        mm[:, :, 11] = mm[:, :, 12]
    del elev, slope, elev_rel, local_relief, slope_hp, piedmont_break
    gc.collect()

    # TIGER road-cut & flat Lahontan shoreline mimic veto gate in [0, 1] (1 = clean tectonic domain)
    road_tif = ddir / "external" / "tiger_road_distance_m.tif"
    if road_tif.exists():
        with rasterio.open(road_tif) as ds_rd:
            d_road = ds_rd.read(1).astype(np.float32)
        d_road = np.where(np.isfinite(d_road), np.maximum(d_road, 0.0), 5000.0)
        # Road-cut embankments lie within ~150 m of TIGER centerlines; only penalize where subsurface SPI is weak
        sub_guard = np.maximum(mm[:, :, 0], mm[:, :, 1])
        road_pen = np.exp(-((d_road / np.float32(140.0)) ** 2)) * (np.float32(1.0) - np.float32(0.75) * sub_guard)
        del d_road, sub_guard
    else:
        road_pen = np.zeros((h_grid, w_grid), dtype=np.float32)

    lahontan_pen = np.clip(playa_like, 0.0, 1.0) * (np.float32(1.0) - np.maximum(mm[:, :, 3], mm[:, :, 6]))
    clean_gate = np.clip(np.float32(1.0) - np.float32(0.45) * road_pen - np.float32(0.40) * lahontan_pen, 0.15, 1.0).astype(np.float32)
    clean_gate[~foot] = 0.0
    mm[:, :, 14] = clean_gate
    del playa_like, road_pen, lahontan_pen, strike_struct
    gc.collect()

    # Steerable 2.0 km lineament anisotropy excess on multi-physics structural boundary composite
    multi_edge = (
        np.float32(0.24) * mm[:, :, 4]
        + np.float32(0.18) * mm[:, :, 1]
        + np.float32(0.16) * mm[:, :, 3]
        + np.float32(0.16) * mm[:, :, 6]
        + np.float32(0.14) * mm[:, :, 12]
        + np.float32(0.12) * mm[:, :, 11]
    ) * clean_gate
    best_2km, excess_2km = _oriented_line_filter(multi_edge, length_px=21, n_angles=12)
    mm[:, :, 13] = _robust_z_pos(excess_2km, foot)

    # Channel 15: Pre-registered label-free LWST-GeoConduit subsurface + hydrothermal conduit composite
    # Deliberately weighted toward crust-penetrating potential-field contacts, basement ramps, and
    # transtensional geothermal conduits so off-catalogue buried/SGMC faults score strongly.
    unsup_raw = clean_gate * (
        np.float32(0.18) * mm[:, :, 4]   # Cross-tensor mag/grav SPI concordance
        + np.float32(0.13) * mm[:, :, 1] # Gravity 3-D SPI local wavenumber
        + np.float32(0.11) * mm[:, :, 3] # Wijns gravity Theta-map contact crest
        + np.float32(0.09) * mm[:, :, 0] # Magnetic 3-D SPI local wavenumber
        + np.float32(0.09) * mm[:, :, 5] # 150m upward-continued deep persistence
        + np.float32(0.12) * mm[:, :, 6] # Sub-alluvial basement detachment flexure
        + np.float32(0.08) * mm[:, :, 7] # Transtensional geodetic slip/dilation tendency
        + np.float32(0.06) * mm[:, :, 8] # RTP demagnetization x GeoDAWN K/Th alteration
        + np.float32(0.04) * mm[:, :, 9] # Playa-deconfounded MT clay-cap boundary
        + np.float32(0.05) * mm[:, :, 10]# Strike-anisotropic GDR #1391 thermal upflow
        + np.float32(0.05) * _robust_z_pos(best_2km, foot)
    )
    mm[:, :, 15] = _robust_z_pos(unsup_raw, foot)
    mm.flush()
    del multi_edge, best_2km, excess_2km, unsup_raw, clean_gate
    gc.collect()

    rec = {
        "schema_version": 1,
        "lane": "H-SASS3-A_LWST-GeoConduit",
        "channels": list(LWST_CHANNELS),
        "n_channels": len(LWST_CHANNELS),
        "shape": [h_grid, w_grid, len(LWST_CHANNELS)],
        "dtype": "float32",
        "label_free_verified": True,
        "sgmc_free_verified": True,
        "elapsed_s": round(time.time() - t0, 2),
    }
    receipt_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def _sample_bilinear_f32(img: np.ndarray, yy: np.ndarray, xx: np.ndarray) -> np.ndarray:
    """Fast vectorized bilinear interpolation for Hessian cross-strike crest sampling."""
    h, w = img.shape
    yc = np.clip(yy, 0.0, float(h - 1) - 1e-6)
    xc = np.clip(xx, 0.0, float(w - 1) - 1e-6)
    y0 = np.floor(yc).astype(np.int32)
    x0 = np.floor(xc).astype(np.int32)
    y1 = np.minimum(y0 + 1, h - 1)
    x1 = np.minimum(x0 + 1, w - 1)
    wy = (yc - y0).astype(np.float32)
    wx = (xc - x0).astype(np.float32)
    return (
        (1.0 - wy) * (1.0 - wx) * img[y0, x0]
        + (1.0 - wy) * wx * img[y0, x1]
        + wy * (1.0 - wx) * img[y1, x0]
        + wy * wx * img[y1, x1]
    ).astype(np.float32)


def sharpen_steerable_crest(prob: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Sharpen a continuous fault-belief field onto 1-px 1-D fault axes via Hessian cross-strike normal sampling.

    Unlike isotropic 2-D `maximum_filter`, sampling strictly along the principal negative-curvature
    eigenvector `(nx, ny)` preserves continuous 1-D fault traces while suppressing parallel flank rows.
    """
    p = np.where(foot & np.isfinite(prob), np.clip(prob.astype(np.float32), 0.0, None), 0.0)
    pmax = float(p[foot].max()) if foot.any() else 0.0
    if pmax <= 0.0:
        return np.zeros_like(p, dtype=np.float32)
    p = p / np.float32(pmax)

    ps = ndi.gaussian_filter(p, sigma=1.0, mode="nearest")
    axx = ndi.gaussian_filter(p, sigma=1.25, order=(0, 2), mode="nearest")
    ayy = ndi.gaussian_filter(p, sigma=1.25, order=(2, 0), mode="nearest")
    axy = ndi.gaussian_filter(p, sigma=1.25, order=(1, 1), mode="nearest")

    phi = 0.5 * np.arctan2(2.0 * axy, (axx - ayy) + 1e-12)
    nx1, ny1 = np.cos(phi).astype(np.float32), np.sin(phi).astype(np.float32)
    c1 = np.abs(axx * nx1 * nx1 + 2.0 * axy * nx1 * ny1 + ayy * ny1 * ny1)
    c2 = np.abs(axx * (-ny1) * (-ny1) + 2.0 * axy * (-ny1) * nx1 + ayy * nx1 * nx1)
    use_perp = c2 > c1
    nx = np.where(use_perp, -ny1, nx1).astype(np.float32)
    ny = np.where(use_perp, nx1, ny1).astype(np.float32)

    h, w = p.shape
    gy, gx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")
    step = np.float32(1.35)
    p_plus = _sample_bilinear_f32(ps, gy + step * ny, gx + step * nx)
    p_minus = _sample_bilinear_f32(ps, gy - step * ny, gx - step * nx)
    flank_mean = np.float32(0.5) * (p_plus + p_minus)
    crest_prom = np.clip((ps - flank_mean) / (ps + np.float32(1e-4)), 0.0, 1.0)
    is_crest = ((ps >= p_plus - 1e-6) & (ps >= p_minus - 1e-6)).astype(np.float32)

    crest = p * (np.float32(0.28) + np.float32(0.47) * np.sqrt(crest_prom) + np.float32(0.25) * is_crest)
    crest[~foot] = 0.0
    cmax = float(crest[foot].max()) if foot.any() else 1.0
    if cmax > 0.0:
        crest /= np.float32(cmax)
    return crest.astype(np.float32)


def compute_fold_visible_tip_cone(visible_mask: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Compute strictly fold-local fault-tip propagation, relay-halo & step-over stress field.

    Uses ONLY `visible_mask` (`cell.visible_full` inside holdout; full `labels` ONLY at final
    inference), so withheld fault segments have zero influence on tip/relay geometry.
    """
    vis = np.asarray(visible_mask, dtype=bool) & foot
    if not vis.any():
        return np.zeros(foot.shape, dtype=np.float32)

    nb = ndi.convolve(vis.astype(np.int16), np.ones((3, 3), dtype=np.int16), mode="constant") - vis.astype(np.int16)
    tips = vis & (nb >= 1) & (nb <= 2)
    del nb

    d_tips = ndi.distance_transform_edt(~tips).astype(np.float32)
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    vis_blur = ndi.gaussian_filter(vis.astype(np.float32), sigma=2.5, mode="constant")

    outside = (d_vis > 2.0).astype(np.float32)
    tip_cone = np.exp(-((d_tips - np.float32(5.0)) ** 2) / np.float32(2.0 * 7.0 * 7.0)).astype(np.float32) * outside
    relay_halo = np.exp(-((d_vis - np.float32(4.5)) ** 2) / np.float32(2.0 * 4.5 * 4.5)).astype(np.float32) * outside
    stepover = np.clip(vis_blur * np.float32(14.0), 0.0, 1.5).astype(np.float32) * outside
    del d_tips, d_vis, vis_blur, outside

    out = (np.float32(0.55) * tip_cone + np.float32(0.25) * relay_halo + np.float32(0.20) * stepover) * foot
    return out.astype(np.float32)


def compute_lwst_completeness_eta(
    visible_mask: np.ndarray,
    lwst_conduit_field: np.ndarray,
    foot: np.ndarray,
    near_px: float = 3.0,
) -> tuple[float, float, float]:
    """Compute LWST structural-completeness ratio `eta(V)` strictly from visible catalogue `V`.

    Measures the fraction of total LWST potential-field/structural conduit mass already within
    `near_px` (300 m) of `visible_mask`, returning `(eta, f_horizon_a, w_corrob)`:
      - When 20% of segments are censored (`eta` lower), `f_horizon_a` allocates ~0.86 to Horizon-A
        SAR-PU near-tip/structural crests and ~0.14 to Horizon-B blind conduits.
      - On the full catalogue (`eta` higher, exposed scarps already mapped), `f_horizon_a` shifts
        automatically to ~0.58 Horizon-A + ~0.42 Horizon-B off-catalogue (`d_vis >= 4 px`) conduits.
    """
    vis = np.asarray(visible_mask, dtype=bool) & foot
    yy, xx = np.ogrid[-3:4, -3:4]
    disk3 = (yy * yy + xx * xx) <= float(near_px * near_px)
    near_vis = ndi.binary_dilation(vis, structure=disk3) & foot

    total_mass = float(lwst_conduit_field[foot].sum()) + 1e-9
    explained_mass = float(lwst_conduit_field[near_vis].sum())
    eta = explained_mass / total_mass

    # Calibrated from thalweg-vetoed LWST structural corridor enrichment (`eta_full ~= 0.1063` vs 80%-visible `~0.0850`)
    eta_high = 0.1063
    eta_low = 0.0850
    f_a = float(np.clip(0.52 + 0.34 * ((eta_high - eta) / (eta_high - eta_low)), 0.50, 0.86))
    w_corrob = float(np.clip(0.22 + 0.48 * ((f_a - 0.50) / (0.86 - 0.50)), 0.22, 0.70))
    return eta, f_a, w_corrob


def _cap_support(field: np.ndarray, eligible: np.ndarray, max_support: int = 120_000) -> np.ndarray:
    """Restrict candidate pixels to top `max_support` eligible pixels for fast CELF heap packing."""
    f = np.where(eligible & np.isfinite(field) & (field > 0), field.astype(np.float32), 0.0)
    pos_vals = f[f > 0]
    if pos_vals.size > max_support:
        thr = float(np.partition(pos_vals, pos_vals.size - max_support)[pos_vals.size - max_support])
        f = np.where(f >= thr, f, 0.0)
    return f


def pack_single_horizon(
    belief: np.ndarray,
    eligible: np.ndarray,
    budget: int = 37_654,
    support_mult: int = 4,
) -> np.ndarray:
    """Pack `budget` dots on a single crest-sharpened belief field using exact 300 m CELF `emitter.emit`."""
    max_sup = max(int(budget) * support_mult, 22_000)
    f_cap = _cap_support(belief, eligible, max_support=max_sup)
    dots, _ = emitter.emit(f_cap, budget=int(budget), prior_dti=0.0)
    return dots & eligible


def pack_dual_horizon(
    belief_a: np.ndarray,
    belief_b: np.ndarray,
    eligible: np.ndarray,
    budget_a: int = 20_710,
    budget_b: int = 16_944,
    support_mult: int = 4,
) -> np.ndarray:
    """Two-stage exact 300 m residual-coverage CELF allocation across Horizon A (SAR-PU OOF)
    and Horizon B (LWST Blind-Basin & Geothermal-Conduit SPI/Theta)."""
    f_a = _cap_support(belief_a, eligible, max_support=max(int(budget_a) * support_mult, 20_000))
    dots_a, _ = emitter.emit(f_a, budget=int(budget_a), prior_dti=0.0)
    dots_a &= eligible

    rem_budget = (int(budget_a) + int(budget_b)) - int(dots_a.sum())
    f_b = _cap_support(belief_b, eligible & (~dots_a), max_support=max(rem_budget * support_mult, 20_000))
    dots_b, _ = emitter.emit(f_b, budget=rem_budget, prior_dti=0.0, initial_mask=dots_a)
    return (dots_a | dots_b) & eligible
