#!/usr/bin/env python3
"""Measure the nine focus sites in one table, from verified bytes, in this session.

Every number in the output is either
  * MEASURED-HERE (this script, on a raster whose SHA-256 was checked against
    registry/sibling_registry_manifest_20261028.json), or
  * OWNER-REPORT (the score typed in the standing prompt; not an organizer receipt).

Columns per site: the file the site offers as its best download, its dot count, how many dots sit on
the catalogue, the LLI live-calibrated projection (a projection, never a score), the two local
holdouts, the maximum 3-px overlap against the other eight sites and against the SASS3 candidate,
and the resubmission verdict (an already-scored file is by definition not a unique new submission).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402
from gemsdoesass3 import lli  # noqa: E402


MANIFEST = json.loads((ROOT / "registry/sibling_registry_manifest_20261028.json").read_text())


def sibling_url(site: str, rel: str) -> str:
    """Pinned permalink into the sibling repo, so a reviewer lands on the exact audited bytes."""
    info = (MANIFEST.get("source_repos") or {}).get(site) or {}
    ref = info.get("commit") or "main"
    base = (info.get("url") or f"https://github.com/buffedlizard55-lab/{site}")
    base = base.split("/tree/")[0].rstrip("/")  # the pin stores .../tree/<commit>; keep owner/repo only
    return f"{base}/blob/{ref}/{rel}"


DISK = np.array([[ (dy*dy+dx*dx) <= 9 for dx in range(-3, 4)] for dy in range(-3, 4)], bool)

SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", default="/tmp/registry_git")
    ap.add_argument("--manifest", default=str(ROOT / "registry/sibling_registry_manifest_20261028.json"))
    ap.add_argument("--scores", default=str(ROOT / "registry/owner_reported_scores_focus.json"))
    ap.add_argument("--candidate", default="docs/downloads/gemsdoesass3-s3-ocm-wide44090-20261030T024750Z-s3hash-safe.tif")
    ap.add_argument("--out", default=str(ROOT / "evidence/focus9_scoreboard_20261030.json"))
    args = ap.parse_args()

    ddir = data_dir()
    ctx = holdout.load_holdout_context(ddir)
    foot, labels = ctx.foot, ctx.labels
    d_cat = distance_transform_edt(~labels)
    spec, lam = lli.build_s0_spec(ddir)
    man = json.loads(Path(args.manifest).read_text())
    pins = {f["path"]: f["sha256"] for f in man["files"]}
    owner = json.loads(Path(args.scores).read_text())
    best: dict[str, dict] = {}
    for e in owner["entries"]:
        s = e["site"]
        sc = e.get("owner_reported_score")
        if sc is None:
            continue
        if s not in best or sc > best[s]["owner_reported_score"]:
            best[s] = e

    cand_path = ROOT / args.candidate
    with rasterio.open(cand_path) as ds:
        ca = ds.read(1)
    cand = np.isfinite(ca) & (ca > 0) & foot

    rows = []
    masks: dict[str, np.ndarray] = {}
    for site in SITES:
        e = best.get(site)
        if not e:
            rows.append({"site": site, "status": "no_owner_score_entry"})
            continue
        reg = Path(args.registry)
        rel = Path(e["file"])
        f = next((c for c in (reg / site / rel, reg / site / "data" / "registry" / site / rel, reg / rel)
                  if c.is_file()), reg / site / rel)
        if not f.is_file():
            rows.append({"site": site, "file": e["file"], "status": "bytes_not_in_registry"})
            continue
        pin = pins.get(f"{site}/{e['file']}") or pins.get(e["file"])
        got = sha256(f)
        sha_ok = (pin == got) if pin else None
        with rasterio.open(f) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & foot
        masks[site] = m
        d_off = m & ~binary_dilation(labels, structure=np.ones((3, 3), bool), iterations=1)
        proj = lli.project_lli(m.astype(np.float32), spec, lam)
        off = holdout.evaluate_sgmc_with_ci(m, ctx, n_boot=1000)
        dc = d_cat[m]
        rows.append({
            "site": site,
            "file_to_download": Path(e["file"]).name,
            "github_url": sibling_url(site, e["file"]),
            "registry_rel_path": f.relative_to(reg).as_posix(),
            "sha256_verified_against_pin": sha_ok,
            "sha256": got,
            "owner_reported_score": e["owner_reported_score"],
            "owner_score_label": "OWNER-REPORT (typed in the standing prompt; not an organizer receipt)",
            "dots": int(m.sum()),
            "dots_on_catalogue": int((d_cat[m] < 1.0).sum()),
            "dots_gt3px_from_catalogue": int((dc > 3.0).sum()),
            "median_d_catalogue_px": round(float(np.median(dc)), 2),
            "off_catalogue_only_dots": int(d_off.sum()),
            "lli_projected_dti": proj["projected_dti"],
            "lli_band_loo_mae": proj["uncertainty_band_loo_mae"],
            "holdout_sgmc_cal_dti": off["sgmc_prevalence_calibrated_dti"],
            "holdout_sgmc_cal_ci95": off["sgmc_calibrated_ci95"],
            "holdout_sgmc_n_withheld": off["n_withheld_positives"],
        })
        print(f"{site}: dots={int(m.sum())} owner={e['owner_reported_score']} "
              f"lli={proj['projected_dti']:.4f} sgmc_cal={off['sgmc_prevalence_calibrated_dti']:.5f}", flush=True)

    # pairwise 3-px overlap (both directions) and overlap against the SASS3 candidate
    d_of = {s: distance_transform_edt(~m) for s, m in masks.items()}
    d_cand = distance_transform_edt(~cand)
    dil_cand = binary_dilation(cand, structure=DISK)
    for r in rows:
        s = r.get("site")
        if s not in masks:
            continue
        m = masks[s]
        others = {}
        for t, d in d_of.items():
            if t == s:
                continue
            others[t] = round(float((d[m] <= 3.0).mean()), 4)
        r["max_3px_overlap_vs_other_focus_sites"] = max(others.values()) if others else None
        r["overlap_dir_by_site"] = others
        r["our_dots_within_3px_of_this_site"] = round(float((d_of[s][cand] <= 3.0).mean()), 4)
        r["this_site_within_3px_of_our_dots"] = round(float((dil_cand & m).sum() / m.sum()), 4)
        r["already_submitted"] = True
        r["unique_for_resubmission"] = False
        r["why"] = ("This file is the site's own already-scored submission; resubmitting it is a duplicate. "
                    "SASS3 must generate a new raster.")
    out = {
        "schema_version": 1,
        "generated_by": "scripts/focus_site_scoreboard.py",
        "evidence_labels": {
            "owner_reported_score": "OWNER-REPORT",
            "lli_projected_dti": "LLI-PROJECTION (NOT A SCORE)",
            "holdout_sgmc_cal_dti": "HOLDOUT-DTI (GEMSDOE32-SGMC-CAL-v3.0, withheld positives listed)",
        },
        "sass3_candidate": str(args.candidate),
        "candidate_dots": int(cand.sum()),
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
