#!/usr/bin/env python3
"""Independent re-derivation and use of the Live-Ledger Inversion (LLI-v1, design S0).

Why this script exists
----------------------
The repository's earlier sessions could not score a candidate: the only holdouts they had draw their
truth from a published catalogue, and both repos document that those holdouts rank the nine live-scored
focus files in the OPPOSITE order to the leaderboard (HIDE-RECOVER rho = -0.849, GEMSDOE32
`evidence/evaluator_rank_validity_20261029.json`; Spearman -0.89 on n = 10 in our own
`evidence/holdout_vs_leaderboard_concordance_20261029.json`).  The organisers mask the catalogue
out of scoring, so catalogue-recovery cannot rank candidates.

The only measurements of the hidden scoring population are the live scores themselves.  LLI inverts them
into a per-stratum truth density lambda_k (strata defined by FEATURES only: distance to the catalogue
and distance to the H19-5 ridge network), so a new raster can be *projected* without ever touching a
submission slot.  GEMSDOE32 published the fit; this script re-derives the design rows for every raster
we can hash-verify locally and checks the published numbers line by line.

Evidence classes (protocol rule 3, enforced in the output schema)
-----------------------------------------------------------------
* ``live``         OWNER-REPORT, from ``docs/score-ledger.csv`` of the mirrored sibling repository
                   (not an organizer receipt).
* ``fit``/``loo``  LLI MODEL OUTPUT -- a PROJECTION, never a score.

Nothing here is a score.  ``ok_to_submit`` is decided by ``scripts/verify_all_gates.py``, not by this file.

Usage
-----
    python scripts/lli_score_model.py                      # rebuild spec, verify, write evidence JSON
    python scripts/lli_score_model.py --project a.tif b.tif # project new rasters
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import ledger_inversion as li  # noqa: E402
from gems32.metric import dti_exact  # noqa: E402

DDIR = ROOT / "data" / "official"
H195 = DDIR / "scored" / "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"
# Hash-verified byte-identical to buffedlizard55-lab/19GEMSDOE:submissions/<same name>
# and to GEMSDOE24's mirror `gems24-h24-0-mirror-h19-5-group-best-20261002-e27054cf-nan.tif`
# (both sha256 ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d).
LEDGER_CSVS = [Path("/home/user/reg32/score-ledger.csv")]
POOL_GLOBS = [
    "/home/user/ledger/*.tif",
    "/home/user/focus/*.tif",
    "/tmp/g32/docs/downloads/*.tif",
    "/tmp/g32/evidence/*.tif",
    "/tmp/g19/docs/downloads/*.tif",
    "/tmp/g19/submissions/*.tif",
    str(ROOT / "docs/downloads/*.tif"),
]
LLI_JSON = Path("/home/user/reg32/live_ledger_inversion.json")


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read1(p, band: int = 1) -> np.ndarray:
    with rasterio.open(p) as ds:
        return ds.read(band)


def digitize(d: np.ndarray, edges, codes) -> np.ndarray:
    idx = np.digitize(d, edges, right=True)
    return np.asarray(codes, np.int8)[idx]


def build_spec():
    """S0 exactly as buffedlizard55-lab/GEMSDOE32:scripts/run_live_ledger_inversion.py::build_spec."""
    foot = np.isfinite(read1(DDIR / "sample_submission.tif"))
    labels = (read1(DDIR / "labels.tif") > 0) & foot
    active = foot & ~labels
    d_cat = distance_transform_edt(~labels)
    cat_lv = digitize(d_cat, [1.01, 2.01, 3.01, 5.01, 10.01, 20.01, 50.01], [1, 2, 3, 4, 5, 6, 7, 0])
    cat_lab = [">50", "1", "1.4-2", "2.2-3", "3-5", "5-10", "10-20", "20-50"]
    h = read1(H195)
    h = np.isfinite(h) & (h > 0) & foot
    d_h = distance_transform_edt(~h)
    h_lv = digitize(d_h, [0.01, 1.01, 2.01, 5.01], [1, 2, 3, 4, 0])
    h_lab = [">5", "on", "1", "1.4-2", "2.2-5"]
    for lv in (cat_lv, h_lv):
        lv[~active] = 0
    spec = li.StrataSpec(names=["d_catalogue_px", "d_H19-5_px"], levels=[cat_lv, h_lv],
                         n_levels=[8, 5], level_labels=[cat_lab, h_lab], active=active)
    meta = {"design": "S0", "n_strata": int(spec.n_strata), "n_params": int(li.n_params(spec)),
            "active_pixels": int(active.sum()), "footprint_pixels": int(foot.sum()),
            "catalogue_pixels_in_footprint": int(labels.sum()),
            "h195_pixels_in_footprint": int(h.sum()),
            "inputs_sha256": {"sample_submission.tif": sha256_file(DDIR / "sample_submission.tif"),
                              "labels.tif": sha256_file(DDIR / "labels.tif"),
                              "h19-5": sha256_file(H195)}}
    return spec, meta, foot, labels


def ledger_index() -> dict:
    """submission-stem -> live score (OWNER-REPORT) from the mirrored score ledger."""
    out = {}
    for csv_path in LEDGER_CSVS:
        if not csv_path.exists():
            continue
        with open(csv_path) as fh:
            for r in csv.DictReader(fh):
                try:
                    sc = float(r["score"])
                except (ValueError, KeyError):
                    continue
                stem = (r.get("submission") or "").strip()
                if stem:
                    out.setdefault(stem, {"score": sc, "site": r.get("site"), "source": str(csv_path)})
    return out


def candidate_files() -> list[Path]:
    files: list[Path] = []
    seen = set()
    for g in POOL_GLOBS:
        for p in sorted(glob.glob(g)):
            p = Path(p)
            rp = p.resolve()
            if rp in seen or p.stat().st_size > 8_000_000:
                continue
            seen.add(rp)
            files.append(p)
    return files


def row_for(path: Path, spec, tpl):
    with rasterio.open(path) as ds:
        if (ds.shape, ds.crs, ds.transform) != tpl or ds.count < 1:
            return None, "grid_mismatch", 0, None
        arr = ds.read(1).astype(np.float32)
    arr = np.where(np.isfinite(arr), arr, 0.0)
    if (arr[spec.active] < -1e-6).any() or (arr[spec.active] > 1 + 1e-6).any():
        return None, "values_outside_unit_interval", 0, None
    arr[~spec.active] = 0.0
    if not (arr[spec.active] > 0).any():
        return None, "empty_in_scored_domain", 0, None
    return (li.design_row(arr, spec), hashlib.sha256(np.round(arr[spec.active], 5).tobytes()).hexdigest()[:16],
            int((arr > 0).sum()), arr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", nargs="*", default=[])
    a = ap.parse_args()

    spec, meta, foot, labels = build_spec()
    with rasterio.open(DDIR / "sample_submission.tif") as ds:
        tpl = (ds.shape, ds.crs, ds.transform)
    led = ledger_index()

    # ---- 1. re-derive design rows for every locally hash-verifiable live-scored raster ----
    digests: dict[str, dict] = {}
    skipped: list[dict] = []
    files = candidate_files()
    print(f"scanning {len(files)} candidate files", flush=True)
    for _i, p in enumerate(files):
        if _i % 10 == 0:
            print(f"  [{_i}/{len(files)}] {p.name[:60]}", flush=True)
        score_rec = None
        for stem, rec in led.items():
            if stem and (stem in p.name or stem.replace("_", "-") in p.name):
                score_rec = rec
                break
        try:
            res, dig, npos, arr = row_for(p, spec, tpl)
        except Exception as exc:  # never silently drop
            skipped.append({"file": p.name, "reason": f"read_error {type(exc).__name__}"})
            continue
        if res is None:
            skipped.append({"file": p.name, "reason": dig})
            continue
        ent = digests.get(dig)
        if ent is not None:
            ent["aliases"].append({"file": p.name, "live": score_rec["score"] if score_rec else None,
                                   "site": score_rec["site"] if score_rec else None})
            if score_rec and ent["score"] is None:
                ent["score"] = score_rec["score"]
                ent["site"] = score_rec["site"]
            ent["npos_max"] = max(ent["npos_max"], npos)
            continue
        if score_rec is None:
            # keep unscored files (our own candidates) for projection, flagged
            digests[dig] = {"digest": dig, "file": p.name, "site": None, "score": None,
                            "live_source": None, "row": res, "npos_raw": npos, "npos_max": npos,
                            "aliases": [], "path": str(p)}
            continue
        digests[dig] = {"digest": dig, "file": p.name, "site": score_rec["site"], "score": score_rec["score"],
                        "live_source": f"score-ledger.csv@{score_rec['source']}", "row": res,
                        "npos_raw": npos, "npos_max": npos, "aliases": [], "path": str(p)}

    scored = [d for d in digests.values() if d["score"] is not None]
    print(f"unique rasters with live scores: {len(scored)}   extra (unscored, projection only): "
          f"{len(digests) - len(scored)}   skipped: {len(skipped)}")
    print("spec:", {k: v for k, v in meta.items() if k != "inputs_sha256"})

    A = np.stack([d["row"]["A"] for d in scored]) if scored else np.zeros((0, spec.n_strata))
    B = np.stack([d["row"]["B"] for d in scored]) if scored else np.zeros((0, spec.n_strata))
    N = np.array([d["row"]["N"] for d in scored]) if scored else np.zeros(0)
    s = np.array([d["score"] for d in scored]) if scored else np.zeros(0)

    # ---- 2. apply the published S0 theta (GEMSDOE32 evidence/live_ledger_inversion.json) ----
    ref = json.loads(LLI_JSON.read_text())["designs"]["S0"] if LLI_JSON.exists() else None
    theta_ref = np.array(ref["fit"]["theta"]) if ref else None
    out = {"schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "evidence_class": {"live": "OWNER-REPORT (score-ledger.csv, mirrored); projections are LLI model "
                              "outputs and are NOT scores"},
           "spec": meta, "n_live_rasters": len(scored), "skipped": skipped[:40]}

    if theta_ref is not None:
        lam_ref = li.strata_lambda(theta_ref, spec)
        comps = li.predict_components(A, B, N, spec.sizes, lam_ref)
        err = comps["dti"] - s
        out["published_theta_check_on_local_pool"] = {
            "n": int(len(s)), "mae": float(np.mean(np.abs(err))), "rmse": float(np.sqrt(np.mean(err ** 2))),
            "spearman_pred_vs_live": float(spearmanr(comps["dti"], s).correlation),
            "max_abs_err": float(np.max(np.abs(err))), "g_truth_pixels": float(comps["g"]),
            "theta": [float(x) for x in theta_ref]}
        rows = []
        for i, d in enumerate(scored):
            rows.append({"site": d["site"], "file": d["file"], "live": float(s[i]),
                         "projected_with_published_theta": float(comps["dti"][i]),
                         "abs_err": float(comps["dti"][i] - s[i]), "N": float(N[i]),
                         "dots_raw": d["npos_raw"], "n_aliases": len(d["aliases"]), "digest": d["digest"]})
        out["per_raster"] = sorted(rows, key=lambda r: -r["live"])
        print(f"published theta on local pool: n={len(s)} MAE={np.mean(np.abs(err)):.4f} "
              f"rho={spearmanr(comps['dti'], s).correlation:.3f} maxerr={np.max(np.abs(err)):.4f} "
              f"g={comps['g']:.0f}")

        # ---- 3. refit locally (independent reproduction of the inversion) ----
        fit = li.fit(A, B, N, s, spec, ridge=float(ref["ridge_selected_by_loo_mae"]))
        lam = fit["lambda"]
        comp = li.predict_components(A, B, N, spec.sizes, lam)
        err2 = comp["dti"] - s
        loo = li.loo(A, B, N, s, spec, ridge=float(ref["ridge_selected_by_loo_mae"]), theta0=fit["theta"])
        sites = np.array([d["site"].split("-")[0] for d in scored])
        ls = li.loo(A, B, N, s, spec, groups=np.unique(sites, return_inverse=True)[1],
                    ridge=float(ref["ridge_selected_by_loo_mae"]), theta0=fit["theta"])
        out["local_refit"] = {"in_sample_mae": float(np.mean(np.abs(err2))),
                              "loo_mae": loo["mae"], "loo_spearman": loo["spearman"],
                              "leave_site_out_mae": ls["mae"], "leave_site_out_spearman": ls["spearman"],
                              "g_truth_pixels": float(fit["g"]), "theta": [float(x) for x in fit["theta"]],
                              "factor_effects_multiplicative": li.factor_effects(fit["theta"], spec),
                              "upstream_loo_mae": ref["loo"]["mae"], "upstream_loo_spearman": ref["loo"]["spearman"],
                              "upstream_leave_site_out_mae": ref["leave_site_out"]["mae"]}
        print(f"local refit: in-sample MAE={np.mean(np.abs(err2)):.4f} LOO={loo['mae']:.4f} "
              f"LOO rho={loo['spearman']:.3f} LSO={ls['mae']:.4f} "
              f"(upstream LOO={ref['loo']['mae']:.4f} rho={ref['loo']['spearman']:.3f})")

    # ---- 4. official-metric sanity: what the champion scores against the CATALOGUE (diagnostic only) ----
    champ = next((d for d in digests.values() if "h33-h33-2-b2" in d["file"] and d["file"].endswith("-zeros.tif")), None)
    if champ is not None:
        arr = np.where(np.isfinite(read1(Path(champ["path"]))), read1(Path(champ["path"])), 0.0)
        d_oncat = dti_exact(np.clip(arr, 0, 1), labels, valid=foot)
        out["champion_catalogue_diagnostic"] = {
            "file": champ["file"], "dti_vs_catalogue_labels": d_oncat["dti"],
            "note": "DTI against labels.tif (= existing-fault catalogue) is a diagnostic of how well the "
                    "raster traces KNOWN faults; the scored truth is the off-catalogue set, so this number "
                    "is not comparable to a leaderboard score.", "n_truth_catalogue_px": d_oncat["n_truth"]}
        print(f"champion DTI vs catalogue = {d_oncat['dti']:.4f} (diagnostic, not a score)")

    # ---- 5. project new rasters with the published theta ----
    if theta_ref is not None and a.project:
        proj = []
        for p in a.project:
            res, dig, npos, arr = row_for(Path(p), spec, tpl)
            if res is None:  # dig carries the reason string here
                proj.append({"file": str(p), "error": dig})
                continue
            c = li.project(res, spec, lam_ref)
            proj.append({"file": os.path.basename(p), "digest": dig, "dots": npos,
                         "N_mass": float(res["N"]), "projected_live_dti": float(c["dti"]),
                         "projected_tp": float(c["tp"]), "projected_g_overlap": float(c["g"]),
                         "evidence_class": "PROJECTION (LLI-v1 S0, published theta) -- not a score"})
            print(f"projection {os.path.basename(p)[:60]:62s} dots={npos:7d} projected={c['dti']:.4f}")
        out["projections"] = proj

    Path(ROOT / "evidence").mkdir(exist_ok=True)
    outp = ROOT / "evidence" / "lli_score_model_verification.json"
    outp.write_text(json.dumps(out, indent=1, default=float))
    print("wrote", outp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
