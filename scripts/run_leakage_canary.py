#!/usr/bin/env python3
"""Protocol Rule 4 Single-Feature Leakage Canary across all 45 static + 2 fold-visible features.

Tests each feature ALONE against withheld whole-component fault pixels on gems57-pooled-hide-v2
folds (seeds 20, 21). Symmetric max(AUC, 1 - AUC) > 0.90 fails closed until proven otherwise.
"""
from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gemsdoesass3.features import (  # noqa: E402
    build_or_load_static_stack,
    compute_fold_visible_tip_and_relay,
)


def main() -> int:
    t0 = time.time()
    data_root = ROOT / ".cache/gems_data"
    feat_dir = ROOT / ".cache/features"
    grid = load_grid(data_root)
    fp = grid.footprint

    mm, names = build_or_load_static_stack(data_root, feat_dir, fp)
    print(f"[features] Static stack ready: shape={mm.shape} ({time.time()-t0:.1f}s)", flush=True)

    # Verify 0 NaNs / Infs across all 45 columns
    nonfinite_cols = {}
    for j, name in enumerate(names):
        col = mm[:, j]
        bad = int((~np.isfinite(col)).sum())
        if bad > 0:
            nonfinite_cols[name] = bad
    if nonfinite_cols:
        raise AssertionError(f"Non-finite feature values found: {nonfinite_cols}")

    # Pool withheld truth vs stratified active off-catalogue negatives across seeds 20 & 21
    rng = np.random.default_rng(20261027)
    pos_idx_list = []
    neg_idx_list = []
    vis_feats_pos = []
    vis_feats_neg = []

    for seed in (20, 21):
        folds, _ = buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        # All 4 folds in a draw share the same global visible & hidden_all!
        eval_union = np.zeros_like(fp)
        truth_union = np.zeros_like(fp)
        for f in folds:
            eval_union |= f["region"]
            truth_union |= f["truth"]
        masked_known = folds[0]["masked_known"]
        visible = folds[0]["visible"]

        active_fp = (eval_union & ~masked_known)[fp]
        truth_fp = truth_union[fp]
        neg_cand = np.flatnonzero(active_fp & ~truth_fp)
        pos_cand = np.flatnonzero(truth_fp)
        neg_sub = rng.choice(neg_cand, size=min(200_000, neg_cand.size), replace=False)

        pos_idx_list.append(pos_cand)
        neg_idx_list.append(neg_sub)

        beam_fp, dvis_fp = compute_fold_visible_tip_and_relay(visible, fp)
        vis_feats_pos.append(np.column_stack([beam_fp[pos_cand], dvis_fp[pos_cand]]))
        vis_feats_neg.append(np.column_stack([beam_fp[neg_sub], dvis_fp[neg_sub]]))
        print(f"[canary] Computed fold-visible features for seed={seed} (n_pos={pos_cand.size:,}, {time.time()-t0:.1f}s)", flush=True)

    y_true = np.concatenate([
        np.ones(sum(p.size for p in pos_idx_list), dtype=np.int8),
        np.zeros(sum(n.size for n in neg_idx_list), dtype=np.int8),
    ])

    results = []
    max_sym_auc = 0.0
    worst_feat = ""
    quarantined = []

    for j, name in enumerate(names):
        col = mm[:, j]
        vals = np.concatenate(
            [col[p] for p in pos_idx_list] + [col[n] for n in neg_idx_list]
        )
        auc = float(roc_auc_score(y_true, vals))
        sym = max(auc, 1.0 - auc)
        passed = sym <= 0.90
        if not passed:
            quarantined.append(name)
        if sym > max_sym_auc:
            max_sym_auc = sym
            worst_feat = name
        results.append({
            "feature": name,
            "kind": "static_catalogue_free",
            "raw_auc": round(auc, 6),
            "symmetric_auc": round(sym, 6),
            "pass_le_0p90": passed,
        })

    vp = np.vstack(vis_feats_pos)
    vn = np.vstack(vis_feats_neg)
    for k, vname in enumerate(["fold_vis_tip_relay_beam", "fold_vis_d_clamped_log"]):
        vals = np.concatenate([vp[:, k], vn[:, k]])
        auc = float(roc_auc_score(y_true, vals))
        sym = max(auc, 1.0 - auc)
        passed = sym <= 0.90
        if not passed:
            quarantined.append(vname)
        if sym > max_sym_auc:
            max_sym_auc = sym
            worst_feat = vname
        results.append({
            "feature": vname,
            "kind": "fold_visible_only",
            "raw_auc": round(auc, 6),
            "symmetric_auc": round(sym, 6),
            "pass_le_0p90": passed,
        })

    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    top5 = sorted(results, key=lambda r: -r["symmetric_auc"])[:8]
    print("[canary top-8 symmetric AUCs]")
    for r in top5:
        print(f"  {r['feature']:28s} raw={r['raw_auc']:.4f} sym={r['symmetric_auc']:.4f} pass={r['pass_le_0p90']}")
    print(f"[canary] ALL PASSED <= 0.90: {len(quarantined) == 0} | max_sym_auc={max_sym_auc:.4f} ({worst_feat}) | peak_rss={rss_mb:.1f} MB | elapsed={time.time()-t0:.1f}s")

    out = {
        "schema_version": 1,
        "threshold_symmetric_auc": 0.90,
        "all_passed": len(quarantined) == 0,
        "quarantined_features": quarantined,
        "max_symmetric_auc": round(max_sym_auc, 6),
        "highest_signal_feature": worst_feat,
        "withheld_positive_evaluations": int(sum(p.size for p in pos_idx_list)),
        "negative_sample_evaluations": int(sum(n.size for n in neg_idx_list)),
        "peak_rss_mb": round(rss_mb, 1),
        "elapsed_seconds": round(time.time() - t0, 2),
        "features": results,
    }
    (ROOT / "evidence").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence/leakage_canary.json").write_text(json.dumps(out, indent=2) + "\n")
    if quarantined:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
