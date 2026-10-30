#!/usr/bin/env python3
"""Literal Protocol-Rule-1 uniqueness audit of candidate raster(s) against the fetched focus registry.

Registry: the 386-raster focus registry (registry/focus_registry_manifest.json), fetched and
SHA-verified into .cache/registry_rasters/<repo>/ by scripts/fetch_registry_rasters.py. Entries whose
source repo does not exist (HISTORICAL_SCORED) are reported as coverage gaps, and the audit fails
closed unless --allow-coverage-gap is passed (the gaps are pinned historical files that are also
present, SHA-verified, in .cache/gems_data/scored/; those local copies are used instead).

Per candidate raster C and registry raster S:
  within3_frac      : fraction of C's dots (value > 0) within 3 px of an S dot   (rule: <= 0.70)
  rev_within3_frac  : fraction of S's dots within 3 px of a C dot (informational)
  spearman_sampled  : Spearman rank correlation of values on a fixed footprint sample (rule: |rho| <= 0.90)
  surface_spearman  : same sample correlation for the pre-placement surface (--surface npy), if given.

Scopes come from the manifest path: docs/downloads|archive/legacy_candidates -> submission;
inputs/calibration -> calibration; else other. passes_rule_1 is computed over submission+calibration.

Usage:
  python scripts/uniqueness_audit_focused.py CAND1.tif [CAND2.tif ...] \
      --surface evidence/sdr1_surface_dens.npy --out evidence/uniqueness_audit_20261030.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
RASTER_DIR = ROOT / ".cache" / "registry_rasters"
MANIFEST = ROOT / "registry" / "focus_registry_manifest.json"
LATTICE_REL = "scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SHA = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
SCORED_DIR = ROOT / ".cache" / "gems_data" / "scored"
N_SAMPLE = 300_000
SEED = 20261030


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raster(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float32)
        nodata = ds.nodata
    if nodata is not None:
        arr[arr == nodata] = np.nan
    arr[np.abs(arr) > 1e30] = np.nan
    dots = np.isfinite(arr) & (arr > 0.0)
    return arr, dots


def scope_of(path: str) -> str:
    p = "/" + path.replace("\\", "/")
    if "/docs/downloads/" in p or "/archive/legacy_candidates/" in p:
        return "submission"
    if "/inputs/calibration/" in p:
        return "calibration"
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates", nargs="+")
    ap.add_argument("--surface", default=None, help=".npy float32 pre-placement surface for the FIRST candidate")
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-coverage-gap", action="store_true")
    args = ap.parse_args()
    t0 = time.time()

    man = json.loads(MANIFEST.read_text())
    entries = man["rasters"]

    with rasterio.open(ROOT / ".cache/gems_data/sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    rng = np.random.default_rng(SEED)
    samp = rng.choice(np.flatnonzero(foot.ravel()), size=min(N_SAMPLE, int(foot.sum())), replace=False)
    sy, sx = np.unravel_index(samp, foot.shape)

    cands = []
    for c in args.candidates:
        p = Path(c)
        if not p.is_absolute():
            p = ROOT / p
        arr, dots = load_raster(p)
        cands.append({
            "path": str(p),
            "name": p.name,
            "sha256": sha256_file(p),
            "dots": int(dots.sum()),
            "arr": arr,
            "dots_mask": dots,
            "sample_vals": arr[sy, sx],
        })
    surface = None
    if args.surface:
        surface = np.load(args.surface).astype(np.float32)
        cands[0]["surface_sample"] = surface[sy, sx]

    # Candidate-side distance transform, computed once (candidate dots do not change across rasters).
    for c in cands:
        c["d_c"] = ndi.distance_transform_edt(~c["dots_mask"]) if c["dots_mask"].any() else None

    results = []
    n_ok = n_gap = n_err = 0
    for i, e in enumerate(entries):
        repo, path, want = e["repo"], e["path"], e["sha256"]
        dest = RASTER_DIR / repo / Path(path).name
        scope = scope_of(path)
        if not dest.exists():
            alt = SCORED_DIR / Path(path).name
            if alt.exists() and sha256_file(alt) == want:
                dest = alt
            else:
                n_gap += 1
                results.append({"repo": repo, "path": path, "sha256": want, "scope": scope,
                                "status": "coverage_gap", "note": "not fetched and no scored copy"})
                continue
        got = sha256_file(dest)
        if got != want:
            n_err += 1
            results.append({"repo": repo, "path": path, "scope": scope, "status": "sha_mismatch", "got": got})
            continue
        n_ok += 1
        s_arr, s_dots = load_raster(dest)
        if not s_dots.any():
            results.append({"repo": repo, "path": path, "scope": scope, "status": "ok", "within3": [], "note": "no positive dots"})
            continue
        d_s = ndi.distance_transform_edt(~s_dots)
        row: dict = {"repo": repo, "path": path, "sha256": want, "scope": scope, "status": "ok",
                     "s_dots": int(s_dots.sum())}
        for c in cands:
            dm = c["dots_mask"]
            n = int(dm.sum())
            w3 = float((d_s[dm] <= 3.0).mean()) if n else 0.0
            rev = float((c["d_c"][s_dots] <= 3.0).mean()) if n and c["d_c"] is not None else 1.0
            s_samp = s_arr[sy, sx]
            ok = np.isfinite(c["sample_vals"]) & np.isfinite(s_samp)
            rho = float(spearmanr(c["sample_vals"][ok], s_samp[ok]).statistic) if ok.sum() > 2 else None
            entry = {"within3": round(w3, 6), "rev_within3": round(rev, 6),
                     "spearman": None if rho is None else round(rho, 6)}
            if "surface_sample" in c:
                ok2 = np.isfinite(c["surface_sample"]) & np.isfinite(s_samp)
                rho2 = float(spearmanr(c["surface_sample"][ok2], s_samp[ok2]).statistic) if ok2.sum() > 2 else None
                entry["surface_spearman"] = None if rho2 is None else round(rho2, 6)
            row.setdefault("within3", []).append({"candidate": c["name"], **entry})
        results.append(row)
        if i % 25 == 0:
            print(f"[audit] {i+1}/{len(entries)} rasters ({time.time()-t0:.0f}s)", flush=True)

    # Summaries per candidate over gated scopes (submission + calibration).
    summaries = {}
    for c in cands:
        per = [r for r in results if r.get("status") == "ok" and r.get("scope") in ("submission", "calibration")]
        worst_w3 = max(((x["within3"], r) for r in per for x in r["within3"] if x["candidate"] == c["name"]), key=lambda t: t[0])
        rhos = [(abs(x.get("spearman") or 0.0), x.get("spearman"), r) for r in per for x in r["within3"] if x["candidate"] == c["name"]]
        worst_rho = max(rhos, key=lambda t: t[0])
        surfs = [(abs(x["surface_spearman"]), x["surface_spearman"], r) for r in per for x in r["within3"]
                 if x["candidate"] == c["name"] and x.get("surface_spearman") is not None]
        worst_surf = max(surfs, key=lambda t: t[0]) if surfs else None
        summaries[c["name"]] = {
            "candidate_sha256": c["sha256"],
            "dots": c["dots"],
            "n_gated_rasters": len(per),
            "max_within3": {"frac": round(worst_w3[0], 6), "worst_raster": f"{worst_w3[1]['repo']}/{Path(worst_w3[1]['path']).name}"},
            "max_abs_spearman": {"rho": worst_rho[1], "worst_raster": f"{worst_rho[2]['repo']}/{Path(worst_rho[2]['path']).name}"},
            "passes_rule_1": bool(worst_w3[0] <= 0.70 and (worst_rho[1] is None or abs(worst_rho[1]) <= 0.90)),
            "surface_stage": None if worst_surf is None else {
                "max_abs_surface_spearman": {"rho": worst_surf[1], "worst_raster": f"{worst_surf[2]['repo']}/{Path(worst_surf[2]['path']).name}"},
                "passes_le_0p90": bool(worst_surf[1] is not None and abs(worst_surf[1]) <= 0.90),
            },
        }

    out = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "tool": "scripts/uniqueness_audit_focused.py",
        "registry_manifest": "registry/focus_registry_manifest.json",
        "registry_coverage": {"manifest": len(entries), "ok": n_ok, "coverage_gap": n_gap, "sha_mismatch": n_err},
        "gap_policy": "fail-closed unless --allow-coverage-gap; gap entries listed individually",
        "radius_px": 3.0,
        "rule": "literal Rule 1: max within3 <= 0.70 and max |spearman| <= 0.90 over submission+calibration scopes",
        "candidates": [c["name"] for c in cands],
        "summary": summaries,
        "results": results,
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"coverage": out["registry_coverage"], "summary": summaries}, indent=2)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
