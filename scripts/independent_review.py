#!/usr/bin/env python3
"""Conservative review of the archived LWST GeoTIFF (2026-10-28).

This script freshly checks the local GeoTIFF's structural/range properties. The
sibling registry rasters and official sample are not in this checkout, so it
reports the previous uniqueness scan and lattice measurement as archived
records, fails the current uniqueness gates closed, and does not claim a fresh
registry clearance. It also renders the score provenance, per-site audit, and
limitations to evidence/independent_review_20261028.json and
 docs/research/independent-review-20261028.md.
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
sys.path.insert(0, str(ROOT / "src"))
LWST = ROOT / "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"
SAMPLE = ROOT / ".cache/gems_data/sample_submission.tif"
CONC = ROOT / "evidence/proxy_leaderboard_concordance.json"
OWNER = ROOT / "registry/owner_reported_scores_focus.json"
UNIQ = ROOT / "evidence/independent_uniqueness_lwst_20261028.json"
EXP_E1 = ROOT / "evidence/hypothesis_h_sass3_e_experiment.json"
OUT_JSON = ROOT / "evidence/independent_review_20261028.json"
OUT_MD = ROOT / "docs/research/independent-review-20261028.md"
ARCHIVE_CARD = ROOT / "evidence/archived_run_card_lwst_20261027.json"
SIB = Path(os.environ.get("GEMS_SIB_ROOT", "/tmp/sib"))
PAGES = ["README.md", "index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"]
EXPECTED_DOTS = 37654


# Geotransform of the organizer sample (.cache/gems_data/sample_submission.tif), recorded 2026-10-28,
# so the gate also runs where the restored data cache is absent (e.g. CI).
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def format_gate() -> dict:
    """Freshly check the archived file's local format; disclose if the sample is absent."""
    checks: dict[str, bool] = {}
    ref_available = SAMPLE.exists()
    with rasterio.open(LWST) as s:
        a = s.read(1)
        checks["single_band"] = s.count == 1
        checks["dtype_float32"] = s.dtypes[0] == "float32"
        checks["crs_epsg_32611"] = s.crs is not None and s.crs.to_epsg() == 32611
        checks["shape_rows_cols_3730x3292"] = s.shape == (3730, 3292)
        if ref_available:
            with rasterio.open(SAMPLE) as ref:
                checks["shape_matches_organizer_sample"] = s.shape == ref.shape
                ref_tf = tuple(ref.transform)[:6]
            checks["geotransform_matches_organizer_sample"] = tuple(round(v, 9) for v in s.transform)[:6] == tuple(
                round(v, 9) for v in ref_tf
            )[:6]
        else:
            ref_tf = EXPECTED_TRANSFORM
            checks["geotransform_matches_recorded_reference"] = tuple(round(v, 9) for v in s.transform)[:6] == tuple(
                round(v, 9) for v in ref_tf
            )[:6]
        checks["all_finite"] = bool(np.isfinite(a).all())
        checks["values_in_0_1"] = bool(np.isfinite(a).all() and a.min() >= 0.0 and a.max() <= 1.0)
        dots = int((a == 1).sum())
        checks["dot_count_expected"] = dots == EXPECTED_DOTS
        checks["zero_or_one_only"] = bool(np.isin(a, [0.0, 1.0]).all())
        meta = {
            "crs": str(s.crs),
            "organizer_sample_available": ref_available,
            "sample_reference": "organizer sample" if ref_available else "recorded EXPECTED_TRANSFORM (not rechecked against sample)",
            "width": s.width,
            "height": s.height,
            "transform": list(s.transform)[:6],
            "nodata": s.nodata,
            "outside_footprint_fill": "0.0 (valid in [0,1]); organizer sample uses NaN nodata. Portal treatment outside the footprint is unconfirmed.",
            "dots": dots,
            "min": float(a.min()),
            "max": float(a.max()),
            "sha256": __import__("hashlib").sha256(LWST.read_bytes()).hexdigest(),
        }
    return {
        "checks": checks,
        "all_pass": all(checks.values()),
        "organizer_sample_comparison_available": ref_available,
        "meta": meta,
    }


def uniqueness_gate() -> dict:
    """Summarize the prior raster scan without misrepresenting it as a fresh recheck.

    The 451-raster comparison JSON is retained as historical evidence, but the
    referenced sibling rasters are not present in this checkout. A stored result
    can explain why an artifact was rejected; it cannot certify the current
    registry or an artifact's pre-placement surface.
    """
    d = json.loads(UNIQ.read_text())
    res = d["results"]
    subs = [r for r in res if "/docs/downloads/" in r["path"]]
    if not subs:
        return {
            "n_submitted_rasters_compared": 0,
            "n_non_submission_rasters_excluded": len(res),
            "threshold_within3_max": 0.70,
            "threshold_abs_spearman_max": 0.90,
            "max_within3_frac": None,
            "max_within3_vs": None,
            "max_abs_spearman_sampled": None,
            "max_abs_spearman_vs": None,
            "vs_champion_e5eb6e7e_within3": None,
            "archived_pass": False,
            "recomputed_this_run": False,
            "pass": False,
            "source": "evidence/independent_uniqueness_lwst_20261028.json",
            "note": "No comparable submission rows are available; uniqueness is unverified and fails closed.",
        }
    max_w3 = max(subs, key=lambda r: r["within3_frac"])
    rho_rows = [r for r in subs if r.get("spearman_sampled") is not None]
    max_rho = max(rho_rows, key=lambda r: abs(r["spearman_sampled"])) if rho_rows else None
    champ = [r for r in subs if "e5eb6e7e" in r["path"] and r["path"].endswith("-zeros.tif")]
    archived_pass = bool(
        max_w3["within3_frac"] <= 0.70
        and max_rho is not None
        and abs(max_rho["spearman_sampled"]) <= 0.90
    )
    return {
        "n_submitted_rasters_compared": len(subs),
        "n_non_submission_rasters_excluded": len(res) - len(subs),
        "threshold_within3_max": 0.70,
        "threshold_abs_spearman_max": 0.90,
        "max_within3_frac": round(max_w3["within3_frac"], 6),
        "max_within3_vs": max_w3["path"],
        "max_abs_spearman_sampled": round(abs(max_rho["spearman_sampled"]), 6) if max_rho else None,
        "max_abs_spearman_vs": max_rho["path"] if max_rho else None,
        "vs_champion_e5eb6e7e_within3": round(champ[0]["within3_frac"], 6) if champ else None,
        "archived_pass": archived_pass,
        "recomputed_this_run": False,
        "pass": False,
        "source": "evidence/independent_uniqueness_lwst_20261028.json (scripts/independent_uniqueness_audit.py)",
        "note": "Archived final-dot scan only; sibling rasters are absent from this checkout. It is not a current uniqueness clearance, and the required pre-placement surface scan is not re-run.",
    }


