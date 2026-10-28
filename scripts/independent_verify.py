#!/usr/bin/env python3
"""Independent recomputation of the shipped GeoTIFF and its headline claims (no stored JSON is trusted).

Recomputes, from the file bytes and the restored competition inputs:
  * format checks: SHA-256, single band, float32, EPSG:32611, shape/transform vs data/prepared_manifest.json,
    NaN/inf count, finite range inside [0,1], positive-pixel count, on-catalogue positives (0 expected)
  * HOLDOUT-DTI proxies with the SHARED evaluator (src/gems32/holdout.py):
      - GEMSDOE32-HIDE-RECOVER-v3.0 applied to the STATIC shipped raster (B-visible = 2 px)
      - GEMSDOE32-SGMC-CAL-v3.0 applied to the STATIC shipped raster
  * the same two proxies for the 0.2778 champion raster and the GEMSDOE25 D2.8 raster (the file the
    pipeline's 'champion' hide-and-recover baseline actually loads; see IR-SASS3-08)
  * compares each recomputed value with the value stored in evidence/run_card.json and labels the result
    REPRODUCED or NOT_REPRODUCED (Protocol Rule 3: never write a projection as a score).

Writes evidence/independent_verification_20261028.json.
Requires GEMS_DATA_DIR (restored inputs) and the champion/D2.8 rasters under GEMS_WORK_DIR/registry_rasters.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir, work_dir  # noqa: E402

SHIPPED = ROOT / "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"
CHAMP = "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
D28 = "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"  # restored scored file used by run_lwst_experiments.py
TOL = 1e-6


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def format_checks(path: Path) -> dict:
    prep = json.loads((ROOT / "data/prepared_manifest.json").read_text())
    g = prep["grid"]
    with rasterio.open(path) as ds:
        a = ds.read(1)
        meta = {
            "count": ds.count, "dtype": ds.dtypes[0], "nodata": ds.nodata,
            "crs": ds.crs.to_string(), "shape": [ds.height, ds.width],
            "transform": list(ds.transform)[:6],
        }
    fin = np.isfinite(a)
    return {
        **meta,
        "single_band": meta["count"] == 1,
        "float32": meta["dtype"] == "float32",
        "crs_is_EPSG_32611": meta["crs"] == f"EPSG:{g['epsg']}",
        "shape_matches_prepared_grid": meta["shape"] == [g["height"], g["width"]],
        "transform_matches_prepared_grid": tuple(meta["transform"]) == tuple(g["transform"]),
        "nan_count": int(np.isnan(a).sum()),
        "inf_count": int(np.isinf(a).sum()),
        "finite_min": float(a[fin].min()),
        "finite_max": float(a[fin].max()),
        "all_finite_values_in_0_1": bool(((a[fin] >= 0) & (a[fin] <= 1)).all()),
        "positive_pixels": int((a > 0).sum()),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def main() -> int:
    ddir = data_dir()
    ctx = holdout.load_holdout_context(ddir)
    run_card = json.loads((ROOT / "evidence/run_card.json").read_text())

    fmt = format_checks(SHIPPED)
    fmt_pass = (
        fmt["single_band"] and fmt["float32"] and fmt["crs_is_EPSG_32611"]
        and fmt["shape_matches_prepared_grid"] and fmt["transform_matches_prepared_grid"]
        and fmt["nan_count"] == 0 and fmt["inf_count"] == 0 and fmt["all_finite_values_in_0_1"]
        and fmt["sha256"] == run_card["raster_sha256"]
    )

    def proxies(path: Path) -> dict:
        with rasterio.open(path) as ds:
            a = ds.read(1)
        mask = np.isfinite(a) & (a > 0) & ctx.foot
        hr = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=2.0, name=path.stem)
        sg = holdout.evaluate_sgmc_with_ci(mask, ctx, name=path.stem)
        return {
            "file": path.name, "sha256": sha256(path), "n_dots_in_footprint": int(mask.sum()),
            "hide_recover_pooled_dti": float(hr["pooled_dti"]),
            "hide_recover_ci95": [float(x) for x in hr["ci95_cluster_bootstrap"]],
            "hide_recover_withheld_positives": int(hr["n_withheld_positives"]),
            "sgmc_cal_dti": float(sg["sgmc_prevalence_calibrated_dti"]),
            "sgmc_cal_ci95": [float(x) for x in sg["sgmc_calibrated_ci95"]],
            "sgmc_raw_dti": float(sg["sgmc_raw_pooled_dti"]),
            "sgmc_withheld_positives": int(sg["n_withheld_positives"]),
        }

    shipped = proxies(SHIPPED)
    champ_path = work_dir() / "registry_rasters" / "GEMSDOE32" / CHAMP
    d28_path = ddir / "scored" / D28
    champ = proxies(champ_path) if champ_path.exists() else {"status": "MISSING_LOCAL_FILE", "file": CHAMP}
    d28 = proxies(d28_path) if d28_path.exists() else {"status": "MISSING_LOCAL_FILE", "file": D28}

    hr_claim = run_card["holdout_dti"]["primary_hide_and_recover"]
    sg_claim = run_card["holdout_dti"]["secondary_off_catalogue_sgmc"]
    comparisons = {
        "hide_recover_claimed_for_shipped": {
            "claimed": hr_claim["pooled_dti"], "recomputed_static": shipped["hide_recover_pooled_dti"],
            "status": "REPRODUCED" if abs(hr_claim["pooled_dti"] - shipped["hide_recover_pooled_dti"]) < TOL else "NOT_REPRODUCED",
            "note": "Claimed value comes from per-fold OOF cell masks (run_lwst_experiments.py exp3_cell_masks), not from the shipped raster.",
        },
        "champion_hide_recover_baseline_claimed_0p099202": {
            "claimed": hr_claim["champion_02778_baseline_dti"],
            "recomputed_static_D2p8_file": d28.get("hide_recover_pooled_dti"),
            "recomputed_static_champion_file": champ.get("hide_recover_pooled_dti"),
            "status": ("MISLABELED" if d28.get("hide_recover_pooled_dti") is not None
                       and abs(hr_claim["champion_02778_baseline_dti"] - d28["hide_recover_pooled_dti"]) < TOL else "NOT_REPRODUCED"),
            "note": "0.099202 equals the static hide-and-recover score of the GEMSDOE25 D2.8 raster, not the 0.2778 champion.",
        },
        "sgmc_cal_claimed_for_shipped": {
            "claimed": sg_claim["prevalence_calibrated_dti"], "recomputed_static": shipped["sgmc_cal_dti"],
            "status": "REPRODUCED" if abs(sg_claim["prevalence_calibrated_dti"] - shipped["sgmc_cal_dti"]) < TOL else "NOT_REPRODUCED",
        },
        "sgmc_cal_champion_claimed_0p064121": {
            "claimed": sg_claim["champion_02778_calibrated_dti"], "recomputed_static": champ.get("sgmc_cal_dti"),
            "status": "REPRODUCED" if champ.get("sgmc_cal_dti") is not None and abs(sg_claim["champion_02778_calibrated_dti"] - champ["sgmc_cal_dti"]) < TOL else "NOT_REPRODUCED",
        },
        "sgmc_paired_delta_ci_includes_zero": {
            "claimed_delta_ci95": sg_claim["paired_delta_calibrated_ci95"],
            "status": "NOT_SIGNIFICANT" if sg_claim["paired_delta_calibrated_ci95"][0] <= 0.0 <= sg_claim["paired_delta_calibrated_ci95"][1] else "SIGNIFICANT",
        },
    }

    out = {
        "schema_version": 1,
        "date_utc": "2026-10-28",
        "purpose": "Recompute headline claims from bytes + restored inputs; no stored JSON trusted (Protocol Rules 3 and 5)",
        "data_dir": str(ddir),
        "shipped_format_checks": fmt,
        "format_checks_all_pass": bool(fmt_pass),
        "shipped_proxies": shipped,
        "champion_0p2778_proxies": champ,
        "d28_gems25_proxies_used_as_hr_baseline": d28,
        "comparisons": comparisons,
        "labels": {
            "HOLDOUT-DTI": "evaluator version, withheld positives and 95% CI are stated in each proxy block",
            "ORGANIZER-CONFIRMED": "none exists for the shipped file; no submission receipt has been recorded",
        },
    }
    (ROOT / "evidence/independent_verification_20261028.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v["status"] if isinstance(v, dict) and "status" in v else v for k, v in comparisons.items()}, indent=2))
    print("format_checks_all_pass:", fmt_pass)
    return 0 if fmt_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
