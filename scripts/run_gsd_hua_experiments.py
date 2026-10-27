#!/usr/bin/env python3
"""Execute H-GASS3-1 (GSD-HUA) controls and <=3 experiments on gems57-pooled-hide-v2,
enforce dual-phase registry uniqueness (continuous surface + final binary dots), and emit the
validated all-finite [0, 1] float32 GeoTIFF submission package via vendor/gems57/submission_writer.py.

Verified 3-Experiment Ladder on GDAL-tag-verified gsd_hua_static_v2 (46 static features):
  - EXP-1_GSD_HUA_PURE_SUBSURF: 100% non-topographic Pure Subsurface + Basement-Throw + IR-DATA-B06 True
    Magnetic Tilt + GeoDAWN Alteration + GDR #1391 Mechano-Thermal Tower (PURE_SUBSURF_COLS, ZERO DEM/slope/LiDAR).
  - EXP-2_GSD_HUA_FULL_MULTIPHYS: Full 46-feature Multi-Physics GSD-HUA Tower + road/shoreline mimic damping.
  - EXP-3_GSD_HUA_SAR_DECONFOUNDED: Two-Tower Coupled GSD-HUA (EXP-1^0.50 x EXP-2^0.50) + Positive-Unlabeled
    SAR Concealment Weighting (Band-15 sedimentary cover thickness + 2.5 km subsurface lineament anisotropy +
    mechano-thermal coupling) + 6-km Regional Background Demagnification (sigma=60 px) + road/shoreline damping.
"""
from __future__ import annotations

import gc
import hashlib
import json
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import convolve, distance_transform_edt, gaussian_filter
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout as eh  # noqa: E402
from gems57.emit import emit_decimated, emit_prefix  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems57.uniqueness import (  # noqa: E402
    compare_array_to_registry,
    compare_to_registry,
    saturation_certificate,
    two_phase_summary,
)
from gemsdoesass3.features import (  # noqa: E402
    PURE_SUBSURF_COLS,
    build_or_load_static_stack,
)
from gemsdoesass3.lli import build_s0_spec, project_lli  # noqa: E402

BUDGET_DEFAULT = 37_654
BASIN_SLOPE_DEG = 4.0      # True Band-19 det_elev_slope diagnostic reference
REG_BG_SIGMA_PX = 60.0     # 6.0 km footprint-compensated regional background demagnification
REG_BG_EPS = 0.02


def _oriented_ridge_enhance(prob_2d: np.ndarray, mask: np.ndarray) -> np.ndarray:
    half = 4
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1].astype(np.float32)
    best = np.zeros_like(prob_2d, dtype=np.float32)
    for k in range(8):
        theta = np.pi * k / 8.0
        d_perp = np.abs(-xx * np.sin(theta) + yy * np.cos(theta))
        d_para = np.abs(xx * np.cos(theta) + yy * np.sin(theta))
        w = np.maximum(1.15 - d_perp, 0.0) * (d_para <= half + 0.25)
        w /= max(float(w.sum()), 1e-6)
        resp = convolve(prob_2d, w.astype(np.float32), mode="nearest")
        np.maximum(best, resp, out=best)
    out = (0.60 * prob_2d + 0.40 * best).astype(np.float32)
    out[~mask] = 0.0
    return out


def _crop_fold(fold: dict, pad: int = 6) -> tuple[dict, tuple[int, int], tuple[slice, slice]]:
    reg = fold["region"]
    rows = np.flatnonzero(reg.any(axis=1))
    cols = np.flatnonzero(reg.any(axis=0))
    H, W = reg.shape
    y0, y1 = max(0, int(rows[0]) - pad), min(H, int(rows[-1]) + pad + 1)
    x0, x1 = max(0, int(cols[0]) - pad), min(W, int(cols[-1]) + pad + 1)
    sl = (slice(y0, y1), slice(x0, x1))
    cf = {
        "fold": fold["fold"],
        "name": fold["name"],
        "region": fold["region"][sl].copy(),
        "truth": fold["truth"][sl].copy(),
        "visible": fold["visible"][sl].copy(),
        "masked_known": fold["masked_known"][sl].copy(),
    }
    return cf, (y0, x0), sl


def _predict_in_chunks(clf: HistGradientBoostingClassifier, X_mm: np.memmap, cols: list[int],
                       mask_fp: np.ndarray, chunk_size: int = 350_000) -> np.ndarray:
    idxs = np.flatnonzero(mask_fp)
    out = np.zeros(mask_fp.shape[0], dtype=np.float32)
    for start in range(0, idxs.size, chunk_size):
        sl_idx = idxs[start:start + chunk_size]
        Xb = X_mm[sl_idx][:, cols].astype(np.float32, copy=False)
        out[sl_idx] = clf.predict_proba(Xb)[:, 1].astype(np.float32)
    return out


