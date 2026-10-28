#!/usr/bin/env python3
"""Experiment E1 (H-SASS3-E): basement-relief minimum-curvature ridges.

Hypothesis (untried in this repo; keyword-screened against the sibling READMEs on 2026-10-28):
  Fault-controlled basement steps (half-graben margins, concealed range-front faults) appear as
  narrow ridges of the most-negative Hessian eigenvalue of the depth-to-basement surface, weighted
  by local relief |grad z|. The layer is `depth_to_base_surf` from the cached 19-band feature stack,
  so no new external data is needed. Non-fault mimic: sedimentary onlap / paleochannel incision.

Protocol (fixed BEFORE running; do not edit the criterion after seeing results):
  * Candidate = top-N pixels of score = max(0, -lambda_min) * |grad z| inside the footprint,
    with N = 37,654 (same dot budget as the 0.2778 champion and the LWST file).
  * Scored only by the shared evaluator `scripts/evaluate_holdout.py::evaluate_path` (Rule 2),
    with B_visible = 2 px, and compared like-for-like with the LWST file and the champion
    in the same process.
  * Single-feature leakage canary (Rule 4): AUC of the continuous score alone vs withheld
    off-catalogue SGMC pixels; symmetric max(AUC, 1-AUC) must be <= 0.90.
  * Overlap within 3 px vs the LWST file and vs the champion (Rule 1; registry audit not run here).
  * PROMOTE-FOR-SELECTOR-REVIEW only if ALL of:
      SGMC-CAL point > LWST SGMC-CAL point (0.065702)
      AND SGMC-CAL 95% CI lower bound > champion SGMC-CAL point (0.064121)
      AND HIDE-RECOVER point > LWST HIDE-RECOVER point (0.006130)
      AND canary symmetric AUC <= 0.90.
    Otherwise NEGATIVE. A promote-for-selector-review result still does NOT spend a slot.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32.paths import data_dir  # noqa: E402
from gems32 import holdout  # noqa: E402
from evaluate_holdout import evaluate_path  # noqa: E402

N_DOTS = 37654
RADIUS_PX = 3.0
LWST_SGMC, LWST_HR = 0.065702, 0.006130  # HOLDOUT-DTI, static evaluator receipt (same evaluator)
CHAMP_SGMC = 0.064121                     # HOLDOUT-DTI, champion e5eb6e7e (same evaluator)
LWST_TIF = ROOT / "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"
CHAMP_TIF_GLOB = "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
OUT_JSON = ROOT / "evidence/hypothesis_h_sass3_e_experiment.json"
TMP = Path("/tmp/hsass3e")


def basement_score(features: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(features) as s:
        names = [d or "" for d in (s.descriptions or ())]
        idx = next(i for i, n in enumerate(names) if n.startswith("depth_to_base_surf")) + 1
        z = s.read(idx).astype(np.float64)
    valid = foot & np.isfinite(z) & (z > -1e30) & (np.abs(z) < 1e20)
    fill = float(np.median(z[valid]))
    zf = np.where(valid, z, fill)
    zs = ndi.gaussian_filter(zf, sigma=2.0)
    gy, gx = np.gradient(zs)
    hyy, hyx = np.gradient(gy)
    hxy, hxx = np.gradient(gx)
    hxy = 0.5 * (hxy + hyx)
    lam_min = 0.5 * (hxx + hyy) - np.sqrt(0.25 * (hxx - hyy) ** 2 + hxy ** 2)
    relief = np.hypot(gx, gy)
    score = np.maximum(0.0, -lam_min) * relief
    score = np.where(foot & valid, score, 0.0)
    return score.astype(np.float64)


def overlap_within(a: np.ndarray, b: np.ndarray, r: float = RADIUS_PX) -> float:
    if a.sum() == 0 or b.sum() == 0:
        return 0.0
    d_b = ndi.distance_transform_edt(~b)
    return float((d_b[a] <= r).mean())


def main() -> int:
    ddir = data_dir()
    features = ddir / "training_features.tif"
    ctx = holdout.load_holdout_context(ddir)
    foot = ctx.foot

    score = basement_score(features, foot)
    pos = score[foot]
    thr = np.partition(pos, -N_DOTS)[-N_DOTS]
    mask = (score >= thr) & foot & (score > 0)
    # Trim ties so the emitted count is exactly N_DOTS when possible.
    if mask.sum() > N_DOTS:
        ys, xs = np.nonzero(mask)
        order = np.argsort(-score[ys, xs], kind="stable")[:N_DOTS]
        m2 = np.zeros_like(mask)
        m2[ys[order], xs[order]] = True
        mask = m2
    TMP.mkdir(parents=True, exist_ok=True)
    cand_npy = TMP / "hsass3e_basement_curv_top37654.npy"
    np.save(cand_npy, mask.astype(np.uint8))

    # Rule 4: single-feature canary vs withheld off-catalogue SGMC pixels.
    neg_pool = foot & ~ctx.labels & ~ctx.sgmc_off
    pos_pool = foot & ~ctx.labels & ctx.sgmc_off
    yy = np.concatenate([np.ones(pos_pool.sum()), np.zeros(neg_pool.sum())])
    ss = np.concatenate([score[pos_pool], score[neg_pool]])
    auc = float(roc_auc_score(yy, ss))
    canary = max(auc, 1.0 - auc)

    cand = evaluate_path(cand_npy, b_visible_px=2.0, ddir=ddir, name="H-SASS3-E-basement-curvature")
    lwst = evaluate_path(LWST_TIF, b_visible_px=2.0, ddir=ddir, name="LWST-GeoConduit")
    cand_hr = cand["hide_and_recover"]
    cand_sg = cand["sgmc_off_catalogue"]

    with rasterio.open(LWST_TIF) as s:
        lwst_mask = s.read(1) > 0
    sib_root = Path(os.environ.get("GEMS_SIB_ROOT", "/tmp/sib"))
    champ_hits = sorted(sib_root.glob(f"x_g32/GEMSDOE32-main/docs/downloads/{CHAMP_TIF_GLOB}"))
    champ_path = champ_hits[0] if champ_hits else None
    champ_overlap = None
    if champ_path is not None:
        with rasterio.open(champ_path) as s:
            champ_mask = s.read(1) > 0
        champ_overlap = overlap_within(mask, champ_mask)
    lwst_overlap = overlap_within(mask, lwst_mask)

    sg_pt = cand_sg["sgmc_prevalence_calibrated_dti"]
    sg_lo = cand_sg["sgmc_calibrated_ci95"][0]
    hr_pt = cand_hr["pooled_dti"]

    criteria = {
        "sgmc_cal_point_gt_lwst": sg_pt is not None and sg_pt > LWST_SGMC,
        "sgmc_cal_ci_lo_gt_champion_point": sg_lo is not None and sg_lo > CHAMP_SGMC,
        "hide_recover_point_gt_lwst": hr_pt is not None and hr_pt > LWST_HR,
        "canary_symmetric_auc_le_090": canary <= 0.90,
    }
    verdict = "promote_for_selector_review" if all(criteria.values()) else "negative"

    out = {
        "schema_version": 1,
        "experiment": "E1 of 3 (Protocol Rule 6 budget)",
        "hypothesis_id": "H-SASS3-E",
        "hypothesis": "Basement-relief minimum-curvature ridges (depth_to_base_surf) weighted by |grad z|",
        "layer": "depth_to_base_surf (cached training_features band, no new external data)",
        "non_fault_mimic": "sedimentary onlap / paleochannel incision along basement surface",
        "candidate_npy": str(cand_npy),
        "emitted_pixels": int(mask.sum()),
        "holdout_dti": {
            "hide_and_recover": cand_hr,
            "sgmc_off_catalogue": cand_sg,
            "label": "HOLDOUT-DTI (evaluator gems32.holdout via scripts/evaluate_holdout.py, B_visible=2 px)",
        },
        "like_for_like_reference": {
            "lwst_hide_and_recover": lwst["hide_and_recover"],
            "lwst_sgmc_off_catalogue": lwst["sgmc_off_catalogue"],
            "champion_sgmc_calibrated_point": CHAMP_SGMC,
            "label": "HOLDOUT-DTI (same process, same evaluator)",
        },
        "leakage_canary_single_feature": {
            "auc_vs_withheld_sgmc": auc,
            "symmetric_auc": canary,
            "pass_le_090": canary <= 0.90,
            "note": "AUC of the continuous score alone vs withheld off-catalogue SGMC pixels; "
                    "not the gems57 fold canary of run_leakage_canary.py",
        },
        "overlap_within_3px": {
            "vs_lwst": lwst_overlap,
            "vs_champion_e5eb6e7e": champ_overlap,
            "registry_rho_and_overlap_audit": "not run for this candidate (no slot; run before any promotion)",
        },
        "pre_registered_criteria": criteria,
        "verdict": verdict,
        "slot_spent": False,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(json.dumps({"verdict": verdict, "criteria": criteria, "auc": canary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
