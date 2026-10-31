#!/usr/bin/env python3
"""Build the per-site table for the executive summary.

For every published raster that carries an owner-reported score (n = 182) this records

* the score the owner typed beside it on their own Pages site — **OWNER-REPORT**; the public
  leaderboard only ever exposes one number per team, and the per-file tables are not
  organizer-signed, so no value in this table can be re-verified against DrivenData;
* this project's **ESTIMATE** of that same score, from the leave-one-family-out model fitted in
  ``evidence/truth_field_20261031.json`` (Pearson r = 0.911, RMSE = 0.0376 over 182 files);
* the dot count, the share of prediction mass within 300 m of a catalogued fault, and the
  enrichment ε implied at N = 12 000;
* the worst 3-px overlap against any scored raster published on a **different** site — the
  standing prompt's "a unique submission unlike any of the other GEMSDOE sites" test;
* the worst 3-px overlap against any other scored raster, with the reference's footprint
  coverage and the resulting lift.

Reference set = the 182 scored rasters (exactly the set whose scores we know).  The full
registry of 1 987 rasters is not used here because most of it has no score attached and because
it contains dense "surface" rasters that cover the whole footprint and therefore overlap
everything at 1.00 — the defect recorded in ``docs/research/lane-decision-20261030.md``.

Output: docs/data/focus_site_table_20261031.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import corpus as CP  # noqa: E402
from gems32.corpus import H, W  # noqa: E402

OUT = ROOT / "docs" / "data" / "focus_site_table_20261031.json"
FOCUS = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
NVALID = None

_DY, _DX = np.meshgrid(np.arange(-3, 4), np.arange(-3, 4), indexing="ij")
_K = (_DY ** 2 + _DX ** 2) <= 9
_OFF = np.stack([_DY[_K], _DX[_K]], 1)


def site_of(pool_file: str) -> str:
    return pool_file.split("__", 1)[0]


def dilate_bitset(idx: np.ndarray) -> np.ndarray:
    """Packed bitmask of the 3-px (300 m) dilation of a dot set."""
    y, x = idx // W, idx % W
    yy = np.clip(y[:, None] + _OFF[None, :, 0], 0, H - 1)
    xx = np.clip(x[:, None] + _OFF[None, :, 1], 0, W - 1)
    flat = np.unique((yy * W + xx).ravel())
    b = np.zeros(H * W, bool)
    b[flat] = True
    return np.packbits(b)


def frac_in(packed: np.ndarray, idx: np.ndarray) -> float:
    return float(((packed[idx >> 3] >> (idx & 7)) & 1).sum()) / max(idx.size, 1)


def main() -> int:
    global NVALID
    valid, cat = CP.load_grid()
    NVALID = int(valid.sum())
    rows = CP.load_scored(valid)
    CP.footprint_mean_credit(rows, valid)
    CP.attach_f0(rows, cat)

    tf = json.loads((ROOT / "evidence" / "truth_field_20261031.json").read_text())
    cal = tf["lofo"]["calibration"]
    lofo = {r["name"]: r["lofo_predicted"] for r in tf["lofo"]["rows"]}

    n = len(rows)
    print(f"packing {n} dilated bitsets ...", flush=True)
    packs = [dilate_bitset(r["idx"]) for r in rows]
    covs = [min(1.0, int(r["idx"].size) * 29.0 / NVALID) for r in rows]
    COV_CAP = 0.50
    n_shaped = sum(1 for c in covs if c <= COV_CAP)
    print(f"submission-shaped references (coverage <= {COV_CAP}): {n_shaped}/{n}", flush=True)

    entries = []
    for i, r in enumerate(rows):
        site = site_of(r["name"])
        idx = r["idx"]
        nd = int(idx.size)
        worst_x, worst_x_file, worst_x_cov = 0.0, "", 0.0
        worst_a, worst_a_file, worst_a_cov, worst_a_lift = 0.0, "", 0.0, 0.0
        for j in range(n):
            if j == i or covs[j] > COV_CAP:
                continue
            f = frac_in(packs[j], idx)
            if site_of(rows[j]["name"]) != site and f > worst_x:
                worst_x, worst_x_file, worst_x_cov = f, rows[j]["name"], covs[j]
            if f > worst_a:
                worst_a, worst_a_file = f, rows[j]["name"]
                worst_a_cov, worst_a_lift = covs[j], f / max(covs[j], 1e-9)
        pred = lofo.get(r["name"])
        A = r["score"] * (0.2 * r["D"] + 0.8 * 12000.0)
        entries.append({
            "site": site, "file": r["name"],
            "owner_reported_score": r["score"],
            "estimate": (float(cal["intercept"] + cal["slope"] * pred) if pred is not None else None),
            "n_dots": nd, "mass": r["D"],
            "f0_within_300m_of_catalogue": r["f0"],
            "mean_no_skill_credit": r["mc"],
            "implied_credit_A": A,
            "enrichment_eps": A / (12000.0 * r["mc"]),
            "footprint_coverage": min(1.0, nd * 29.0 / NVALID),
            "worst_3px_overlap_other_site": worst_x,
            "worst_3px_overlap_other_site_file": worst_x_file,
            "worst_3px_overlap_other_site_ref_coverage": worst_x_cov,
            "worst_3px_overlap_other_site_lift": worst_x / max(worst_x_cov, 1e-9),
            "worst_3px_overlap_scored": worst_a,
            "worst_3px_overlap_scored_file": worst_a_file,
            "worst_3px_overlap_scored_ref_coverage": worst_a_cov,
            "worst_3px_overlap_scored_lift": worst_a_lift,
        })
        print(f"{site:11s} {r['score']:.4f} est={entries[-1]['estimate']:.4f} dots={nd:7d} "
              f"x-site={worst_x:.3f} scored={worst_a:.3f} lift={worst_a_lift:5.2f} "
              f"{r['name'][9:52]}", flush=True)

    by_site: dict[str, list] = {}
    for e in entries:
        by_site.setdefault(e["site"], []).append(e)
    for s in by_site:
        by_site[s].sort(key=lambda e: -(e["owner_reported_score"] or 0))
    allsites = sorted(by_site, key=lambda s: -max(e["owner_reported_score"] or 0 for e in by_site[s]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reference_set": (f"the 182 published rasters that carry an owner-reported score; self "
                          f"excluded, and references covering more than 50% of the footprint "
                          f"excluded as degenerate (see docs/research/uniqueness-criterion-20261031.md). "
                          f"{n_shaped} of {n} references qualify."),
        "score_label": ("OWNER-REPORT — typed by the owner on the sibling Pages sites. Not "
                        "organizer-confirmed: no per-file value is re-verifiable against "
                        "DrivenData."),
        "estimate_label": (f"ESTIMATE — leave-one-family-out model, Pearson r="
                           f"{tf['lofo']['pearson_r']:.3f}, RMSE={tf['lofo']['rmse']:.4f} over "
                           f"{tf['lofo']['n']} files. Not a leaderboard score."),
        "calibration": cal,
        "focus_sites": FOCUS,
        "per_site_best": {s: (by_site[s][0] if s in by_site else None) for s in FOCUS},
        "all_sites_ranked": [
            {"site": s,
             "best_score": max(e["owner_reported_score"] or 0 for e in by_site[s]),
             "best_file": by_site[s][0]["file"],
             "best_estimate": by_site[s][0]["estimate"],
             "worst_3px_overlap_other_site": by_site[s][0]["worst_3px_overlap_other_site"],
             "n_files": len(by_site[s])} for s in allsites],
        "entries": entries,
    }, indent=1))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
