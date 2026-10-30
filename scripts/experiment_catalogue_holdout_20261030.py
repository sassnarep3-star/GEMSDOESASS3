#!/usr/bin/env python3
"""E1 (2026-10-30): spatially blocked hide-and-recover on the public fault catalogue.

Purpose
-------
Decide, with evidence, which *blind* dot placement strategy maximises the official
Distance-weighted Tversky Index (DTI) when nothing about the withheld faults is known
except the visible catalogue. This is the only validation that can be run in this
workspace, because the competition labels (the withheld new faults) are login-walled.

What is measured
----------------
Every dot field is scored against withheld catalogue cells that were removed from a
whole set of 4 km blocks *before* any placement was built. All catalogue-derived
placement rules see only the visible cells.

Numbers printed here are labelled **HOLDOUT-DTI (catalogue-recovery surrogate v1)**.
They are NOT the leaderboard metric: the scored set is expert-mapped faults that are
absent from the catalogue, and this experiment can only test recovery of catalogue
faults. Reporting rule (protocol rule 3): every number gets the evaluator, the number
of withheld positive cells, and a 95% CI.

Metric source (official): https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  TP_w = sum_g max_{x: d(x,g)<=R} p(x) k(d(x,g))
  FP_w = sum_{x: p(x)>0} p(x) [1 - max_g k(d(x,g))]
  FN_w = sum_g [1 - max_{x: d(x,g)<=R} p(x) k(d(x,g))]
  DTI(alpha=beta=) = TP_w / (TP_w + alpha FP_w + beta FN_w), alpha=0.2, beta=0.8, R=300 m.
Masking of known faults (DrivenData staff): https://community.drivendata.org/t/.../11516
Masking is deliberately NOT applied here, which is the conservative choice: it removes
false-positive cost from dots that sit on the catalogue, and the catalogue-proximity
strategies are the ones that would benefit.

Data used (all already inside this repository, no new downloads)
---------------------------------------------------------------
* catalogue: evidence/gsd_hua_map_preview.npz['catalogue_ds'] - the public USGS/INGENIOUS
  catalogue raster decimated to every 4th cell (400 m sample spacing, 3,806 cells).
* footprint: evidence/organizer_footprint_mask.npz (finite cells of the official sample
  submission, 5,167,373 cells).

Usage
-----
    python scripts/experiment_catalogue_holdout_20261030.py --out evidence/holdout_catalogue_20261030.json
"""
from __future__ import annotations

import argparse
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
SHAPE = (3730, 3292)
ALPHA, BETA, RADIUS_PX = 0.2, 0.8, 3.0
EVALUATOR = "catalogue-recovery-surrogate-v1 (exact official DTI equations, alpha=0.2, beta=0.8, R=3 px)"
SEED = 20261030
BLOCK = 40                 # 40 cells = 4 km blocks
HOLDOUT_FRACTION = 0.20
N_DOTS = 24000             # equal budget for every strategy
DECIMATION = 4             # catalogue_ds is every 4th cell


def kernel(d):
    return np.maximum(1.0 - np.asarray(d, float) / RADIUS_PX, 0.0)


def load_masks():
    fp = np.load(ROOT / "evidence" / "organizer_footprint_mask.npz")
    n = int(fp["shape"][0]) * int(fp["shape"][1])
    footprint = np.unpackbits(fp["packed"])[:n].reshape(tuple(fp["shape"])).astype(bool)
    prev = np.load(ROOT / "evidence" / "gsd_hua_map_preview.npz")
    # catalogue_ds[i, j] == catalogue[4i, 4j]; recover full-resolution coordinates.
    di, dj = np.nonzero(prev["catalogue_ds"])
    catalogue_yx = np.column_stack([di * DECIMATION, dj * DECIMATION]).astype(np.int32)
    return footprint, catalogue_yx, prev


