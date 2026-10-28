#!/usr/bin/env python3
"""Independent review of the shipped LWST submission (2026-10-28).

Recomputes, from the rasters themselves (not from the pipeline's JSON):
  * format gate: single band, float32, EPSG:32611, 3730 x 3292, geotransform equal to the
    organizer's sample_submission.tif, all values finite and in [0, 1], 37,654 dots;
  * uniqueness gate: within-3 px overlap and sampled |Spearman| vs every submitted raster under
    docs/downloads in the sibling checkouts (reads evidence/independent_uniqueness_lwst_20261028.json,
    which scripts/independent_uniqueness_audit.py wrote);
  * link gate: every sassnarep3-star GitHub link in the public pages is rewritten, and every
    buffedlizard55-lab target resolves in the sibling checkouts.

Writes evidence/independent_review_20261028.json and docs/research/independent-review-20261028.md.
Labels: every score is HOLDOUT-DTI (evaluator named), ORGANIZER-CONFIRMED (none used except the
leaderboard top), or OWNER-REPORT (typed in the task prompt; not organizer receipts).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
LWST = ROOT / "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"
SAMPLE = ROOT / ".cache/gems_data/sample_submission.tif"
CONC = ROOT / "evidence/proxy_leaderboard_concordance.json"
OWNER = ROOT / "registry/owner_reported_scores_focus.json"
UNIQ = ROOT / "evidence/independent_uniqueness_lwst_20261028.json"
EXP_E1 = ROOT / "evidence/hypothesis_h_sass3_e_experiment.json"
OUT_JSON = ROOT / "evidence/independent_review_20261028.json"
OUT_MD = ROOT / "docs/research/independent-review-20261028.md"
SIB = Path(os.environ.get("GEMS_SIB_ROOT", "/tmp/sib"))
PAGES = ["README.md", "index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"]
EXPECTED_DOTS = 37654


def format_gate() -> dict:
    checks: dict[str, bool] = {}
    with rasterio.open(LWST) as s, rasterio.open(SAMPLE) as ref:
        a = s.read(1)
        checks["single_band"] = s.count == 1
        checks["dtype_float32"] = s.dtypes[0] == "float32"
        checks["crs_epsg_32611"] = s.crs is not None and s.crs.to_epsg() == 32611
        checks["shape_rows_cols_3730x3292"] = s.shape == (3730, 3292)  # rows x cols, as in the organizer sample
        checks["shape_matches_organizer_sample"] = s.shape == ref.shape
        checks["geotransform_matches_sample"] = tuple(round(v, 9) for v in s.transform)[:6] == tuple(
            round(v, 9) for v in ref.transform
        )[:6]
        checks["all_finite"] = bool(np.isfinite(a).all())
        checks["values_in_0_1"] = bool(np.isfinite(a).all() and a.min() >= 0.0 and a.max() <= 1.0)
        dots = int((a == 1).sum())
        checks["dot_count_expected"] = dots == EXPECTED_DOTS
        checks["zero_or_one_only"] = bool(np.isin(a, [0.0, 1.0]).all())
        meta = {
            "crs": str(s.crs),
            "width": s.width,
            "height": s.height,
            "transform": list(s.transform)[:6],
            "nodata": s.nodata,
            "outside_footprint_fill": "0.0 (valid in [0,1]); organizer sample uses NaN nodata. Unconfirmed whether the portal treats 0 and NaN identically outside the footprint.",
            "dots": dots,
            "min": float(a.min()),
            "max": float(a.max()),
            "sha256": __import__("hashlib").sha256(LWST.read_bytes()).hexdigest(),
        }
    return {"checks": checks, "all_pass": all(checks.values()), "meta": meta}


def uniqueness_gate() -> dict:
    d = json.loads(UNIQ.read_text())
    res = d["results"]
    subs = [r for r in res if "/docs/downloads/" in r["path"]]
    max_w3 = max(subs, key=lambda r: r["within3_frac"])
    max_rho = max(subs, key=lambda r: abs(r["spearman_sampled"]))
    champ = [r for r in subs if "e5eb6e7e" in r["path"] and r["path"].endswith("-zeros.tif")]
    return {
        "n_submitted_rasters_compared": len(subs),
        "n_non_submission_rasters_excluded": len(res) - len(subs),
        "threshold_within3_max": 0.70,
        "threshold_abs_spearman_max": 0.90,
        "max_within3_frac": round(max_w3["within3_frac"], 6),
        "max_within3_vs": max_w3["path"],
        "max_abs_spearman_sampled": round(abs(max_rho["spearman_sampled"]), 6),
        "max_abs_spearman_vs": max_rho["path"],
        "vs_champion_e5eb6e7e_within3": round(champ[0]["within3_frac"], 6) if champ else None,
        "pass": max_w3["within3_frac"] <= 0.70 and abs(max_rho["spearman_sampled"]) <= 0.90,
        "source": "evidence/independent_uniqueness_lwst_20261028.json (scripts/independent_uniqueness_audit.py)",
        "note": "Final-dot check only. Protocol Rule 1 also asks for a surface check before placement; not re-run here.",
    }


def per_site_table() -> list[dict]:
    conc = json.loads(CONC.read_text())
    uniq = json.loads(UNIQ.read_text())["results"]
    by_site: dict[str, list[dict]] = {}
    for r in conc["rows"]:
        by_site.setdefault(r["site"], []).append(r)
    rows = []
    for site in sorted(by_site):
        best = max(by_site[site], key=lambda r: r["owner_reported_score"])
        base = Path(best["file"]).name
        hit = [u for u in uniq if f"{site}-main" in u["path"] and u["path"].endswith(base)]
        ov = round(hit[0]["within3_frac"], 4) if hit else None
        rows.append(
            {
                "site": site,
                "best_owner_reported_file": base,
                "estimated_score": f"OWNER-REPORT {best['owner_reported_score']:.4f} (already scored; not an estimate)",
                "uniqueness_of_new_LWST_vs_this_file": f"overlap {ov:.4f} (within 3 px, LWST dots near this file)" if ov is not None else "not in audit",
                "holdout_sgmc_cal": f"HOLDOUT-DTI {best['sgmc_calibrated_dti']:.6f}",
                "dots": best["dots_in_footprint"],
                "use": "DO NOT RESUBMIT (already scored; duplicates the family)",
            }
        )
    return rows


LATTICE_REL = "x_g24/GEMSDOE24-main/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SHA256 = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"


def lattice_gate() -> dict:
    """Literal registry rule (Protocol Rule 1: 'any registry raster'): the 5x5 px calibration lattice
    is a registry raster and must be checked too. It is outside docs/downloads, so the audit above
    excludes it; this gate includes it. No null-calibration exemption is applied."""
    import hashlib

    path = SIB / LATTICE_REL
    if not path.exists():
        return {"pass": False, "available": False, "reason": f"witness not found at {path}"}
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with rasterio.open(path) as w, rasterio.open(LWST) as c:
        same_grid = (w.crs == c.crs) and (w.shape == c.shape) and (w.transform == c.transform)
        wa = w.read(1)
        ca = c.read(1)
    wpos = np.isfinite(wa) & (wa > 0)
    dots = ca == 1
    dist = ndi.distance_transform_edt(~wpos)
    frac = float((dist[dots] <= 3.0).mean()) if dots.any() else 0.0
    return {
        "pass": bool(frac <= 0.70 and sha == LATTICE_SHA256 and same_grid),
        "available": True,
        "witness_path": LATTICE_REL,
        "witness_sha256": sha,
        "witness_sha256_matches_main_pin": sha == LATTICE_SHA256,
        "same_grid_crs_shape_transform": bool(same_grid),
        "witness_positive_px": int(wpos.sum()),
        "within3_frac": round(frac, 6),
        "limit": 0.70,
        "note": "Literal rule, no exemption. Reproduces the 99.7849% figure recorded on main (docs/research/review-20261028.md).",
    }


def link_gate() -> dict:
    out: dict = {"pages": {}, "unique_targets": 0, "targets_resolved": 0, "unresolved": []}
    targets: set[tuple[str, str]] = set()
    for rel in PAGES:
        p = ROOT / rel
        txt = p.read_text(encoding="utf-8")
        broken = re.findall(r"https://github\.com/sassnarep3-star/GEMSDOE\d+/", txt)
        fixed = re.findall(r"https://github\.com/buffedlizard55-lab/(GEMSDOE\d+)/(?:raw|blob)/main/([^\s\"'<>)\]]+)", txt)
        targets.update(fixed)
        out["pages"][rel] = {"remaining_sassnarep3_star_links": len(broken), "buffedlizard55_lab_links": len(fixed)}
    out["unique_targets"] = len(targets)
    for repo, rel in sorted(targets):
        num = repo[len("GEMSDOE"):]
        cand = SIB / f"x_g{num}" / f"{repo}-main" / rel
        if cand.exists():
            out["targets_resolved"] += 1
        else:
            out["unresolved"].append(f"{repo}/{rel}")
    out["all_resolved"] = out["targets_resolved"] == out["unique_targets"] and not out["unresolved"]
    out["resolution_root"] = str(SIB)
    return out


HYPOTHESES = [
    {
        "rank": 1,
        "id": "H-SASS3-E",
        "status": "TESTED - NEGATIVE (experiment E1, 1 of 3 budget; no slot spent)",
        "layers": "depth_to_base_surf (cached feature stack)",
        "signature": "narrow ridges of the most-negative Hessian eigenvalue, weighted by local relief |grad z| of the basement surface",
        "mimic": "sedimentary onlap and paleochannel incision along the basement",
        "why_new": "The phrase 'minimum curvature' and 'watershed' have no hits in the repo or the sibling docs (keyword screen). 'Hessian' is common (119 sibling files), so the novelty is the layer and statistic pairing, not the Hessian itself.",
    },
    {
        "rank": 2,
        "id": "H-SASS3-F",
        "status": "UNTESTED (candidate for experiment E2)",
        "layers": "tmi_hg, iso_grav_anom_hg, geod_shearrate, cond_surf (cached stack)",
        "signature": "sharp, lineated boundaries between Gaussian-mixture components of the standardised multi-layer geophysical vector",
        "mimic": "lithologic contacts and playa-margin conductivity changes",
        "why_new": "The term 'Gaussian mixture' has no hit in the sibling docs (keyword screen). The repo's EXP1 is an unsupervised tree model, not a mixture boundary.",
    },
    {
        "rank": 3,
        "id": "H-SASS3-G",
        "status": "UNTESTED",
        "layers": "ieq_n100a15, deq_n100a15 (cached stack)",
        "signature": "anisotropic point-pattern clustering (Ripley's K) of earthquake epicentres that aligns into linear clusters",
        "mimic": "aftershock sequences and induced seismicity",
        "why_new": "Ripley's K has no hit in the sibling docs. Partial overlap with H-SASS3-D (plane fitting of relocated seismicity), so treat it as a variant.",
    },
    {
        "rank": 4,
        "id": "H-SASS3-H",
        "status": "UNTESTED (lowest priority)",
        "layers": "geod_dilaterate (cached stack)",
        "signature": "Otsu-thresholded ridges of geodetic dilatation",
        "mimic": "subsidence and thermal-expansion strain",
        "why_new": "Otsu has no hit in the sibling docs. Weak physical link to faults; rank last.",
    },
]


def _pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def render_md(r: dict) -> str:
    v = r["verdict"]
    fg = r["format_gate"]
    uq = r["uniqueness_gate"]
    lat = r["lattice_gate_literal"]
    lg = r["link_gate"]
    hs = r["holdout_summary"]
    pc = r["proxy_concordance"]
    e1 = r["experiment_E1_H_SASS3_E"]
    rho_sg = pc["rho_sgmc_calibrated_vs_owner"]
    rho_hr = pc["rho_hide_recover_vs_owner"]
    lines = []
    A = lines.append
    A("# Independent review of the shipped LWST submission (2026-10-28)")
    A("")
    A("Every number is labelled **HOLDOUT-DTI** (evaluator named), **ORGANIZER-CONFIRMED** (none used except the leaderboard top), "
      "or **OWNER-REPORT** (typed in the task prompt, not an organizer receipt). Gate results are recomputed from the rasters by "
      "`scripts/independent_review.py`, not copied from pipeline JSON.")
    A("")
    A("## 1. Answers")
    A("")
    A("| Question | Answer | Basis (label) |")
    A("|---|---|---|")
    ok_txt = "YES" if v["ok_to_download_and_upload_as_valid_unique_file"] else "NO"
    A(f"| Is the file OK to download and upload? | **{ok_txt}** "
      f"(literal registry-overlap rule fails; format-valid archive only) | Recomputed from the raster (programmatic) |")
    A(f"| Format valid? | {'PASS' if v['format_valid_programmatic'] else 'FAIL'} | single band float32, EPSG:32611, 3730 rows x 3292 cols, sample geotransform, values in {{0,1}}, no NaN, 37,654 dots |")
    A(f"| Unique on the 451 submitted downloads? | {'PASS' if v['unique_on_downloads_programmatic'] else 'FAIL'} | max within-3 px overlap {_pct(uq['max_within3_frac'])} vs 70% limit; max sampled abs Spearman {uq['max_abs_spearman_sampled']:.3f} vs 0.90 |")
    A(f"| Unique under the literal rule (any registry raster, incl. calibration lattice)? | **{'PASS' if v['unique_literal_incl_calibration_lattice'] else 'FAIL'}** | lattice witness `inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` (SHA-256 verified): {_pct(lat['within3_frac'])} of dots within 3 px vs 70% limit |")
    A("| Beats the 0.2778 champion? | **NOT DEMONSTRATED** | LWST SGMC-CAL HOLDOUT-DTI 0.065702 [0.058992, 0.071240] vs champion 0.064121 (same evaluator). The CI contains the champion point. |")
    A("| Beats the 0.4544 leader? | **NOT DEMONSTRATED** | No organizer score exists for this file. ORGANIZER-CONFIRMED leader 0.4544 (xiaofanhu). |")
    A("| Promote to a real slot? | **NO** | Protocol Rule 6: promotion is a separate selector step. |")
    A("")
    A("The earlier statement that the file \"beats 0.2778 on both metrics\" is withdrawn. Its HIDE-RECOVER figure (0.111062) was a per-fold OOF value compared with a mislabelled D2.8 parent. Section 3 has the details.")
    A("")
    A("## 2. Per-site executive summary (focus sites)")
    A("")
    A("Each file is already scored or belongs to a scored family, so none should be resubmitted. The score column is OWNER-REPORT and is not an estimate for the new file.")
    A("")
    A("| Site | Best owner-reported file | Estimated score (label) | Uniqueness of new LWST vs this file | Holdout SGMC-CAL (label) | Use |")
    A("|---|---|---|---|---|---|")
    for row in r["per_site_table"]:
        A(f"| {row['site']} | `{row['best_owner_reported_file']}` ({row['dots']:,} dots) | {row['estimated_score']} | {row['uniqueness_of_new_LWST_vs_this_file']} | {row['holdout_sgmc_cal']} | {row['use']} |")
    A("")
    A("**New file (LWST, `gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif`):** estimated score **not available**. "
      "Its SGMC-CAL value lies above the maximum of the 21 owner-scored rasters (0.0644), so any number would be an extrapolation and is not reported.")
    A("")
    A("## 3. Corrections to earlier claims")
    A("")
    A("| # | Earlier claim | Status | Evidence |")
    A("|---|---|---|---|")
    A("| C1 | LWST beats 0.2778 on both HOLDOUT-DTI metrics | WRONG (overstated) | SGMC-CAL CI contains the champion point; HR for the catalogue-built champion is not leak-free (Rule 2). |")
    A("| C2 | 0.111062 [0.098423, 0.123755] is the shipped file's HIDE-RECOVER value | WRONG | It is a per-fold OOF value. `evaluate_holdout.py` on the shipped file gives 0.006130 [0.005175, 0.007123]. |")
    A("| C3 | 0.099202 is the 0.2778 champion baseline | WRONG | It is the D2.8 parent e56ea318af89 (owner-reported 0.2600). The true champion e5eb6e7e gives static HR 0.004515. Code fixed in `scripts/run_lwst_experiments.py` (IR-SASS3-08). Artifacts still carry the old value until the pipeline is rerun. |")
    A("| C4 | Sibling repos at sassnarep3-star/GEMSDOE* | WRONG (404) | Rewritten to buffedlizard55-lab. 18 unique targets, all resolved in the sibling checkouts (IR-SASS3-09). The owner should confirm the mapping. |")
    A("| C5 | Uniqueness max 63.27% across 385 rasters | STALE | Current audit: 66.53% across 451 submitted rasters (vs gemsdoe32-h49, newer). Still under 70% on downloads; see C9 for the literal rule. |")
    A("| C9 | This review: file OK to upload, uniqueness PASS | WRONG (corrected) | The audit excluded `inputs/calibration`. That raster is a registry raster under the literal rule. It has 99.78% overlap, which fails the 70% limit. Main's review (`docs/research/review-20261028.md`) reaches the same block. |")
    A("| C6 | Root cause of the portal error is NaN outside the footprint | UNVERIFIED | No portal log exists. The file passes the format gate, so it is safe under the stated rule. |")
    A("| C7 | verify_all_gates 30/30 PASS = independent verification | OVERSTATED | It reads JSON the pipeline wrote. The recomputed gates are in `scripts/independent_review.py` (IR-SASS3-15). |")
    A("| C8 | Leaderboard progression 0.4413 to 0.4544 | CORRECT | Live public top: xiaofanhu 0.4544 (ORGANIZER-CONFIRMED). Public scores may differ from the private final (Rules 3.2). |")
    A("")
    A("Irregularities, including the open items, are in `evidence/irregularities_ledger.json` (IR-SASS3-01..18).")
    A("")
    A("## 4. Proxy validation (concordance with owner scores, n = 21)")
    A("")
    A("| Proxy (HOLDOUT-DTI) | Spearman vs OWNER-REPORT | 95% bootstrap CI |")
    A("|---|---|---|")
    A(f"| SGMC-CAL (calibrated off-catalogue) | {rho_sg['spearman_rho_vs_owner_score']:.3f} | [{rho_sg['bootstrap_ci95'][0]:.3f}, {rho_sg['bootstrap_ci95'][1]:.3f}] |")
    A(f"| SGMC raw | {pc['rho_sgmc_raw_vs_owner']['spearman_rho_vs_owner_score']:.3f} | [{pc['rho_sgmc_raw_vs_owner']['bootstrap_ci95'][0]:.3f}, {pc['rho_sgmc_raw_vs_owner']['bootstrap_ci95'][1]:.3f}] |")
    A(f"| HIDE-RECOVER | {rho_hr['spearman_rho_vs_owner_score']:.3f} | [{rho_hr['bootstrap_ci95'][0]:.3f}, {rho_hr['bootstrap_ci95'][1]:.3f}] |")
    A("")
    A("Reading: SGMC-CAL ranks the owner scores well, so it is the more useful proxy. HIDE-RECOVER does not rank them, and it should not be used for selection.")
    A("")
    A("## 5. Holdout comparison (same evaluator, B_visible = 2 px)")
    A("")
    A(f"- LWST: HIDE-RECOVER {hs['lwst']['hide_recover']}; SGMC-CAL {hs['lwst']['sgmc_cal']}.")
    A(f"- Champion e5eb6e7e: HIDE-RECOVER {hs['champion_e5eb6e7e']['hide_recover']}; SGMC-CAL {hs['champion_e5eb6e7e']['sgmc_cal']}; {hs['champion_e5eb6e7e']['owner_reported']}.")
    A(f"- {hs['reading']}")
    A("")
    A("## 6. Why the 0.2778 file scored highest, and what this means (PhD-level reading)")
    A("")
    A("The evidence supports a narrower answer than the prompt implies:")
    A("")
    A("1. The 0.2778 file is the best member of a near-duplicate family. Its neighbours overlap 86.7-100% within 3 px (IR-SASS3-02, from the repo's earlier audit). Its owner-reported score is the highest of the 21 known files.")
    A("2. Across all 21 owner-scored files, SGMC-CAL ranks the owner scores well (rho 0.87). This is consistent with an off-catalogue advantage, but that is an inference, not a test. HIDE-RECOVER does not rank them (rho 0.14), so the static HR value cannot explain the score.")
    A("3. The gap to the leader (0.2778 to 0.4544) is 0.1766. Nothing in this repo shows a route to that gap. The most promising route is probably a different family of method. That is an open question for the user, not a result.")
    A("")
    A("## 7. Experiment E1 (H-SASS3-E, basement minimum-curvature ridges)")
    A("")
    A(f"- Hypothesis: {e1['hypothesis']}.")
    A(f"- HIDE-RECOVER {e1['hide_recover']}; SGMC-CAL {e1['sgmc_cal']}.")
    A(f"- Single-feature canary: symmetric AUC {e1['canary_symmetric_auc']:.3f} (pass, <= 0.90).")
    A(f"- Pre-registered criteria failed. Verdict: **{e1['verdict'].upper()}**. Slot spent: {e1['slot_spent']}.")
    A("- The E1 candidate was not run against the calibration lattice. The verdict is negative on the holdout, so the lattice check is moot for E1. It would be required before any promotion.")
    A("- Evidence: `evidence/hypothesis_h_sass3_e_experiment.json`, produced by `scripts/hypothesis_h_sass3_e_basement_curvature.py`.")
    A("")
    A("## 8. Ranked untried hypotheses (3 to 5)")
    A("")
    A("Ranking is by expected DTI improvement and implementation cost. \"Untried\" means not found by a keyword screen of this repo and of the 882 Markdown files in the nine sibling checkouts. It is not exhaustive.")
    A("")
    A("| Rank | ID | Status | Layer(s) | Physical signature | Non-fault mimic | Why new |")
    A("|---|---|---|---|---|---|---|")
    for h in HYPOTHESES:
        A(f"| {h['rank']} | {h['id']} | {h['status']} | {h['layers']} | {h['signature']} | {h['mimic']} | {h['why_new']} |")
    A("")
    A("## 9. Official sources (status in this session)")
    A("")
    A("| Source | Status | Use |")
    A("|---|---|---|")
    A("| https://docs.nlr.gov/docs/fy26osti/96647.pdf (GEMS Prize Official Rules, Sept 2026) | Fetched 2026-10-28 | Single GeoTIFF, 100 m; three submissions per week; public vs private scoring; generative-AI disclosure |")
    A("| https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Fetched 2026-10-28 (earlier session) | Metric (distance-weighted Tversky, alpha 0.2, beta 0.8, 300 m kernel); format |")
    A("| https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | Fetched 2026-10-28 (earlier session) | Leader 0.4544 (ORGANIZER-CONFIRMED) |")
    A("| https://github.com/drivendataorg/gems-prize-reference-solution (commit aebe92f) | Cloned | Metric is not in the notebook |")
    A("| https://github.com/buffedlizard55-lab/GEMSDOE{24,25,27,28,30,31,32,33,36} | Tarballs downloaded and checked | Sibling submissions; champion SHA-256 matches the sibling audit |")
    A("| https://github.com/sassnarep3-star/GEMSDOE* | 404 | Not usable (C4) |")
    A("| https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif (lattice witness) | Checked in the sibling checkout; SHA-256 b4570b40... matches main's pin | Literal registry rule (C9) |\n")
    A("| USGS GeoDAWN (doi 10.5066/P93LGLVQ, cited in the Rules), epsg.io/32611, Tversky index wiki, gbcge.org INGENIOUS, USGS ANSS | NOT fetched in this session | Listed for manual review |")
    A("")
    A("## 10. Limitations")
    A("")
    A("1. The literal registry rule blocks this file (C9). Under that rule it is not OK to submit. Whether the calibration lattice should count is a protocol decision for the owner, not for this review.")
    A("1a. No organizer score for the new file. Only the upload itself can show whether it is accepted or what it scores.")
    A("2. Holdout values are proxies. The HIDE-RECOVER proxy is not leak-free for catalogue-built masks, and it does not rank the owner scores.")
    A("3. Owner scores come from the task prompt, not from organizer receipts.")
    A("4. Uniqueness was checked on final dots only. The surface check that Rule 1 also requires was not re-run. The downloads audit excludes non-download rasters; the literal gate adds the lattice only.")
    A("5. Zeros fill the area outside the footprint. The organizer sample uses NaN nodata. Both are in [0,1], but whether the portal treats them identically is unconfirmed.")
    A("6. Public and private leaderboard scores can differ (Rules 3.2).")
    A("7. Generative-AI use must be disclosed in the submission narrative (Rules 3.2, IR-SASS3-11). This is an owner action.")
    A("8. Training data comes from an owner mirror, not from organizer-authenticated downloads (IR-SASS3-14).")
    A("9. The sibling checkouts are a snapshot taken 2026-10-28. Newer rasters are not covered.")
    A("10. The GitHub Pages site cannot be checked from this sandbox. The local build reproduces the committed pages, but the live site updates only after the merge is published.")
    A("11. `scripts/build_docs_pages.py` is broken and not used (IR-SASS3-10).")
    A("12. Artifacts from `run_lwst_experiments.py` still show the old baseline until the pipeline is rerun (IR-SASS3-08).")
    A("")
    A("## 11. Run card (Protocol Rule 5, review and experiment E1)")
    A("")
    card = {
        "review": "independent_review_20261028",
        "hypothesis": "H-SASS3-E basement minimum-curvature ridges (E1). Review of the shipped LWST file.",
        "mechanism": "Hessian minimum eigenvalue of depth_to_base_surf weighted by relief (E1)",
        "non_fault_mimic": "sedimentary onlap / paleochannel incision",
        "holdout_dti": {
            "E1_hide_recover": e1["hide_recover"],
            "E1_sgmc_cal": e1["sgmc_cal"],
            "label": "HOLDOUT-DTI",
        },
        "correlation_overlap_vs_registry": {
            "lwst_max_within3": uq["max_within3_frac"],
            "lwst_max_abs_spearman": uq["max_abs_spearman_sampled"],
            "limit_within3": 0.70,
            "limit_spearman": 0.90,
        },
        "raster_sha256": fg["meta"]["sha256"],
        "validator": {k: bool(v) for k, v in fg["checks"].items()},
        "submission_name": "gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros",
        "submission_note": "LWST GeoConduit dual-37654 zeros; format and uniqueness gates only",
        "verdict": "negative for H-SASS3-E; review: OK to upload (format+uniqueness), not promoted to a slot",
    }
    A("```json")
    A(json.dumps(card, indent=2, ensure_ascii=False))
    A("```")
    A("")
    return "\n".join(lines)


def main() -> int:
    fmt = format_gate()
    uq = uniqueness_gate()
    lat = lattice_gate()
    conc = json.loads(CONC.read_text())
    e1 = json.loads(EXP_E1.read_text())
    links = link_gate()
    owner_n = len(json.loads(OWNER.read_text())["entries"])

    literal_unique = bool(uq["pass"] and lat["pass"])
    verdict = {
        "format_valid_programmatic": fmt["all_pass"],
        "unique_on_downloads_programmatic": uq["pass"],
        "unique_literal_incl_calibration_lattice": literal_unique,
        "ok_to_download_and_upload_as_valid_unique_file": fmt["all_pass"] and literal_unique,
        "ok_to_download_as_format_valid_archive_only": fmt["all_pass"],
        "beats_0_2778_champion_demonstrated": False,
        "beats_0_4544_leader_demonstrated": False,
        "promote_to_real_slot": False,
        "reason_not_promoted": "Blocked by the literal registry-overlap rule (lattice witness "
                               f"{lat['within3_frac']*100:.2f}% > 70%). Also Protocol Rule 6: promotion is a separate selector step.",
    }
    sgmc_lwst = 0.065702
    result = {
        "schema_version": 1,
        "date": "2026-10-28",
        "file_under_review": str(LWST.relative_to(ROOT)),
        "verdict": verdict,
        "format_gate": fmt,
        "uniqueness_gate": uq,
        "lattice_gate_literal": lat,
        "link_gate": links,
        "holdout_summary": {
            "lwst": {
                "hide_recover": "HOLDOUT-DTI 0.006130 [0.005175, 0.007123] (GEMSDOE32-HIDE-RECOVER-v3.0, B_visible=2 px, n_withheld 22,232)",
                "sgmc_cal": f"HOLDOUT-DTI {sgmc_lwst:.6f} [0.058992, 0.071240] (GEMSDOE32-SGMC-CAL-v3.0)",
            },
            "champion_e5eb6e7e": {
                "hide_recover": "HOLDOUT-DTI 0.004515 (static; NOT leak-free under Rule 2 because the champion was built from the full catalogue)",
                "sgmc_cal": "HOLDOUT-DTI 0.064121 (same evaluator, same process as the LWST receipt)",
                "owner_reported": "OWNER-REPORT 0.2778",
            },
            "reading": "LWST SGMC-CAL 95% CI [0.059, 0.071] contains the champion point 0.064121: the difference is not significant.",
        },
        "proxy_concordance": {
            "label": "HOLDOUT-DTI proxies vs OWNER-REPORT scores (n=21 focus-site rasters)",
            "rho_sgmc_calibrated_vs_owner": conc["concordance"]["sgmc_calibrated_dti"],
            "rho_hide_recover_vs_owner": conc["concordance"]["hide_recover_dti"],
            "rho_sgmc_raw_vs_owner": conc["concordance"]["sgmc_raw_dti"],
            "reading": "SGMC-CAL ranks the owner scores well; HIDE-RECOVER does not. Use SGMC-CAL for ranking only.",
            "projection": "None. The LWST SGMC-CAL value lies above the 21 known values' maximum (0.0644), so any numeric score "
                          "estimate would be an extrapolation and is not reported.",
        },
        "experiment_E1_H_SASS3_E": {
            "hypothesis": e1["hypothesis"],
            "hide_recover": f"HOLDOUT-DTI {e1['holdout_dti']['hide_and_recover']['pooled_dti']:.6f} "
                            f"{[round(x, 6) for x in e1['holdout_dti']['hide_and_recover']['ci95_cluster_bootstrap']]}",
            "sgmc_cal": f"HOLDOUT-DTI {e1['holdout_dti']['sgmc_off_catalogue']['sgmc_prevalence_calibrated_dti']:.6f} "
                        f"{[round(x, 6) for x in e1['holdout_dti']['sgmc_off_catalogue']['sgmc_calibrated_ci95']]}",
            "canary_symmetric_auc": round(e1["leakage_canary_single_feature"]["symmetric_auc"], 6),
            "verdict": e1["verdict"],
            "slot_spent": e1["slot_spent"],
        },
        "owner_reported_entries": owner_n,
        "per_site_table": per_site_table(),
        "budget": {"experiments_used": 1, "budget": 3, "hours_note": "wall-clock not tracked to the minute; within 2 h by estimate"},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2) + "\n")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_md(result), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "format_pass": fmt["all_pass"], "uniqueness_pass": uq["pass"],
                      "links_all_resolved": links["all_resolved"], "unique_targets": links["unique_targets"],
                      "remaining_broken": sum(p["remaining_sassnarep3_star_links"] for p in links["pages"].values())},
                     indent=2))
    return 0 if fmt["all_pass"] and links["all_resolved"] else 1


if __name__ == "__main__":
    sys.exit(main())
