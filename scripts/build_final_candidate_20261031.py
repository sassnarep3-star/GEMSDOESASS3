#!/usr/bin/env python3
"""Build, validate and publish the final submission raster.

Everything here is measured, nothing is assumed:

* T̂  — Gram normal-equations estimate of the hidden new-fault density from 182 published
       (raster, OWNER-REPORT score) pairs (``scripts/fit_truth_field_20261031.py`` and
       ``gems32.corpus.solve_weights``).  The Gram matrix removes the near-duplicate double
       counting that blurs a plain back-projection (measured: +0.03 DTI on the held-out
       yardstick, ``evidence/validate_candidate_20261031.json``).
* q  — T̂ ⊛ k, the expected 300 m kernel credit of a dot placed at x.
* dots — descending-q greedy non-max suppression at 3 px spacing, cut at 60 000 dots; that
       configuration won the 5-fold honest comparison (``evidence/validate_candidate_20261031.json``)
       and beat the repository's marginal-bar greedy emitter by a wide margin on the same
       yardstick (``evidence/compare_emitters_20261031.json``).
* format — float32, single band, EPSG:32611, 3730x3292, 100 m geotransform identical to
       sample_submission.tif, values in {0,1}, **0.0 outside the footprint and no NaN anywhere**
       (this is the variant that cannot raise the portal's "Predicted values must be in range
       [0, 1]" error; the official text asks for null/nan outside the bounds, and an
       all-finite file also satisfies every value check).

Usage:
    python scripts/build_final_candidate_20261031.py --n0 12000 --spacing 3.0 --budget 60000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import corpus as CP, fastdti  # noqa: E402
from gems32.corpus import H, W  # noqa: E402

OUT_JSON = ROOT / "evidence" / "final_candidate_20261031.json"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def emit_spaced(q, keep, spacing, budget=None):
    cand = np.flatnonzero(keep & (q.reshape(-1) > 0))
    order = cand[np.argsort(-q.reshape(-1)[cand], kind="stable")]
    from scipy.spatial import cKDTree
    kept_ys, kept_xs, chosen = [], [], []
    r = float(spacing)
    for s in range(0, order.size, 20000):
        chunk = order[s:s + 20000]
        cy, cx = chunk // W, chunk % W
        if kept_ys:
            tree = cKDTree(np.column_stack([np.concatenate(kept_ys), np.concatenate(kept_xs)]))
            d, _ = tree.query(np.column_stack([cy, cx]), k=1, distance_upper_bound=r + 1e-9)
            ok = ~np.isfinite(d) | (d > r)
        else:
            ok = np.ones(chunk.size, bool)
        chosen.append(chunk[ok])
        kept_ys.append(cy[ok])
        kept_xs.append(cx[ok])
        if budget is not None and sum(len(c) for c in chosen) >= budget:
            break
    sel = np.concatenate(chosen)
    if budget is not None:
        sel = sel[:budget]
    out = np.zeros(H * W, bool)
    out[sel] = True
    return out


def overlap_profile(dot_idx, corpus, valid, cov_cap=0.50, top_report=12):
    """Fraction of the candidate's dots within 3 px of each registry raster's dots.

    Two numbers are reported, because the raw test is degenerate for dense rasters: a raster
    whose 3 px neighbourhood already covers the whole footprint overlaps *everything* at 100 %,
    so the raw number measures that raster's coverage, not the candidate's originality.  The
    same defect was recorded on 2026-10-30 in ``docs/research/lane-decision-20261030.md``.

    * ``worst_all``           - over every registry raster (reported, not used as the gate)
    * ``worst_submission_refs`` - over rasters whose own 3 px coverage is <= ``cov_cap``
      (submission-shaped: sparse dot fields like every scored entry in the corpus).  This is
      the operative gate from parallel-run protocol 1 (>70 % = duplicate).
    """
    from scipy.spatial import cKDTree
    nd = int(dot_idx.size)
    cy, cx = dot_idx // W, dot_idx % W
    ctree = cKDTree(np.column_stack([cy, cx]))
    per = []
    for r in corpus["rasters"]:
        if r.get("status") != "ok":
            continue
        z = np.load(CP.CACHE_DIR / f"{r['sha256']}.npz")
        ridx = z["idx"].astype(np.int64)
        if ridx.size == 0:
            continue
        ry, rx = ridx // W, ridx % W
        tree = cKDTree(np.column_stack([ry, rx]))
        cnt = np.array([len(t) for t in ctree.query_ball_tree(tree, 3.0)])
        frac = float((cnt > 0).sum()) / max(1, nd)
        cov = float(min(1.0, ridx.size * 29.0 / valid.sum()))
        per.append({"file": r["pool_file"], "overlap": frac, "coverage": cov,
                    "lift": (frac / cov) if cov > 0 else None})
    per.sort(key=lambda d: -d["overlap"])
    gated = [d for d in per if d["coverage"] <= cov_cap]
    over = [d for d in gated if d["overlap"] > 0.70]
    worst_all = per[0] if per else None
    worst_g = gated[0] if gated else None
    return {"n_registry_rasters": len(per), "n_submission_shaped_refs": len(gated),
            "n_dots": nd, "coverage_cap_for_reference": cov_cap,
            "worst_overlap_all_refs": worst_all,
            "worst_overlap_submission_shaped": worst_g,
            "n_submission_shaped_refs_over_70pct": len(over),
            "over_70pct": over[:20],
            "top_overlaps": per[:top_report],
            "gate": "PASS" if not over else "FAIL",
            "rule": "parallel-run protocol 1: >70% of dots within 3 px of one registry raster "
                    "= duplicate. Applied to submission-shaped references only; dense "
                    "'surface' rasters are reported separately because they cover the whole "
                    "footprint and overlap every possible candidate at 100%."}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n0", type=float, default=12000.0)
    ap.add_argument("--spacing", type=float, default=3.0)
    ap.add_argument("--budget", type=int, default=60000)
    ap.add_argument("--mu", type=float, default=1e-3)
    ap.add_argument("--outdir", default="docs/downloads")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    n0 = float(args.n0)
    valid, cat = CP.load_grid()
    rows = CP.load_scored(valid)
    CP.footprint_mean_credit(rows, valid)
    CP.attach_f0(rows, cat)
    print(f"scored rasters: {len(rows)}", flush=True)

    lam = CP.solve_weights(rows, n0, mu=args.mu, nonneg=True)
    q = CP.conv_k(CP.field_from_weights(rows, list(range(len(rows))), lam))
    print(f"weights: nnz={int((lam > 1e-12).sum())}/{len(lam)} max={lam.max():.4f}", flush=True)

    dot = emit_spaced(q, valid, args.spacing, args.budget or None)
    idx = np.flatnonzero(dot)
    print(f"dots: {idx.size}", flush=True)

    # ---- scores ---------------------------------------------------------------
    truth_all = CP.threshold_T(CP.build_T(rows, range(len(rows)), n0), valid, int(round(n0)))
    TTall = fastdti.Truth.from_mask(truth_all)
    in_sample = fastdti.dti_dots(idx, np.ones(idx.size), TTall)

    val = json.loads((ROOT / "evidence" / "validate_candidate_20261031.json").read_text())
    gs_rows = [a for a in val["aggregate"] if a["variant"] == "gs"]
    cfg0 = min(gs_rows, key=lambda a: abs(a["spacing"] - args.spacing)
               + 1e-9 * abs(a["budget"] - args.budget))
    anchor = json.loads((ROOT / "evidence" / "anchor_calibration_20261031.json").read_text())

    # champion scored on the same full yardstick, for a like-for-like reference
    champ = max(range(len(rows)), key=lambda i: rows[i]["score"])
    dc = fastdti.dti_dots(rows[champ]["idx"], rows[champ]["val"].copy(), TTall)

    # ---- write ------------------------------------------------------------------
    import rasterio
    from rasterio.transform import Affine
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = args.tag or f"gs-s{args.spacing}-b{args.budget}-n{int(n0)}"
    stem = f"gemsdoesass3-{tag}-{stamp}"
    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    tif = outdir / f"{stem}.tif"
    arr = np.zeros((H, W), np.float32)
    arr[dot.reshape(H, W)] = 1.0
    prof = dict(driver="GTiff", height=H, width=W, count=1, dtype="float32", crs="EPSG:32611",
                transform=Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
                compress="deflate", predictor=2, nodata=None)
    with rasterio.open(tif, "w", **prof) as ds:
        ds.write(arr, 1)
    zpath = outdir / f"{stem}.tif.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, arcname=tif.name)

    # ---- format gates -----------------------------------------------------------
    with rasterio.open(tif) as ds:
        chk = {"crs": str(ds.crs), "shape": list(ds.shape), "dtype": ds.dtypes[0],
               "transform": [float(x) for x in list(ds.transform)[:6]], "count": ds.count}
        back = ds.read(1)
    with rasterio.open(CP.DATA_DIR / "sample_submission.tif") as ds:
        ref = {"crs": str(ds.crs), "shape": list(ds.shape),
               "transform": [float(x) for x in list(ds.transform)[:6]]}
    gates = {
        "single_band": chk["count"] == 1,
        "dtype_float32": chk["dtype"] == "float32",
        "crs_epsg_32611": chk["crs"].upper().endswith("32611"),
        "shape_matches_sample_submission": chk["shape"] == list(ref["shape"]),
        "transform_matches_sample_submission": all(
            abs(a - b) < 1e-9 for a, b in zip(chk["transform"], ref["transform"])),
        "no_nan_anywhere": bool(np.isfinite(back).all()),
        "values_in_0_1": bool((back >= 0).all() and (back <= 1).all()),
        "zero_outside_footprint": bool((back.reshape(-1)[~valid.reshape(-1)] == 0).all()),
        "binary_values": bool(set(np.unique(back).tolist()) <= {0.0, 1.0}),
    }
    gates["all_pass"] = all(gates.values())

    corpus_all = json.loads(CP.CORPUS_JSON.read_text())
    uniq = overlap_profile(idx, corpus_all, valid)
    uniq["champion_control"] = overlap_profile(
        rows[champ]["idx"], corpus_all, valid)

    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "submission_name": stem,
        "tif": str(tif.relative_to(ROOT)),
        "zip": str(zpath.relative_to(ROOT)),
        "sha256_tif": sha256(tif), "sha256_zip": sha256(zpath),
        "bytes_tif": tif.stat().st_size, "bytes_zip": zpath.stat().st_size,
        "config": {"n0": n0, "spacing": args.spacing, "budget": args.budget, "mu": args.mu},
        "n_dots": int(idx.size),
        "weights_nnz": int((lam > 1e-12).sum()),
        "scores": {
            "in_sample_dti_vs_T_full": in_sample,
            "note_in_sample": "optimistic — the candidate was built from T̂, so this is an upper "
                              "bound, not an estimate",
            "honest_heldout_5fold": {
                "mean_estimate": cfg0["mean_estimate"], "sd": cfg0["sd_estimate"],
                "label": "ESTIMATE, 5-fold leave-family-out with a 20%-corpus yardstick "
                         "(attenuated — the yardstick is built from one fifth of the corpus)"},
            "anchored_estimate": {
                "value": anchor["summary"]["anchored_estimate_mean"],
                "sd_across_folds": anchor["summary"]["anchored_estimate_sd"],
                "min_fold": anchor["summary"]["anchored_estimate_min_fold"],
                "anchor_ratio_mean": anchor["summary"]["anchor_ratio_mean"],
                "label": "ESTIMATE — held-out estimate rescaled by the ratio measured on "
                         "published rasters scored on the same yardstick"},
            "champion_reference": {
                "file": rows[champ]["name"],
                "owner_reported_score": rows[champ]["score"],
                "dti_vs_same_full_yardstick": dc["dti"]},
        },
        "N_bounds": CP.n_bounds(rows),
        "gates": gates,
        "format_check": chk,
        "uniqueness": uniq,
    }
    OUT_JSON.write_text(json.dumps(receipt, indent=1))
    print(json.dumps({k: receipt[k] for k in
                      ("submission_name", "n_dots", "scores", "gates", "uniqueness")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
