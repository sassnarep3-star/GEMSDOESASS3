#!/usr/bin/env python3
"""Per-site best candidate and cross-site uniqueness (Review 2026-10-28).

For each of the 9 focus sites:
  1. candidate = the registry raster with the highest SGMC-CAL proxy among rasters whose
     dot count lies in the calibrated band [36,000 ; 46,000] (the only regime where the
     proxy was validated against public scores). Research-only / DO-NOT-SUBMIT / probe
     files are excluded.
  2. uniqueness = max within-3-px overlap of the candidate's dots against every registry
     raster from a DIFFERENT repo (the lattice raster is reported but excluded from the max,
     because a 206,895-dot lattice makes the metric degenerate).
  3. public score = OWNER-REPORT value from registry/public_scores_listing.json if matched.

Also records the shipped LWST flagship for comparison.
All numbers are PROXY or OWNER-REPORT; none is an ORGANIZER-CONFIRMED score.

Inputs : evidence/registry_sgmc_rank_20261028.json, evidence/proxy_validation_20261028.json
         registry cache under GEMS_WORK_DIR/registry_rasters (SHA-verified by validate_proxies.py)
Output : evidence/site_best_uniqueness_20261028.json
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
BAND = (36_000, 46_000)
EXCLUDE_TOKENS = ("RESEARCH-NOT-SUBMISSION", "DO-NOT-SUBMIT", "probe", "PLACEHOLDER", "FORMAT_TEST")
LATTICE = "lattice"
R_PX = 3.0
UNIQUE_MAX = 0.70


def work_dir() -> Path:
    return Path(os.environ.get("GEMS_WORK_DIR", ROOT / ".cache/gems_work"))


def main() -> int:
    rank = json.loads((ROOT / "evidence/registry_sgmc_rank_20261028.json").read_text())
    cal = json.loads((ROOT / "evidence/proxy_validation_20261028.json").read_text())
    public_by_file = {}
    for r in cal.get("rows", []):
        if r.get("match_status") == "MATCHED" and r.get("public_score") is not None:
            public_by_file[r["matched_file"]] = r["public_score"]

    rows = rank["rows"]
    cache = work_dir() / "registry_rasters"
    path_of = {}
    for r in rows:
        cand = list(cache.rglob(r["file"]))
        if not cand:
            raise SystemExit(f"missing cached raster: {r['file']}")
        path_of[r["file"]] = cand[0]

    def load_dots(f: str) -> np.ndarray:
        with rasterio.open(path_of[f]) as ds:
            return ds.read(1) > 0.0

    # 1) choose one candidate per site (proxy inside the calibrated band)
    chosen: dict[str, dict] = {}
    for site in SITES:
        pool = [r for r in rows if r["repo"] == site
                and BAND[0] <= r["n_dots"] <= BAND[1]
                and not any(t.lower() in r["file"].lower() for t in EXCLUDE_TOKENS)]
        if pool:
            chosen[site] = max(pool, key=lambda r: r["sgmc_cal_dti"])
    cand_dots = {site: load_dots(r["file"]) for site, r in chosen.items()}
    cand_n = {site: int(cand_dots[site].sum()) for site in chosen}

    # 2) one streaming pass over the registry: dist of each OTHER raster, scored vs each candidate
    best_ov: dict[str, tuple[float, dict | None]] = {site: (-1.0, None) for site in chosen}
    lattice_ov: dict[str, float | None] = {site: None for site in chosen}
    for o in rows:
        dist_o = distance_transform_edt(~load_dots(o["file"]))
        for site, r in chosen.items():
            if o["repo"] == site:
                continue
            c = cand_dots[site]
            ov = float((dist_o[c] <= R_PX).sum() / max(cand_n[site], 1))
            if LATTICE in o["file"]:
                lattice_ov[site] = ov if lattice_ov[site] is None else max(lattice_ov[site], ov)
                continue
            if ov > best_ov[site][0]:
                best_ov[site] = (ov, o)
        del dist_o

    out_sites: dict[str, dict] = {}
    for site in SITES:
        if site not in chosen:
            out_sites[site] = {"status": "NO_CANDIDATE_IN_CALIBRATED_BAND"}
            continue
        best = chosen[site]
        cf = best["file"]
        max_ov, max_o = best_ov[site]
        out_sites[site] = {
            "candidate_file": cf,
            "candidate_sha256": best["sha256"],
            "candidate_n_dots": best["n_dots"],
            "sgmc_cal_proxy_PROJECTION_NOT_A_SCORE": round(best["sgmc_cal_dti"], 6),
            "public_score_OWNER_REPORT": public_by_file.get(cf),
            "max_within3px_overlap_vs_other_sites": round(max_ov, 4),
            "max_overlap_partner": {"repo": max_o["repo"], "file": max_o["file"]},
            "unique_vs_other_gemsdoe_sites_le_70pct": bool(max_ov <= UNIQUE_MAX),
            "lattice_overlap_reported_not_in_max": None if lattice_ov[site] is None else round(lattice_ov[site], 4),
            "pool_size_in_band": sum(1 for r in rows if r["repo"] == site and BAND[0] <= r["n_dots"] <= BAND[1]),
        }
        print(site, "->", cf[:60], f"ov={max_ov:.4f}", "unique" if max_ov <= UNIQUE_MAX else "NOT unique", flush=True)

    result = {
        "schema_version": 1,
        "date_utc": "2026-10-28",
        "band_n_dots": list(BAND),
        "excluded_name_tokens": list(EXCLUDE_TOKENS),
        "uniqueness_threshold": UNIQUE_MAX,
        "radius_px": R_PX,
        "caveats": [
            "SGMC-CAL is a PROXY validated only on 27 owner-reported public scores in the 11k-174k dot range (median 41,865).",
            "Within-3px overlap is directional (candidate dots -> other raster dots).",
            "Candidate chosen by the proxy inside the calibrated band; a different proxy would change the pick.",
        ],
        "sites": out_sites,
        "n_registry_rasters_compared": len(rows),
    }
    (ROOT / "evidence/site_best_uniqueness_20261028.json").write_text(json.dumps(result, indent=2) + "\n")
    print("wrote evidence/site_best_uniqueness_20261028.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