def block_id(yx, block=BLOCK):
    return (yx[:, 0] // block).astype(np.int64) * 10_000 + (yx[:, 1] // block).astype(np.int64)


def split_blocks(ids, fraction=HOLDOUT_FRACTION, seed=SEED):
    uniq = np.unique(ids)
    rng = np.random.default_rng(seed)
    held = rng.permutation(uniq)[: int(round(fraction * uniq.size))]
    return set(held.tolist())


def to_raster(yx):
    r = np.zeros(SHAPE, dtype=bool)
    if len(yx):
        ok = (yx[:, 0] >= 0) & (yx[:, 0] < SHAPE[0]) & (yx[:, 1] >= 0) & (yx[:, 1] < SHAPE[1])
        yx = yx[ok]
        r[yx[:, 0], yx[:, 1]] = True
    return r


def scores_from_dots(dots_yx, truth_yx, footprint, block=BLOCK):
    """Exact TP_w/FP_w/FN_w per block, from the published equations, using point sets only."""
    dot_r = to_raster(dots_yx)
    # max over predictions of p*k at each truth cell (p=1 for every dot)
    _, idx = cKDTree(dots_yx).query(truth_yx, k=1)
    d = np.linalg.norm(dots_yx[idx] - truth_yx, axis=1) if len(truth_yx) else np.zeros(0)
    k_tp = kernel(d)
    # max over truth of k at each dot
    dt = distance_transform_edt(~to_raster(truth_yx))
    ys, xs = np.nonzero(dot_r)
    fp_terms = 1.0 - kernel(dt[ys, xs])
    bids_d = block_id(np.column_stack([ys, xs]), block)
    bids_t = block_id(truth_yx, block)
    return dict(k_tp=k_tp, fp_terms=fp_terms, bids_d=bids_d, bids_t=bids_t,
                dot_raster=dot_r, footprint=footprint)


def dti_from_components(tp, fp, fn):
    return float(tp / (tp + ALPHA * fp + BETA * fn + 1e-12))


def block_bootstrap(s, n_boot=400, seed=SEED):
    """Resample blocks with replacement; TP/FN are sums over truth cells, FP over dots."""
    rng = np.random.default_rng(seed)
    all_blocks = np.unique(np.concatenate([s["bids_t"], s["bids_d"]]))
    tp_by = {b: float(s["k_tp"][s["bids_t"] == b].sum()) for b in all_blocks}
    fn_by = {b: float((1.0 - s["k_tp"])[s["bids_t"] == b].sum()) for b in all_blocks}
    fp_by = {b: float(s["fp_terms"][s["bids_d"] == b].sum()) for b in all_blocks}
    tp_v = np.array([tp_by[b] for b in all_blocks]); fn_v = np.array([fn_by[b] for b in all_blocks])
    fp_v = np.array([fp_by[b] for b in all_blocks])
    out = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(all_blocks), len(all_blocks))
        out.append(dti_from_components(tp_v[pick].sum(), fp_v[pick].sum(), fn_v[pick].sum()))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


# ----------------------------------------------------------------------------------
# placement strategies (each sees only `visible` catalogue cells and the footprint)
# ----------------------------------------------------------------------------------
def sample_footprint(footprint, n, rng):
    ys, xs = np.nonzero(footprint)
    pick = rng.integers(0, ys.size, n)
    return np.column_stack([ys[pick], xs[pick]]).astype(np.int32)


