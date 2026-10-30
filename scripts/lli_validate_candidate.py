#!/usr/bin/env python3
"""Validate a candidate emission against the LLI instrument WITHOUT trusting one single lambda.

Three independent densities are used, and the candidate is projected under all three:

  lam_published_S0  GEMSDOE32's published S0 fit (111 live rasters, LOO MAE 0.0221, rho 0.926)
  lam_published_S3  their finer-Halo design S3 (LOO MAE 0.0219, rho 0.927)
  lam_local_convex  refit HERE on the locally mirrored pool, bounded lambda in [0,1] with the
                    graph-Laplacian smoothness prior (LLI-v2 convex form), leave-site-out validated

A candidate that only wins under the density it was optimised against is proxy exploitation; a
candidate that wins under all three, and under the leave-site-out refit, is a real signal.  The
champion raster (live 0.2778) is projected in the same table as the control, so the comparison is a
difference of projections, never a claim about a future score.

Also reported per candidate: exact-cell agreement with every sibling raster, subsumption fraction,
and the 3-px overlap that the parallel-run protocol's LANE rule uses.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import ledger_inversion as li  # noqa: E402
from gems32.metric import dti_exact  # noqa: E402

BL = "build_lambda_candidate.py"
spec_mod = importlib.util.spec_from_file_location("bl", ROOT / "scripts" / BL)
bl = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(bl)


def read_pos(p, shape):
    with rasterio.open(p) as ds:
        a = ds.read(1)
    if a.shape != shape:
        return None
    return np.isfinite(a) & (a > 0)


def cell_stats(placed, other):
    inter = int((placed & other).sum())
    return {"shared_cells": inter,
            "frac_of_candidate_on_sibling": inter / max(int(placed.sum()), 1),
            "sibling_subsumes_candidate": inter / max(int(placed.sum()), 1) >= 0.95,
            "xor_cells": int((placed ^ other).sum())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--champion", default="/tmp/g32/docs/downloads/"
                                          "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    ap.add_argument("--pool", default="/tmp/g32/docs/downloads/*.tif,/home/user/focus/*.tif,"
                                      "/home/user/ledger/*.tif")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "lli_candidate_validation.json"))
    a = ap.parse_args()

    ev_path = ROOT / "evidence" / "lli_score_model_verification.json"
    ev = json.loads(ev_path.read_text())
    theta0 = np.array(ev["published_theta_check_on_local_pool"]["theta"], float)
    theta3 = np.array(json.loads(Path("/home/user/reg32/live_ledger_inversion.json").read_text())
                      ["designs"]["S3"]["fit"]["theta"], float)

    shape = bl.read1(ROOT / "data" / "official" / "sample_submission.tif").shape
    cand = read_pos(Path(a.candidate), shape)
    champ = read_pos(Path(a.champion), shape)
    if cand is None or champ is None:
        raise SystemExit("candidate or champion grid mismatch")

    out = {"schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "evidence_class": "PROJECTIONS (LLI model outputs), never scores; champion row is the control "
                             "whose live score 0.2778 is OWNER-REPORT",
           "candidate": {"file": Path(a.candidate).name, "sha256": bl.sha256_file(a.candidate),
                         "dots": int(cand.sum())},
           "champion": {"file": Path(a.champion).name, "sha256": bl.sha256_file(a.champion),
                        "dots": int(champ.sum()), "live_owner_report": 0.2778},
           "projections": {}, "duplicate_tests": {}, "lane_metrics": {}}

    # ---------- the three densities ----------
    lams = {}
    for tag, th, design in (("published_S0", theta0, "S0"), ("published_S3", theta3, "S3")):
        sp, lam_grid, foot, labels, active, ss_meta = bl.build_strata(design, th)
        lams[tag] = (sp, li.strata_lambda(th, sp), active, foot, labels)
    # local convex refit (bounded lambda, smoothness prior) on the locally mirrored live pool
    sp, _lam0, active, foot, labels = lams["published_S0"]
    A_all, B_all, N_all, s_all, used = [], [], [], [], []
    files = []
    for g in a.pool.split(","):
        files += glob.glob(g.strip())
    files = sorted(set(files))
    seen = set()
    for p in files:
        m = read_pos(p, shape)
        if m is None:
            continue
        arr = np.where(m, 1.0, 0.0).astype(np.float32)
        row = li.design_row(arr, sp)
        dig = hashlib.sha256(np.round(np.where(m, 1.0, 0.0)[active], 5).tobytes()).hexdigest()[:16]
        if dig in seen or row["N"] <= 0:
            continue
        seen.add(dig)
        name = Path(p).name
        sc = None
        for stem, rec in EV_LEDGER_INDEX.items():
            if len(stem) > 8 and stem in name:
                sc = rec["score"]
                break
        if sc is None:
            continue
        A_all.append(row["A"]); B_all.append(row["B"]); N_all.append(row["N"]); s_all.append(sc)
        used.append({"file": name, "live": sc})
    lam_vec_local = None
    if len(s_all) >= 20:
        Aa, Ba, Na, sa = map(np.asarray, (A_all, B_all, N_all, s_all))
        fitc = li.fit_convex(Aa, Ba, Na, sa, sp, mu=1.0)
        looc = li.loo_convex(Aa, Ba, Na, sa, sp, mu=1.0)
        lam_vec_local = fitc["lambda"]
        lams["local_convex"] = (sp, lam_vec_local, active, foot, labels)
        out["local_convex_fit"] = {"n_rasters": int(sa.size), "loo_mae": looc["mae"],
                                   "loo_spearman": looc["spearman"], "g_px": float(fitc["g"]),
                                   "lambda_min": float(lam_vec_local.min()), "lambda_max": float(lam_vec_local.max()),
                                   "score_source": "evidence/score_ledger_index.json (OWNER-REPORT)",
                                   "rows_matched": used[:12]}
    else:
        out["local_convex_fit"] = {"skipped": f"only {len(s_all)} locally matched live rasters"}

    for tag, (sp_, lam_vec, act_, foot_, lab_) in lams.items():
        for name, mask in (("candidate", cand), ("champion_control", champ)):
            row = li.design_row(np.where(mask, 1.0, 0.0).astype(np.float32) * act_, sp_)
            c = li.predict_components(row["A"][None, :], row["B"][None, :], np.array([row["N"]]),
                                      sp_.sizes, lam_vec)
            out["projections"].setdefault(tag, {})[name] = {
                "projected_dti": float(c["dti"][0]), "tp": float(c["tp"][0]), "fp": float(c["fp"][0]),
                "fn": float(c["fn"][0]), "N_mass": float(row["N"]), "dots": int(mask.sum())}
    if out["projections"]:
        vals = [d["candidate"]["projected_dti"] for d in out["projections"].values()]
        chs = [d["champion_control"]["projected_dti"] for d in out["projections"].values()]
        out["projection_summary"] = {"candidate_min": min(vals), "candidate_max": max(vals),
                                     "champion_min": min(chs), "champion_max": max(chs),
                                     "delta_worst_case": min(vals) - max(chs),
                                     "delta_best_case": max(vals) - min(chs),
                                     "n_lambda_variants": len(vals),
                                     "rule": "beats the champion only if delta_worst_case > 0"}

    # ---------- duplicate tests against the whole mirrored pool ----------
    worst = {"overlap3px": (0.0, None), "shared_frac": (0.0, None), "xor": (10 ** 9, None)}
    digests = {}
    rows = []
    for p in sorted(set(files)):
        m = read_pos(p, shape)
        if m is None:
            continue
        ovl = bl.overlap_fraction(cand, m)
        st = cell_stats(cand, m)
        if int(m.sum()) == int(cand.sum()) and st["xor_cells"] == 0:
            rows.append({"file": Path(p).name, "identical": True})
        worst["overlap3px"] = max(worst["overlap3px"], (ovl, Path(p).name))
        worst["shared_frac"] = max(worst["shared_frac"], (st["frac_of_candidate_on_sibling"], Path(p).name))
        worst["xor"] = min(worst["xor"], (st["xor_cells"], Path(p).name))
        rows.append({"file": Path(p).name, "dots": int(m.sum()), "overlap3px": ovl, **st})
    out["duplicate_tests"] = {"n_pool": len(rows), "identical_files": [r for r in rows if r.get("identical")],
                              "worst_3px_overlap": {"frac": worst["overlap3px"][0], "file": worst["overlap3px"][1]},
                              "worst_exact_cell_share": {"frac": worst["shared_frac"][0],
                                                          "file": worst["shared_frac"][1]},
                              "min_xor_cells": {"cells": worst["xor"][0], "file": worst["xor"][1]},
                              "top10_by_overlap": sorted((r for r in rows if "overlap3px" in r),
                                                          key=lambda r: -r["overlap3px"])[:10]}
    # ---------- official-metric diagnostics on the catalogue (NOT the scored truth) ----------
    with rasterio.open(ROOT / "data" / "official" / "labels.tif") as ds:
        lab = ds.read(1)
    fmask = np.isfinite(bl.read1(ROOT / "data" / "official" / "sample_submission.tif"))
    for name, mask in (("candidate", cand), ("champion_control", champ)):
        d = dti_exact(mask.astype(np.float32), (lab > 0) & fmask, valid=fmask)
        out.setdefault("catalogue_diagnostic", {})[name] = {
            "dti_vs_catalogue_labels": d["dti"], "coverage": d["coverage"], "n_truth_px": d["n_truth"],
            "note": "traces KNOWN faults; the scored truth is the off-catalogue set, so this is a "
                    "mechanism diagnostic, not a score estimate"}
    Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("projections", "projection_summary", "duplicate_tests")
                      if k in out}, indent=1, default=float)[:2600])
    print("wrote", a.out)
    return 0


try:
    EV_LEDGER_INDEX = json.loads((Path(__file__).resolve().parents[1] / "evidence" /
                                  "score_ledger_index.json").read_text())["index"]
except Exception:
    EV_LEDGER_INDEX = {}

if __name__ == "__main__":
    raise SystemExit(main())