def _build_concealment_factor_fp(mm: np.memmap) -> np.ndarray:
    """Zero-label Selected-At-Random (SAR) geological concealment & mechano-thermal discovery factor:
      - mm[:, 28] = basin_cover_log = log1p(Band-15 depth_to_base_surf [m])
      - mm[:, 30] = subsurf_line_aniso_2p5km (2.5 km pure-subsurface basement+gravity+tilt lineament anisotropy)
      - mm[:, 35] = mechano_thermal_coupling (dilation x GDR #1391 2m-probe / spring / sinter plume)
    """
    c_sed = mm[:, 28] / (float(np.percentile(mm[:, 28], 95.0)) + 1e-6)
    c_lin = np.clip(mm[:, 30] / (float(np.percentile(mm[:, 30], 95.0)) + 1e-6), 0.0, 2.0)
    c_thm = np.clip(mm[:, 35] / (float(np.percentile(mm[:, 35], 95.0)) + 1e-6), 0.0, 2.0)
    return (0.40 * c_sed + 0.35 * c_lin + 0.25 * c_thm).astype(np.float32)


def _build_sar_deconfounded_surface(
    p_sub_fp: np.ndarray,
    p_full_fp: np.ndarray,
    conceal_fp: np.ndarray,
    fp: np.ndarray,
    fp_blur: np.ndarray,
    mimic_road_2d: np.ndarray,
    mimic_shore_2d: np.ndarray,
    allowed: np.ndarray,
) -> np.ndarray:
    """EXP-3: Two-Tower Coupled GSD-HUA posterior weighted by PU-SAR concealment odds
    and spatially whitened against its 6-km regional background to prevent regional
    coordinate memorization from 100-km smooth seismicity/geodetic bands.
    """
    raw_fp = (
        (np.maximum(p_full_fp, 1e-6) ** 0.50)
        * (np.maximum(p_sub_fp, 1e-6) ** 0.50)
        * (0.20 + conceal_fp)
    ).astype(np.float32)
    s2d = np.zeros(fp.shape, dtype=np.float32)
    s2d[fp] = raw_fp
    bg = gaussian_filter(s2d, sigma=REG_BG_SIGMA_PX) / fp_blur
    s2d = (s2d / (bg + REG_BG_EPS)) * fp
    s2d = _oriented_ridge_enhance(s2d, allowed)
    s2d *= (1.0 - 0.40 * mimic_road_2d) * (1.0 - 0.30 * mimic_shore_2d)
    # Normalize strictly into [0, 1] using 99.95th percentile on allowed cells
    if allowed.any():
        scale = max(float(np.percentile(s2d[allowed], 99.95)), 1e-6)
        s2d = np.clip(s2d / scale, 0.0, 1.0).astype(np.float32)
    s2d[~allowed] = 0.0
    return s2d


