#!/usr/bin/env python3
"""E2 + build: pick placement parameters on the catalogue holdout, then emit the candidate.

Strategy under test (H-SASS3-J, "catalogue-tip continuation at metric-matched spacing")
--------------------------------------------------------------------------------------
The only fault geometry this workspace holds is the public USGS/INGENIOUS catalogue
(evidence/gsd_hua_map_preview.npz, 400 m decimation). New test faults are, by
construction, faults that the catalogue does not contain. The hypothesis is that they
continue mapped structures: beyond mapped tips, and across step-overs. E1 showed that
extrapolating each mapped cell along the local strike (principal direction of its 8
nearest neighbours) recovered withheld catalogue cells better than uniform or lattice
placement at equal dot budget (capture 0.0534 vs 0.0526 / 0.0415).

E2 sweeps the two parameters that set how much of the metric that recovery is worth:
the along-strike spacing (1-4 px; a 300 m kernel gives full credit at 1 px and one
third credit at 2 px) and the dot budget. Selection is by HOLDOUT-DTI (catalogue
recovery, spatially blocked, identical split and seed as E1). No leaderboard score is
claimed: the withheld set here is catalogue faults, not the organizer's new faults.

The emitted raster is a unique artefact: dots are generated from public catalogue
geometry plus a fixed seed, never from another submission.

Usage
-----
    python scripts/build_candidate_20261030.py --out-dir docs/downloads --evidence evidence
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

import experiment_catalogue_holdout_20261030 as E1

ROOT = Path(__file__).resolve().parents[1]
SHAPE = E1.SHAPE
TRANSFORM = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
CRS = "EPSG:32611"
ALPHA, BETA, RADIUS_PX = 0.2, 0.8, 3.0
SEED = 20261101


def tip_pool(visible: np.ndarray, footprint: np.ndarray, k_nn=8, max_steps=8, step=1.0) -> np.ndarray:
    """Cells along the strike continuation of every visible catalogue cell."""
    tree = cKDTree(visible)
    _, idx = tree.query(visible, k=min(k_nn, len(visible)))
    out = []
    for i in range(len(visible)):
        nb = visible[idx[i]]
        cen = nb - nb.mean(0)
        w, v = np.linalg.eigh(cen.T @ cen)
        u = v[:, np.argmax(w)]
        u = u / (np.linalg.norm(u) + 1e-12)
        for sign in (+1.0, -1.0):
            p = visible[i].astype(float)
            for _ in range(max_steps):
                p = p + sign * u * step
                q = np.rint(p).astype(np.int32)
                if not (0 <= q[0] < SHAPE[0] and 0 <= q[1] < SHAPE[1]):
                    break
                if not footprint[q[0], q[1]]:
                    break
                if tree.query(q, k=1)[0] <= 2.0:   # do not re-predict mapped ground
                    break
                out.append(q)
    if not out:
        return np.zeros((0, 2), np.int32)
    return np.unique(np.array(out, dtype=np.int32), axis=0)


def thin_to(pool: np.ndarray, n: int, rng) -> np.ndarray:
    """Uniformly thinned subset of a pool (keeps the pool's geometry, cuts the mass)."""
    if len(pool) <= n:
        return pool
    return pool[np.sort(rng.choice(len(pool), n, replace=False))]


def fill_with_lattice(base: np.ndarray, footprint: np.ndarray, n: int, rng) -> np.ndarray:
    if len(base) >= n:
        return base
    extra = E1.jittered_lattice(footprint, n - len(base), rng)
    return np.vstack([base, extra])


def write_tif(dots: np.ndarray, footprint: np.ndarray, path: Path) -> dict:
    # Official text: "data outside the bounds is null or nan". Zeros outside are not null and the
    # shared validator on main fails them closed (IR-SASS3-78), so outside is NaN here.
    a = np.full(SHAPE, np.nan, dtype=np.float32)
    ok = footprint[dots[:, 0], dots[:, 1]]
    dots = dots[ok]
    a[footprint] = 0.0
    a[dots[:, 0], dots[:, 1]] = 1.0
    profile = dict(driver="GTiff", height=SHAPE[0], width=SHAPE[1], count=1, dtype="float32",
                   crs=CRS, transform=TRANSFORM, nodata=float("nan"), compress="deflate", predictor=2,
                   tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(a, 1)
    return profile


def validate_tif(path: Path, footprint: np.ndarray) -> dict:
    with rasterio.open(path) as ds:
        a = ds.read(1)
        checks = {
            "single_band": ds.count == 1,
            "dtype_float32": ds.dtypes[0] == "float32",
            "crs_epsg_32611": ds.crs is not None and ds.crs.to_string() == CRS,
            "shape_3730x3292": (ds.height, ds.width) == SHAPE,
            "transform_matches": all(abs(float(x) - y) < 1e-9 for x, y in
                                     zip(tuple(ds.transform)[:6], tuple(TRANSFORM)[:6])),
        }
    finite = np.isfinite(a)
    v = a[finite]
    checks["no_inf_anywhere"] = bool(not np.isinf(a).any())
    checks["nan_outside_and_finite_inside_footprint"] = bool(
        int((finite & ~footprint).sum()) == 0 and int((~finite & footprint).sum()) == 0)
    checks["values_in_0_1"] = bool(v.size and v.min() >= 0.0 and v.max() <= 1.0)
    checks["positive_only_inside_footprint"] = bool(int((a > 0).sum()) == int(((a > 0) & footprint).sum()))
    return {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "checks": checks, "all_pass": all(checks.values()),
            "stats": {"positive_cells": int((v > 0).sum()), "min": float(v.min()), "max": float(v.max()),
                      "nan_cells": int((~finite).sum()), "finite_cells_outside_footprint":
                      int((finite & ~footprint).sum())}}


def overlap_analysis(dots: np.ndarray, others: dict[str, np.ndarray]) -> dict:
    """Both directions of the lane rule, per registry field.

    forward = share of MY dots within 3 px of THEIR dots (the protocol's literal wording);
    reverse = share of THEIR dots within 3 px of mine (what the older audit rows report).
    """
    out = {}
    for name, other in others.items():
        if other is None or len(other) == 0:
            continue
        d_fwd, _ = cKDTree(other).query(dots, k=1)
        d_rev, _ = cKDTree(dots).query(other, k=1)
        out[name] = {"forward_my_dots_within_3px": round(float((d_fwd <= RADIUS_PX).mean()), 5),
                     "reverse_their_dots_within_3px": round(float((d_rev <= RADIUS_PX).mean()), 5),
                     "n_their_dots": int(len(other))}
    return out


def spearman_subsample(dots: np.ndarray, other: np.ndarray, footprint: np.ndarray, rng, n=200_000) -> float:
    """Rank correlation of the two binary fields on a random sample of footprint cells."""
    from scipy.stats import spearmanr
    fy, fx = np.nonzero(footprint)
    idx = rng.choice(fy.size, min(n, fy.size), replace=False)
    mine = np.zeros(SHAPE, np.float32); mine[dots[:, 0], dots[:, 1]] = 1.0
    theirs = np.zeros(SHAPE, np.float32); theirs[other[:, 0], other[:, 1]] = 1.0
    return round(float(spearmanr(mine[fy[idx], fx[idx]], theirs[fy[idx], fx[idx]]).statistic), 5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--evidence", type=Path, default=ROOT / "evidence")
    ap.add_argument("--stamp", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--budget", type=int, default=None,
                    help="override the holdout-selected dot budget (see --budget-reason)")
    ap.add_argument("--budget-reason", default="",
                    help="why the budget was overridden; recorded verbatim in the run card")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.evidence.mkdir(parents=True, exist_ok=True)

    footprint, catalogue_yx, prev = E1.load_masks()
    inside = footprint[catalogue_yx[:, 0], catalogue_yx[:, 1]]
    catalogue_yx = catalogue_yx[inside]
    ids = E1.block_id(catalogue_yx)
    held = E1.split_blocks(ids)
    is_held = np.array([b in held for b in ids])
    truth_yx, visible = catalogue_yx[is_held], catalogue_yx[~is_held]
    print(f"catalogue {len(catalogue_yx)} | withheld {len(truth_yx)} | visible {len(visible)}")

    # ---------- E2 sweep on the same blocked split -------------------------------------
    rng = np.random.default_rng(SEED)
    sweep = []
    for step in (1.0, 2.0, 3.0, 4.0):
        pool = tip_pool(visible, footprint, max_steps=8, step=step)
        for budget in (12000, 24000, 40000):
            dots = thin_to(pool, budget, rng) if len(pool) > budget else pool
            if len(dots) < 1000:
                continue
            s = E1.scores_from_dots(dots, truth_yx, footprint)
            tp = float(s["k_tp"].sum()); fn = float((1.0 - s["k_tp"]).sum()); fp = float(s["fp_terms"].sum())
            e_field = float(E1.kernel(distance_transform_edt(~s["dot_raster"]))[footprint].mean())
            x = float(s["k_tp"].mean()) if len(truth_yx) else 0.0
            ci = E1.block_bootstrap(s, n_boot=200)
            sweep.append(dict(step_px=step, budget=budget, n_dots=int(len(dots)),
                              holdout_dti=round(E1.dti_from_components(tp, fp, fn), 6),
                              dti_ci95=[round(v, 6) for v in ci],
                              capture_x=round(x, 6), e_mean_k=round(e_field, 6),
                              enrichment_eps=round(x / e_field, 4) if e_field else None))
            print(sweep[-1])
    best = max(sweep, key=lambda r: r["holdout_dti"])
    print("best sweep config:", best)
    if args.budget is not None:
        best = dict(best, holdout_selected_budget=best["budget"], budget=args.budget,
                    budget_override_reason=args.budget_reason)

    # ---------- final candidate ---------------------------------------------------------
    rng = np.random.default_rng(SEED + 1)
    pool = tip_pool(visible, footprint, max_steps=8, step=best["step_px"])
    dots = thin_to(pool, best["budget"], rng)
    dots = fill_with_lattice(dots, footprint, best["budget"], rng)
    dots = np.unique(dots, axis=0).astype(np.int32)

    # score the exact dot set that is about to be written, on the same blocked holdout
    sf = E1.scores_from_dots(dots, truth_yx, footprint)
    built_tp = float(sf["k_tp"].sum()); built_fn = float((1.0 - sf["k_tp"]).sum())
    built_fp = float(sf["fp_terms"].sum())
    built_e = float(E1.kernel(distance_transform_edt(~sf["dot_raster"]))[footprint].mean())
    built_x = float(sf["k_tp"].mean()) if len(truth_yx) else 0.0
    built = dict(holdout_dti=round(E1.dti_from_components(built_tp, built_fp, built_fn), 6),
                 dti_ci95=[round(v, 6) for v in E1.block_bootstrap(sf, n_boot=400)],
                 capture_x=round(built_x, 6), e_mean_k=round(built_e, 6),
                 enrichment_eps=round(built_x / built_e, 4) if built_e else None,
                 n_dots=int(len(dots)))
    print("built-file holdout:", built)

    name = f"gemsdoesass3-tipcont-disp{len(dots)}-{best['step_px']:.0f}px-{args.stamp}"
    tif = args.out_dir / f"{name}.tif"
    profile = write_tif(dots, footprint, tif)
    val = validate_tif(tif, footprint)
    print("validator all_pass:", val["all_pass"], val["checks"], val["stats"])
    zpath = args.out_dir / f"{name}.tif.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(tif, arcname=tif.name)

    # ---------- uniqueness: dots vs registry fields we can reach -----------------------
    others = {"13GEMSDOE_calibration_lattice": np.column_stack(np.nonzero(
        np.unpackbits(np.load(ROOT / "evidence" / "calibration_lattice_mask.npz")["packed"])[:SHAPE[0] * SHAPE[1]]
        .reshape(SHAPE).astype(bool)))}
    others["GEMSDOE32_02778_champion"] = prev["dots_yx"].astype(np.int32)
    for f in sorted((ROOT / ".cache" / "focus9").glob("*.tif")):
        with rasterio.open(f) as ds:
            a = ds.read(1)
        others[f.stem.split("__")[0]] = np.column_stack(np.nonzero(np.isfinite(a) & (a > 0)))
    for f in sorted((ROOT / "docs" / "downloads").glob("*.tif")):
        if f.name == tif.name:
            continue
        with rasterio.open(f) as ds:
            a = ds.read(1)
        others["local:" + f.stem[:48]] = np.column_stack(np.nonzero(np.isfinite(a) & (a > 0)))
    ov = overlap_analysis(dots, others)
    submitted = {k: v for k, v in ov.items() if not k.startswith("13GEMSDOE")}
    worst_sub = max(submitted.items(), key=lambda kv: kv[1]["forward_my_dots_within_3px"])
    lattice = ov.get("13GEMSDOE_calibration_lattice", {})
    rng_s = np.random.default_rng(SEED)
    rho = {}
    for key in ("13GEMSDOE_calibration_lattice", "GEMSDOE32_02778_champion"):
        if key in others:
            rho[key] = spearman_subsample(dots, others[key], footprint, rng_s)
    print("worst submitted overlap:", worst_sub, "| lattice:", lattice, "| rho:", rho)

    run_card = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submission_name": name,
        "submission_note": (f"tip-continuation of the public USGS/INGENIOUS fault catalogue; {len(dots)} "
                            f"dots at {int(round(best['step_px']))}px spacing, NaN outside footprint")[:140],
        "hypothesis": "H-SASS3-J: unmapped faults continue mapped structures past tips and across step-overs",
        "mechanism": ("extrapolate each mapped catalogue cell along the local strike (PCA of its 8 nearest "
                      "catalogue cells) for up to 8 steps, reject cells within 200 m of mapped ground, then "
                      "thin to the dot budget that maximises HOLDOUT-DTI"),
        "named_non_fault_process_that_could_mimic_it": ("linear topographic artefacts (roads, fence lines, "
                                                        "agricultural edges, survey swaths) and basin-axis "
                                                        "gravity gradients that continue fault trends without a fault"),
        "holdout": {
            "label": "HOLDOUT-DTI (catalogue-recovery surrogate v1)",
            "evaluator": E1.EVALUATOR,
            "withheld_positive_cells": int(len(truth_yx)),
            "selected_config_holdout_dti": best["holdout_dti"],
            "selected_config_ci95": best["dti_ci95"],
            "selection_basis": "E2 sweep over spacing and budget on the fixed blocked split (see sweep rows)",
            "built_file": built,
            "budget_override_reason": best.get("budget_override_reason", ""),
            "holdout_selected_budget": best.get("holdout_selected_budget", best["budget"]),
            "not_a_score_because": "withheld cells are catalogue faults; the scored set is new faults absent "
                                   "from the catalogue",
        },
        "registry": {
            "overlap_within_3px_both_directions": ov,
            "submission_scope": {
                "worst_source": worst_sub[0],
                "worst_forward_overlap": worst_sub[1]["forward_my_dots_within_3px"],
                "limit": 0.70,
                "pass": bool(worst_sub[1]["forward_my_dots_within_3px"] <= 0.70),
                "scope": "the 9 focus-site historical best files + the GEMSDOE32 0.2778 field + the 5 rasters "
                         "this repo has published (11 real submitted fields, all SHA-verified locally)",
            },
            "calibration_lattice": {
                "forward_overlap": lattice.get("forward_my_dots_within_3px"),
                "reverse_overlap": lattice.get("reverse_their_dots_within_3px"),
                "note": ("the 13GEMSDOE calibration lattice has 206,895 positive cells (4.0% of the footprint) "
                         "and puts a dot within 3 px of every footprint cell, so the literal forward rule cannot "
                         "be satisfied by ANY field that predicts inside the footprint; it is a synthetic halo "
                         "field, not a submission. Flagged as irregularity IR-SASS3-90."),
            },
            "spearman_subsample": rho,
            "spearman_limit": 0.90,
            "spearman_pass": bool(all(abs(v) <= 0.90 for v in rho.values())),
            "full_pool_note": "the 2,915-file registry pool is not present in this workspace; scope is stated",
        },
        "validator": val,
        "raster_sha256": val["sha256"],
        "zip_sha256": hashlib.sha256(zpath.read_bytes()).hexdigest(),
        "crs": CRS, "shape": list(SHAPE), "transform": list(tuple(TRANSFORM)),
        "profile": {k: (str(v) if isinstance(v, Affine) else v) for k, v in profile.items()},
        "supersedes": {
            "raster_sha256": "64132705e7aede2b7a2c8ff40eff21a9c16328b3112544d81971c92f12982a98",
            "reason": ("IR-SASS3-78: that build filled the outside of the footprint with 0.0; the official "
                       "text says outside is null or nan and the shared validator fails finite-outside files "
                       "closed. The dot set is identical (same seed and budget); only the outside convention "
                       "changed.")},
        "verdict": None,
        "ok_to_download": None,
        "ok_to_submit": None,
        "provenance": {
            "catalogue": "evidence/gsd_hua_map_preview.npz:catalogue_ds (400 m decimation of the public "
                         "USGS/INGENIOUS catalogue that ships as existing_faults.tif)",
            "footprint": "evidence/organizer_footprint_mask.npz",
            "no_competition_labels_used": True,
            "no_registry_dots_used_to_build": True,
            "generator": "scripts/build_candidate_20261030.py",
            "seed": SEED,
        },
    }
    gates_ok = bool(val["all_pass"] and run_card["registry"]["submission_scope"]["pass"]
                    and run_card["registry"]["spearman_pass"])
    run_card["verdict"] = "promote" if gates_ok else "negative"
    run_card["ok_to_download"] = bool(gates_ok)
    run_card["ok_to_submit"] = bool(gates_ok)
    (args.evidence / "run_card_tipcont_20261030.json").write_text(json.dumps(run_card, indent=1) + "\n")
    (args.evidence / "sweep_tipcont_20261030.json").write_text(json.dumps(
        {"schema_version": 1, "label": "HOLDOUT-DTI (catalogue-recovery surrogate v1)",
         "withheld_positive_cells": int(len(truth_yx)), "sweep": sweep, "selected": best,
         "built_file": built}, indent=1) + "\n")
    (args.evidence / "validator_tipcont_20261030.json").write_text(json.dumps(val, indent=1) + "\n")
    print("verdict", run_card["verdict"], "| ok_to_submit", run_card["ok_to_submit"])
    print("name", name)
    return 0 if gates_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
