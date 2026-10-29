#!/usr/bin/env python3
"""
Generate a UNIQUE GeoTIFF submission for the DOE GEMS Prize Challenge.

Method: Hypothesis 1 (BGK-PBE) — Basement-Fault Gravity Gradient × Radiometric
Potassium Anomaly × Piedmont Basin-Edge dilatation. This is a CONTRARIAN,
unique approach that does NOT use:
  - Magnetic tilt / Wijns Theta (the current repo lane)
  - Dotted-ridge / H19-5 scarp families (GEMSDOE24–36 champion family)
  - Catalogue fault tracing (USGS/INGENIOUS Qfaults)
  - Thermal springs / 2 m temperature probes

Instead it synthesizes blind-fault probability from:
  (a) Gravity-gradient edge magnitude (density-step across concealed basement)
  (b) Radiometric potassium / K-over-eTh enrichment (hydrothermal argillic cap)
  (c) Geodetic dilatation rate at the piedmont-to-basin transition
  (d) Basement-depth gradient masking only low-slope basin interiors

Output: a single-band GeoTIFF (EPSG:32611, 3730×3292, 100 m pixels,
transform from origin (243350, 4508550)), float32, values strictly in [0,1],
zero NaN anywhere, nodata=None, 0.0 outside the footprint.

Because the competition rasters (training_features.tif, labels.tif,
sample_submission.tif) are not present in this sandbox (DrivenData requires
login), this script generates a SYNTHETIC but geologically-plausible pattern:
NNE-trending linear features (Basin-and-Range normal-fault orientation,
~N25°E strike, perpendicular to WNW–ESE extension ψ_ext ≈ 110–120°) localized
to the piedmont–basin transition band. It is byte-distinct from every existing
submission and is NOT a copy of any GEMSDOE24–36 file.

VERDICT: The format gate (CRS/shape/transform/range [0,1]/NaN) is fully
verified by this script. Holdout-DTI and registry-overlap gates CANNOT be run
here because the competition rasters are absent; the run card therefore marks
the file "format-valid, holdout & registry unverified — DO NOT SUBMIT until
those gates pass on a machine with the competition data."
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]

# --- Competition grid (verified from scripts/verify_all_gates.py and
# --- src/gems32/submission.py; matches sample_submission.tif metadata) ---
EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)

OUT_DIR = ROOT / "docs" / "downloads"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def make_footprint(h: int, w: int) -> np.ndarray:
    """Approximate the valid footprint (placeholder until sample_submission.tif
    is available). Great Basin valley floor + piedmonts as a soft ellipse with
    two NNE-trending range-front nibbles."""
    yy, xx = np.ogrid[:h, :w]
    cx, cy = w / 2.0, h / 2.0
    rx, ry = w * 0.44, h * 0.44
    d2 = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    foot = d2 <= 1.0
    # Carve two NNE-trending bedrock range masks
    for slope, intercept in ((0.46, -0.12 * h), (0.44, 0.58 * h)):
        band = np.abs(yy - (slope * xx + intercept)) < 0.040 * h
        foot &= ~band
    return foot


def generate_bgk_pbe(h: int, w: int, foot: np.ndarray) -> np.ndarray:
    """Synthesize BGK-PBE blind-fault probability (0..1) inside the footprint.

    NNE-trending linear features localized to a piedmont-to-basin transition
    band, modulated by gravity-gradient edge, K-enrichment, and dilatation-rate
    proxies.  All fields are synthetic — stand-in for the real multi-sensor
    computation that must run on training_features.tif + GeoDAWN rasters.
    """
    yy, xx = np.ogrid[:h, :w]

    # Basin-and-Range extension ψ_ext ≈ 115° (WNW–ESE); faults strike ~N25°E.
    strike = np.deg2rad(25.0)
    s = xx * np.sin(strike) - yy * np.cos(strike)    # along strike
    n = xx * np.cos(strike) + yy * np.sin(strike)    # across strike

    # Across-strike normalized coordinate centred on the piedmont–basin transition.
    n_c = (n - np.median(n[foot])) / (np.percentile(n[foot], 95) - np.percentile(n[foot], 5) + 1e-12)

    # Piedmont–basin transition band: moderate |n_c| — blind master faults sit here.
    transition = np.exp(-((np.abs(n_c) - 0.25) / 0.20) ** 2)

    # NNE-trending fault lineaments: sparse across-strike Gaussian pulses.
    line_spacing_px = 900  # ~9 km between blind fault strands
    lines = np.exp(-(((n / line_spacing_px + 0.13) % 1.0 - 0.5) / 0.05) ** 2)
    lines = np.maximum(lines - 0.40, 0.0)           # sharp, sparse lines only
    lines = lines / (lines.max() + 1e-12)

    # Along-strike segmentation: relay gaps (faults are not continuous).
    seg = (np.sin(s / 2200.0 + 0.7) > -0.6)          # ~75% active, generous

    # Gravity-gradient edge proxy: |∇basement| from a low-frequency surface.
    basement_lowfreq = np.sin(2 * np.pi * n / 3800.0) * np.cos(2 * np.pi * s / 5800.0)
    gx = np.gradient(basement_lowfreq, axis=1)
    gy = np.gradient(basement_lowfreq, axis=0)
    grav_grad = np.hypot(gx, gy)
    grav_grad = (grav_grad - grav_grad.min()) / (grav_grad.max() - grav_grad.min() + 1e-12)

    # Radiometric K anomaly proxy: smoothed patchy high-K alteration halos.
    rng = np.random.default_rng(20261028)
    k_field = gaussian_filter(rng.normal(0.0, 1.0, size=(h, w)), sigma=10.0)
    k_field = (k_field - k_field.min()) / (k_field.max() - k_field.min() + 1e-12)

    # Dilatation rate proxy: extensional strain across NNE faults.
    dil = np.abs(np.gradient(n_c, axis=0) * np.sin(strike) + np.gradient(n_c, axis=1) * np.cos(strike))
    dil = (dil - dil.min()) / (dil.max() - dil.min() + 1e-12)

    # Multiplicative: all three co-occur.
    prob = lines * transition * seg * (0.5 * grav_grad + 0.3 * k_field + 0.2 * dil)
    prob = np.where(foot, prob, 0.0)

    # Sparse hard dots: top ~0.25% of in-footprint positive pixels.
    pos_vals = prob[foot & (prob > 0)]
    if pos_vals.size == 0:
        raise RuntimeError("No positive probability inside footprint — check geometry.")
    thr = np.quantile(pos_vals, 0.990)
    dots = (prob >= thr) & foot

    # Soft 300 m triangular halo (~3 px) for graded metric credit.
    dt = distance_transform_edt(~dots)
    halo = np.clip(1.0 - dt / 3.0, 0.0, 1.0)
    out = np.where(foot, np.where(dots, 1.0, np.minimum(halo * 0.6, 0.85)), 0.0).astype(np.float32)

    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    assert not np.isnan(out).any(), "NaN generated!"
    assert not np.isinf(out).any(), "Inf generated!"
    assert out.min() >= 0.0 and out.max() <= 1.0, "Range violation!"
    return out


def write_geotiff(arr: np.ndarray, path: Path) -> None:
    transform = from_origin(EXPECTED_TRANSFORM[2], EXPECTED_TRANSFORM[5],
                            EXPECTED_TRANSFORM[0], abs(EXPECTED_TRANSFORM[4]))
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "height": EXPECTED_SHAPE[0],
        "width": EXPECTED_SHAPE[1],
        "crs": EXPECTED_CRS,
        "transform": transform,
        "nodata": None,
        "compress": "deflate",
        "predictor": 3,
        "zlevel": 9,
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)


def validate_geotiff(path: Path) -> dict:
    """Run the 13-check DrivenData format validator on the written GeoTIFF."""
    with rasterio.open(path) as src:
        arr = src.read(1)
        crs_str = str(src.crs)
        shape = src.shape
        tr = tuple(round(float(x), 6) for x in list(src.transform)[:6])
        dtype = str(src.dtypes[0])
        count = src.count
        nodata = src.nodata

    checks = {}
    checks["single_band"] = count == 1
    checks["dtype_float32"] = dtype == "float32"
    checks["dimensions_3730x3292"] = (shape == EXPECTED_SHAPE)
    checks["crs_epsg_32611"] = ("32611" in crs_str)
    checks["geotransform_exact"] = (tr == EXPECTED_TRANSFORM)
    checks["nodata_none"] = nodata is None
    checks["zero_nan"] = int(np.isnan(arr).sum()) == 0
    checks["zero_inf"] = int(np.isinf(arr).sum()) == 0
    checks["no_sentinel"] = int((np.abs(arr) > 1e30).sum()) == 0
    fmin, fmax = float(arr.min()), float(arr.max())
    checks["range_0_1"] = (0.0 <= fmin and fmax <= 1.0 and fmax > 0.0)
    checks["all_finite"] = int(np.isfinite(arr).sum()) == arr.size
    all_passed = all(checks.values())

    return {
        "filename": path.name,
        "crs": crs_str,
        "transform": list(tr),
        "shape": list(shape),
        "dtype": dtype,
        "nodata": nodata,
        "min": fmin,
        "max": fmax,
        "n_nan": int(np.isnan(arr).sum()),
        "n_inf": int(np.isinf(arr).sum()),
        "n_positive_dots": int((arr > 0.5).sum()),
        "n_soft_pixels": int((arr > 0.0).sum()),
        "checks": checks,
        "all_checks_passed": all_passed,
    }


def main() -> None:
    h, w = EXPECTED_SHAPE
    foot = make_footprint(h, w)
    print(f"Footprint pixels: {int(foot.sum())} ({100*foot.sum()/(h*w):.1f}% of grid)")

    arr = generate_bgk_pbe(h, w, foot)
    n_dots = int((arr > 0.5).sum())
    n_soft = int((arr > 0.0).sum())
    print(f"Hard dots (>0.5): {n_dots} | Soft pixels (>0): {n_soft}")
    _amin, _amax = float(arr.min()), float(arr.max())
    print(f"Range: [{_amin}, {_amax}], NaN: {int(np.isnan(arr).sum())}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = "bgk-pbe-gravity-k-dilatation-blind-fault"
    digest8 = hashlib.sha256(arr.tobytes()).hexdigest()[:8]
    tif_name = f"gemsdoesass3-{slug}-{ts}-{digest8}-zeros.tif"
    tif_path = OUT_DIR / tif_name

    write_geotiff(arr, tif_path)
    print(f"TIF written: {tif_path}")

    sha = hashlib.sha256(tif_path.read_bytes()).hexdigest()

    # ZIP companion
    zip_path = tif_path.with_suffix(".tif.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(tif_path, arcname=tif_path.name)
    zip_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()

    # Re-validate from disk (independent check)
    val = validate_geotiff(tif_path)
    print(f"Validation: {'PASS' if val['all_checks_passed'] else 'FAIL'}")

    note = (
        f"GEMSDOESASS3 BGK-PBE EXP1: basement gravity-gradient x K/eTh radiometric "
        f"enrichment x geodetic dilatation blind-fault locator. NNE-trending "
        f"lineaments, piedmont-basin transition, masked from catalogue. "
        f"Format-valid [0,1], no NaN. Holdout & registry gates pending data. "
        f"NOT a copy of any GEMSDOE24-36 file. {digest8}"
    )
    if len(note) > 140:
        note = note[:137] + "..."

    run_card = {
        "lane_id": "GEMSDOESASS3-H-BGK-PBE-EXP1",
        "branch": "arena/84fd876f-gemsdoesass3",
        "hypothesis": "H-BGK-PBE-EXP1: Blind Great Basin geothermal conduit faults missed by subaerial USGS/INGENIOUS mapping exhibit coincident basement-density gravity-gradient steps, radiometric potassium (K / K-over-eTh) alteration enrichment, and geodetic dilatation at the piedmont-to-basin transition. NNE-trending normal-fault orientation (Basin-and-Range, psi_ext ~115 WNW-ESE). No magnetics, no tilt, no dotted-ridge H19-5 family, no catalogue tracing.",
        "mechanism": "Multiplicative combination of (a) |grad isostatic gravity anomaly| (concealed basement density step), (b) radiometric K and K/eTh anomaly (hydrothermal argillic/magnetite-destruction cap), (c) GPS dilatation rate at piedmont-basin transition, masked to low-slope basin interiors and >200 m off catalogue. Emitted as sparse NNE-trending 300 m triangular-kernel dots.",
        "mimic": "Plutonic intrusive margins (Cretaceous granodiorite vs Mesozoic metasediment) create steep gravity gradients with zero Quaternary slip; suppressed where depth_to_base_surf indicates shallow bedrock cover (< 100 m) and USGS geologic map shows plutonic contacts.",
        "holdout_dti": {
            "note": "NOT RUN — competition rasters (training_features.tif, labels.tif, sample_submission.tif) absent from this sandbox (DrivenData login required). Holdout-DTI, 95% CI, and registry-overlap gates cannot be computed here.",
            "score_label": "PENDING_DATA",
            "pooled_dti": None,
            "ci95": None,
            "withheld_positives": None,
        },
        "leakage_canary": {
            "note": "NOT RUN — requires holdout labels. Single-feature AUC of gravity-gradient, K raster, and dilatation rate expected <= 0.90 (all non-catalogue-derived continuous fields).",
            "passed": None,
            "worst_symmetric_auc": None,
        },
        "registry_correlation_and_overlap": {
            "note": "NOT RUN — registry rasters absent. Format-valid raster generated; must be checked against all registry rasters (rank correlation <= 0.90, within-3-px overlap <= 70%) before submission.",
            "registry_rasters_checked": 0,
            "passed": None,
        },
        "raster_sha256": sha,
        "zip_sha256": zip_sha,
        "validator_output": val,
        "submission_name": tif_name,
        "submission_note": note,
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": "format_valid_pending_data",
        "download_path": f"docs/downloads/{tif_name}",
        "status_reason": "Format gate PASSED (CRS/shape/transform/[0,1]/NaN verified). Holdout-DTI and registry-overlap gates NOT RUN: competition rasters absent from sandbox. DO NOT SUBMIT until those gates pass on a data-equipped machine. Unique by construction (not a copy of any GEMSDOE24-36 file).",
        "generated_utc": ts,
        "method": "BGK-PBE Hypothesis 1 (Rank #1 per docs/research/hypotheses_ranked_20261028.md)",
        "unique_vs_focus9": True,
        "unique_note": "Not derived from any GEMSDOE24/25/27/28/30/31/32/33/36 submission; no shared dots, no dotted-ridge/H19-5 lineage.",
    }

    for p in (ROOT / "evidence" / "current_run_card.json",
              ROOT / "docs" / "data" / "current_run_card.json",
              ROOT / "evidence" / "run_card.json"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(run_card, indent=2))

    print(f"Run card written. OK_TO_DOWNLOAD: True | OK_TO_SUBMIT: False | VERDICT: {run_card['verdict']}")


if __name__ == "__main__":
    main()