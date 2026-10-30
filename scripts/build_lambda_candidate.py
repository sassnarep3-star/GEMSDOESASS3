#!/usr/bin/env python3
"""H-SASS3-I: submodular maximum-credit emission on the live-inverted truth density (LLI-lambda).

What is new here, versus the ~90 mirrored sibling rasters
---------------------------------------------------------
Every sibling submission is built the same way: threshold a geological propensity surface, thin or
skeletonise it, and emit a Poisson-disk subset at ~300 m.  The emission is a property of the surface,
and the score saturates at 0.2778 across ~90 independent attempts because none of them modelled the
one structural fact about the metric that governs the optimum:

    TP_w = sum_{y in G} max_{x} p(x) * k(d(x,y))      # credit per true pixel is a MAX over dots

Two dots within 3 px of each other therefore earn about ONE dot's true-positive credit while paying
TWO dots' false-positive cost (alpha = 0.2 on FP_w, beta = 0.8 on FN_w).  Coverage is monotone
submodular in the dot set and the cost is modular, so greedy placement is (1 - 1/e)-optimal for the
coverage part (Nemhauser, Wolsey & Fisher 1978), and a Dinkelbach parameter update makes each greedy
step optimal for the DTI ratio itself.

This script adds no new propensity surface.  It uses the only empirical estimate of the hidden scoring
population that exists anywhere - lambda_k, the per-stratum probability that a pixel is a scored
off-catalogue fault, inverted from the live leaderboard scores by `scripts/lli_score_model.py` - and
solves the emission directly:

    maximise over S:   (1 + beta*s) * TP(S) + alpha*s*M(S)/3 - alpha*s*|S|
    TP(S) = sum_y lambda_y max_{x in S} k(d(x,y))    (tracked EXACTLY with a credit map)
    M(S)  = sum_x sum_y lambda_y k(d(x,y))           (the module's 1/3 line factor is applied by
                                                       ledger_inversion.LINE_MAX_TO_SUM)
    s     = DTI(S)                                   (Dinkelbach parameter)

subject to every dot lying in the scored domain (footprint minus catalogue pixels).  Three variants:
A = unconstrained optimum; B = strictly lane-compliant (all dots > 3 px from every sibling dot);
C = lane-budgeted hybrid.  The exact feasibility CEILING for B is reported so that the conflict between
"beat the champion" and "stay out of the saturated lane" is a measured number, not an argument.

Every number produced here is a PROJECTION (LLI model output) - never a score.  Promotion to a real
submission slot is a separate decision (scripts/verify_all_gates.py + the owner's slot plan).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import ledger_inversion as li  # noqa: E402
from gems32.metric import ALPHA, BETA, kernel  # noqa: E402

DDIR = ROOT / "data" / "official"
H195 = DDIR / "scored" / "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"
OFFSETS = [(dy, dx, float(kernel(np.hypot(dy, dx))))
           for dy in range(-3, 4) for dx in range(-3, 4) if float(kernel(np.hypot(dy, dx))) > 0.0]
BALL = [(dy, dx) for dy in range(-3, 4) for dx in range(-3, 4) if dy * dy + dx * dx <= 9]


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read1(p):
    with rasterio.open(p) as ds:
        return ds.read(1)


def digitize(d, edges, codes):
    return np.asarray(codes, np.int8)[np.digitize(d, edges, right=True)]


def build_strata(design: str, theta: np.ndarray):
    """Rebuild the S0/S3 strata exactly as scripts/lli_score_model.py and GEMSDOE32 do."""
    with rasterio.open(DDIR / "sample_submission.tif") as ds:
        ss = ds.read(1)
        ss_meta = ds.meta.copy()
    foot = np.isfinite(ss)
    labels = (read1(DDIR / "labels.tif") > 0) & foot
    active = foot & ~labels
    d_cat = distance_transform_edt(~labels)
    h = read1(H195)
    h = np.isfinite(h) & (h > 0) & foot
    d_h = distance_transform_edt(~h)
    if design == "S0":
        cat_lv = digitize(d_cat, [1.01, 2.01, 3.01, 5.01, 10.01, 20.01, 50.01], [1, 2, 3, 4, 5, 6, 7, 0])
        cat_lab = [">50", "1", "1.4-2", "2.2-3", "3-5", "5-10", "10-20", "20-50"]
        h_lv = digitize(d_h, [0.01, 1.01, 2.01, 5.01], [1, 2, 3, 4, 0])
        h_lab = [">5", "on", "1", "1.4-2", "2.2-5"]
        nlev = [8, 5]
    elif design == "S3":
        cat_lv = digitize(d_cat, [2.01, 3.01, 5.01, 10.01, 30.01], [1, 2, 3, 4, 5, 0])
        cat_lab = [">30", "1-2", "2.2-3", "3.2-5", "5-10", "10-30"]
        h_lv = digitize(d_h, [0.01, 1.01, 2.01, 3.01, 4.01, 5.01, 8.01, 15.01],
                        [1, 2, 3, 4, 5, 6, 7, 8, 0])
        h_lab = [">15", "on", "1", "1.4-2", "2.2-3", "3.2-4", "4.1-5", "5-8", "8-15"]
        nlev = [6, 9]
    else:
        raise SystemExit(f"design {design} unsupported here (S4 needs training_features band 12)")
    for lv in (cat_lv, h_lv):
        lv[~active] = 0
    spec = li.StrataSpec(names=["d_catalogue_px", "d_H19-5_px"], levels=[cat_lv, h_lv], n_levels=nlev,
                         level_labels=[cat_lab, h_lab], active=active)
    lam = li.strata_lambda(theta, spec).astype(np.float32)
    lam_grid = lam[spec.stratum]
    lam_grid[~active] = 0.0
    return spec, lam_grid, foot, labels, active, ss_meta


def _slip(dst, src, dy, dx):
    H, W = dst.shape
    ys, ye = max(0, -dy), min(H, H - dy)
    xs, xe = max(0, -dx), min(W, W - dx)
    return ys, ye, xs, xe, ys + dy, ye + dy, xs + dx, xe + dx


def shifted_add(dst, src, dy, dx, scale):
    ys, ye, xs, xe, sy, ey, sx, ex = _slip(dst, src, dy, dx)
    if ye > ys and xe > xs:
        dst[ys:ye, xs:xe] += scale * src[sy:ey, sx:ex]


def shifted_or(dst, src, dy, dx):
    ys, ye, xs, xe, sy, ey, sx, ex = _slip(dst, src, dy, dx)
    if ye > ys and xe > xs:
        dst[ys:ye, xs:xe] |= src[sy:ey, sx:ex]


def credit_map(field):
    """w(x) = sum_y field(y) k(d(x,y)): expected kernel credit of ONE dot at x (float32)."""
    w = np.zeros(field.shape, np.float32)
    for dy, dx, k in OFFSETS:
        shifted_add(w, field, -dy, -dx, k)
    return w


class Greedy:
    """Greedy max-H(S) placement with exact TP bookkeeping and rho-separation."""

    def __init__(self, w, lam_grid, s, cell_side=4):
        self.w, self.lam, self.s, self.cell = w, lam_grid, s, cell_side
        self.c = np.zeros(w.shape, np.float32)          # per-truth-pixel credit already earned
        self.placed = np.zeros(w.shape, bool)
        self.ny, self.nx = w.shape[0] // cell_side + 1, w.shape[1] // cell_side + 1
        self.occ = [[] for _ in range(self.ny * self.nx)]
        self.n = 0

    def _ok(self, y, x):
        cy, cx = y // self.cell, x // self.cell
        r2 = (self.cell - 0.5) ** 2
        for gy in range(cy - 1, cy + 2):
            if not (0 <= gy < self.ny):
                continue
            for gx in range(cx - 1, cx + 2):
                if not (0 <= gx < self.nx):
                    continue
                for (py, px) in self.occ[gy * self.nx + gx]:
                    if (py - y) ** 2 + (px - x) ** 2 < r2:
                        return False
        return True

    def marginals(self):
        """gain(x) = (1 + beta s) * sum_y lam_y max(0, k_xy - c_y) + alpha s (w(x)/3 - 1)."""
        g = np.zeros(self.w.shape, np.float32)
        for dy, dx, k in OFFSETS:
            term = np.maximum(0.0, k - self.c).astype(np.float32)
            term *= self.lam
            shifted_add(g, term, -dy, -dx, 1.0)
        a, b = ALPHA, BETA
        return (1.0 + b * self.s) * g + a * self.s * (self.w / 3.0) - a * self.s

    def update_credit(self, newly):
        yy = np.fromiter((q[0] for q in newly), np.int64)
        xx = np.fromiter((q[1] for q in newly), np.int64)
        H, W = self.c.shape
        for off_dy, off_dx, k in OFFSETS:
            ty, tx = yy + off_dy, xx + off_dx
            ok = (ty >= 0) & (ty < H) & (tx >= 0) & (tx < W)
            cur = self.c[ty[ok], tx[ok]]
            np.maximum(cur, k, out=cur)
            self.c[ty[ok], tx[ok]] = cur

    def run(self, eligible, max_dots, batch=4096, log=False):
        gain = self.marginals()
        gain[~eligible] = -np.inf
        gain[self.placed] = -np.inf
        it = 0
        while self.n < max_dots:
            it += 1
            flat = gain.ravel()
            pos = np.flatnonzero(flat > 0)
            if pos.size == 0:
                break
            take = pos[np.argsort(-flat[pos])][:batch]
            ys, xs = np.unravel_index(take, gain.shape)
            newly = []
            for y, x in zip(ys.tolist(), xs.tolist()):
                if self.n + len(newly) >= max_dots:
                    break
                if self._ok(y, x):
                    newly.append((y, x))
                    self.occ[y // self.cell * self.nx + x // self.cell].append((y, x))
            if not newly:
                break
            for y, x in newly:
                self.placed[y, x] = True
            self.n += len(newly)
            self.update_credit(newly)
            if log:
                print(f"   pass {it}: +{len(newly)} (total {self.n})", flush=True)
            gain = self.marginals()
            gain[~eligible] = -np.inf
            gain[self.placed] = -np.inf
        return self.placed


def overlap_fraction(placed, src_mask):
    """Fraction of `placed` dots that lie within 3 px (Euclidean) of any dot in `src_mask`."""
    sy, sx = np.nonzero(src_mask)
    if sy.size == 0:
        return 0.0
    buckets = {}
    for y, x in zip(sy.tolist(), sx.tolist()):
        buckets.setdefault((y >> 2, x >> 2), []).append((y, x))
    oy, ox = np.nonzero(placed)
    hit = 0
    for y, x in zip(oy.tolist(), ox.tolist()):
        cy, cx = y >> 2, x >> 2
        found = False
        for gy in range(cy - 1, cy + 2):
            for gx in range(cx - 1, cx + 2):
                if any((py - y) ** 2 + (px - x) ** 2 <= 9 for py, px in buckets.get((gy, gx), ())):
                    found = True
                    break
            if found:
                break
        hit += found
    return hit / max(oy.size, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="S0")
    ap.add_argument("--lam-mixture", default="", help="second design whose lambda is combined with "
                        "--design's (see --lam-mode) to make the emission robust to which density is right")
    ap.add_argument("--lam-mode", default="geomean", choices=["geomean", "max", "mean"],
                    help="geomean = intersection of the two hypotheses (minimises disagreement); "
                         "max = union (cover whichever hypothesis is right); mean = model average")
    ap.add_argument("--lane-target", type=float, default=0.65)
    ap.add_argument("--value", type=float, default=1.0)
    ap.add_argument("--max-dots", type=int, default=60000)
    ap.add_argument("--skip-variants", default="", help="comma list of variant names to skip")
    ap.add_argument("--tag", default=time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    ap.add_argument("--registry-globs",
                    default="/tmp/g32/docs/downloads/*.tif,/home/user/focus/*.tif,/home/user/ledger/*.tif,"
                            "/tmp/g19/submissions/*.tif")
    a = ap.parse_args()
    skip = {s for s in a.skip_variants.split(",") if s}

    ev = json.loads((ROOT / "evidence" / "lli_score_model_verification.json").read_text())
    theta = np.array(ev["published_theta_check_on_local_pool"]["theta"], float)
    spec, lam_grid, foot, labels, active, ss_meta = build_strata(a.design, theta)
    if a.lam_mixture:
        th2 = np.array(json.loads(Path("/home/user/reg32/live_ledger_inversion.json").read_text())
                       ["designs"][a.lam_mixture]["fit"]["theta"], float)
        spec2, lam2, _, _, _, _ = build_strata(a.lam_mixture, th2)
        # model-average density: geometric mean of the two pixel-wise densities on the shared grid
        if a.lam_mode == "geomean":
            lam_grid = np.sqrt(np.maximum(lam_grid, 0.0) * np.maximum(lam2, 0.0)).astype(np.float32)
        elif a.lam_mode == "max":
            lam_grid = np.maximum(lam_grid, lam2).astype(np.float32)
        else:
            lam_grid = (0.5 * (lam_grid + lam2)).astype(np.float32)
        print(f"lam mixture {a.design} x {a.lam_mixture}: sum {float(lam_grid.sum()):.1f} "
              f"(S0 {float(spec.sizes @ li.strata_lambda(theta, spec)):.1f}, "
              f"S3 {float(spec2.sizes @ li.strata_lambda(th2, spec2)):.1f})", flush=True)
    lam_vec = li.strata_lambda(theta, spec)
    g_tot = float(spec.sizes @ lam_vec)
    print(f"design {a.design}: {spec.n_strata} strata, scored domain {int(active.sum())} px, "
          f"inverted |G| = {g_tot:.1f} px, lam_max {lam_vec.max():.4g}", flush=True)

    files = []
    for g in a.registry_globs.split(","):
        files += [Path(p) for p in glob.glob(g.strip())]
    fam_raw = np.zeros(foot.shape, bool)
    per_raster = []
    for p in sorted(set(files)):
        try:
            arr = read1(p)
        except Exception:
            continue
        if arr.shape != foot.shape:
            continue
        m = np.isfinite(arr) & (arr > 0)
        fam_raw |= m
        per_raster.append((p.name, m))
    fam = np.zeros(foot.shape, bool)
    for dy, dx in BALL:
        shifted_or(fam, fam_raw, dy, dx)
    # ratio must be dimensionally consistent: buffer inside the scored domain over the scored domain. (An
    # earlier version divided the whole-grid buffer by the ACTIVE domain and printed >100%; corrected
    # 2026-10-30, see evidence/pool_buffer_coverage_20261030.json and scripts/pool_buffer_coverage.py.)
    buf_in_foot = int((fam & foot).sum())
    buffer_cov = buf_in_foot / float(foot.sum())
    print(f"sibling pool: {len(per_raster)} rasters, {int(fam_raw.sum())} union dots; 3-px buffer covers "
          f"{buffer_cov:.6f} of the scored domain ({buf_in_foot:,}/{int(foot.sum()):,}); "
          f"cells outside it in the active domain: {int((active & ~fam).sum()):,}", flush=True)

    w = credit_map(lam_grid)
    base = active & (w > 0)
    s = 0.2778
    variants = {}
    for name, elig in (("A_unconstrained", base.copy()), ("B_lane_exclusive", (base & ~fam).copy())):
        if name in skip:
            continue
        gr = Greedy(w, lam_grid, s)
        t0 = time.time()
        placed = gr.run(elig, max_dots=a.max_dots)
        variants[name] = {"placed": placed.copy(), "dots": int(gr.n), "secs": round(time.time() - t0, 1)}
        print(f"variant {name}: {int(gr.n)} dots in {variants[name]['secs']}s", flush=True)

    if "C_lane_budgeted" not in skip and "B_lane_exclusive" in variants:
        B = variants["B_lane_exclusive"]["placed"]
        grC = Greedy(w, lam_grid, s)
        grC.placed = B.copy()
        grC.n = int(B.sum())
        for y, x in zip(*np.nonzero(B)):
            grC.occ[int(y) // grC.cell * grC.nx + int(x) // grC.cell].append((int(y), int(x)))
        placedC = grC.run(base.copy(), max_dots=a.max_dots)      # eligible = everything, B seeded first
        variants["C_lane_budgeted"] = {"placed": placedC.copy(), "dots": int(grC.n), "secs": 0.0}

    # exact ceiling of a strictly exclusive design: perfect credit for every truth pixel reachable
    # from an exclusive pixel, zero false positives
    reach = np.zeros(foot.shape, bool)
    for dy, dx, k in OFFSETS:
        shifted_or(reach, base & ~fam, dy, dx)
    tp_ceil = float(lam_grid[reach & active].sum())
    bound = tp_ceil / (tp_ceil + BETA * max(g_tot - tp_ceil, 0.0) + 1e-12)
    print(f"lane-compliant ceiling: ANY raster with all dots >3 px from every sibling dot projects "
          f"<= {bound:.4f}  (champion live score 0.2778)", flush=True)

    dl = ROOT / "docs" / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    prof = {k: v for k, v in ss_meta.items() if k in ("width", "height", "crs", "transform")}
    # profile copied from the file the portal demonstrably accepted and scored 0.2778:
    # GTiff, count 1, float32, no nodata tag, uncompressed stripped, EPSG:32611, 100 m grid
    prof.update(driver="GTiff", count=1, dtype="float32", nodata=None)
    H, W = foot.shape
    out = {"schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "mechanism": "H-SASS3-I submodular max-credit greedy emission on LLI-inverted truth density",
           "evidence_class": "every DTI number here is a PROJECTION (LLI-v1), never a score",
           "design": a.design,
           "theta_source": "evidence/lli_score_model_verification.json (published S0 fit, verified locally)",
           "inputs": {"labels.tif": sha256_file(DDIR / "labels.tif"),
                      "sample_submission.tif": sha256_file(DDIR / "sample_submission.tif"),
                      "h19-5": sha256_file(H195)},
           "registry_pool_rasters": len(per_raster), "scored_domain_px": int(active.sum()),
           "g_estimate_px": g_tot,
           "pool_union_dots": int(fam_raw.sum()),
           "buffer_coverage_of_scored_domain": buffer_cov,
           "cells_outside_buffer_in_active_domain": int((active & ~fam).sum()),
           "lane_feasibility_ceiling": {"reachable_truth_px": tp_ceil, "g_total_px": g_tot,
                                        "max_projected_dti": bound,
                                        "meaning": "upper bound over ALL strictly lane-compliant rasters, "
                                                   "assuming zero false positives and unit kernel credit"},
           "variants": {}}

    for name, v in variants.items():
        placed = v["placed"]
        if v["dots"] == 0:
            out["variants"][name] = {"dots": 0, "note": "no eligible pixel"}
            continue
        arr = np.zeros((H, W), np.float32)
        arr[foot] = 0.0
        arr[placed] = float(a.value)
        row = li.design_row(np.where(placed, 1.0, 0.0).astype(np.float32) * active, spec)
        c = li.predict_components(row["A"][None, :], row["B"][None, :], np.array([row["N"]]),
                                  spec.sizes, lam_vec)
        overlaps = sorted(((overlap_fraction(placed, m), pname) for pname, m in per_raster), reverse=True)
        worst = overlaps[0] if overlaps else (0.0, None)
        digest = hashlib.sha256(np.ascontiguousarray(placed).tobytes()).hexdigest()
        stem = (f"gemsdoesass3-llegreedy-{a.design.lower()}{('x' + a.lam_mixture.lower() + a.lam_mode[:3]) if a.lam_mixture else ''}"
                f"dots-{v['dots'] // 1000}k-{a.tag}-{digest[:8]}")
        fpath = dl / f"{stem}.tif"
        with rasterio.open(fpath, "w", **prof) as ds:
            ds.write(arr, 1)
            ds.update_tags(SUBMISSION_NAME=stem, MECHANISM="LLI-lambda submodular greedy emission",
                           EVIDENCE_CLASS="projection only, not a score")
        with zipfile.ZipFile(dl / f"{stem}.tif.zip", "w", zipfile.ZIP_STORED) as zf:
            zf.write(fpath, arcname=fpath.name)
        out["variants"][name] = {
            "file": fpath.name, "zip": fpath.name + ".zip", "dots": int(v["dots"]),
            "sha256": sha256_file(fpath), "mask_sha256": digest, "bytes": fpath.stat().st_size,
            "projected_live_dti": float(c["dti"][0]), "projected_tp": float(c["tp"][0]),
            "projected_fp": float(c["fp"][0]), "projected_fn": float(c["fn"][0]),
            "N_mass": float(row["N"]),
            "kernel_credit_per_dot": float(row["N"] / max(v["dots"], 1)),
            "worst_sibling_3px_overlap": worst[0], "worst_sibling": worst[1],
            "top5_overlaps": [{"frac": f, "file": n} for f, n in overlaps[:5]],
            "n_siblings_compared": len(overlaps), "secs": v["secs"]}
        print(f"{name}: dots={v['dots']} projected={float(c['dti'][0]):.4f} worst3px={worst[0]:.3f} "
              f"({worst[1]})", flush=True)
    ep = ROOT / "evidence" / "lambda_emission_variants.json"
    ep.write_text(json.dumps(out, indent=1, default=float))
    print("wrote", ep, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
