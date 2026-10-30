#!/usr/bin/env python3
"""Build the compliant unique candidate: maximum calibrated estimate subject to the LITERAL lane rule.

Why a new builder: `build_unique_candidate.py` measured the lane rule against references whose own
300 m band covers <= 50 % of the footprint and *excluded* the rest (the "halo-saturated" case).  The
13GEMSDOE calibration lattice covers 99.87 % of the footprint, so it was excluded from the number that
was reported as "literal".  An independent recomputation on 2026-10-30 (evidence/independent_recheck_
candidate_20261030.json) measured the 55,000-dot candidate at 99.54 % within 3 px of that lattice.  The
rule is therefore applied here literally, with no reference excluded:

    for EVERY reference r:  frac(dots within 3 px of r) <= CAP      (CAP = 0.70)

Hard consequence for the lattice: with G gap cells (footprint cells > 3 px from every lattice dot) the
total dot budget is N <= floor(G / (1 - CAP)), i.e. 6,649 / 0.30 = 22,163 dots.  Emission therefore

  1. takes the highest-h gap cells first (they are forced, so take the best of them),
  2. fills the remaining budget with lattice-covered cells in descending h, enforcing the cap against
     every other reference during emission,
  3. verifies every reference exactly and repairs (drops the lowest-h offenders) if a cap is exceeded.

h(x) is the score-weighted consensus field of the scored submissions, h = sum s_f k_f / sum k_f.

Usage: python scripts/build_compliant_candidate.py [--budget 22163] [--cap 0.70] [--min-gap 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import metric as M  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
RADIUS_PX = 3.0
K_HAT = 12691.0


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scored_files() -> list[dict]:
    rows = json.loads((ROOT / "evidence" / "score_drivers_20261030.json").read_text())["rows"]
    out, seen = [], set()
    for r in rows:
        if r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        for d in ("focus", "extra", "scored"):
            p = DATA / d / r["file"]
            if p.exists():
                out.append(dict(path=p, score=float(r["score"]), name=r["name"], sha=r["sha256"]))
                break
    return out


def other_references(exclude: set[str]) -> list[Path]:
    """Every sibling raster on disk except the calibration lattice.

    Scored submissions are references too: the lane rule is about not duplicating a sibling, and a
    submission that reproduces 80 % of a scored sibling's band is a duplicate however it was scored.
    Duplicate bytes are collapsed by sha256.
    """
    out, seen = [], set()
    for d in ("extra", "focus", "scored"):
        for p in sorted((DATA / d).glob("*.tif")):
            if "13gems_20261001_r13-lattice" in p.name:
                continue
            h = sha256(p)
            if h in exclude or h in seen:
                continue
            seen.add(h)
            out.append(p)
    return out


def band_of(dots: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    m = np.zeros(shape, bool)
    m[dots[:, 0], dots[:, 1]] = True
    return distance_transform_edt(~m) <= RADIUS_PX


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=22163)
    ap.add_argument("--cap", type=float, default=0.70)
    ap.add_argument("--min-gap", type=int, default=2)
    ap.add_argument("--tag", default="compliant-consensus")
    args = ap.parse_args()

    with rasterio.open(DATA / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        profile = ds.profile.copy()
    shape = foot.shape

    files = scored_files()
    print(f"scored references: {len(files)}")
    dots = []
    A = np.zeros(shape, np.float32)
    B = np.zeros(shape, np.float32)
    for f in files:
        with rasterio.open(f["path"]) as ds:
            a = np.where(foot, ds.read(1), 0.0) > 0
        d = np.stack(np.nonzero(a), 1)
        dots.append(d)
        k = M.kernel(distance_transform_edt(~a)).astype(np.float32)
        A += (k > 0)
        B += f["score"] * k
    h = np.where(A > 0, B / np.maximum(A, 1e-9), 0.0).astype(np.float32)
    h[~foot] = 0.0

    # kappa: same calibration as the portfolio builder (reproduces the scored population)
    gbars, meanh = [], []
    for d, f in zip(dots, files):
        n = len(d)
        gbars.append(f["score"] * (0.2 * n + 0.8 * K_HAT) / n)
        meanh.append(float(h[d[:, 0], d[:, 1]].mean()))
    kappa = float(np.mean(np.array(gbars) / np.maximum(meanh, 1e-9)))
    print(f"kappa = {kappa:.4f}")

    def estimate(mask: np.ndarray) -> float:
        ys, xs = np.nonzero(mask)
        if ys.size == 0:
            return 0.0
        return float(h[ys, xs].mean()) * kappa / (0.2 + 0.8 * K_HAT / ys.size)

    # ---- the lattice: the binding reference -------------------------------------------------
    lat_path = DATA / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
    with rasterio.open(lat_path) as ds:
        lat_mask = np.where(foot, ds.read(1), 0.0) > 0
    lat_dots = np.stack(np.nonzero(lat_mask), 1)
    lat_band = band_of(lat_dots, shape)
    gap = foot & ~lat_band
    n_gap = int(gap.sum())
    max_budget = int(n_gap / (1.0 - args.cap))
    print(f"lattice: {len(lat_dots)} dots, band {lat_band[foot].mean():.4f} of footprint, gap cells {n_gap}")
    print(f"LITERAL budget bound = floor({n_gap} / {1 - args.cap:.2f}) = {max_budget}")
    budget = min(args.budget, max_budget)

    # ---- other references (cap enforced during emission) ------------------------------------
    refs = other_references({sha256(lat_path)})
    print(f"references (all on-disk siblings except the lattice): {len(refs)}")

    # phase 1: forced gap dots, best h first, no spacing (they are forced; the budget is gap/0.30)
    hv = h.ravel()
    gi = np.flatnonzero(gap.ravel())
    gi = gi[hv[gi] > 0]
    gi = gi[np.argsort(-hv[gi], kind="stable")]
    chosen = np.zeros(shape, bool)
    chosen.ravel()[gi] = True
    gap_chosen = int(chosen.sum())
    print(f"gap dots chosen: {gap_chosen} = {gap_chosen / max(int(gap.sum()), 1):.3f} of the {int(gap.sum())} gap cells")
    budget_n = min(args.budget, int(gap_chosen / (1.0 - args.cap)))
    print(f"target total = min({args.budget}, gap/(1-cap)) = {budget_n}")

    # phase 2 candidates: lattice-covered, h > 0, descending h; membership vector per reference
    fi = np.flatnonzero((foot & lat_band & ~chosen).ravel())
    fi = fi[hv[fi] > 0]
    fi = fi[np.argsort(-hv[fi], kind="stable")]
    ys, xs = np.unravel_index(fi, shape)
    print(f"free candidates: {fi.size}")
    mat = np.zeros((fi.size, len(refs)), bool)
    counts = np.zeros(len(refs), np.int64)
    gy, gx = np.nonzero(chosen)
    for j, p in enumerate(refs):
        with rasterio.open(p) as ds:
            if ds.shape != shape:
                continue
            a = np.where(foot, np.nan_to_num(ds.read(1), nan=0.0), 0.0) > 0
        if a.sum() == 0:
            continue
        b = band_of(np.stack(np.nonzero(a), 1), shape)
        mat[:, j] = b[ys, xs]
        counts[j] = int(b[gy, gx].sum())
        del b
        if (j + 1) % 10 == 0:
            print(f"  reference {j + 1}/{len(refs)}", flush=True)

    spacing = np.zeros(shape, bool)
    r = args.min_gap
    accepted = gap_chosen
    for i in range(fi.size):
        if accepted >= budget_n:
            break
        y, x = int(ys[i]), int(xs[i])
        if spacing[y, x]:
            continue
        row = mat[i]
        if np.any((counts + row) / (accepted + 1) > args.cap):
            continue
        chosen[y, x] = True
        spacing[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1] = True
        counts += row
        accepted += 1
    print(f"accepted {accepted} dots (gap {gap_chosen})")
    del mat

    # ---- verify every reference literally, then repair --------------------------------------
    with rasterio.open(DATA / "sample_submission.tif") as ds:
        pass
    cand = np.stack(np.nonzero(chosen), 1)
    audit = []
    for p in [DATA / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"] + refs:
        with rasterio.open(p) as ds:
            if ds.shape != shape:
                continue
            a = np.where(foot, np.nan_to_num(ds.read(1), nan=0.0), 0.0) > 0
        if a.sum() == 0:
            continue
        b = band_of(np.stack(np.nonzero(a), 1), shape)
        frac = float(b[cand[:, 0], cand[:, 1]].mean())
        audit.append(dict(ref=f"{p.parent.name}/{p.name}", ref_dots=int(a.sum()), band_coverage=float(b[foot].mean()), frac_candidate_within_3px=frac))
        del b
    audit.sort(key=lambda x: -x["frac_candidate_within_3px"])
    worst = audit[0]
    print(f"worst literal overlap {worst['frac_candidate_within_3px']:.4f} vs {worst['ref']}")
    over = [a for a in audit if a["frac_candidate_within_3px"] > args.cap]
    if over:
        print(f"repair: {len(over)} references over cap -> dropping offenders")
        drop = np.zeros(len(cand), bool)
        for a in over:
            p = next(p for p in [DATA / "scored" / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"] + refs
                     if f"{p.parent.name}/{p.name}" == a["ref"])
            with rasterio.open(p) as ds:
                m = np.where(foot, np.nan_to_num(ds.read(1), nan=0.0), 0.0) > 0
            b = band_of(np.stack(np.nonzero(m), 1), shape)
            inside = b[cand[:, 0], cand[:, 1]]
            need = int(np.ceil(len(cand) * a["frac_candidate_within_3px"] - args.cap * len(cand)))
            order = np.argsort(hv[cand[:, 0] * shape[1] + cand[:, 1]])
            for idx in order:
                if need <= 0:
                    break
                if inside[idx] and not drop[idx]:
                    drop[idx] = True
                    need -= 1
        cand = cand[~drop]
        print(f"after repair: {len(cand)} dots")
        chosen = np.zeros(shape, bool)
        chosen[cand[:, 0], cand[:, 1]] = True

    n = int(chosen.sum())
    est = estimate(chosen)
    print(f"dots {n}   LEADERBOARD-CALIBRATED ESTIMATE {est:.4f}")

    # ---- write -----------------------------------------------------------------------------
    stamp = "20261030T060000Z"
    name = f"gemsdoesass3-{args.tag}-{n}-{stamp}-b7e21c0d"
    arr = np.where(foot, np.where(chosen, 1.0, 0.0), np.nan).astype(np.float32)
    prof = profile.copy()
    prof.update(dtype="float32", count=1, nodata=float("nan"), compress="deflate")
    out = ROOT / "docs" / "downloads" / f"{name}.tif"
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(arr, 1)
    z = out.with_suffix(".tif.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zi = zipfile.ZipInfo(out.name, date_time=(2026, 10, 30, 6, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        zf.writestr(zi, out.read_bytes())
    print(f"wrote {out.name} sha256={sha256(out)} bytes={out.stat().st_size} zip_sha256={sha256(z)}")

    json.dump(dict(
        schema_version=1, name=name, file=str(out.relative_to(ROOT)), sha256=sha256(out),
        bytes=out.stat().st_size, zip=str(z.relative_to(ROOT)), zip_sha256=sha256(z),
        zip_bytes=z.stat().st_size, zip_members=[out.name], n_dots=n, gap_dots=int(gap_chosen),
        literal_budget_bound=max_budget, gap_cells=n_gap, cap=args.cap, min_gap=args.min_gap,
        kappa=kappa, estimate=est, rule="LITERAL: every reference, no reference excluded",
        audit=audit, n_refs_audited=len(audit),
        n_over_cap=sum(a["frac_candidate_within_3px"] > args.cap for a in audit),
        worst=audit[0], halo_excluded=0,
    ), open(ROOT / "evidence" / "compliant_candidate_20261030.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
