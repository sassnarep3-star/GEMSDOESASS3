#!/usr/bin/env python3
"""Measure pixel-pattern descriptors of every scored raster whose leaderboard score is known,
then test which descriptors predict that score (OWNER-REPORT calibration, not a score claim).

What this is
------------
The competition truth is a *private* set of expert-labelled faults that are **not** in the USGS
catalogue (official problem description, page 967).  We therefore cannot compute the scored DTI
locally.  What we can measure is the geometry of each submission: how much mass it emits, how much
of that mass sits near the public catalogue, how much sits near an independent off-catalogue fault
source (SGMC), how redundant the emission is under the 300 m kernel, and so on.

This script computes those descriptors for every raster with a known owner-reported leaderboard
score and writes a table plus rank correlations.  It produces a *calibrated proxy*, never a score
claim.  Every number it writes is labelled either MEASURED (pixels) or OWNER-REPORT (score typed in
the task prompt / recorded in registry/owner_reported_scores_focus.json).

Usage
-----
    python scripts/analyze_score_drivers.py            # writes evidence/score_drivers_20261030.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, label
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32.metric import ALPHA, BETA, EPS, kernel  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
FOCUS = DATA / "focus"
RADIUS_PX = 3.0
OUT = ROOT / "evidence" / "score_drivers_20261030.json"


def read1(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        return ds.read(1)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    foot = np.isfinite(read1(DATA / "sample_submission.tif"))
    lab = read1(DATA / "labels.tif")
    cat = (lab > 0) & foot
    n_cat = int(cat.sum())
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    k_cat = kernel(d_cat)

    sg = read1(DATA / "external" / "derived_sgmc_faults_100m_u8.tif") > 0
    near_cat = kernel(d_cat) > 0  # within 3 px
    sg_off = sg & ~cat & ~near_cat & foot
    n_sg_off = int(sg_off.sum())
    d_sg = distance_transform_edt(~sg_off).astype(np.float32)
    k_sg = kernel(d_sg)
    d_sg_all = distance_transform_edt(~(sg & foot)).astype(np.float32)

    # catalogue distance histogram edges (px) for emission placement
    edges = np.array([0, 1, 2, 3, 4, 6, 10, 20, 50, 1e9], dtype=np.float32)

    # gather files with known scores
    reg = json.loads((ROOT / "registry" / "owner_reported_scores_focus.json").read_text())
    entries = []
    for e in reg["entries"]:
        p = FOCUS / Path(e["file"]).name
        if p.exists():
            entries.append(dict(site=e["site"], name=e["prompt_name"], path=p,
                                score=float(e["owner_reported_score"]), source="OWNER-REPORT/focus-registry"))
    # the rasters restored from the owner's own mirror, with scores typed in the task prompt
    prompt_scores = {
        "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif": 0.1922,
        "gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif": 0.1894,
        "gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif": 0.1855,
        "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif": 0.2477,
        "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif": 0.2600,
        "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif": 0.0904,
        "8GEMSDOE_Hedge-v2_submission.tif": 0.1563,
        "gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif": 0.1280,
        "gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif": 0.1839,
        "gemsdoe-ens12-adopted-7f00890a.tif": 0.1563,
        "gemsdoe9-PLACEHOLDER-2314b599.tif": 0.0107,
        "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif": 0.2449,
        "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif": 0.2600,
        "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif": 0.2708,
    }
    extra = DATA / "extra"
    man = extra / "manifest.json"
    if man.exists():
        for e in json.loads(man.read_text()):
            if e.get("status") == "ok" and (extra / e["file"]).exists():
                entries.append(dict(site=e["repo"].split("/")[-1], name=Path(e["file"]).stem,
                                    path=extra / e["file"], score=float(e["score"]),
                                    source="OWNER-REPORT/prompt-extra"))
    for fn, sc in prompt_scores.items():
        p = DATA / "scored" / fn
        if p.exists():
            entries.append(dict(site="prompt", name=fn.replace(".tif", ""), path=p, score=sc,
                                source="OWNER-REPORT/prompt"))

    rows = []
    seen = {}
    for e in entries:
        a = read1(e["path"]).astype(np.float32)
        a = np.where(foot, a, np.nan)
        mass = np.nan_to_num(a, nan=0.0)
        S = float(mass.sum())
        pos = mass > 0
        npos = int(pos.sum())
        h = sha256(e["path"])
        if npos == 0:
            continue
        vals = mass[pos]
        binary = bool(np.allclose(vals, 1.0))
        # catalogue geometry
        fp_cat = float((mass * (1.0 - k_cat)).sum())
        tp_cat = float((k_cat * np.where(pos, mass, 0.0)).sum())  # credit proxy (max over pred)
        # exact catalogue TP via EDT on the binary positive set (needs no truth)
        dp = distance_transform_edt(~pos)
        tp_cat_exact = float(kernel(dp[cat]).sum()) if cat.any() else 0.0
        dti_cat = tp_cat_exact / (tp_cat_exact + ALPHA * fp_cat + BETA * (n_cat - tp_cat_exact) + EPS)
        # off-catalogue SGMC geometry
        sg_credit = float((mass * k_sg).sum())
        sg_credit_per_mass = sg_credit / S
        sg_all_credit_per_mass = float((mass * kernel(d_sg_all)).sum()) / S
        # emission spacing / redundancy
        red = np.zeros_like(mass)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                red += np.roll(np.roll(mass, dy, 0), dx, 1)
        redundancy_frac = float((red[pos] > 0).mean())
        # distance-to-catalogue profile of the positive cells
        dc = d_cat[pos]
        hist = np.histogram(dc, bins=edges)[0].astype(float) / max(npos, 1)
        # connected components of the positive set (segment count)
        ncomp = int(label(pos, structure=np.ones((3, 3), int))[1])
        rows.append(dict(
            site=e["site"], name=e["name"], file=e["path"].name, sha256=h, score=e["score"],
            score_source=e["source"], bytes=e["path"].stat().st_size,
            S=S, n_positive=npos, binary=binary,
            dti_catalogue_proxy=float(dti_cat),
            fp_catalogue_mass=fp_cat, offcat_mass_fraction=1.0 - (tp_cat_exact / S if S else 0.0),
            cat_frac_within_3px=float((dc <= 3).mean()),
            cat_frac_beyond_10px=float((dc > 10).mean()),
            cat_frac_beyond_20px=float((dc > 20).mean()),
            sgmc_offcat_credit_per_mass=sg_credit_per_mass,
            sgmc_all_credit_per_mass=sg_all_credit_per_mass,
            redundancy_fraction_8nn=redundancy_frac,
            n_components=ncomp,
            mass_per_component=S / max(ncomp, 1),
            cat_dist_hist_frac=hist.tolist(),
        ))
        seen[h] = seen.get(h, 0) + 1

    json.dump(dict(
        schema_version=1,
        generated_utc="2026-10-30",
        note=("MEASURED pixel descriptors of scored rasters joined to OWNER-REPORTED leaderboard "
              "scores. No number here is an organizer score. dti_catalogue_proxy is a local proxy "
              "against the PUBLIC catalogue, which is NOT the scored truth (official page 967)."),
        n_catalogue_px=n_cat, n_sgmc_offcat_px=n_sg_off,
        duplicate_sha_counts={k: v for k, v in seen.items() if v > 1},
        rows=rows,
    ), open(OUT, "w"), indent=1)

    # rank correlations on de-duplicated rows
    uniq, hashes = [], set()
    for r in rows:
        if r["sha256"] in hashes:
            continue
        hashes.add(r["sha256"])
        uniq.append(r)
    keys = ["S", "n_positive", "dti_catalogue_proxy", "cat_frac_within_3px", "cat_frac_beyond_10px",
            "cat_frac_beyond_20px", "sgmc_offcat_credit_per_mass", "sgmc_all_credit_per_mass",
            "redundancy_fraction_8nn", "n_components", "mass_per_component"]
    print(f"rows={len(rows)} unique={len(uniq)}")
    print(f"{'descriptor':34s} {'spearman':>9s} {'p':>8s}")
    out_corr = {}
    y = np.array([r["score"] for r in uniq])
    for k in keys:
        x = np.array([r[k] for r in uniq], float)
        rho, p = spearmanr(x, y)
        out_corr[k] = dict(rho=float(rho), p=float(p), n=len(uniq))
        print(f"{k:34s} {rho:9.3f} {p:8.4f}")
    d = json.load(open(OUT))
    d["spearman_vs_owner_score"] = out_corr
    d["n_unique"] = len(uniq)
    json.dump(d, open(OUT, "w"), indent=1)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
