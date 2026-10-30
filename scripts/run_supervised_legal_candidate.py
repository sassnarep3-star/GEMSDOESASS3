#!/usr/bin/env python3
"""EXP3 — supervised SAR-PU dual-objective HGB surface, packed to the literal 21,713-dot legal cap.

Reuses the frozen EXP2 pipeline pieces from scripts/run_lwst_experiments.py (imported, not forked):
_fit_sarpu_dual_fold + _predict_dual_chunked + the LWST crest/tip/pack helpers. Changes ONLY the
budget policy: instead of 37,654 structure-hugging dots (99.8% within 3 px of the 13GEMSDOE lattice
→ Protocol Rule 1 duplicate), the map is packed to the legal cap — K = floor(0.69·G/(1−0.69))
inside dots (lattice-covered, >2 px from catalogue labels) + all G = 6,514 gap dots
(footprint pixels >3 px from every lattice dot) = 21,012 dots, inside share 0.690 ≤ 0.70.

Evaluations (all HOLDOUT-DTI, never organizer scores):
  * hide-and-recover (GEMSDOE32-HIDE-RECOVER-v3.0, b_visible=2.0) on 8 leak-free fold-cell packs
  * SGMC-CAL-v3.0 on the full legal map
  * 51-channel single-feature leakage canary (recomputed, not inherited)
  * paired spatial-block bootstrap vs the champion reference recorded in the ledger

Usage: python scripts/run_supervised_legal_candidate.py --out-doc <name>.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

spec = importlib.util.spec_from_file_location("rle", ROOT / "scripts" / "run_lwst_experiments.py")
rle = importlib.util.module_from_spec(spec)
sys.modules["rle"] = rle
spec.loader.exec_module(rle)

from gems32 import holdout, lwst_geoconduit as lwst  # noqa: E402
from gems32.paths import data_dir, downloads_dir, evidence_dir, work_dir  # noqa: E402
from gems32.submission import audit_geotiff  # noqa: E402

TAU = 0.69
INSIDE_BUDGET = 14_498  # floor(0.69*6514/0.31), same as build_literal_candidate.py
GAP_DOTS = 6_514
TOTAL = INSIDE_BUDGET + GAP_DOTS


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def legal_gap_mask(foot: np.ndarray, labels: np.ndarray, lattice: np.ndarray) -> np.ndarray:
    d = ndi.distance_transform_edt(~lattice)
    return foot & ~(d <= 3.0) & ~labels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-doc", required=True)
    ap.add_argument("--skip-hr", action="store_true", help="skip the 8 leak-free fold-cell fits (HR eval)")
    args = ap.parse_args()
    t0 = time.time()
    ddir, wdir, edir, dl = data_dir(), work_dir(), evidence_dir(), downloads_dir()

    base_npy, lwst_npy = wdir / "feature_stack.npy", wdir / "lwst_extra_stack.npy"
    if not base_npy.exists() or not lwst_npy.exists():
        raise SystemExit("missing stacks; run scripts/prepare_data.py and the LWST stack build first")
    base_mm = np.load(base_npy, mmap_mode="r")
    lwst_mm = np.load(lwst_npy, mmap_mode="r")
    ctx = holdout.load_holdout_context(ddir)
    collars = {
        f: ndi.binary_dilation(ctx.quad == f, structure=np.ones((3, 3), dtype=bool), iterations=rle.COLLAR_PX) & ctx.foot
        for f in range(4)
    }
    fold_domains = {
        f: ndi.binary_erosion(ctx.quad == f, iterations=holdout.DOMAIN_ERODE) & ctx.foot
        for f in range(4)
    }

    # --- Rule-4 canary on the 51 channels (recomputed for this run) ---
    print("[EXP3] 51-channel leakage canary...", flush=True)
    canary = rle.run_leakage_canary(base_mm, lwst_mm, ctx)
    if not canary["all_passed"]:
        raise SystemExit(f"leakage canary failed on {canary['worst_channel']} ({canary['worst_symmetric_auc']})")
    print(f"[EXP3] canary PASS worst={canary['worst_channel']} {canary['worst_symmetric_auc']:.4f}", flush=True)

    # --- Full-map 4-quadrant spatially-collared OOF surface (deployment model) ---
    full_ckpt = wdir / "lwst_full_oof.npy"
    if full_ckpt.exists():
        prob_full_oof = np.load(full_ckpt)
        print("[EXP3] loaded cached full-map OOF surface", flush=True)
    else:
        prob_full_oof = np.zeros(ctx.foot.shape, dtype=np.float32)
        for q in range(4):
            tq = time.time()
            train_zone_q = ctx.foot & (~collars[q])
            clf_lgb_q, clf_hgb_q = rle._fit_sarpu_dual_fold(base_mm, lwst_mm, train_zone_q, ctx.labels, seed=20262000 + q * 31)
            q_mask = (ctx.quad == q) & ctx.foot
            prob_full_oof[q_mask] = rle._predict_dual_chunked(clf_lgb_q, clf_hgb_q, base_mm, lwst_mm, q_mask)[q_mask]
            del clf_lgb_q, clf_hgb_q
            print(f"[EXP3] quadrant {q} fit+predict done ({time.time()-tq:.0f}s)", flush=True)
        np.save(full_ckpt, prob_full_oof)

    clean_gate = lwst_mm[:, :, 14].astype(np.float32)
    tip_full = lwst.compute_fold_visible_tip_cone(ctx.labels, ctx.foot)
    prob_full_raw = prob_full_oof * (np.float32(0.75) + np.float32(0.25) * clean_gate)
    prob_full_mod = prob_full_raw * (np.float32(1.0) + np.float32(0.75) * tip_full)
    del prob_full_oof, tip_full, clean_gate

    crest_full = lwst.sharpen_steerable_crest(prob_full_mod, ctx.foot)
    del prob_full_mod

    # --- Legal pack: K inside dots + all G gap dots ---
    with rasterio.open(ddir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    labels = holdout.read_binary(ddir / "labels.tif") & foot
    lattice = holdout.read_binary(ddir / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif") & foot
    gap = legal_gap_mask(foot, labels, lattice)
    G = int(gap.sum())
    K = int(np.floor(TAU * G / (1.0 - TAU)))
    if (G, K) != (GAP_DOTS, INSIDE_BUDGET):
        raise SystemExit(f"gap/K mismatch: G={G} K={K} (expected {GAP_DOTS}/{INSIDE_BUDGET})")
    dist_labels = ndi.distance_transform_edt(~labels).astype(np.float32)
    eligible_inside = foot & ~gap & (dist_labels > rle.B_VISIBLE_PX) & ~labels
    del dist_labels
    inside_dots = lwst.pack_single_horizon(crest_full, eligible_inside, budget=K)
    legal_mask = inside_dots | gap
    total = int(legal_mask.sum())
    inside_share = float(inside_dots.sum()) / float(total)
    print(f"[EXP3] legal pack: inside={int(inside_dots.sum())} gap={G} total={total} inside_share={inside_share:.4f}", flush=True)

    # --- Leak-free fold-cell packs at the same legal policy (for hide-and-recover) ---
    hr_res = None
    if not args.skip_hr:
        cell_masks: dict[str, np.ndarray] = {}
        for idx, cell in enumerate(ctx.cells):
            tc = time.time()
            cid = cell.key
            sl = cell.bbox
            train_zone = ctx.foot & (~collars[cell.fold])
            clf_lgb, clf_hgb = rle._fit_sarpu_dual_fold(base_mm, lwst_mm, train_zone, cell.visible_full, seed=20261027 + idx * 17)
            quad_target = np.zeros(ctx.foot.shape, dtype=bool)
            quad_target[sl] = ctx.foot[sl]
            prob_q = rle._predict_dual_chunked(clf_lgb, clf_hgb, base_mm, lwst_mm, quad_target)
            prob_raw_sub = prob_q[sl] * (np.float32(0.75) + np.float32(0.25) * lwst_mm[:, :, 14].astype(np.float32)[sl])
            tip_vis = lwst.compute_fold_visible_tip_cone(cell.visible_full, ctx.foot)
            prob_sub = prob_raw_sub * (np.float32(1.0) + np.float32(0.75) * tip_vis[sl])
            del clf_lgb, clf_hgb, prob_q, tip_vis
            crest_sub = lwst.sharpen_steerable_crest(prob_sub, ctx.foot[sl])
            elig_sub = fold_domains[cell.fold][sl] & cell.active_sub & (cell.d_visible_sub > rle.B_VISIBLE_PX)
            gap_sub = gap[sl]
            K_sub = max(1, int(round(K * float(elig_sub.sum()) / max(int(eligible_inside.sum()), 1))))
            in_dots = lwst.pack_single_horizon(crest_sub, elig_sub, budget=K_sub)
            m = in_dots | gap_sub
            cell_masks[cid] = m
            del prob_raw_sub, prob_sub, crest_sub, in_dots
            print(f"[EXP3] fold cell {idx+1}/8 ({cid}) packed ({time.time()-tc:.0f}s, {int(m.sum())} dots)", flush=True)
        hr_res = holdout.evaluate_hide_and_recover(cell_masks, ctx, b_visible_px=rle.B_VISIBLE_PX, name="EXP3_SARPU_LEGAL21K")
        print(f"[EXP3] hide-and-recover: {hr_res['pooled_dti']:.6f} {hr_res['ci95_cluster_bootstrap']}", flush=True)

    sg_res = holdout.evaluate_sgmc_with_ci(legal_mask, ctx, name="EXP3_SARPU_LEGAL21K")
    print(f"[EXP3] SGMC-CAL: cal={sg_res['sgmc_prevalence_calibrated_dti']:.6f} raw={sg_res['sgmc_raw_pooled_dti']:.6f}", flush=True)

    # --- Emit GeoTIFF (NaN outside, values {1.0}) ---
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"gemsdoesass3-exp3-sarpu-legal21k-{ts}-nan"
    out_path = dl / f"{name}.tif"
    out = np.zeros(foot.shape, dtype=np.float32)
    out[legal_mask] = np.float32(1.0)
    out[~foot] = np.nan
    with rasterio.open(ddir / "sample_submission.tif") as t:
        profile = t.profile.copy()
    profile.update(driver="GTiff", dtype="float32", count=1, nodata=float("nan"), compress="deflate")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(out, 1)
    with zipfile.ZipFile(out_path.with_suffix(".tif.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        z.write(out_path, arcname=out_path.name)
    fmt = audit_geotiff(out_path, foot, labels, mode="nan", template_tif=ddir / "sample_submission.tif")

    doc = {
        "schema_version": 1,
        "generated_utc": ts,
        "experiment": "EXP3_SARPU_LEGAL21K",
        "lane": "H-SASS3-I: supervised SAR-PU dual-objective HGB, legal literal-cap pack",
        "budget_policy": {"tau": TAU, "inside": int(inside_dots.sum()), "gap": G, "total": total, "inside_share": round(inside_share, 4)},
        "leakage_canary": {"all_passed": canary["all_passed"], "worst_channel": canary["worst_channel"], "worst_symmetric_auc": canary["worst_symmetric_auc"], "n_channels": canary["n_channels_tested"]},
        "hide_and_recover": None if hr_res is None else {
            "score_label": "HOLDOUT-DTI", "evaluator_version": hr_res["evaluator_version"],
            "b_visible_px": hr_res["b_visible_px"], "n_withheld_positives": hr_res["n_withheld_positives"],
            "pooled_dti": hr_res["pooled_dti"], "ci95": hr_res["ci95_cluster_bootstrap"],
        },
        "sgmc": {
            "score_label": "HOLDOUT-DTI", "evaluator_version": holdout.SGMC_EVALUATOR_VERSION,
            "n_withheld_positives": int(ctx.sgmc_n_truth),
            "calibrated": sg_res["sgmc_prevalence_calibrated_dti"], "calibrated_ci95": sg_res["sgmc_calibrated_ci95"],
            "raw": sg_res["sgmc_raw_pooled_dti"], "raw_ci95": sg_res["sgmc_raw_ci95"],
        },
        "champion_reference": {
            "note": "37,654-dot champion — NOT a legal alternative under Rule 1; reference only",
            "hide_recover_pooled_dti": 0.09920232315251679, "hide_recover_ci95": [0.08595140754809347, 0.11266835751415871],
            "sgmc_calibrated": 0.0641209376417646, "sgmc_calibrated_ci95": [0.056730181217206584, 0.0716486609703412],
        },
        "output": {"tif": str(out_path), "tif_sha256": sha256_file(out_path), "zip_sha256": sha256_file(out_path.with_suffix(".tif.zip"))},
        "format_audit_passed": fmt["all_checks_passed"],
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.out_doc).write_text(json.dumps(doc, indent=2) + "\n")
    np.save(edir / "exp3_surface_crest.npy", crest_full.astype(np.float32))
    print(json.dumps({k: doc[k] for k in ("budget_policy", "hide_and_recover", "sgmc", "output")}, indent=2)[:1800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