def per_site_table() -> list[dict]:
    """Build a provenance-explicit summary from archived per-site audit records."""
    audit = json.loads((ROOT / "evidence/nine_sites_executive_audit.json").read_text())
    conc = json.loads(CONC.read_text())
    uniq = json.loads(UNIQ.read_text()).get("results", [])
    rows = []
    for site_record in audit.get("sites", []):
        site = site_record["site"]
        historical = site_record["historical_best"]
        filename = site_record["hist_name"]
        conc_match = next(
            (
                row for row in conc.get("rows", [])
                if row.get("site") == site and Path(row.get("file", "")).name.removesuffix(".tif") == filename
            ),
            None,
        )
        # Prefer the exact filename-matched row, then fall back to the audited best
        # owner report without implying that its proxy values are organizer scores.
        if conc_match is None:
            conc_match = max(
                (row for row in conc.get("rows", []) if row.get("site") == site),
                key=lambda row: row.get("owner_reported_score", float("-inf")),
                default=None,
            )
        hold = historical.get("holdout_dti", {})
        projection = historical.get("lli_projection", {})
        base = Path(conc_match["file"]).name if conc_match else filename
        overlap_row = next(
            (
                row for row in uniq
                if f"{site}-main" in row.get("path", "") and row.get("path", "").endswith(base)
            ),
            None,
        )
        rows.append(
            {
                "site": site,
                "best_owner_reported_file": base,
                "owner_reported_score": site_record.get("hist_score_owner_report"),
                "owner_report_status": "OWNER-REPORT; transcribed in the archived sibling audit, no organizer receipt",
                "organizer_confirmed_score": None,
                "organizer_confirmed_status": "No per-file organizer receipt in this checkout",
                "holdout_dti": {
                    "label": "HOLDOUT-DTI (historical proxy; not a leaderboard score)",
                    "evaluator_version": hold.get("evaluator_version"),
                    "withheld_positive_pixels": hold.get("withheld_positive_pixels"),
                    "dti": hold.get("dti"),
                    "ci95": hold.get("ci95"),
                },
                "model_projection_not_score": {
                    "label": projection.get("evidence_class", "LLI-PROJECTION (NOT A SCORE)"),
                    "model": projection.get("model"),
                    "projected_dti": projection.get("projected_dti"),
                    "loo_mae_band": projection.get("uncertainty_band_loo_mae"),
                    "loo_mae": projection.get("loo_mae"),
                },
                "historical_pairwise_overlap_vs_other_8": historical.get("max_3px_overlap_vs_other_8_hist"),
                "nearest_historical_peer": historical.get("nearest_peer_site"),
                "historically_unique_vs_other_8": historical.get("unique_vs_other_8_sites"),
                "archived_lwst_overlap_vs_this_file": overlap_row.get("within3_frac") if overlap_row else None,
                "archived_lwst_overlap_recomputed_this_run": False,
                "dots": historical.get("dots"),
                "use": "Historical comparison only; do not resubmit this recorded file.",
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
        # Keep candidate-overlap evidence archived and fail the live gate closed.
        # Prefer the later checked-in bound audit over the older, retracted
        # footprint count; neither is a fresh calculation in this checkout.
        archived = {}
        if OUT_JSON.exists():
            try:
                archived = json.loads(OUT_JSON.read_text()).get("lattice_gate_literal", {})
            except (OSError, json.JSONDecodeError):
                archived = {}
        coverage = archived.get("coverage_analysis")
        bound_path = ROOT / "evidence/lattice_bound_audit_20261028.json"
        if bound_path.exists():
            bound = json.loads(bound_path.read_text())
            primary = bound["bound_by_convention"][bound["primary_convention"]]
            footprint_cells = bound["footprint"]["cells"]
            coverage = {
                "footprint_px": footprint_cells,
                "footprint_fraction_within_3px_of_lattice": round(primary["footprint_cells_within_3px_of_lattice"] / footprint_cells, 8),
                "footprint_px_outside_3px_of_lattice": primary["footprint_cells_outside_buffer"],
                "dots": bound["candidate_dots_assumed"],
                "dots_needed_outside_3px_to_pass": int(np.ceil(bound["candidate_dots_assumed"] * 0.30)),
                "pass_possible_at_this_dot_count": primary["candidate_37654_dots_can_pass"],
                "reading": "Archived value from evidence/lattice_bound_audit_20261028.json; not recomputed in this review.",
                "evidence_status": "ARCHIVED REGISTRY-MEASUREMENT; not recomputed this run",
                "source": "evidence/lattice_bound_audit_20261028.json",
            }
        return {
            "pass": False,
            "available": False,
            "recomputed_this_run": False,
            "reason": f"witness not present in this checkout: {path}",
            "evidence_status": "archived prior verification; not re-run",
            "witness_path": LATTICE_REL,
            "witness_sha256": archived.get("witness_sha256"),
            "witness_sha256_matches_main_pin": archived.get("witness_sha256_matches_main_pin"),
            "same_grid_crs_shape_transform": archived.get("same_grid_crs_shape_transform"),
            "witness_positive_px": archived.get("witness_positive_px"),
            "within3_frac": archived.get("within3_frac"),
            "limit": 0.70,
            "coverage_analysis": coverage,
        }
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with rasterio.open(path) as w, rasterio.open(LWST) as c:
        same_grid = (w.crs == c.crs) and (w.shape == c.shape) and (w.transform == c.transform)
        wa = w.read(1)
        ca = c.read(1)
    wpos = np.isfinite(wa) & (wa > 0)
    dots = ca == 1
    dist = ndi.distance_transform_edt(~wpos)
    frac = float((dist[dots] <= 3.0).mean()) if dots.any() else 0.0
    coverage = None
    feats = ROOT / ".cache/gems_data/training_features.tif"
    if feats.exists():
        from gems32.grid import read_footprint  # local import: src/ on path only when needed

        foot = read_footprint(feats)
        cov_frac = float((dist[foot] <= 3.0).mean())
        uncovered = int((dist[foot] > 3.0).sum())
        n_dots = int(dots.sum())
        need_outside = int(np.ceil(n_dots * (1.0 - 0.70)))
        coverage = {
            "footprint_px": int(foot.sum()),
            "footprint_fraction_within_3px_of_lattice": round(cov_frac, 5),
            "footprint_px_outside_3px_of_lattice": uncovered,
            "dots": n_dots,
            "dots_needed_outside_3px_to_pass": need_outside,
            "pass_possible_at_this_dot_count": bool(uncovered >= need_outside),
            "reading": "Literal rule is unsatisfiable at this dot count: the uncovered footprint pixels are fewer than the dots needed outside the 3 px buffer."
            if uncovered < need_outside else "Literal rule is satisfiable at this dot count.",
        }
    return {
        "coverage_analysis": coverage,
        "pass": bool(frac <= 0.70 and sha == LATTICE_SHA256 and same_grid),
        "available": True,
        "recomputed_this_run": True,
        "evidence_status": "recomputed from the witness raster in this checkout",
        "witness_path": LATTICE_REL,
        "witness_sha256": sha,
        "witness_sha256_matches_main_pin": sha == LATTICE_SHA256,
        "same_grid_crs_shape_transform": bool(same_grid),
        "witness_positive_px": int(wpos.sum()),
        "within3_frac": round(frac, 6),
        "limit": 0.70,
        "note": "Literal rule, no exemption.",
    }


def link_gate() -> dict:
    out: dict = {"pages": {}, "unique_targets": 0, "targets_resolved": 0, "unresolved": []}
    targets: set[tuple[str, str]] = set()
    for rel in PAGES:
        p = ROOT / rel
        txt = p.read_text(encoding="utf-8")
        broken = re.findall(r"https://github\.com/sassnarep3-star/GEMSDOE\d+/", txt)
        fixed = re.findall(
            r"https://github\.com/buffedlizard55-lab/(GEMSDOE\d+)/(?:raw|blob)/[^/\s\"'<>)\]]+/([^\s\"'<>)\]]+)",
            txt,
        )
        targets.update(fixed)
        out["pages"][rel] = {"remaining_sassnarep3_star_links": len(broken), "buffedlizard55_lab_links": len(fixed)}
    out["unique_targets"] = len(targets)
    out["remaining_broken_links"] = sum(page["remaining_sassnarep3_star_links"] for page in out["pages"].values())
    out["local_sibling_root_available"] = SIB.exists()
    for repo, rel in sorted(targets):
        num = repo[len("GEMSDOE"):]
        cand = SIB / f"x_g{num}" / f"{repo}-main" / rel
        if cand.exists():
            out["targets_resolved"] += 1
        else:
            out["unresolved"].append(f"{repo}/{rel}")
    out["verification_complete"] = not targets or SIB.exists()
    out["all_resolved"] = (
        out["verification_complete"]
        and out["remaining_broken_links"] == 0
        and out["targets_resolved"] == out["unique_targets"]
        and not out["unresolved"]
    )
    if not out["verification_complete"]:
        out["reason"] = "Sibling targets exist, but no local sibling checkout is available; path resolution was not verified."
    elif not targets:
        out["reason"] = "No sibling file targets were present on the reviewed pages; there was nothing to resolve locally."
    out["resolution_root"] = str(SIB)
    return out


HYPOTHESES = [
    {
        "rank": 1,
        "id": "H-SASS3-PLAN-1",
        "status": "PLANNING ONLY — not implemented or validated",
        "layers": "Official GeoDAWN magnetic field plus radiometric K and Th; requires source rasters",
        "signature": "Robust paired-flank local residual contrast across a lineament, retained after upward continuation",
        "mimic": "Lithologic contacts, remanent magnetic bodies, and radiometric facies boundaries",
        "why_new": "Targets asymmetric alteration around buried fluid pathways rather than scalar SPI/Theta ridge strength or simple ratio fusion. Novelty is a code-inventory hypothesis, not established across sibling repositories.",
        "cost": "Moderate; raster alignment, paired-profile statistic, then buffered whole-segment validation",
        "source_status": "USGS GeoDAWN is the named official source; coverage/download availability was not verified, so not currently viable.",
        "expected_dti": "Unquantified; qualitative priority only, not a score or projection.",
    },
    {
        "rank": 2,
        "id": "H-SASS3-PLAN-2",
        "status": "PLANNING ONLY — not implemented or validated",
        "layers": "Competition-provided DEM and gravity anomaly; requires the official data package",
        "signature": "Scale-dependent cross-slope asymmetry around gravity-gradient lineaments, evaluated on both basin flanks",
        "mimic": "Alluvial-fan margins, basin stratigraphy, and asymmetric erosional slopes",
        "why_new": "Tests a paired basin-flank response rather than existing piedmont/gravity score fusion; any distinction from related repository code still needs a code-level audit.",
        "cost": "Moderate; multiscale derivatives and controls, then the shared blocked evaluator",
        "source_status": "The competition data page is the named official source; local package/cache is absent and external availability was not verified, so not currently viable.",
        "expected_dti": "Unquantified; qualitative priority only, not a score or projection.",
    },
    {
        "rank": 3,
        "id": "H-SASS3-PLAN-3",
        "status": "PLANNING ONLY — not implemented or validated",
        "layers": "Multi-height upward continuations of the official GeoDAWN magnetic field",
        "signature": "Direction and magnitude of magnetic gradient-ridge migration across continuation heights",
        "mimic": "Dipping intrusive contacts and depth-varying lithologic boundaries",
        "why_new": "Focuses on displacement direction of a ridge through scale, not only its persistence or an Euler-style depth cluster; novelty remains unverified outside this checkout.",
        "cost": "High; requires trusted grids at multiple heights, synthetic depth controls, and a leakage-safe holdout",
        "source_status": "USGS GeoDAWN is the named official source; coverage/download availability was not verified, so not currently viable.",
        "expected_dti": "Unquantified; lowest priority due data and implementation cost; not a score or projection.",
    },
]


def _pct(x: float | None) -> str:
    return f"{x * 100:.2f}%" if isinstance(x, (int, float)) else "not available"


def _float_text(x: float | None, digits: int = 6) -> str:
    return f"{x:.{digits}f}" if isinstance(x, (int, float)) else "not available"


def _ci_text(ci: list[float] | None, digits: int = 6) -> str:
    if not isinstance(ci, list) or len(ci) != 2:
        return "CI unavailable"
    return f"[{ci[0]:.{digits}f}, {ci[1]:.{digits}f}]"


def _safe_block_reason(lat: dict) -> str:
    frac = lat.get("within3_frac")
    if isinstance(frac, (int, float)):
        freshness = "freshly recomputed" if lat.get("recomputed_this_run") else "archived measurement; witness unavailable for recheck"
        return (
            f"Blocked: the calibration-lattice overlap is {_pct(frac)} (>70%; {freshness}); "
            "the all-registry uniqueness clearance is also unavailable. No slot was promoted."
        )
    return (
        "Blocked: the calibration-lattice witness and comparable measurements are unavailable in this checkout; "
        "the literal registry uniqueness gate fails closed. No slot was promoted."
    )


def _run_card(fmt: dict, uq: dict, lat: dict, e1: dict, old_card: dict, ledger: dict) -> dict:
    lwst_ref = e1.get("like_for_like_reference", {})
    lwst_hr = lwst_ref.get("lwst_hide_and_recover", {})
    lwst_sg = lwst_ref.get("lwst_sgmc_off_catalogue", {})
    e1_hr = e1.get("holdout_dti", {}).get("hide_and_recover", {})
    e1_sg = e1.get("holdout_dti", {}).get("sgmc_off_catalogue", {})
    old_registry = old_card.get("registry_correlation_and_overlap", {})
    canary = json.loads((ROOT / "evidence/leakage_canary_report.json").read_text())
    zip_path = LWST.with_suffix(".tif.zip")
    zip_sha = __import__("hashlib").sha256(zip_path.read_bytes()).hexdigest() if zip_path.exists() else None
    fmt_meta = fmt.get("meta", {})
    return {
        "review_date": "2026-10-28",
        "review_scope": "Conservative review of an archived candidate; no new experiment or submission was run.",
        "branch": "arena/16f75a44-gemsdoesass3",
        "lane_id": None,
        "assigned_lane_status": "UNRESOLVED: the supplied brief does not identify this checkout's single method paragraph.",
        "historical_lane_record": old_card.get("lane_id"),
        "hypothesis": "Review-only. The archived LWST-GeoConduit candidate is not re-proposed or promoted. The most recent separate candidate record is H-SASS3-E and is negative.",
        "mechanism": "No mechanism implemented in this review. Historical candidate descriptions are retained in the archived run card for provenance only.",
        "non_fault_mimic": "The historical H-SASS3-E test lists sedimentary onlap and paleochannel incision; this is not a validation of the archived LWST candidate.",
        "holdout_dti": {
            "archived_lwst_hide_and_recover": {
                "score_label": lwst_hr.get("score_label", "HOLDOUT-DTI"),
                "evaluator_version": lwst_hr.get("evaluator_version"),
                "withheld_positive_pixels": lwst_hr.get("n_withheld_positives"),
                "b_visible_px": lwst_hr.get("b_visible_px"),
                "pooled_dti": lwst_hr.get("pooled_dti"),
                "ci95": lwst_hr.get("ci95_cluster_bootstrap"),
                "evidence_status": "ARCHIVED evaluator record; not recomputed in this review",
            },
            "archived_lwst_sgmc_cal": {
                "score_label": lwst_sg.get("score_label", "HOLDOUT-DTI"),
                "evaluator_version": lwst_sg.get("evaluator_version"),
                "withheld_positive_pixels": lwst_sg.get("n_withheld_positives"),
                "prevalence_calibrated_dti": lwst_sg.get("sgmc_prevalence_calibrated_dti"),
                "ci95": lwst_sg.get("sgmc_calibrated_ci95"),
                "evidence_status": "ARCHIVED evaluator record; not recomputed in this review",
            },
            "experiment_E1_hide_and_recover": {
                "score_label": e1_hr.get("score_label", "HOLDOUT-DTI"),
                "evaluator_version": e1_hr.get("evaluator_version"),
                "withheld_positive_pixels": e1_hr.get("n_withheld_positives"),
                "b_visible_px": e1_hr.get("b_visible_px"),
                "pooled_dti": e1_hr.get("pooled_dti"),
                "ci95": e1_hr.get("ci95_cluster_bootstrap"),
                "evidence_status": "ARCHIVED negative experiment E1; no slot spent",
            },
            "experiment_E1_sgmc_cal": {
                "score_label": e1_sg.get("score_label", "HOLDOUT-DTI"),
                "evaluator_version": e1_sg.get("evaluator_version"),
                "withheld_positive_pixels": e1_sg.get("n_withheld_positives"),
                "prevalence_calibrated_dti": e1_sg.get("sgmc_prevalence_calibrated_dti"),
                "ci95": e1_sg.get("sgmc_calibrated_ci95"),
                "evidence_status": "ARCHIVED negative experiment E1; no slot spent",
            },
            "organizer_score": None,
            "organizer_score_status": "No submission-page receipt for the reviewed candidate is in this checkout.",
        },
        "leakage_canary": {
            "E1_single_feature": {
                "feature": "depth_to_base_surf curvature score",
                "auc_vs_withheld_sgmc": e1.get("leakage_canary_single_feature", {}).get("auc_vs_withheld_sgmc"),
                "symmetric_auc": e1.get("leakage_canary_single_feature", {}).get("symmetric_auc"),
                "threshold": 0.90,
                "passed": e1.get("leakage_canary_single_feature", {}).get("pass_le_090"),
                "evidence_status": "ARCHIVED; this is the experiment-specific single-feature canary, not a current rerun",
            },
            "historical_51_channel_report": {
                "channels_tested": canary.get("n_channels_tested"),
                "withheld_positive_samples": canary.get("n_withheld_positive_samples"),
                "negative_samples": canary.get("n_negative_samples"),
                "worst_channel": canary.get("worst_channel"),
                "worst_symmetric_auc": canary.get("worst_symmetric_auc"),
                "all_passed": canary.get("all_passed"),
                "evidence_status": "ARCHIVED; separate prior report, not a fresh validation of this checkout",
            },
        },
        "registry_correlation_and_overlap": {
            "recomputed_this_run": False,
            "thresholds": {"within3_max_fraction": 0.70, "absolute_spearman_max": 0.90, "buffer_px": 3},
            "archived_preplacement_surface_scan": {
                "registry_rasters_checked": old_registry.get("registry_rasters_checked"),
                "max_abs_spearman": old_registry.get("pre_placement_surface_max_abs_spearman"),
                "closest_raster": old_registry.get("pre_placement_surface_closest_raster"),
                "evidence_status": "ARCHIVED prior run-card result; not rechecked",
            },
            "archived_final_dot_scan_451_downloads": {
                "submitted_rasters_compared": uq.get("n_submitted_rasters_compared"),
                "max_within3_fraction": uq.get("max_within3_frac"),
                "max_abs_sampled_spearman": uq.get("max_abs_spearman_sampled"),
                "archived_subset_pass": uq.get("archived_pass"),
                "evidence_status": "ARCHIVED subset-only result; not a current full-registry clearance",
            },
            "archived_literal_lattice_result": {
                "within3_fraction": lat.get("within3_frac"),
                "limit": lat.get("limit", 0.70),
                "pass": False,
                "witness_sha256": lat.get("witness_sha256"),
                "available_in_this_checkout": lat.get("available", False),
                "recomputed_this_run": lat.get("recomputed_this_run", False),
                "evidence_status": lat.get("evidence_status", "unavailable; fail closed"),
            },
            "current_registry_clearance": False,
            "preplacement_surface_currently_cleared": False,
            "final_dots_currently_cleared": False,
        },
        "raster_sha256": fmt_meta.get("sha256"),
        "zip_sha256": zip_sha,
        "validator_output": {
            "all_local_checks_passed": fmt.get("all_pass", False),
            "organizer_sample_comparison_available": fmt.get("organizer_sample_comparison_available", False),
            "crs": fmt_meta.get("crs"),
            "shape_rows_cols": [fmt_meta.get("height"), fmt_meta.get("width")],
            "transform": fmt_meta.get("transform"),
            "dtype": "float32",
            "finite_range": [fmt_meta.get("min"), fmt_meta.get("max")],
            "positive_pixels": fmt_meta.get("dots"),
            "checks": fmt.get("checks", {}),
            "evidence_status": "Local raster checks freshly rerun; official sample comparison unavailable.",
        },
        "submission_name": LWST.name,
        "submission_note": "Archive only: format checked; literal registry uniqueness fails the 3-px rule. Do not submit.",
        "download_path": str(LWST.relative_to(ROOT)),
        "new_candidate_generated_this_review": False,
        "repository_archive_available_for_research": LWST.exists(),
        "ok_to_download": False,
        "download_status": "NO for competition use. The TIF is retained in the repository as historical audit evidence only; it is not a download-ready submission.",
        "ok_to_submit": False,
        "status_reason": _safe_block_reason(lat),
        "verdict": "negative",
        "promote_to_real_slot": False,
        "slot_spent": False,
        "budget": {
            "prior_lane": ledger.get("lane"),
            "prior_lane_experiments": ledger.get("experiment_count"),
            "prior_lane_budget_cap": ledger.get("experiment_budget_cap"),
            "prior_lane_elapsed_seconds": ledger.get("elapsed_seconds"),
            "new_experiments_this_review": 0,
            "current_lane_resolved": False,
            "reason_no_new_experiment": "Prior lane budget is exhausted; the current task does not identify an assigned method paragraph.",
        },
        "official_data_availability": {
            "cached_feature_stack_present": (ROOT / ".cache/gems_data/training_features.tif").exists(),
            "official_sample_present": SAMPLE.exists(),
            "local_sibling_registry_present": SIB.exists(),
            "official_external_data_checked_this_review": False,
            "status": "Required inputs are absent; no new candidate can be validated or cleared in this checkout.",
        },
    }


def render_md(r: dict) -> str:
    card = r["run_card"]
    verdict = r["verdict"]
    uq = r["uniqueness_gate"]
    lat = r["lattice_gate_literal"]
    budget = card["budget"]
    links = r["link_gate"]
    e1 = r["experiment_E1_H_SASS3_E"]
    lwst_hr = card["holdout_dti"]["archived_lwst_hide_and_recover"]
    lwst_sg = card["holdout_dti"]["archived_lwst_sgmc_cal"]
    e1_hr = card["holdout_dti"]["experiment_E1_hide_and_recover"]
    e1_sg = card["holdout_dti"]["experiment_E1_sgmc_cal"]
    lines: list[str] = []
    A = lines.append
    A("# Independent review of the archived LWST GeoTIFF — 2026-10-28")
    A("")
    A("> **Decision: NO COMPETITION DOWNLOAD / NO SUBMISSION.** The TIF remains in this repository as historical audit evidence, not as a download-ready competition file. Its literal registry uniqueness gate fails on the archived lattice measurement, current source rasters are missing, and no new candidate was generated or cleared in this review.")
    A("")
    A("## Executive summary")
    A("")
    A("- **Competition download:** **NO**. The TIF exists in the repository as a historical audit artifact at `docs/downloads/" + LWST.name + "`, not as a download-ready submission.")
    A("- **Upload/submission:** **NO**. Archived lattice overlap exceeds the 70% limit; current full-registry uniqueness and pre-placement surface comparisons are not available to rerun. No calibration-lattice exemption is applied.")
    A("- **New unique GeoTIFF:** None created in this review. Repackaging or renaming the old file would not make it unique. Generating another raster is blocked by the missing feature stack/registry/sample, the unresolved method lane, and the exhausted prior lane budget.")
    A("- **Slot:** None spent; no promotion decision was made by a selector.")
    A("")
    A("## 1. Evidence status and submission gates")
    A("")
    A("| Check | Result | Evidence and freshness |")
    A("|---|---|---|")
    A(f"| Local raster format/range | {'PASS' if r['format_gate']['all_pass'] else 'FAIL'} | Fresh local checks: one float32 band, EPSG:32611, 3730 x 3292, recorded transform, finite values in [0,1], 37,654 positives. Official sample comparison available: **{r['format_gate'].get('organizer_sample_comparison_available', False)}**. |")
    if uq.get("max_within3_frac") is not None:
        archived_uq = f"archived subset scan over {uq['n_submitted_rasters_compared']} downloads: {_pct(uq['max_within3_frac'])} max within 3 px; max sampled |Spearman| {_float_text(uq['max_abs_spearman_sampled'], 3)}; archived subset-only pass={uq.get('archived_pass')}"
    else:
        archived_uq = "no archived comparable rasters available"
    A(f"| Historical submitted-download comparison | **ARCHIVED ONLY — not a current clearance** | {archived_uq}. Sibling raster files are absent, and this final-dot scan does not verify the required pre-placement surface for the current registry. |")
    lat_value = lat.get("within3_frac")
    lat_text = _pct(lat_value) if isinstance(lat_value, (int, float)) else "not available"
    lat_source = "archived prior verification; witness absent from this checkout" if not lat.get("available") else "recomputed from the local witness raster"
    A(f"| Literal rule including calibration lattice | **FAIL CLOSED** | {lat_text} within 3 px vs 70% limit; {lat_source}. Witness hash: `{lat.get('witness_sha256') or 'not available'}`. |")
    A(f"| Current all-registry surface and final-dot gates | **NOT VERIFIED** | No complete current registry is present. Surface scan freshness={card['registry_correlation_and_overlap']['archived_preplacement_surface_scan']['evidence_status']}; final-dot scan freshness={card['registry_correlation_and_overlap']['archived_final_dot_scan_451_downloads']['evidence_status']}. |")
    A("| Competition download / upload | **NO / NO** | The local TIF is retained for audit only; it is not download-ready for competition use and has no submission approval. |")
    A("")
    A("### Archived lattice coverage check")
    A("")
    cov = lat.get("coverage_analysis")
    if isinstance(cov, dict) and isinstance(cov.get("footprint_px_outside_3px_of_lattice"), int):
        A(
            f"The checked-in archived bound audit reports {cov.get('footprint_fraction_within_3px_of_lattice', 0) * 100:.4f}% of the footprint within 3 px, "
            f"leaving {cov['footprint_px_outside_3px_of_lattice']:,} pixels outside the buffer. At {cov.get('dots', 37_654):,} dots, "
            f"at least {cov.get('dots_needed_outside_3px_to_pass', 0):,} would need to be outside to meet the 70% cap, so that archived calculation says the gate is unsatisfiable at this dot count. "
            "The earlier 5,379-cell figure was retracted after the 2026-10-28 bound audit recomputed 6,649 uncovered cells; neither figure was freshly recomputed here."
        )
    else:
        A("No lattice coverage raster is available for a fresh calculation. The literal uniqueness gate therefore remains blocked; no exemption is inferred.")
    A("")
    A("## 2. Score provenance and what can be concluded")
    A("")
    A("No organizer submission-page receipt for the candidate or the nine site files is present in this checkout. All site scores below are **OWNER-REPORT** values copied from the archived audit. **HOLDOUT-DTI** is a local proxy evaluation, not a leaderboard estimate or organizer score. **LLI-PROJECTION** is a model-only estimate with a leave-one-out-error band, not a confidence interval and not a score.")
    A("")
    A("The archived LWST record reports:")
    A("")
    A(f"- {lwst_hr['score_label']} {lwst_hr['pooled_dti']:.6f} {_ci_text(lwst_hr['ci95'])}; evaluator `{lwst_hr['evaluator_version']}`, {lwst_hr['withheld_positive_pixels']:,} withheld positives, B_visible={lwst_hr['b_visible_px']} px. Archived; not rerun here.")
    A(f"- {lwst_sg['score_label']} {lwst_sg['prevalence_calibrated_dti']:.6f} {_ci_text(lwst_sg['ci95'])}; evaluator `{lwst_sg['evaluator_version']}`, {lwst_sg['withheld_positive_pixels']:,} withheld positives. Archived; not rerun here.")
    paired_delta = json.loads((ROOT / "evidence/archived_run_card_lwst_20261027.json").read_text()).get("holdout_dti", {}).get("secondary_off_catalogue_sgmc", {})
    A(f"- Archived SGMC-CAL comparator: champion point 0.064121; paired delta {paired_delta.get('paired_delta_calibrated_vs_champion', 0.001581):+.6f} {_ci_text(paired_delta.get('paired_delta_calibrated_ci95'))}. The paired interval includes zero.")
    A("- **Outperformance status: NOT DEMONSTRATED.** These are archived HOLDOUT-DTI proxies, not organizer scores or leaderboard predictions.")
    A("")
    A("The earlier 0.111062 HIDE-RECOVER claim is withdrawn as the shipped raster's score: it was an OOF/per-fold result using a mislabeled parent baseline. The archived static-file evaluation above is the relevant proxy record, and still does not predict a competition score. The task prompt gives conflicting 0.3195 and 0.4413 leaderboard snapshots; later repository notes record a 0.4544 public-board read. This review did not fetch the live leaderboard, so none is asserted as today's value, and no public-board snapshot is an organizer receipt for a particular site file.")
    A("")
    A("### Nine-site executive summary")
    A("")
    A("The maximum pairwise overlap column compares each historical leader against the other eight historical leaders only. It is not a full-registry uniqueness test. The LWST comparison is a separate archived pairwise scan, not a fresh clearance.")
    A("")
    A("| Site | Best file in archived audit | OWNER-REPORT (no receipt) | ORGANIZER-CONFIRMED file score | LLI-v1-S0 projection (NOT a score) | HOLDOUT-DTI proxy | Max 3-px overlap vs other 8 historic leaders | Archived LWST overlap vs this file |")
    A("|---|---|---:|---|---|---|---|---|")
    for row in r["per_site_table"]:
        owner = _float_text(row.get("owner_reported_score"), 4)
        proj = row.get("model_projection_not_score", {})
        proj_score = proj.get("projected_dti")
        proj_band = proj.get("loo_mae_band")
        projection_text = (
            f"{proj_score:.6f}; LOO-MAE band {_ci_text(proj_band, 4)}"
            if isinstance(proj_score, (int, float)) and isinstance(proj_band, list)
            else "not available"
        )
        hold = row.get("holdout_dti", {})
        hold_text = (
            f"HOLDOUT-DTI {hold['dti']:.6f} {_ci_text(hold.get('ci95'))}; {hold.get('evaluator_version')}; "
            f"n={hold.get('withheld_positive_pixels'):,}"
            if isinstance(hold.get("dti"), (int, float)) and isinstance(hold.get("withheld_positive_pixels"), int)
            else "not available"
        )
        ov = row.get("historical_pairwise_overlap_vs_other_8")
        peer = row.get("nearest_historical_peer") or "peer not recorded"
        pairwise = f"{_pct(ov)} vs {peer} (ARCHIVE)" if isinstance(ov, (int, float)) else "not available"
        lwst_ov = row.get("archived_lwst_overlap_vs_this_file")
        lwst_text = f"{_pct(lwst_ov)} (ARCHIVE)" if isinstance(lwst_ov, (int, float)) else "not available"
        filename = row.get("best_owner_reported_file", "unknown")
        A(f"| {row['site']} | `{filename}` | {owner} (OWNER-REPORT) | No per-file receipt | {projection_text} (not a CI) | {hold_text} | {pairwise} | {lwst_text} |")
    A("")
    A("**Cross-site reading:** the archived leader-to-leader overlaps are all above the 70% threshold, so those historical leaders are not unique relative to one another under the specified 3-pixel comparison. The separate old LWST/download scan cannot clear the new/current full registry.")
    A("")
    A("## 3. Prior experiment E1 — negative result")
    A("")
    A(f"Archived H-SASS3-E ({e1.get('hypothesis', 'basement-curvature candidate')}) was marked **{e1.get('verdict', 'negative').upper()}**, with no slot spent. Its metrics were:")
    A("")
    A(f"- {e1_hr['score_label']} {e1_hr['pooled_dti']:.6f} {_ci_text(e1_hr['ci95'])}; `{e1_hr['evaluator_version']}`, {e1_hr['withheld_positive_pixels']:,} withheld positives, B_visible={e1_hr['b_visible_px']} px.")
    A(f"- {e1_sg['score_label']} {e1_sg['prevalence_calibrated_dti']:.6f} {_ci_text(e1_sg['ci95'])}; `{e1_sg['evaluator_version']}`, {e1_sg['withheld_positive_pixels']:,} withheld positives.")
    can = card["leakage_canary"]["E1_single_feature"]
    A(f"- Single-feature canary: symmetric AUC {_float_text(can['symmetric_auc'])} vs 0.90 limit; pass={can['passed']}. This is the experiment-specific scalar canary, not the separate 51-channel report.")
    A("- This negative historical result is not a reason to start another experiment: the H-SASS3-A ledger records 3/3 experiments and the current checkout's task brief does not identify the active method lane.")
    A("")
    A("## 4. Ranked geological hypotheses — planning only")
    A("")
    A("Ranks are qualitative expected-value/cost priorities, not measured gains. None is approved or validated; expected DTI improvement is unquantified. The cached feature stack is missing. The official sources below were not checked for current coverage or downloadable files, so these ideas are not currently viable experimental plans.")
    A("")
    A("| Rank | Candidate | Status | Layers | Physical signature / why it may reveal uncatalogued faults | Non-fault mimic | Difference from existing repo work | Cost and data availability |")
    A("|---:|---|---|---|---|---|---|---|")
    for h in HYPOTHESES:
        A(f"| {h['rank']} | {h['id']} | {h['status']} | {h['layers']} | {h['signature']} | {h['mimic']} | {h['why_new']} | {h['cost']}. {h['source_status']} {h['expected_dti']} |")
    A("")
    A("## 5. Current blockers, provenance, and official sources")
    A("")
    A(f"- Lane/budget: active method lane is unresolved. Prior ledger `{budget.get('prior_lane')}` records {budget.get('prior_lane_experiments')} of {budget.get('prior_lane_budget_cap')} experiments (elapsed {budget.get('prior_lane_elapsed_seconds')} seconds); no new experiment was run.")
    A(f"- Data: cached feature stack present={card['official_data_availability']['cached_feature_stack_present']}; official sample present={card['official_data_availability']['official_sample_present']}; local sibling registry present={card['official_data_availability']['local_sibling_registry_present']}. No current full-registry uniqueness or surface scan is possible from these files.")
    A(f"- Sibling links on the reviewed public pages: {links.get('unique_targets', 0)} targets; local resolution complete={links.get('verification_complete')}; all resolved={links.get('all_resolved')}. {links.get('reason', '')}")
    A("")
    A("| Official/reference source | Status in this review | Intended use |")
    A("|---|---|---|")
    A("| [GEMS Official Rules (PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Cited in the archived review; not fetched again for this edit | File format, scoring disclosure, submission rules; confirm against current organizer page before upload. |")
    A("| [Competition problem/data page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [data download](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Not checked in this review; cache absent | Official training data and metric. |")
    A("| [Competition leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Not checked in this review; prompt values conflict | No current leaderboard value asserted. An organizer receipt is needed for a per-submission score. |")
    A("| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Named in planning only; coverage and download access not verified | Potential official geophysical layers for hypotheses 1 and 3. |")
    A("| [Reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | Repository is cited in the archived work; not reaudited in this review | Evaluator and submission conventions; use shared `vendor/gems57` tools where appropriate. |")
    A("| [Archived lattice witness source](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif) | Previously pinned/hash-checked; local witness missing now | Explains the archived literal uniqueness failure; not a fresh local recheck. |")
    A("")
    A("## 6. Limitations and required next steps")
    A("")
    A("1. Do not submit or spend a slot. First resolve the lane and whether the synthetic calibration raster is in scope without silently changing the protocol.")
    A("2. Restore authenticated official data, the sample GeoTIFF, cached feature stack, and a complete current registry. Re-run surface correlation and final-dot overlap against every in-scope registry raster; keep archived results separate.")
    A("3. Only after that, and only if the lane budget permits, use the shared `vendor/gems57` evaluator/writer, whole-segment buffered hide-and-recover, single-feature leakage canaries, and report evaluator, withheld positives and 95% CI. No new experiment is authorized by this review.")
    A("4. Generate and validate a distinct GeoTIFF only after its method clears the protocol. Check exact CRS, shape, transform, finite [0,1] range and unique name; write a <=140-character truthful note. A selector—not this report—makes any slot promotion decision.")
    A("5. Preserve negative results. Do not turn OWNER-REPORT, HOLDOUT-DTI, or model projections into organizer-confirmed scores.")
    A("")
    A("## 7. Run card (Protocol Rule 5)")
    A("")
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
    owner_n = len(json.loads(OWNER.read_text()).get("entries", []))
    old_card = json.loads(ARCHIVE_CARD.read_text()) if ARCHIVE_CARD.exists() else {}
    ledger_path = ROOT / "evidence/lwst_experiment_ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}

    literal_unique = bool(uq.get("pass") and lat.get("pass"))
    verdict = {
        "format_valid_programmatic": fmt["all_pass"],
        "unique_on_downloads_programmatic": False,
        "unique_on_downloads_archived_pass": bool(uq.get("archived_pass")),
        "uniqueness_recomputed_this_run": bool(uq.get("recomputed_this_run")),
        "unique_literal_incl_calibration_lattice": literal_unique,
        "ok_to_download_and_upload_as_valid_unique_file": False,
        "ok_to_download_for_competition": False,
        "archive_file_present_for_research": LWST.exists(),
        "beats_0_2778_champion_demonstrated": False,
        "beats_current_leaderboard_demonstrated": False,
        "promote_to_real_slot": False,
        "reason_not_promoted": _safe_block_reason(lat),
    }
    per_site = per_site_table()
    card = _run_card(fmt, uq, lat, e1, old_card, ledger)
    result = {
        "schema_version": 2,
        "date": "2026-10-28",
        "file_under_review": str(LWST.relative_to(ROOT)),
        "verdict": verdict,
        "format_gate": fmt,
        "uniqueness_gate": uq,
        "lattice_gate_literal": lat,
        "link_gate": links,
        "holdout_summary": card["holdout_dti"],
        "proxy_concordance": {
            "label": "HOLDOUT-DTI proxy rank correlations versus OWNER-REPORT scores; archived, n=21",
            "evaluator_versions": ["GEMSDOE32-HIDE-RECOVER-v3.0", "GEMSDOE32-SGMC-CAL-v3.0"],
            "rho_sgmc_calibrated_vs_owner": conc["concordance"]["sgmc_calibrated_dti"],
            "rho_hide_recover_vs_owner": conc["concordance"]["hide_recover_dti"],
            "rho_sgmc_raw_vs_owner": conc["concordance"]["sgmc_raw_dti"],
            "evidence_status": "Archived concordance; proxy ranking only, not score prediction.",
        },
        "experiment_E1_H_SASS3_E": e1,
        "owner_reported_entries": owner_n,
        "per_site_table": per_site,
        "budget": card["budget"],
        "run_card": card,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_md(result), encoding="utf-8")
    # This report concerns an archived LWST raster. Keep its run card nested in
    # the dated review receipt; never overwrite the repository's canonical
    # current-candidate cards (which may describe a different, later artifact).
    print(json.dumps({
        "verdict": verdict,
        "format_pass": fmt["all_pass"],
        "archived_download_subset_pass": uq.get("archived_pass"),
        "current_uniqueness_verified": uq.get("recomputed_this_run"),
        "literal_lattice_overlap": lat.get("within3_frac"),
        "lattice_witness_recomputed": lat.get("recomputed_this_run"),
        "links_all_resolved": links.get("all_resolved"),
        "link_verification_complete": links.get("verification_complete"),
        "experiments_run_this_review": 0,
    }, indent=2))
    # This is a report generator. Submission eligibility is represented separately
    # and remains false unless all current uniqueness evidence is revalidated.
    return 0 if fmt["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
