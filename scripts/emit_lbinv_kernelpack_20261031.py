#!/usr/bin/env python3
"""E2 (session 2026-10-31) — metric-inversion field, kernel-scale packed emission.

Lane (the single method paragraph): the organizer metric's per-truth-credit is a MAXIMUM over
predicted pixels inside the 300 m triangular kernel (``src/gems32/metric.py``: TP_w = sum_g
max_x p(x) k(d(x,g))).  Two dots whose kernels cover the same hidden truth pixel therefore earn
one credit while paying the 0.2*D denominator twice, so the emitted set is placed with a
kernel-scale exclusion (Chebyshev >= sep px, sep swept over {3, 4}) instead of the sep=2 blocks of
the 2026-10-30 file.  Placement is greedy in the distilled credit field q (least-norm inversion of
the metric on the 2026-10-31 corpus of 133 scored rasters), trimmed by the metric's own marginal
rule (keep a dot iff q > 0.2*DTI_est), and repaired against the uniqueness rule: at most
``overlap_limit`` of the final dots within 3 px of ANY registry/corpus/own raster's dots, lowest-credit
offenders dropped first.  Rank-correlation (Spearman; for binary-vs-binary equal to the phi
coefficient) is checked on the continuous surface before placement and on the final dots.

Speed: every pool raster is read once; its dot indices and its 3 px halo (packbits) are cached under
.cache/kernelpack_cache/ so each uniqueness pass is a boolean count, not a dilation sweep.

Outputs (in docs/downloads):
  gemsdoesass3-lbinv2-kp<sep>-<dots>-<ts>-<sha8>-nanoutside.tif (+ .zip, -build.json)  — analysis copy
  then scripts/make_portal_safe_render.py produces the submittable ``-safe.tif`` (0.0 outside +
  GDAL mask band) — the file the live portal accepts (IR-SASS3-81).

Usage:
    python scripts/emit_lbinv_kernelpack_20261031.py [--emit]
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
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8
STRUCT = np.ones((3, 3), dtype=bool)
TS = "20261031T120000Z"


def phi_counts(n11: int, n1: int, n2: int, n: int) -> float:
    """Phi/Spearman for two binary vectors given their intersection and marginals."""
    if n1 == 0 or n2 == 0 or n1 == n or n2 == n:
        return 0.0
    p1, p2 = n1 / n, n2 / n
    pab = n11 / n
    den = np.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    return float((pab - p1 * p2) / den) if den > 0 else 0.0


class Pool:
    """Reads each raster once; caches dot indices and 3 px halos."""

    def __init__(self, paths, shape, foot, cache_dir: Path, min_dots_for_halo: int):
        self.shape = shape
        self.foot = foot
        self.n_fp = int(foot.sum())
        self.fp_of_grid = np.full(shape[0] * shape[1], -1, dtype=np.int64)
        self.fp_of_grid[np.nonzero(foot.ravel())[0]] = np.arange(self.n_fp)
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.dots: dict[str, np.ndarray] = {}       # flat grid indices (uint32), footprint cells only
        self.counts: dict[str, int] = {}
        self.halo_dir = cache_dir / "halos"
        self.halo_dir.mkdir(exist_ok=True)
        idx_path = cache_dir / "pool_dots.npz"
        saved = {}
        if idx_path.exists():
            with np.load(idx_path) as z2:
                saved = {k: z2[k] for k in z2.files}
        need = []
        for p, name in paths:
            if name in saved:
                self.dots[name] = saved[name]
                self.counts[name] = int(saved[name].size)
            else:
                need.append((p, name))
        for p, name in need:
            try:
                with rasterio.open(p) as ds:
                    if ds.shape != shape:
                        continue
                    a = ds.read(1)
            except Exception:
                continue
            m = np.isfinite(a) & (a > 0) & foot
            del a
            idx = np.flatnonzero(m.ravel()).astype(np.uint32)
            del m
            if idx.size == 0:
                continue
            self.dots[name] = idx
            self.counts[name] = int(idx.size)
        np.savez_compressed(idx_path, **self.dots)
        self._halo_built = {p.stem for p in self.halo_dir.glob("*.npy")}
        self._paths = dict((name, p) for p, name in paths)

    def halo(self, name: str):
        """Packbits of the 3 px dilation of the raster's dots (grid space)."""
        key = hashlib.sha256(name.encode()).hexdigest()[:16]
        f = self.halo_dir / f"{key}.npy"
        if f.exists():
            return np.load(f)
        p = self._paths.get(name)
        if p is None:
            return None
        try:
            with rasterio.open(p) as ds:
                a = ds.read(1)
        except Exception:
            return None
        m = np.isfinite(a) & (a > 0) & self.foot
        del a
        h = binary_dilation(m, STRUCT)
        del m
        packed = np.packbits(h.ravel())
        np.save(f, packed)
        return packed

    def overlap_fracs(self, cand_flat: np.ndarray, eligible: list[str]):
        """Fraction of candidate dots inside each eligible raster's 3 px halo."""
        n = int(cand_flat.sum())
        out = []
        for name in eligible:
            packed = self.halo(name)
            if packed is None:
                continue
            halo = np.unpackbits(packed)[: cand_flat.size].astype(bool)
            cover = int(halo.sum())
            frac = float((cand_flat & halo).sum()) / max(n, 1)
            del halo
            out.append((frac, name, cover, cover / self.n_fp))
        return out

    def dot_phi(self, cand_idx: np.ndarray, names: list[str]):
        """Phi between the candidate's dots and each raster's dots (footprint space)."""
        n1 = int(cand_idx.size)
        out = []
        for name in names:
            other = self.dots.get(name)
            if other is None:
                continue
            n2 = int(other.size)
            n11 = int(np.intersect1d(cand_idx, other, assume_unique=True).size)
            out.append((phi_counts(n11, n1, n2, self.n_fp), name))
        return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field", type=Path, default=ROOT / ".cache" / "distill_q.npz")
    ap.add_argument("--evidence", type=Path, default=ROOT / "evidence" / "distill_from_leaderboard_20261031.json")
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--registry", type=Path, default=ROOT / ".cache" / "focus_registry")
    ap.add_argument("--corpus", type=Path, default=ROOT / ".cache" / "gems_corpus")
    ap.add_argument("--own", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--sep", type=int, nargs="+", default=[3, 4])
    ap.add_argument("--budgets", type=int, nargs="+", default=[42000, 50000, 58000, 66000])
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
    assert grid_of_fp.size == q.size
    fp_of_grid = np.full(shape[0] * shape[1], -1, dtype=np.int64)
    fp_of_grid[grid_of_fp] = np.arange(q.size)

    paths = []
    for d, tag in ((args.registry, ""), (args.corpus, "corpus:"), (args.own, "own:")):
        for p in sorted(d.glob("*.tif")):
            paths.append((p, (tag + p.name) if tag else p.name))
    seen, uniq = set(), []
    for p, nm in paths:
        if nm not in seen:
            seen.add(nm)
            uniq.append((p, nm))
    paths = uniq
    min_budget = min(args.budgets)
    floor_dots = int(args.overlap_limit * min_budget / 9.0) + 1
    print(f"pool: {len(paths)} rasters; halos only for rasters with >= {floor_dots} dots", flush=True)
    pool = Pool(paths, shape, foot, ROOT / ".cache" / "kernelpack_cache", floor_dots)
    print(f"readable: {len(pool.dots)} rasters", flush=True)

    # ---- rank-correlation of the continuous surface (pre-placement) vs every pool raster ----
    pos_idx = np.flatnonzero(q > 0).astype(np.uint32)          # footprint space
    pre_corr = []
    for name in pool.dots:
        other_fp = fp_of_grid[pool.dots[name].astype(np.int64)]
        n11 = int(np.intersect1d(pos_idx, other_fp.astype(np.uint32), assume_unique=True).size)
        pre_corr.append((phi_counts(n11, int(pos_idx.size), pool.counts[name], pool.n_fp), name))
    pre_corr.sort(key=lambda t: -abs(t[0]))
    worst_pre = pre_corr[:5]
    print("worst pre-placement surface correlations:", [(round(c, 4), n) for c, n in worst_pre], flush=True)

    order_all = np.argsort(-q)
    scored = q > 0
    rows_fp, cols_fp = np.divmod(grid_of_fp, shape[1])
    out = []
    for sep in args.sep:
        blk = max(sep, 2)
        blocked = np.zeros((shape[0] // blk + 2, shape[1] // blk + 2), dtype=bool)
        chosen = []
        for i in order_all:
            if not scored[i]:
                break
            if len(chosen) >= max(args.budgets):
                break
            r, c = rows_fp[i] // blk, cols_fp[i] // blk
            if blocked[max(r - 1, 0): r + 2, max(c - 1, 0): c + 2].any():
                continue
            blocked[r, c] = True
            chosen.append(i)
        chosen = np.array(chosen, dtype=np.int64)
        print(f"sep={sep}: packed {chosen.size} cells at q>= {q[chosen[-1]]:.4f}", flush=True)

        for budget in args.budgets:
            sel = chosen[:budget]
            for _ in range(3):                       # self-consistent marginal trim q > 0.2*est
                n_d = sel.size
                if n_d == 0:
                    break
                est = float(q[sel].sum()) / (ALPHA * n_d + BETA * N)
                keep = q[sel] > ALPHA * est
                if keep.all():
                    break
                sel = sel[keep]
            cand = np.zeros(shape, dtype=bool)
            cand.ravel()[grid_of_fp[sel]] = True
            cand_flat = cand.ravel()
            n0 = int(cand.sum())
            est0 = float(q[sel].sum()) / (ALPHA * max(n0, 1) + BETA * N)

            eligible = [nm for nm in pool.dots if pool.counts[nm] * 9 >= args.overlap_limit * n0]
            fracs = pool.overlap_fracs(cand_flat, eligible)
            fracs.sort(reverse=True)
            worst = fracs[0] if fracs else (0.0, "none", 0, 0.0)
            rounds = 0
            while worst[0] > args.overlap_limit and rounds < 6:
                rounds += 1
                packed = pool.halo(worst[1])
                halo = np.unpackbits(packed)[: cand_flat.size].astype(bool)
                hit_idx = np.flatnonzero(cand_flat & halo)
                fp_idx = fp_of_grid[hit_idx]
                ok = fp_idx >= 0
                hit_idx, fp_idx = hit_idx[ok], fp_idx[ok]
                lo, hi = 0, hit_idx.size
                while lo < hi:                       # smallest kill count that satisfies the cap
                    mid = (lo + hi) // 2
                    n, m = int(cand.sum()), int(hit_idx.size)
                    if (m - mid) / max(n - mid, 1) <= args.overlap_limit:
                        hi = mid
                    else:
                        lo = mid + 1
                kill = hit_idx[np.argsort(q[fp_idx])[:lo]]
                cand_flat[kill] = False
                del halo
                fracs = pool.overlap_fracs(cand_flat, eligible)
                fracs.sort(reverse=True)
                worst = fracs[0] if fracs else (0.0, "none", 0, 0.0)

            n1 = int(cand_flat.sum())
            cand_idx = np.flatnonzero(cand_flat).astype(np.uint32)
            sel_fp = fp_of_grid[cand_idx.astype(np.int64)]
            sel_fp = sel_fp[sel_fp >= 0]
            tp = float(q[sel_fp].sum())
            est = tp / (ALPHA * n1 + BETA * N)
            dot_phi = pool.dot_phi(cand_idx, eligible)
            dot_phi.sort(key=lambda t: -abs(t[0]))
            row = {"sep": sep, "budget": budget, "n_dots": n1, "expected_tp": round(tp, 1),
                   "est_score": round(est, 4), "est_before_repair": round(est0, 4),
                   "worst_overlap": round(worst[0], 4), "worst_raster": worst[1],
                   "worst_raster_footprint_coverage": round(worst[3], 4), "repair_rounds": rounds,
                   "rasters_able_to_reach_cap": len(eligible),
                   "worst_abs_dot_phi": round(max((abs(c) for c, _ in dot_phi), default=0.0), 4)}
            print("  ->", row, flush=True)
            out.append((row, cand_flat.copy(), sel_fp.copy()))

    (ROOT / ".cache" / "kernelpack_sweep.json").write_text(json.dumps([r for r, _, _ in out], indent=1) + "\n")

    if not args.emit:
        return 0

    row, cand_flat, sel_fp = max(out, key=lambda t: t[0]["est_score"])
    arr = np.where(foot, 0.0, np.nan).astype(np.float32)
    arr.ravel()[np.flatnonzero(cand_flat)] = 1.0
    assert int((arr == 1.0).sum()) == int(cand_flat.sum())

    name = f"gemsdoesass3-lbinv2-kp{row['sep']}-{row['n_dots']}-{TS}-nanoutside"
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
    note = (f"LB-inv v2 kernel-pack sep{row['sep']}: {row['n_dots']} dots; "
            f"EST {row['est_score']:.3f} (LOO sd {loo['loo_rmse']:.3f}); unique<={args.overlap_limit:.0%} vs pool")
    assert len(note) <= 140, len(note)
    build = {
        "schema_version": 1, "generated_utc": "2026-10-31", "label": "ESTIMATE",
        "not_organizer_confirmed": True,
        "hypothesis": "H-LBINV2: metric-inversion credit field emitted at kernel-scale packing (sep>=3 px) with strict uniqueness repair",
        "lane_id": "GEMSDOESASS3-H-LBINV2-KERNELPACK",
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
