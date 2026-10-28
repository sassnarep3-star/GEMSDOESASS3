#!/usr/bin/env python3
"""Validate the HOLDOUT-DTI proxies against public scores, then rank every registry raster.

Protocol Rule 2 (reuse, don't rebuild): every number here comes from the shared evaluator
`src/gems32/holdout.py` (no private fork). This script only (a) fetches registry rasters,
(b) verifies each SHA-256 against the registry, (c) runs the evaluator, and (d) writes receipts.

Outputs
  evidence/proxy_validation_20261028.json   calibration of each proxy vs public scores (OWNER-REPORT labels)
  evidence/registry_sgmc_rank_20261028.json  SGMC-CAL-v3.0 for every registry raster + per-site best

Requires GEMS_DATA_DIR with the restored competition inputs (scripts/restore_data.py).
Registry rasters are cached under GEMS_WORK_DIR/registry_rasters (default .cache/gems_work).

Usage:  python scripts/validate_proxies.py [--skip-fetch] [--max N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree
from scipy.stats import kendalltau, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir, work_dir  # noqa: E402

SHIPPED_REL = "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"
CHAMPION_TOKEN = "e5eb6e7e"
OVERLAP_PX = 3.0


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_registry_raster(repo: str, path: str, want_sha: str, cache: Path) -> Path:
    dest = cache / repo / Path(path).name
    if dest.exists() and sha256_file(dest) == want_sha:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    with tmp.open("wb") as f:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/{path}", "-H", "Accept: application/vnd.github.raw"],
            stdout=f, check=True,
        )
    got = sha256_file(tmp)
    if got != want_sha:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"SHA mismatch for {repo}:{path}: {got} != {want_sha}")
    tmp.replace(dest)
    return dest


def locate_rasters(skip_fetch: bool) -> list[dict]:
    """Return one record per valid registry raster with a local path verified by SHA-256."""
    focus = json.loads((ROOT / "registry/focus_registry_manifest.json").read_text())
    dm = json.loads((ROOT / "registry/data_manifest.json").read_text())
    scored_by_name = {Path(e["dest"]).name: e for e in dm["files"] if e.get("group") == "scored"}
    cache = work_dir() / "registry_rasters"
    recs = []
    for r in focus["rasters"]:
        if r["repo"] == "HISTORICAL_SCORED":
            name = Path(r["path"]).name
            entry = scored_by_name.get(name)
            if entry is None:
                recs.append({"repo": r["repo"], "file": name, "status": "NO_LOCAL_FILE"})
                continue
            local = data_dir() / entry["dest"]
            if not local.exists() or sha256_file(local) != entry["sha256"]:
                recs.append({"repo": r["repo"], "file": name, "status": "HISTORICAL_LOCAL_SHA_MISMATCH"})
                continue
            recs.append({"repo": r["repo"], "file": name, "path": str(local), "sha256": entry["sha256"], "status": "OK"})
            continue
        if skip_fetch:
            local = cache / r["repo"] / Path(r["path"]).name
            if not local.exists() or sha256_file(local) != r["sha256"]:
                recs.append({"repo": r["repo"], "file": Path(r["path"]).name, "status": "NOT_CACHED"})
                continue
        else:
            local = fetch_registry_raster(r["repo"], r["path"], r["sha256"], cache)
        recs.append({"repo": r["repo"], "file": Path(r["path"]).name, "path": str(local),
                     "sha256": r["sha256"], "status": "OK"})
    # Scored rasters known only to the data manifest (e.g. GEMSDOE19 h19-5) — add once, de-duplicated by SHA-256.
    seen = {r.get("sha256") for r in recs if r.get("status") == "OK"}
    for e in dm["files"]:
        if e.get("group") != "scored" or not e["dest"].endswith(".tif"):
            continue
        if e["sha256"] in seen:
            continue
        local = data_dir() / e["dest"]
        if not local.exists() or sha256_file(local) != e["sha256"]:
            recs.append({"repo": e.get("repo"), "file": Path(e["dest"]).name, "status": "MANIFEST_LOCAL_SHA_MISMATCH"})
            continue
        seen.add(e["sha256"])
        recs.append({"repo": "DATA_MANIFEST_SCORED", "file": Path(e["dest"]).name, "path": str(local),
                     "sha256": e["sha256"], "status": "OK"})
    return recs


def load_binary(path: str) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-fetch", action="store_true", help="use cached rasters only (no network)")
    ap.add_argument("--max", type=int, default=None, help="limit number of rasters (debug)")
    args = ap.parse_args()

    ctx = holdout.load_holdout_context(data_dir())
    recs = locate_rasters(args.skip_fetch)
    ok_all = [r for r in recs if r["status"] == "OK"]
    ok = ok_all[: args.max] if args.max else ok_all

    ship_mask = load_binary(str(ROOT / SHIPPED_REL))
    ship_dots = np.column_stack(np.nonzero(ship_mask)).astype(float)
    champ_rec = next(r for r in ok_all if CHAMPION_TOKEN in r["file"] and r["repo"] == "GEMSDOE32" and "zeros" in r["file"])
    champ_mask = load_binary(champ_rec["path"])
    champ_dots = np.column_stack(np.nonzero(champ_mask)).astype(float)

    def overlap(a_dots: np.ndarray, b_tree: cKDTree) -> float:
        if len(a_dots) == 0:
            return float("nan")
        d, _ = b_tree.query(a_dots, k=1)
        return float((d <= OVERLAP_PX).mean())

    ship_tree = cKDTree(ship_dots)
    champ_tree = cKDTree(champ_dots)

    # ---- (1) SGMC-CAL for every registry raster, plus overlap with shipped & champion ----
    rank_rows = []
    for i, r in enumerate(ok):
        mask = load_binary(r["path"]) & ctx.foot
        sg = holdout.evaluate_sgmc_with_ci(mask, ctx, name=Path(r["file"]).stem)
        dots = np.column_stack(np.nonzero(mask)).astype(float)
        rank_rows.append({
            "repo": r["repo"], "file": r["file"], "sha256": r["sha256"], "n_dots": int(mask.sum()),
            "sgmc_cal_dti": float(sg["sgmc_prevalence_calibrated_dti"]),
            "sgmc_cal_ci95": [float(x) for x in sg["sgmc_calibrated_ci95"]],
            "overlap_shipped_frac": overlap(dots, ship_tree),
            "overlap_champion_frac": overlap(dots, champ_tree),
            "shipped_dots_within_3px_of_this": float((cKDTree(dots).query(ship_dots, k=1)[0] <= OVERLAP_PX).mean()) if len(dots) else float("nan"),
        })
        if (i + 1) % 50 == 0:
            print(f"[rank] {i + 1}/{len(ok)}", flush=True)

    # ---- (2) calibration of proxies vs public scores ----
    listing = json.loads((ROOT / "registry/public_scores_listing.json").read_text())
    cal_rows = []
    for row in listing["rows"]:
        match = [r for r in ok if row["token"] in r["file"]]
        if row.get("file_hint"):
            match = [r for r in match if row["file_hint"] in r["file"]] or match
        match = [r for r in match if r["repo"] == row["site"]] or match
        if not match:
            cal_rows.append({**row, "match_status": "NO_LOCAL_FILE"})
            continue
        m = match[0]
        mask = load_binary(m["path"]) & ctx.foot
        hr = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=2.0, name=Path(m["file"]).stem)
        sg = holdout.evaluate_sgmc_with_ci(mask, ctx, name=Path(m["file"]).stem)
        cal_rows.append({**row, "match_status": "MATCHED", "matched_file": m["file"],
                         "static_hide_recover_dti": float(hr["pooled_dti"]),
                         "sgmc_cal_dti": float(sg["sgmc_prevalence_calibrated_dti"])})
    matched = [r for r in cal_rows if r.get("match_status") == "MATCHED"]
    pub = np.array([r["public_score"] for r in matched])
    hr_v = np.array([r["static_hide_recover_dti"] for r in matched])
    sg_v = np.array([r["sgmc_cal_dti"] for r in matched])
    top = pub >= 0.20
    rng = np.random.default_rng(20261028)
    boot_hr, boot_sg = [], []
    for _ in range(2000):
        idx = rng.integers(0, len(matched), len(matched))
        if len(set(pub[idx])) > 1:
            boot_hr.append(spearmanr(pub[idx], hr_v[idx]).correlation)
            boot_sg.append(spearmanr(pub[idx], sg_v[idx]).correlation)
    if len(matched) >= 3:
        slope, intercept = np.polyfit(sg_v, pub, 1)
        resid_sd = float(np.std(pub - (intercept + slope * sg_v), ddof=2))
    else:
        slope = intercept = resid_sd = float("nan")
    calibration = {
        "n_matched": len(matched),
        "n_listing_rows": len(listing["rows"]),
        "spearman_public_vs_static_hide_recover": float(spearmanr(pub, hr_v).correlation),
        "spearman_public_vs_static_hide_recover_ci95": [float(np.nanpercentile(boot_hr, 2.5)), float(np.nanpercentile(boot_hr, 97.5))],
        "spearman_public_vs_sgmc_cal": float(spearmanr(pub, sg_v).correlation),
        "spearman_public_vs_sgmc_cal_ci95": [float(np.nanpercentile(boot_sg, 2.5)), float(np.nanpercentile(boot_sg, 97.5))],
        "kendall_public_vs_sgmc_cal": float(kendalltau(pub, sg_v).correlation),
        "within_top_cluster_n": int(top.sum()),
        "within_top_cluster_spearman_sgmc_cal": float(spearmanr(pub[top], sg_v[top]).correlation) if top.sum() > 2 else None,
        "within_top_cluster_spearman_static_hide_recover": float(spearmanr(pub[top], hr_v[top]).correlation) if top.sum() > 2 else None,
        "linear_map_public_on_sgmc_cal": {"slope": float(slope), "intercept": float(intercept), "residual_sd": resid_sd,
                                          "label": "PROJECTION ONLY - never a score"},
    }

    shipped_sg = holdout.evaluate_sgmc_with_ci(ship_mask & ctx.foot, ctx, name="shipped")
    out_cal = {
        "schema_version": 1,
        "label": "CALIBRATION of HOLDOUT-DTI proxies vs OWNER-REPORT public scores (not organizer receipts)",
        "evaluator": "src/gems32/holdout.py: evaluate_sgmc_with_ci (GEMSDOE32-SGMC-CAL-v3.0) and evaluate_hide_and_recover (GEMSDOE32-HIDE-RECOVER-v3.0, B-visible=2px), static masks",
        "calibration": calibration,
        "rows": cal_rows,
    }
    (ROOT / "evidence/proxy_validation_20261028.json").write_text(json.dumps(out_cal, indent=2) + "\n")

    # ---- (3) registry ranking by the validated proxy ----
    rank_rows.sort(key=lambda x: -x["sgmc_cal_dti"])
    per_site = {}
    for row in rank_rows:
        per_site.setdefault(row["repo"], row)  # first = best SGMC-CAL for that site
    out_rank = {
        "schema_version": 1,
        "label": "HOLDOUT-DTI (GEMSDOE32-SGMC-CAL-v3.0) for every registry raster; NOT a leaderboard score",
        "n_rasters": len(rank_rows),
        "shipped": {"file": Path(SHIPPED_REL).name, "sgmc_cal_dti": float(shipped_sg["sgmc_prevalence_calibrated_dti"]),
                    "rank_among_registry": 1 + sum(1 for r in rank_rows if r["sgmc_cal_dti"] > float(shipped_sg["sgmc_prevalence_calibrated_dti"]))},
        "best_per_site_by_sgmc_cal": per_site,
        "rows": rank_rows,
        "unfetchable_or_unmatched": [r for r in recs if r["status"] != "OK"],
    }
    (ROOT / "evidence/registry_sgmc_rank_20261028.json").write_text(json.dumps(out_rank, indent=2) + "\n")

    print(json.dumps({k: calibration[k] for k in ["n_matched", "spearman_public_vs_static_hide_recover",
                                                 "spearman_public_vs_sgmc_cal", "within_top_cluster_spearman_sgmc_cal"]}, indent=2))
    print("shipped SGMC-CAL", out_rank["shipped"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