def main() -> int:
    t0 = time.time()
    hyp_doc = ROOT / "docs/hypotheses.md"
    canary_path = ROOT / "evidence/leakage_canary.json"
    reg_path = ROOT / "evidence/registry_index.json"
    if not hyp_doc.exists():
        raise RuntimeError("Preregistration docs/hypotheses.md must exist before running experiments.")
    if not canary_path.exists():
        raise RuntimeError("Leakage canary evidence/leakage_canary.json must be run first.")
    canary = json.loads(canary_path.read_text())
    if not canary.get("all_passed", False):
        raise RuntimeError(f"Leakage canary failed: {canary.get('quarantined_features')}")
    registry_index = json.loads(reg_path.read_text())

    data_root = ROOT / ".cache/gems_data"
    feat_dir = ROOT / ".cache/features"
    grid = load_grid(data_root)
    fp = grid.footprint
    cat = grid.catalogue
    H, W = fp.shape

    mm, _ = build_or_load_static_stack(data_root, feat_dir, fp)
    n_fp = int(fp.sum())

    elev_slope_2d = np.zeros((H, W), dtype=np.float32)
    elev_slope_2d[fp] = mm[:, 18]
    mimic_road_2d = np.zeros((H, W), dtype=np.float32)
    mimic_road_2d[fp] = mm[:, 44]
    mimic_shore_2d = np.zeros((H, W), dtype=np.float32)
    mimic_shore_2d[fp] = mm[:, 45]
    conceal_fp = _build_concealment_factor_fp(mm)
    fp_blur = gaussian_filter(fp.astype(np.float32), sigma=REG_BG_SIGMA_PX) + 1e-6

    d_cat_full = distance_transform_edt(~cat).astype(np.float32)
    allowed_full = fp & (d_cat_full > 2.0)
    n_allowed_full = float(allowed_full.sum())
    basin_frac_fp = float((allowed_full & (elev_slope_2d < BASIN_SLOPE_DEG)).sum()) / n_allowed_full
    print(f"[regime] True Band-19 det_elev_slope < {BASIN_SLOPE_DEG} deg covers {basin_frac_fp*100:.1f}% of allowed footprint", flush=True)

    with rasterio.open(data_root / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif") as src:
        h195_raw = src.read(1)
    h195_surf = gaussian_filter(
        np.where(np.isfinite(h195_raw) & (h195_raw > 0) & fp, 1.0, 0.0).astype(np.float32),
        sigma=0.8,
    )
    del h195_raw

    cols_ctrl1 = list(range(19))
    cols_subsurf = list(PURE_SUBSURF_COLS)
    cols_full = list(range(46))

    arms = [
        "CTRL-0_H19_5_B2",
        "CTRL-1_19BAND_HGB",
        "EXP-1_GSD_HUA_PURE_SUBSURF",
        "EXP-2_GSD_HUA_FULL_MULTIPHYS",
        "EXP-3_GSD_HUA_SAR_DECONFOUNDED",
    ]
    terms_by_arm: dict[str, np.ndarray | None] = {a: None for a in arms}
    per_fold_records: list[dict] = []

    oof_cache = feat_dir / "oof_gsd_hua_v2.npz"
    cached_oof = dict(np.load(oof_cache)) if oof_cache.exists() else {}
    oof_updated = False

    print(f"[start] Evaluating 2 controls + 3 GSD-HUA experiments across seeds (20, 21) ({time.time()-t0:.1f}s)", flush=True)

    for seed in (20, 21):
        folds, quad = buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        d_vis_2d = distance_transform_edt(~visible).astype(np.float32)
        d_vis_fp = d_vis_2d[fp]
        vis_fp = visible[fp]
        quad_fp = quad[fp]

        k_c1, k_e1, k_e2 = f"c1_s{seed}", f"e1_sub_s{seed}", f"e2_full_s{seed}"
        if k_c1 in cached_oof and k_e1 in cached_oof and k_e2 in cached_oof:
            oof_ctrl1 = cached_oof[k_c1]
            oof_sub = cached_oof[k_e1]
            oof_full = cached_oof[k_e2]
            print(f"  [cache] Loaded cached v2 OOF posteriors for seed={seed}", flush=True)
        else:
            oof_ctrl1 = np.zeros(n_fp, dtype=np.float32)
            oof_sub = np.zeros(n_fp, dtype=np.float32)
            oof_full = np.zeros(n_fp, dtype=np.float32)
            rng = np.random.default_rng(1000 + seed)

            for q in range(4):
                fold = folds[q]
                t_fold = time.time()
                train_quad_fp = quad_fp != q
                test_quad_fp = quad_fp == q

                pos_idx = np.flatnonzero(train_quad_fp & vis_fp)
                neg_pool = np.flatnonzero(train_quad_fp & (d_vis_fp > 4.0))
                n_neg = min(pos_idx.size * 4, neg_pool.size, 180_000)
                neg_idx = rng.choice(neg_pool, size=n_neg, replace=False)
                tr_idx = np.concatenate([pos_idx, neg_idx])
                y_tr = np.concatenate([
                    np.ones(pos_idx.size, dtype=np.int8),
                    np.zeros(neg_idx.size, dtype=np.int8),
                ])
                perm = rng.permutation(tr_idx.size)
                tr_idx = tr_idx[perm]
                y_tr = y_tr[perm]

                clf_c1 = HistGradientBoostingClassifier(
                    max_iter=200, learning_rate=0.06, max_leaf_nodes=63,
                    min_samples_leaf=80, l2_regularization=2.0,
                    random_state=42 + 10 * seed + q,
                )
                clf_c1.fit(mm[tr_idx][:, cols_ctrl1], y_tr)
                oof_ctrl1[test_quad_fp] = _predict_in_chunks(clf_c1, mm, cols_ctrl1, test_quad_fp)[test_quad_fp]
                del clf_c1

                clf_sub = HistGradientBoostingClassifier(
                    max_iter=240, learning_rate=0.055, max_leaf_nodes=63,
                    min_samples_leaf=80, l2_regularization=2.5,
                    random_state=142 + 10 * seed + q,
                )
                clf_sub.fit(mm[tr_idx][:, cols_subsurf], y_tr)
                oof_sub[test_quad_fp] = _predict_in_chunks(clf_sub, mm, cols_subsurf, test_quad_fp)[test_quad_fp]
                del clf_sub

                clf_full = HistGradientBoostingClassifier(
                    max_iter=240, learning_rate=0.055, max_leaf_nodes=63,
                    min_samples_leaf=80, l2_regularization=2.5,
                    random_state=242 + 10 * seed + q,
                )
                clf_full.fit(mm[tr_idx][:, cols_full], y_tr)
                oof_full[test_quad_fp] = _predict_in_chunks(clf_full, mm, cols_full, test_quad_fp)[test_quad_fp]
                del clf_full

                print(f"  [fit] seed={seed} fold={fold['name']} trained CTRL-1/EXP-1/EXP-2 in {time.time()-t_fold:.1f}s", flush=True)

            cached_oof[k_c1] = oof_ctrl1
            cached_oof[k_e1] = oof_sub
            cached_oof[k_e2] = oof_full
            oof_updated = True

        allowed_draw = fp & (d_vis_2d > 2.0)

        surf_c1 = np.zeros((H, W), dtype=np.float32)
        surf_c1[fp] = oof_ctrl1
        surf_c1 = gaussian_filter(surf_c1, sigma=0.7)

        surf_e1 = np.zeros((H, W), dtype=np.float32)
        surf_e1[fp] = oof_sub
        surf_e1 = _oriented_ridge_enhance(surf_e1, fp) * (1.0 - 0.40 * mimic_road_2d)

        surf_e2 = np.zeros((H, W), dtype=np.float32)
        surf_e2[fp] = oof_full
        surf_e2 = _oriented_ridge_enhance(surf_e2, fp) * (1.0 - 0.35 * mimic_road_2d) * (1.0 - 0.25 * mimic_shore_2d)

        surf_e3 = _build_sar_deconfounded_surface(
            oof_sub, oof_full, conceal_fp, fp, fp_blur, mimic_road_2d, mimic_shore_2d, allowed_draw
        )

        for q in range(4):
            fold = folds[q]
            cf, orig, sl = _crop_fold(fold)
            fp_sub = fp[sl]
            allowed_fold = fold["region"] & allowed_draw
            frac_fold = float(allowed_fold.sum()) / n_allowed_full
            b_fold = max(1, int(round(BUDGET_DEFAULT * frac_fold)))

            rk_c0, _ = emit_decimated(h195_surf[sl], allowed_fold[sl], tile_px=3)
            em_c0 = emit_prefix(rk_c0, b_fold).astype(np.float32)

            rk_c1, _ = emit_decimated(surf_c1[sl], allowed_fold[sl], tile_px=3)
            em_c1 = emit_prefix(rk_c1, b_fold).astype(np.float32)

            rk_e1, _ = emit_decimated(surf_e1[sl], allowed_fold[sl], tile_px=3)
            em_e1 = emit_prefix(rk_e1, b_fold).astype(np.float32)

            rk_e2, _ = emit_decimated(surf_e2[sl], allowed_fold[sl], tile_px=3)
            em_e2 = emit_prefix(rk_e2, b_fold).astype(np.float32)

            rk_e3, _ = emit_decimated(surf_e3[sl], allowed_fold[sl], tile_px=3)
            em_e3 = emit_prefix(rk_e3, b_fold).astype(np.float32)

            rec = {"seed": seed, "fold": fold["name"], "dti": {}}
            for arm_name, pred_sub in [
                ("CTRL-0_H19_5_B2", em_c0),
                ("CTRL-1_19BAND_HGB", em_c1),
                ("EXP-1_GSD_HUA_PURE_SUBSURF", em_e1),
                ("EXP-2_GSD_HUA_FULL_MULTIPHYS", em_e2),
                ("EXP-3_GSD_HUA_SAR_DECONFOUNDED", em_e3),
            ]:
                sc, terms = eh.evaluate(pred_sub, cf, fp_sub, block_side=200, origin=orig, global_shape=(H, W))
                terms_by_arm[arm_name] = terms if terms_by_arm[arm_name] is None else (terms_by_arm[arm_name] + terms)
                rec["dti"][arm_name] = round(sc["dti"], 6)
            per_fold_records.append(rec)
            print(f"  [eval] seed={seed} fold={fold['name']} -> {rec['dti']}", flush=True)

        del folds, quad, visible, d_vis_2d, d_vis_fp, vis_fp, quad_fp
        del surf_c1, surf_e1, surf_e2, surf_e3
        gc.collect()

    if oof_updated:
        np.savez_compressed(oof_cache, **cached_oof)
    del cached_oof
    gc.collect()

    # =========================================================================
    # Full-footprint production fits (EXP-1 Pure Subsurface & EXP-2 Full Multi-Physics)
    # =========================================================================
    cat_fp = cat[fp]
    d_cat_fp = d_cat_full[fp]
    rng_full = np.random.default_rng(20261027)
    pos_all = np.flatnonzero(cat_fp)
    neg_pool_all = np.flatnonzero(d_cat_fp > 4.0)
    neg_all = rng_full.choice(neg_pool_all, size=min(pos_all.size * 4, neg_pool_all.size, 240_000), replace=False)
    tr_all = np.concatenate([pos_all, neg_all])
    y_all = np.concatenate([np.ones(pos_all.size, dtype=np.int8), np.zeros(neg_all.size, dtype=np.int8)])
    perm_all = rng_full.permutation(tr_all.size)
    tr_all = tr_all[perm_all]
    y_all = y_all[perm_all]

    all_true_mask = np.ones(n_fp, dtype=bool)
    prod_sub_cache = feat_dir / "prod_sub_fp_v2.npy"
    if prod_sub_cache.exists():
        p_sub_full_fp = np.load(prod_sub_cache)
    else:
        p_sub_full_fp = np.zeros(n_fp, dtype=np.float32)
        for m_seed in (301, 302):
            clf_s = HistGradientBoostingClassifier(
                max_iter=260, learning_rate=0.05, max_leaf_nodes=63,
                min_samples_leaf=80, l2_regularization=2.5, random_state=m_seed,
            )
            clf_s.fit(mm[tr_all][:, cols_subsurf], y_all)
            p_sub_full_fp += 0.5 * _predict_in_chunks(clf_s, mm, cols_subsurf, all_true_mask)
            del clf_s
        np.save(prod_sub_cache, p_sub_full_fp)

    prod_full_cache = feat_dir / "prod_full_fp_v2.npy"
    if prod_full_cache.exists():
        p_full_full_fp = np.load(prod_full_cache)
    else:
        p_full_full_fp = np.zeros(n_fp, dtype=np.float32)
        for m_seed in (401, 402):
            clf_f = HistGradientBoostingClassifier(
                max_iter=260, learning_rate=0.05, max_leaf_nodes=63,
                min_samples_leaf=80, l2_regularization=2.5, random_state=m_seed,
            )
            clf_f.fit(mm[tr_all][:, cols_full], y_all)
            p_full_full_fp += 0.5 * _predict_in_chunks(clf_f, mm, cols_full, all_true_mask)
            del clf_f
        np.save(prod_full_cache, p_full_full_fp)

    surf_e1_full = np.zeros((H, W), dtype=np.float32)
    surf_e1_full[fp] = p_sub_full_fp
    surf_e1_full = _oriented_ridge_enhance(surf_e1_full, fp) * (1.0 - 0.40 * mimic_road_2d)

    surf_e2_full = np.zeros((H, W), dtype=np.float32)
    surf_e2_full[fp] = p_full_full_fp
    surf_e2_full = _oriented_ridge_enhance(surf_e2_full, fp) * (1.0 - 0.35 * mimic_road_2d) * (1.0 - 0.25 * mimic_shore_2d)

    surf_e3_full = _build_sar_deconfounded_surface(
        p_sub_full_fp, p_full_full_fp, conceal_fp, fp, fp_blur, mimic_road_2d, mimic_shore_2d, allowed_full
    )

    lattice_path = data_root / "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
    sat_cert = saturation_certificate(lattice_path, fp, cat)
    (ROOT / "evidence/uniqueness_saturation_certificate.json").write_text(json.dumps(sat_cert, indent=2) + "\n")

    prelim = eh.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate="EXP-3_GSD_HUA_SAR_DECONFOUNDED")
    print("\n=== POOLED HOLDOUT-DTI SUMMARY (gems57-pooled-hide-v2, 20 km physical-block bootstrap) ===")
    for a in arms:
        s = prelim["scores"][a]
        print(f"  {a:32s}: DTI = {s['dti']:.6f}  95% CI [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]  (n_withheld={s['withheld_positive_pixels']:,})")

    cand_builders = {
        "EXP-3_GSD_HUA_SAR_DECONFOUNDED": (
            surf_e3_full,
            emit_prefix(emit_decimated(surf_e3_full, allowed_full, tile_px=3)[0], BUDGET_DEFAULT).astype(np.float32),
            "gsdhua3-sar-deconf",
        ),
        "EXP-2_GSD_HUA_FULL_MULTIPHYS": (
            surf_e2_full,
            emit_prefix(emit_decimated(surf_e2_full, allowed_full, tile_px=3)[0], BUDGET_DEFAULT).astype(np.float32),
            "gsdhua2-multiphys",
        ),
        "EXP-1_GSD_HUA_PURE_SUBSURF": (
            surf_e1_full,
            emit_prefix(emit_decimated(surf_e1_full, allowed_full, tile_px=3)[0], BUDGET_DEFAULT).astype(np.float32),
            "gsdhua1-subsurf",
        ),
    }

    exp_ranked = sorted(cand_builders.keys(), key=lambda a: -prelim["scores"][a]["dti"])
    arm_uniqueness_audit = {}
    chosen_arm = None
    surface_clean = None
    dots_clean = None
    uniq_surface = None
    tp_surface = None
    arm_slug = ""

    for arm_name in exp_ranked:
        s_raw, d_raw, slug = cand_builders[arm_name]
        s_clean = np.zeros((H, W), dtype=np.float32)
        s_clean[allowed_full] = np.clip(s_raw[allowed_full], 1e-5, 1.0)
        d_clean = d_raw.astype(np.float32)
        d_clean[~allowed_full] = 0.0

        u_surf = compare_array_to_registry(s_clean, registry_index, fp)
        tp_s = two_phase_summary(u_surf["rows"], n_fp, expected_rasters=len(registry_index["rasters"]))
        s_ok = (not tp_s["like_for_like_reading"]["duplicate"]) and u_surf["complete_accessible_scan"]

        u_dots = compare_array_to_registry(d_clean, registry_index, fp)
        tp_d = two_phase_summary(u_dots["rows"], n_fp, expected_rasters=len(registry_index["rasters"]))
        d_ok = (not tp_d["like_for_like_reading"]["duplicate"]) and u_dots["complete_accessible_scan"]

        arm_uniqueness_audit[arm_name] = {
            "holdout_dti": round(prelim["scores"][arm_name]["dti"], 6),
            "dots": int((d_clean > 0).sum()),
            "surface_unique": s_ok,
            "surface_max_3px_ov_42": round(tp_s["like_for_like_reading"]["worst_forward_overlap_dot_fields"], 6),
            "surface_max_spearman": round(abs(u_surf["worst_spearman_full_footprint"]), 6),
            "dots_unique": d_ok,
            "dots_max_3px_ov_42": round(tp_d["like_for_like_reading"]["worst_forward_overlap_dot_fields"], 6),
            "dots_worst_ov_source": tp_d["like_for_like_reading"]["worst_forward_overlap_dot_field_submission"],
            "dots_max_spearman": round(abs(u_dots["worst_spearman_full_footprint"]), 6),
            "dots_max_jaccard": round(tp_d["like_for_like_reading"]["worst_jaccard"], 6),
        }
        print(f"[uniqueness] {arm_name}: {arm_uniqueness_audit[arm_name]}", flush=True)
        if chosen_arm is None and s_ok and d_ok:
            chosen_arm = arm_name
            surface_clean = s_clean
            dots_clean = d_clean
            uniq_surface = u_surf
            tp_surface = tp_s
            arm_slug = slug

    if chosen_arm is None:
        raise RuntimeError(f"No experimental arm passed dual-phase uniqueness: {arm_uniqueness_audit}")

    summary = eh.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate=chosen_arm)
    for comp_k, comp_v in summary["paired_differences"].items():
        print(f"  [{chosen_arm}] delta vs {comp_k:32s}: {comp_v['delta']:+.6f}  95% CI [{comp_v['ci95'][0]:+.6f}, {comp_v['ci95'][1]:+.6f}]", flush=True)

    emit_dti = summary["scores"][chosen_arm]["dti"]
    ctrl0_dti = summary["scores"]["CTRL-0_H19_5_B2"]["dti"]
    ctrl1_dti = summary["scores"]["CTRL-1_19BAND_HGB"]["dti"]
    beat_controls = (emit_dti > ctrl0_dti) and (emit_dti > ctrl1_dti)

    lli_spec, lli_lam = build_s0_spec(data_root)
    lli_proj = project_lli(dots_clean, lli_spec, lli_lam)
    print(f"[lli] {lli_proj['evidence_class']}: {lli_proj['projected_dti']:.4f} ({lli_proj['uncertainty_band_loo_mae']})", flush=True)

    ts_slug = "20261027"
    raw_bytes_hash = hashlib.sha256(dots_clean.tobytes()).hexdigest()[:12]
    stem = f"gemsdoesass3-{arm_slug}-{int(dots_clean.sum())}-{ts_slug}-{raw_bytes_hash}-zeros"
    sub_note = (
        f"GEMSDOESASS3 {arm_slug} ({int(dots_clean.sum())} dots, B=2, all-finite [0,1]); "
        f"HOLDOUT-DTI={emit_dti:.4f} (gems57-v2)"
    )
    assert len(sub_note) <= 140, f"Note length {len(sub_note)} > 140"

    out_dir = ROOT / "docs/downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old_f in out_dir.glob("gemsdoesass3-*"):
        old_f.unlink()

    tif_path = out_dir / f"{stem}.tif"
    sample_path = data_root / "sample_submission.tif"
    receipt = write_submission(
        tif_path,
        dots_clean,
        sample_path,
        fp,
        note=sub_note,
        name=stem,
        catalogue=cat,
        metadata={
            "lane": "H-GASS3-1 (GSD-HUA)",
            "winning_arm": chosen_arm,
            "holdout_dti": round(emit_dti, 6),
            "evaluator_version": eh.VERSION,
        },
    )
    val_rep = receipt["validator"]
    tmpl_rep = receipt["template_report"]
    uniq_file = compare_to_registry(tif_path, registry_index, fp)
    tp_file = two_phase_summary(uniq_file["rows"], n_fp, expected_rasters=len(registry_index["rasters"]))
    surf_ok = (not tp_surface["like_for_like_reading"]["duplicate"]) and uniq_surface["complete_accessible_scan"]
    file_uniq_ok = (
        (not tp_file["like_for_like_reading"]["duplicate"])
        and uniq_file["complete_accessible_scan"]
        and uniq_file["byte_unique_among_checked"]
        and uniq_file["pixel_unique_among_checked"]
    )

    all_gates_ok = (
        bool(tmpl_rep["ok"])
        and bool(val_rep.get("submittable", True))
        and int(val_rep.get("nan_or_inf", 0)) == 0
        and bool(surf_ok)
        and bool(file_uniq_ok)
        and int(val_rep.get("catalogue_overlap_pixels", 0)) == 0
    )
    verdict = "promote" if (beat_controls and all_gates_ok) else "negative"

    basin_dots_frac = float(((dots_clean > 0) & (elev_slope_2d < BASIN_SLOPE_DEG)).sum()) / max(float((dots_clean > 0).sum()), 1.0)
    deep_sed_dots_frac = float(((dots_clean[fp] > 0) & (mm[:, 14] >= 150.0)).sum()) / max(float((dots_clean > 0).sum()), 1.0)

    np.savez_compressed(
        ROOT / "evidence/gsd_hua_map_preview.npz",
        surface_ds=surface_clean[::4, ::4].astype(np.float16),
        dots_yx=np.column_stack(np.nonzero(dots_clean > 0)).astype(np.int16),
        footprint_ds=fp[::4, ::4],
        catalogue_ds=cat[::4, ::4],
    )

    elapsed = time.time() - t0
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    dot_field_rows = [r for r in uniq_file["rows"] if r.get("representation") == "dot_field"]

    exp_summary = {
        "schema_version": 2,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane_id": "H-GASS3-1 (GSD-HUA)",
        "evaluator_version": eh.VERSION,
        "experiments_run": 3,
        "budget_cap_experiments": 3,
        "elapsed_seconds": round(elapsed, 2),
        "budget_cap_seconds": 7200,
        "peak_rss_mb": round(rss_mb, 1),
        "emitted_unique_arm": chosen_arm,
        "highest_raw_holdout_arm": exp_ranked[0],
        "arm_uniqueness_audit": arm_uniqueness_audit,
        "beat_all_controls": beat_controls,
        "verdict": verdict,
        "target_budget_dots": int(dots_clean.sum()),
        "basin_fraction_of_footprint": round(basin_frac_fp, 4),
        "emitted_dots_basin_slope_lt_4deg_fraction": round(basin_dots_frac, 4),
        "emitted_dots_sedimentary_cover_ge_150m_fraction": round(deep_sed_dots_frac, 4),
        "holdout_scores": summary["scores"],
        "paired_differences_vs_emitted": summary["paired_differences"],
        "per_fold_dti": per_fold_records,
        "saturation_certificate_r13_lattice_s5": sat_cert,
        "surface_uniqueness_two_phase": tp_surface,
        "dots_uniqueness_two_phase": tp_file,
        "dots_per_raster_top12_dotfields": sorted(
            dot_field_rows, key=lambda r: -r["my_dots_within_3px_of_theirs"]
        )[:12],
        "lli_projection": lli_proj,
        "validator_report": val_rep,
        "template_report": tmpl_rep,
        "submission_receipt": receipt,
    }
    (ROOT / "evidence/gsd_hua_experiments.json").write_text(json.dumps(exp_summary, indent=2) + "\n")

    run_card = {
        "schema_version": "gems-run-card-v1",
        "site": "GEMSDOESASS3",
        "branch": "arena/d076f77e-gemsdoesass3",
        "generated_at_utc": exp_summary["timestamp_utc"],
        "hypothesis": (
            "H-GASS3-1 (GSD-HUA): Geothermally Coupled Geomechanical Slip-Dilation & Hydrothermal "
            "Alteration Upflow Architecture — Two-Tower coupling of Pure Subsurface Potential-Field + "
            "Band-15 basement-depth gradient (|grad depth_to_base_surf|) + IR-DATA-B06 true Miller-Singh "
            "magnetic tilt + GeoDAWN TMI_up150 magnetite-destruction & eTh/K + GDR #1391 2m-probe/"
            "geothermometer/sinter plumes with Multi-Physics 3DEP scarp coherence, Positive-Unlabeled SAR "
            "concealment weighting, 6-km regional background demagnification, and road/shoreline mimic suppression."
        ),
        "mechanism": (
            "Active & blind Quaternary Great Basin faults dilate where subsurface basement-relief & potential-field "
            "strike aligns perpendicular to WNW-ESE GPS extension (~114 deg CW, amplified by Band-7/8 geodetic "
            "shear/dilatation), channeling oxidizing/thermal fluids that destroy shallow titanomagnetite "
            "(TMI_up150 - RTP), alter eTh/K and clay-cap boundaries (|grad cond_surf|), and create buried "
            "basement fault walls (|grad depth_to_base_surf|) beneath Quaternary sedimentary cover (depth_to_base_surf). "
            "Weighting coupled subsurface x multi-physics posteriors by SAR concealment odds and whitening against "
            "the 6-km regional background eliminates 100-km seismicity/geodetic coordinate memorization."
        ),
        "mimic": (
            "1) Anthropogenic graded highways, railroad embankments, and canals (US Census TIGER / OpenEI GDR "
            "Transportation) producing sharp 100 m DEM breaks without isostatic gravity (iso_grav_anom_slope) "
            "or basement-throw (|grad depth_to_base_surf|) steps; "
            "2) Pleistocene Lake Lahontan wave-cut shorelines and concentric basin-margin evaporite benches "
            "with uniform gentle slope (~3 deg) and zero subsurface gravity/basement fault roots."
        ),
        "winning_experiment_arm": chosen_arm,
        "experiments_executed": 3,
        "wall_clock_seconds": round(elapsed, 2),
        "leakage_canary": {
            "threshold_symmetric_auc": 0.90,
            "all_passed": canary["all_passed"],
            "max_symmetric_auc": canary["max_symmetric_auc"],
            "highest_signal_feature": canary["highest_signal_feature"],
        },
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": eh.VERSION,
            "split_protocol": "buffered-whole-components-loqo-v2 (seeds 20, 21; hide_frac=0.20; buffer_px=3; boundary_px=12)",
            "withheld_positive_pixels": summary["scores"][chosen_arm]["withheld_positive_pixels"],
            "dti": round(emit_dti, 6),
            "ci": [
                round(summary["scores"][chosen_arm]["ci95"][0], 6),
                round(summary["scores"][chosen_arm]["ci95"][1], 6),
            ],
            "controls_same_split": {
                "CTRL-0_H19_5_B2": {
                    "dti": round(ctrl0_dti, 6),
                    "ci": [
                        round(summary["scores"]["CTRL-0_H19_5_B2"]["ci95"][0], 6),
                        round(summary["scores"]["CTRL-0_H19_5_B2"]["ci95"][1], 6),
                    ],
                },
                "CTRL-1_19BAND_HGB": {
                    "dti": round(ctrl1_dti, 6),
                    "ci": [
                        round(summary["scores"]["CTRL-1_19BAND_HGB"]["ci95"][0], 6),
                        round(summary["scores"]["CTRL-1_19BAND_HGB"]["ci95"][1], 6),
                    ],
                },
            },
            "all_arms": {
                a: {
                    "dti": round(summary["scores"][a]["dti"], 6),
                    "ci": [round(summary["scores"][a]["ci95"][0], 6), round(summary["scores"][a]["ci95"][1], 6)],
                }
                for a in arms
            },
            "paired_differences_vs_emitted": summary["paired_differences"],
        },
        "lli_projection_not_a_score": lli_proj,
        "registry_correlation_overlap": {
            "registry_unique_sha256_count": uniq_file["registry_rasters_checked"],
            "comparable_dot_field_rasters": tp_file["like_for_like_reading"]["dot_field_rasters"],
            "halo_saturated_lattice_rasters": 1,
            "halo_saturated_witness": sat_cert,
            "complete_accessible_scan": uniq_file["complete_accessible_scan"],
            "byte_unique": uniq_file["byte_unique_among_checked"],
            "pixel_unique": uniq_file["pixel_unique_among_checked"],
            "surface_phase": {
                "unique": surf_ok,
                "max_abs_spearman_all_43": round(abs(uniq_surface["worst_spearman_full_footprint"]), 6),
                "worst_spearman_source": uniq_surface["worst_rho_submission"],
                "max_3px_overlap_dot_fields_42": round(tp_surface["like_for_like_reading"]["worst_forward_overlap_dot_fields"], 6),
                "worst_overlap_dot_field_source": tp_surface["like_for_like_reading"]["worst_forward_overlap_dot_field_submission"],
                "literal_5px_lattice_overlap": round(uniq_surface["worst_dot_overlap"], 6),
            },
            "dots_phase": {
                "unique": file_uniq_ok,
                "max_abs_spearman_all_43": round(abs(uniq_file["worst_spearman_full_footprint"]), 6),
                "worst_spearman_source": uniq_file["worst_rho_submission"],
                "max_3px_overlap_dot_fields_42": round(tp_file["like_for_like_reading"]["worst_forward_overlap_dot_fields"], 6),
                "worst_overlap_dot_field_source": tp_file["like_for_like_reading"]["worst_forward_overlap_dot_field_submission"],
                "max_jaccard_all_43": round(uniq_file["worst_jaccard_dot_sets"], 6),
                "literal_5px_lattice_overlap": round(uniq_file["worst_dot_overlap"], 6),
            },
        },
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "validator_output": {
            "validator": val_rep,
            "template_report": tmpl_rep,
        },
        "submission_name": tif_path.name,
        "submission_zip_name": receipt["zip_file"],
        "download_path": f"docs/downloads/{tif_path.name}",
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "ok_to_download": bool(all_gates_ok),
        "ok_to_submit": bool(verdict == "promote"),
        "verdict": verdict,
    }
    (ROOT / "evidence/current_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (ROOT / "docs/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/data/current_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    print(f"\n[DONE] Verdict={verdict.upper()} | File=docs/downloads/{tif_path.name} | SHA256={receipt['sha256'][:16]}... | Elapsed={elapsed:.1f}s | PeakRSS={rss_mb:.1f}MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
