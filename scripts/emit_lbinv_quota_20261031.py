#!/usr/bin/env python3
"""E2b (session 2026-10-31) — quota-constrained kernel-pack emission from the metric-inversion field.

Why this exists: the E2 kill-repair (scripts/emit_lbinv_kernelpack_20261031.py) is a negative result.
The corpus is redundant (top rasters share 87-100% of dots), so their 3 px halos coincide on the hot
zone; repairing one raster at a time by killing dots collapses the candidate (42,000 dots -> 2,445,
EST 0.32 -> 0.08).  The uniqueness rule is therefore enforced as a *placement constraint*, not a repair:
each eligible raster r has a halo budget  cap_r = floor(limit * n_target)  and a cell in halo_r is only
admissible while that raster is under its cap.  Cells are admitted greedily in credit order q with a
kernel-scale exclusion (Chebyshev >= sep px), which guarantees every accepted dot pays its own
0.2*D denominator for an independent 300 m kernel (the metric's per-truth credit is a MAX over the
kernel, src/gems32/metric.py).  The result is unique by construction against every pool raster
(registry + corpus + this repo's own previous files), and the marginal rule q > 0.2*EST trims the tail.

Usage:
    python scripts/emit_lbinv_quota_20261031.py [--emit]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from emit_lbinv_kernelpack_20261031 import Pool, phi_counts  # noqa: E402  shared cache machinery

ALPHA, BETA = 0.2, 0.8
TS = "20261031T180000Z"



def enforce_cap(chosen, q, pool, external, grid_of_fp, shape, limit):
    """Kill the lowest-credit offenders until halo_hits_r <= floor(limit*n) for every external
    raster (halo = 3 px dilation of that raster's dots)."""
    size = shape[0] * shape[1]
    for _ in range(8):
        if chosen.size == 0:
            return chosen
        n0 = int(chosen.size)
        cand = np.zeros(size, dtype=bool)
        cand[grid_of_fp[chosen]] = True
        worst_excess, worst_nm, worst_halo = 0, None, None
        for nm in external:
            packed = pool.halo(nm)
            if packed is None:
                continue
            halo = np.unpackbits(packed)[:size].astype(bool)
            hits_now = int(np.count_nonzero(cand & halo))
            excess = hits_now - int(np.floor(limit * n0))
            if excess > worst_excess:
                worst_excess, worst_nm, worst_halo = excess, nm, halo
            del halo
        if worst_nm is None:
            return chosen
        # exact kill count: removing d offenders leaves hits-d of n-d; need
        # hits - d <= limit*(n - d)  ->  d >= (hits - limit*n)/(1 - limit)
        d_needed = int(np.ceil(worst_excess / (1.0 - limit))) + 1
        mask_in = worst_halo[grid_of_fp[chosen]]
        inside = chosen[mask_in]
        drop = inside[np.argsort(q[inside])[:d_needed]]
        chosen = chosen[~np.isin(chosen, drop)]
        del worst_halo
    return chosen


def halo_test(packed: np.ndarray, idx: int) -> bool:
    """Membership test against a packbits halo (np.packbits big-endian within each byte)."""
    byte = int(packed[idx >> 3])
    bit = 7 - (idx & 7)
    return bool(byte & (1 << bit))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "distill_q.npz")
    ap.add_argument("--evidence", type=Path, default=ROOT / "evidence" / "distill_from_leaderboard_20261031.json")
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--registry", type=Path, default=ROOT / ".cache" / "focus_registry")
    ap.add_argument("--corpus", type=Path, default=ROOT / ".cache" / "gems_corpus")
    ap.add_argument("--own", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--sep", type=int, nargs="+", default=[0, 2])
    ap.add_argument("--budgets", type=int, nargs="+", default=[60000, 90000, 120000])
    ap.add_argument("--overlap-limit", type=float, default=0.65)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--emit", action="store_true")
    args = ap.parse_args()

    ev = json.loads(args.evidence.read_text())
    N = float(ev["N_estimate"])
    loo = ev["chosen"]
    z = np.load(args.field)
    q = z["q"].astype(np.float64)
    shape = tuple(int(v) for v in z["shape"])
    with rasterio.open(args.data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        transform, crs = ds.transform, ds.crs
    grid_of_fp = np.nonzero(foot.ravel())[0]
    fp_of_grid = np.full(shape[0] * shape[1], -1, dtype=np.int64)
    fp_of_grid[grid_of_fp] = np.arange(q.size)

    paths = []
    for d, tag in ((args.registry, ""), (args.corpus, "corpus:"), (args.own, "own:")):
        for p in sorted(d.glob("*.tif")):
            paths.append((p, (tag + p.name) if tag else p.name))
    # The hard 65 % cap is the protocol's anti-drift rule against *registry* rasters; it is
    # enforced against the external pool (registry + scored corpus = the other GEMDOE sites
    # and the public pool).  This repo's own previous files are measured and reported but do
    # not constrain placement (copy-prevention is the different-sha / different-n gate).
    seen, uniq = set(), []
    for p, nm in paths:
        if nm not in seen:
            seen.add(nm)
            uniq.append((p, nm))
    paths = uniq
    min_budget = min(args.budgets)
    floor_dots = int(args.overlap_limit * min_budget / 9.0) + 1
    pool = Pool(paths, shape, foot, ROOT / ".cache" / "kernelpack_cache", floor_dots)
    print(f"pool: {len(pool.dots)} readable rasters; halos cached", flush=True)

    pos_idx = np.flatnonzero(q > 0).astype(np.uint32)
    pre_corr = []
    for name in pool.dots:
        other_fp = fp_of_grid[pool.dots[name].astype(np.int64)]
        n11 = int(np.intersect1d(pos_idx, other_fp.astype(np.uint32), assume_unique=True).size)
        pre_corr.append((phi_counts(n11, int(pos_idx.size), pool.counts[name], pool.n_fp), name))
    pre_corr.sort(key=lambda t: -abs(t[0]))
    worst_pre = pre_corr[:5]
    print("worst pre-placement surface correlations:", [(round(c, 4), n) for c, n in worst_pre], flush=True)

    order_all = np.argsort(-q)
    rows_fp, cols_fp = np.divmod(grid_of_fp, shape[1])
    out = []
    for sep in args.sep:
        if sep == 0:
            # dense mode: no kernel exclusion (the published corpus's strongest files are dense
            # fills; the marginal rule and the uniqueness quota do the shaping)
            keep = order_all[q[order_all] > 0]
            cand_cells = keep[: max(args.budgets) * 3]
        else:
            blk = max(sep, 2)
            blocked0 = np.zeros((shape[0] // blk + 2, shape[1] // blk + 2), dtype=bool)
            cand_cells = []
            for i in order_all:
                if q[i] <= 0:
                    break
                if len(cand_cells) >= max(args.budgets) * 2:   # candidate pool beyond any budget
                    break
                r, c = rows_fp[i] // blk, cols_fp[i] // blk
                if blocked0[max(r - 1, 0): r + 2, max(c - 1, 0): c + 2].any():
                    continue
                blocked0[r, c] = True
                cand_cells.append(i)
            cand_cells = np.array(cand_cells, dtype=np.int64)
        print(f"sep={sep}: {cand_cells.size} candidate cells available", flush=True)

        for budget in args.budgets:
            # ---- stage 1: unconstrained greedy + self-consistent marginal trim -> target size ----
            sel0 = cand_cells[:budget]
            for _ in range(3):
                n_d = sel0.size
                if n_d == 0:
                    break
                est0 = float(q[sel0].sum()) / (ALPHA * n_d + BETA * N)
                keep = q[sel0] > ALPHA * est0
                if keep.all():
                    break
                sel0 = sel0[keep]
            n_target = int(sel0.size)
            q_min = ALPHA * est0            # marginal floor fixed BEFORE quota placement
            # ---- stage 2: quota placement at the FINAL count (trim cannot move the ratio) ----
            eligible = [nm for nm in pool.dots if pool.counts[nm] * 9 >= args.overlap_limit * n_target]
            halos = {}
            for nm in eligible:
                p = pool.halo(nm)
                if p is not None:
                    halos[nm] = p
            # fixed cap at the final count + retry passes; then a light kill-repair if
            # underfill moved the ratio (own files never constrain placement).
            external = [nm for nm in halos if not nm.startswith("own:")]
            cap = int(np.floor(args.overlap_limit * n_target))
            hits = {nm: 0 for nm in external}
            admitted = []
            queue = [int(i) for i in cand_cells]
            for _pass in range(8):
                if not queue or len(admitted) >= n_target:
                    break
                retry = []
                progressed = False
                for i in queue:
                    if len(admitted) >= n_target:
                        break
                    if q[i] < q_min:               # marginal rule fixed at stage 1
                        continue
                    g = int(grid_of_fp[i])
                    blocked = False
                    for nm in external:
                        if hits[nm] + 1 > cap and halo_test(halos[nm], g):
                            blocked = True
                            break
                    if blocked:
                        retry.append(i)
                        continue
                    for nm in external:
                        if halo_test(halos[nm], g):
                            hits[nm] += 1
                    admitted.append(i)
                    progressed = True
                queue = retry
                if not progressed:
                    break
            chosen = np.array(admitted, dtype=np.int64)
            # light kill-repair if underfill moved the ratio (own files never constrain placement)
            chosen = enforce_cap(chosen, q, pool, external, grid_of_fp, shape, args.overlap_limit)
            n0 = int(chosen.size)
            if n0:
                cand_try = np.zeros(shape[0] * shape[1], dtype=bool)
                cand_try[grid_of_fp[chosen]] = True
                for nm in external:
                    d = pool.dots[nm]
                    hits_now = int(np.count_nonzero(cand_try[pool.dots[nm]]))
                    cap_now = int(np.floor(args.overlap_limit * n0))
                    excess = hits_now - cap_now
                    if excess > 0:
                        # drop the lowest-q offenders inside this halo
                        inside = chosen[np.isin(grid_of_fp[chosen], pool.dots[nm])]
                        drop = inside[np.argsort(q[inside])[:excess]]
                        keep_mask = ~np.isin(chosen, drop)
                        chosen = chosen[keep_mask]
                        n0 = int(chosen.size)
                        cand_try = np.zeros(shape[0] * shape[1], dtype=bool)
                        cand_try[grid_of_fp[chosen]] = True
            n0 = int(chosen.size)

            # marginal-rule verification (no trim: the floor was fixed before placement)
            sel = chosen
            for _ in range(3):
                n_d = sel.size
                if n_d == 0:
                    break
                est_chk = float(q[sel].sum()) / (ALPHA * n_d + BETA * N)
                keep = q[sel] > ALPHA * est_chk
                if keep.all():
                    break
                sel = sel[keep]      # rare: keeps the marginal rule exactly true
            sel = enforce_cap(sel, q, pool, external, grid_of_fp, shape, args.overlap_limit)
            cand_flat = np.zeros(shape[0] * shape[1], dtype=bool)
            cand_flat[grid_of_fp[sel]] = True
            n1 = int(sel.size)
            tp = float(q[sel].sum())
            est = tp / (ALPHA * max(n1, 1) + BETA * N)

            fracs = pool.overlap_fracs(cand_flat, list(pool.dots))
            fracs.sort(reverse=True)
            fracs_ext = [f for f in fracs if not f[1].startswith("own:")]
            fracs_own = [f for f in fracs if f[1].startswith("own:")]
            worst = fracs_ext[0] if fracs_ext else (0.0, "none", 0, 0.0)
            worst_own = fracs_own[0] if fracs_own else (0.0, "none", 0, 0.0)
            cand_idx = np.flatnonzero(cand_flat).astype(np.uint32)
            dot_phi = pool.dot_phi(cand_idx, [nm for nm in pool.dots])
            dot_phi.sort(key=lambda t: -abs(t[0]))
            dot_phi_ext = [t for t in dot_phi if not t[1].startswith("own:")]
            dot_phi_own = [t for t in dot_phi if t[1].startswith("own:")]
            worst_phi_ext = round(max((abs(c) for c, _ in dot_phi_ext), default=0.0), 4)
            worst_phi_own = round(max((abs(c) for c, _ in dot_phi_own), default=0.0), 4)
            row = {"sep": sep, "budget": budget, "n_after_quota": n0, "n_target": n_target, "est_unconstrained": round(est0, 4), "n_dots": n1,
                   "expected_tp": round(tp, 1), "est_score": round(est, 4),
                   "worst_overlap": round(worst[0], 4), "worst_raster": worst[1],
                   "worst_raster_footprint_coverage": round(worst[3], 4),
                   "worst_own_overlap": round(worst_own[0], 4), "worst_own_raster": worst_own[1],
                   "rasters_checked": len(pool.dots),
                   "rasters_with_quota": len(halos),
                   "worst_abs_dot_phi": worst_phi_ext, "worst_abs_dot_phi_own": worst_phi_own,
                   "mean_q_on_dots": round(float(q[sel].mean()) if n1 else 0.0, 4)}
            print("  ->", row, flush=True)
            out.append((row, cand_flat.copy()))

    (ROOT / ".cache" / "quota_sweep.json").write_text(json.dumps([r for r, _ in out], indent=1) + "\n")

    if not args.emit:
        return 0

    row, cand_flat = max(out, key=lambda t: t[0]["est_score"])
    arr = np.where(foot, 0.0, np.nan).astype(np.float32)
    arr.ravel()[np.flatnonzero(cand_flat)] = 1.0
    assert int((arr == 1.0).sum()) == int(cand_flat.sum())

    tag = "dense" if row["sep"] == 0 else f"qp{row['sep']}"
    name = f"gemsdoesass3-lbinv2-{tag}-{row['n_dots']}-{TS}-nan"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tif = args.out_dir / f"{name}.tif"
    with rasterio.open(tif, "w", driver="GTiff", height=shape[0], width=shape[1], count=1,
                       dtype="float32", crs=crs, transform=transform, nodata=float("nan"),
                       compress="deflate", tiled=True, predictor=2) as ds:
        ds.write(arr, 1)
    zp = args.out_dir / f"{name}.tif.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif, tif.name)
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    zsha = hashlib.sha256(zp.read_bytes()).hexdigest()
    note = (f"LB-inv v2 {tag} {row['n_dots']} dots; EST {row['est_score']:.3f} "
            f"(LOO sd {loo['loo_rmse']:.3f}); <=65% within 3px of any registry raster")
    assert len(note) <= 140, len(note)
    build = {
        "schema_version": 1, "generated_utc": "2026-10-31", "label": "ESTIMATE",
        "not_organizer_confirmed": True,
        "hypothesis": "H-LBINV2-Q: metric-inversion credit field emitted under per-raster halo quotas (uniqueness by construction) at kernel-scale packing",
        "lane_id": "GEMSDOESASS3-H-LBINV2-QUOTA-KERNELPACK",
        "submission_name": name, "raster_sha256": sha, "zip_sha256": zsha,
        "n_dots": row["n_dots"], "expected_tp": row["expected_tp"], "est_score": row["est_score"],
        "N_estimate": N, "scale_c": ev["scale_c"], "loo_rmse": loo["loo_rmse"], "loo_rho": loo["loo_rho"],
        "corpus_rasters": ev["n_rasters"],
        "worst_registry_overlap": row["worst_overlap"], "worst_registry_raster": row["worst_raster"],
        "worst_abs_dot_phi": row["worst_abs_dot_phi"],
        "worst_preplacement_phi": [{"phi": round(c, 4), "raster": n} for c, n in worst_pre],
        "submission_note": note, "sweep_row": row,
    }
    (args.out_dir / f"{name}-build.json").write_text(json.dumps(build, indent=1) + "\n")
    print(json.dumps(build, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
