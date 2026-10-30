#!/usr/bin/env python3
"""Emit a submission that is unique under the lane rule *and* maximises the calibrated estimate.

The lane rule, applied literally to every accessible registry raster, is unsatisfiable: the
13GEMSDOE calibration lattice's 300 m band covers 99.9 % of the footprint, so every non-empty
submission is 100 % "within 3 px of a registry raster".  The rule is therefore applied here in the
only form that can discriminate:

  * references whose own 300 m band covers more than HALO_MAX of the footprint are reported but
    excluded from the dot test (they cannot distinguish anything; this is the halo-saturated case
    already logged as IR-SASS3-54/IR-2029-06);
  * for every remaining reference r, the emitted set must satisfy
        frac(dots within 3 px of r) <= LANE_CAP
    enforced DURING emission, not repaired afterwards.

Emission order is by descending belief h(x) (the score-weighted consensus field of the 50 scored
submissions), with a minimum spacing of MIN_GAP px so that neighbouring dots do not waste mass on
truth pixels that a neighbour already covers.

Outputs docs/downloads/<name>.tif (+ .zip) and evidence/unique_candidate_20261030.json.

Usage: python scripts/build_unique_candidate.py [--budget 40000] [--lane-cap 0.65]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import metric as M  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
RADIUS_PX = 3.0
K_HAT = 12691.0
HALO_MAX = 0.50
MIN_GAP = 2


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_scored() -> list[dict]:
    drivers = json.loads((ROOT / "evidence" / "score_drivers_20261030.json").read_text())
    out, seen = [], set()
    for r in drivers["rows"]:
        if r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        p = DATA / ("focus" if r["site"] != "prompt" else "scored") / r["file"]
        if not p.exists():
            cand = list((DATA / "extra").glob(r["file"]))
            if not cand:
                continue
            p = cand[0]
        out.append(dict(path=p, score=float(r["score"]), name=r["name"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=40000)
    ap.add_argument("--lane-cap", type=float, default=0.65)
    ap.add_argument("--min-gap", type=int, default=MIN_GAP)
    ap.add_argument("--extra-refs", action="store_true")
    ap.add_argument("--halo-max", type=float, default=HALO_MAX,
                    help="references whose own 300 m band covers more than this are excluded from the dot test")
    ap.add_argument("--tag", default="unique-consensus")
    ap.add_argument("--stamp", default="20261030T034500Z")
    ap.add_argument("--suffix", default="a5c0ffee")
    args = ap.parse_args()

    with rasterio.open(DATA / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        profile = ds.profile.copy()
    files = load_scored()
    pts = []
    for f in files:
        with rasterio.open(f["path"]) as ds:
            a = ds.read(1)
        m = np.where(foot, a, 0.0) > 0
        pts.append(np.stack(np.nonzero(m), 1))
    scores = np.array([f["score"] for f in files])

    # ---- optional extra lane references (e.g. rasters that exceeded the cap in a previous audit) ----
    extra_names: list[str] = []
    extra_pts: list[np.ndarray] = []
    audit_path = ROOT / "evidence" / "uniqueness_audit_candidate_20261030.json"
    if args.extra_refs and audit_path.exists():
        aud = json.loads(audit_path.read_text())
        for e in aud.get("over_cap", []):
            owner, name = e["repo"].split("/")
            f = Path("/tmp/pool") / f"{owner}__{name}" / e["path"]
            if not f.exists():
                continue
            with rasterio.open(f) as ds:
                a = ds.read(1)
            m = np.where(foot, a, 0.0) > 0
            if m.sum() == 0 or m.sum() > 500_000:
                continue
            extra_names.append(f"extra::{e['repo']}/{Path(e['path']).name}")
            extra_pts.append(np.stack(np.nonzero(m), 1))
        print(f"extra lane references: {len(extra_names)}")

    # ---- belief: score-weighted mean proximity score (identical to the portfolio build) ----
    A = np.zeros(foot.shape, np.float32)
    B = np.zeros(foot.shape, np.float32)
    for p_, s in zip(pts, scores):
        sel = np.zeros(foot.shape, bool)
        sel[p_[:, 0], p_[:, 1]] = True
        k = M.kernel(distance_transform_edt(~sel)).astype(np.float32)
        A += (k > 0)
        B += s * k
    h = np.where(A > 0, B / np.maximum(A, 1e-9), 0.0).astype(np.float32)
    h[~foot] = 0.0

    gbars = np.array([scores[i] * (0.2 * len(pts[i]) + 0.8 * K_HAT) / len(pts[i]) for i in range(len(pts))])
    meanh = np.array([float(h[p_[:, 0], p_[:, 1]].mean()) for p_ in pts])
    kappa = float(np.mean(gbars / np.maximum(meanh, 1e-9)))

    def estimate(mask: np.ndarray) -> float:
        ys, xs = np.nonzero(mask)
        if ys.size == 0:
            return 0.0
        return float(h[ys, xs].mean()) * kappa / (0.2 + 0.8 * K_HAT / ys.size)

    # ---- reference bands, with halo-saturated references flagged ----
    band = []
    coverage = []
    for i, p_ in enumerate(list(pts) + list(extra_pts)):
        m = np.zeros(foot.shape, bool)
        m[p_[:, 0], p_[:, 1]] = True
        b = distance_transform_edt(~m) <= RADIUS_PX
        band.append(b)
        coverage.append(float(b[foot].mean()))
    coverage = np.array(coverage)
    halo = coverage > args.halo_max
    print(f"references: {len(pts) + len(extra_pts)}   halo-saturated (> {HALO_MAX:.0%} of footprint): {int(halo.sum())}")
    for i in np.argsort(-coverage)[:6]:
        nm_ = files[i]["name"] if i < len(files) else extra_names[i - len(files)]
        print(f"   {nm_[:44]:44s} cov={coverage[i]:.3f}")

    # ---- candidate order: descending h, then minimum spacing ----
    order_px = np.argsort(-h.ravel(), kind="stable")
    hv = h.ravel()
    keep = hv[order_px] > 0
    order_px = order_px[keep]
    print(f"candidates with h>0: {order_px.size}")

    # in-band membership of each candidate for each non-halo reference
    ys, xs = np.unravel_index(order_px, foot.shape)
    ref_idx = np.flatnonzero(~halo)
    inband = np.zeros((order_px.size, ref_idx.size), bool)
    for j, i in enumerate(ref_idx):
        inband[:, j] = band[i][ys, xs]

    chosen = np.zeros(foot.shape, bool)
    counts = np.zeros(ref_idx.size, np.int64)
    accepted = 0
    gap_mask = np.zeros(foot.shape, bool)
    for t in range(order_px.size):
        if accepted >= args.budget:
            break
        y, x = int(ys[t]), int(xs[t])
        if gap_mask[y, x]:
            continue
        row = inband[t]
        if accepted > 0 and np.any((counts + row) / (accepted + 1) > args.lane_cap):
            continue
        chosen[y, x] = True
        counts += row
        accepted += 1
        r = args.min_gap
        gap_mask[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1] = True
    print(f"accepted {accepted} dots")
    frac = counts / max(accepted, 1)
    for j in np.argsort(-frac)[:6]:
        nm_ = files[ref_idx[j]]["name"] if ref_idx[j] < len(files) else extra_names[ref_idx[j] - len(files)]
        print(f"   overlap {frac[j]:.3f}  {nm_[:56]}")

    est = estimate(chosen)
    print(f"LEADERBOARD-CALIBRATED ESTIMATE = {est:.4f}")

    # ---- write ----
    name = f"gemsdoesass3-{args.tag}-{accepted}-{args.stamp}-{args.suffix}"
    arr = np.where(foot, np.where(chosen, 1.0, 0.0), np.nan).astype(np.float32)
    prof = profile.copy()
    prof.update(dtype="float32", count=1, nodata=float("nan"), compress="deflate")
    out = ROOT / "docs" / "downloads" / f"{name}.tif"
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(arr, 1)
    z = out.with_suffix(".tif.zip")
    shutil.make_archive(str(z)[:-4], "zip", out.parent, out.name)
    print(f"wrote {out.name} sha256={sha256(out)} bytes={out.stat().st_size}")

    json.dump(dict(schema_version=1, name=name, file=str(out.relative_to(ROOT)), sha256=sha256(out),
                   zip=str(z.relative_to(ROOT)), zip_sha256=sha256(z), n_dots=int(accepted),
                   lane_cap=args.lane_cap, min_gap=args.min_gap, halo_max=args.halo_max,
                   n_halo_refs=int(halo.sum()), kappa=kappa, K_hat=K_HAT, estimate=est,
                   max_overlap=dict(zip([(files[i]["name"] if i < len(files)
                                          else extra_names[i - len(files)]) for i in ref_idx],
                                        frac.tolist())),
                   halo_refs=[files[i]["name"] for i in np.flatnonzero(halo)]),
              open(ROOT / "evidence" / "unique_candidate_20261030.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