def jittered_lattice(footprint, n, rng):
    """Low-discrepancy hexagonal-ish lattice, jittered by <half a cell, clipped to the footprint."""
    area = int(footprint.sum())
    s = float(np.sqrt(1.732 * area / max(n, 1)))       # hex nearest-neighbour spacing
    h = s * np.sqrt(3.0) / 2.0
    yy, xx = np.mgrid[0:SHAPE[0]:1, 0:SHAPE[1]:1]
    row = (yy % h) < 1.0
    # two-row stagger so columns alternate
    stagger = ((yy // max(h, 1e-9)).astype(int) % 2) * (s / 2.0)
    col = ((xx - stagger) % s) < 1.0
    cand = np.column_stack(np.nonzero(row & col))
    cand = cand[footprint[cand[:, 0], cand[:, 1]]]
    if len(cand) > n:
        cand = cand[rng.choice(len(cand), n, replace=False)]
    elif len(cand) < n:
        extra = sample_footprint(footprint, n - len(cand), rng)
        cand = np.vstack([cand, extra])
    jit = rng.normal(0, 0.35, cand.shape)
    cand = np.rint(cand + jit).astype(np.int32)
    cand[:, 0] = np.clip(cand[:, 0], 0, SHAPE[0] - 1); cand[:, 1] = np.clip(cand[:, 1], 0, SHAPE[1] - 1)
    keep = footprint[cand[:, 0], cand[:, 1]]
    return cand[keep]


def annulus_placement(footprint, visible, n, rng, rmin=4.0, rmax=20.0):
    """Dots at 400-2000 m from a visible catalogue cell: next to mapped traces, not on them."""
    tree = cKDTree(visible)
    out = []
    tries = 0
    while len(out) < n and tries < 40:
        tries += 1
        base = visible[rng.integers(0, len(visible), n)]
        ang = rng.uniform(0, 2 * np.pi, n)
        rad = rng.uniform(rmin, rmax, n)
        cand = np.rint(base + np.column_stack([rad * np.sin(ang), rad * np.cos(ang)])).astype(np.int32)
        ok = (cand[:, 0] >= 0) & (cand[:, 0] < SHAPE[0]) & (cand[:, 1] >= 0) & (cand[:, 1] < SHAPE[1])
        cand = cand[ok]
        cand = cand[footprint[cand[:, 0], cand[:, 1]]]
        d, _ = tree.query(cand, k=1)
        cand = cand[(d >= rmin) & (d <= rmax)]
        out.append(cand)
    allc = np.vstack(out) if out else np.zeros((0, 2), int)
    if len(allc) > n:
        allc = allc[rng.choice(len(allc), n, replace=False)]
    return allc.astype(np.int32)


def tip_extrapolation(footprint, visible, n, rng, k_nn=8, max_steps=6, step=4.0):
    """Extend each visible cell along its local strike beyond the local terminus."""
    tree = cKDTree(visible)
    _, idx = tree.query(visible, k=min(k_nn, len(visible)))
    out = []
    for i in range(len(visible)):
        nb = visible[idx[i]]
        cen = nb - nb.mean(0)
        # principal direction of the neighbourhood
        w, v = np.linalg.eigh(cen.T @ cen)
        u = v[:, np.argmax(w)]
        u = u / (np.linalg.norm(u) + 1e-12)
        for sign in (+1.0, -1.0):
            p = visible[i].astype(float)
            for step_i in range(1, max_steps + 1):
                p = p + sign * u * step
                q = np.rint(p).astype(np.int32)
                if not (0 <= q[0] < SHAPE[0] and 0 <= q[1] < SHAPE[1]):
                    break
                if not footprint[q[0], q[1]]:
                    break
                out.append(q)
    cand = np.unique(np.array(out, dtype=np.int32), axis=0) if out else np.zeros((0, 2), np.int32)
    if len(cand) > n:
        cand = cand[rng.choice(len(cand), n, replace=False)]
    return cand


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "holdout_catalogue_20261030.json")
    args = ap.parse_args()

    footprint, catalogue_yx, prev = load_masks()
    inside = footprint[catalogue_yx[:, 0], catalogue_yx[:, 1]]
    catalogue_yx = catalogue_yx[inside]
    ids = block_id(catalogue_yx)
    held = split_blocks(ids)
    is_held = np.array([b in held for b in ids])
    truth_yx, visible = catalogue_yx[is_held], catalogue_yx[~is_held]
    print(f"catalogue cells {len(catalogue_yx)}; withheld {len(truth_yx)} in {len(held)} blocks; visible {len(visible)}")
    print(f"footprint cells {int(footprint.sum())}")

    rng = np.random.default_rng(SEED)
    strategies = {
        "S1_uniform_random": lambda: sample_footprint(footprint, N_DOTS, rng),
        "S2_jittered_lattice": lambda: jittered_lattice(footprint, N_DOTS, rng),
        "S3_annulus_400_2000m": lambda: annulus_placement(footprint, visible, N_DOTS, rng),
        "S4_tip_extrapolation": lambda: tip_extrapolation(footprint, visible, N_DOTS, rng),
    }
    tip = strategies["S4_tip_extrapolation"]()
    lat = strategies["S2_jittered_lattice"]()
    strategies["S5_tip60_lattice40"] = lambda: np.vstack([
        tip, lat[rng.choice(len(lat), max(0, N_DOTS - len(tip)), replace=False)]])

    # reference: the champion dot field scored against the same withheld cells (context only,
    # not a candidate: it is a registry raster and would fail the uniqueness gate)
    champ = prev["dots_yx"].astype(np.int32)

    rows = []
    fp_area = float(footprint.sum())
    for name, fn in strategies.items():
        dots = fn()
        s = scores_from_dots(dots, truth_yx, footprint)
        tp = float(s["k_tp"].sum()); fn_ = float((1.0 - s["k_tp"]).sum()); fp_ = float(s["fp_terms"].sum())
        e_field = float(kernel(distance_transform_edt(~s["dot_raster"]))[footprint].mean())
        x_gt = float(s["k_tp"].mean()) if len(truth_yx) else 0.0
        ci = block_bootstrap(s)
        rows.append(dict(
            strategy=name, n_dots=int(len(dots)),
            tp_w=round(tp, 3), fp_w=round(fp_, 3), fn_w=round(fn_, 3),
            holdout_dti=round(dti_from_components(tp, fp_, fn_), 6), dti_ci95=[round(v, 6) for v in ci],
            capture_fraction_x=round(x_gt, 6), mean_k_over_footprint_e=round(e_field, 8),
            enrichment_eps=round(x_gt / e_field, 4) if e_field > 0 else None,
            covered_footprint_fraction=round(float((distance_transform_edt(~s["dot_raster"])[footprint] <= RADIUS_PX).mean()), 5),
        ))
        print(rows[-1])

    # same scoring for the champion field, for scale (context only)
    s = scores_from_dots(champ, truth_yx, footprint)
    tp = float(s["k_tp"].sum()); fn_ = float((1.0 - s["k_tp"]).sum()); fp_ = float(s["fp_terms"].sum())
    champ_row = dict(strategy="REFERENCE_champion_gemsdoe32_field (not a candidate)",
                     n_dots=int(len(champ)), tp_w=round(tp, 3), fp_w=round(fp_, 3), fn_w=round(fn_, 3),
                     holdout_dti=round(dti_from_components(tp, fp_, fn_), 6),
                     dti_ci95=[round(v, 6) for v in block_bootstrap(s)],
                     capture_fraction_x=round(float(s["k_tp"].mean()), 6))
    print(champ_row)

    cat_bytes = (ROOT / "evidence" / "gsd_hua_map_preview.npz").read_bytes()
    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "experiment": "E1 catalogue hide-and-recover (spatially blocked)",
        "evaluator_version": EVALUATOR,
        "label": "HOLDOUT-DTI (catalogue-recovery surrogate v1)",
        "not_the_leaderboard_metric_because": (
            "the scored set is expert-mapped faults absent from the catalogue; this experiment can only "
            "measure recovery of catalogue faults that were hidden from the placement rules"),
        "withheld_positive_cells": int(len(truth_yx)),
        "visible_positive_cells": int(len(visible)),
        "holdout_blocks": {"block_cells": BLOCK, "block_km": BLOCK * 0.1, "n_blocks": int(len(held)),
                           "fraction": HOLDOUT_FRACTION, "seed": SEED},
        "n_dots_per_strategy": N_DOTS,
        "footprint_cells": int(footprint.sum()),
        "masking_applied": False,
        "masking_note": ("known-fault masking (organizer confirmed) is not applied; this is conservative for "
                         "catalogue-proximity strategies, which are the ones masking would reward"),
        "inputs": {
            "catalogue": "evidence/gsd_hua_map_preview.npz:catalogue_ds (400 m decimation of the public catalogue)",
            "catalogue_npz_sha256": hashlib.sha256(cat_bytes).hexdigest(),
            "footprint": "evidence/organizer_footprint_mask.npz",
        },
        "rows": rows,
        "champion_reference": champ_row,
        "decision": None,
    }
    best = max(rows, key=lambda r: r["holdout_dti"])
    payload["decision"] = {
        "best_strategy": best["strategy"],
        "best_holdout_dti": best["holdout_dti"],
        "reading": ("strategy with the highest HOLDOUT-DTI at equal dot budget; the winner is used to build the "
                    "candidate only if its enrichment exceeds the uniform baseline"),
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
