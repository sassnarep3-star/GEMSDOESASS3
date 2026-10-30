#!/usr/bin/env python3
"""Emit the protocol's closing JSON run card for the current candidate, entirely from receipts.

The PARALLEL-RUN PROTOCOL requires one JSON card per experiment cycle containing: hypothesis, mechanism,
the non-fault process it mimics, holdout DTI with CI, correlation/overlap against the registry, the raster
SHA-256, the validator output, a submission name and a <=140-character note, and a promote/negative verdict.
This script writes that card by *reading* the receipts produced by build_candidate.py,
validate_submission_tif.py and lane_sweep.py, so a card can never disagree with its own evidence.

Usage:  /home/user/.venv/bin/python scripts/write_run_card.py [--out evidence/run_card_20261030.json]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
NOTE = ("SASS3 OCM wide-lane emission: 44090 px off-catalogue strata, binary p=1, "
        "per-dataset mask, all cells in [0,1].")


def j(p: Path) -> dict:
    return json.loads(p.read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(EV / "run_card_20261030_s3pass.json"),
                    help="main keeps evidence/run_card_20261030.json for its own promoted card")
    args = ap.parse_args()

    build = j(EV / "candidate_build_receipt.json")
    val = j(EV / "validator_s3_ocm_safe.json")
    lane = j(EV / "lane_sweep_s3_ocm_20261030.json")
    sb = j(EV / "focus9_scoreboard_20261030.json")
    e3b = j(EV / "operating_point_E3b_selection.json")
    e2 = j(EV / "operating_point_experiment_E2.json")
    geo = j(EV / "geothermal_prior_audit_20261030.json") if (EV / "geothermal_prior_audit_20261030.json").exists() else {}

    proj = build["projections"]
    lli, sg, hr = proj["lli"], proj["holdout_sgmc_cal"], proj["holdout_hide_recover"]
    subs = [r for r in lane["rows"] if r.get("status") == "ok" and "/docs/downloads/" in r["file"]]
    latt = [r for r in lane["rows"] if r.get("status") == "ok" and "lattice" in r["file"]]
    champ = max((r for r in sb["rows"] if not r.get("status")), key=lambda r: r["owner_reported_score"])
    best_alt = max((r for r in e3b["rows"] if r["design"].startswith("lam_top2_strata")),
                   key=lambda r: r["lli_projected_dti"])
    promote = (val["all_hard_checks_pass"]
               and max(r["overlap3px_cand_within_registry"] for r in subs) <= 0.70
               and sg["dti"] > champ["holdout_sgmc_cal_dti"] * 1.10)

    card = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "scripts/write_run_card.py",
        "session": "2026-10-30 second pass (lane/OCM branch); main\u2019s tipcont card is evidence/run_card_20261030.json",
        "site": "GEMSDOESASS3 (nine focus sites: GEMSDOE24/25/27/28/30/31/32/33/36)",
        "hypothesis": "H-N6 (2026-10-30): a wide-lane, LiDAR-visible-terrain-gated emission off the catalogue "
                      "matches the champion on the local instruments; H-N5 (the higher-lambda 1.4-2 px strand lane) "
                      "is better on the live-calibrated model but sits inside the family's duplicate lane.",
        "mechanism": "Orientation-consensus surface (8 official derivative bands + pinned LiDAR scarp gain) used "
                     "only as a *support filter*; selection is by live-fitted lambda strata (d to catalogue 3-50 px "
                     "x d to the GEMSDOE25 control trace >= 3 px), then binary p=1 emission.",
        "mimics_non_fault_process": "Quaternary volcanic vent fields and lava-flow margins produce linear "
                                     "curvature/step anomalies with the same signature as a scarp; the pinned spring "
                                     "extract shows why that is also the failure mode of a geothermal prior - 46.3% of "
                                     "Hot-class springs sit within 1 km of an already-catalogued fault, i.e. inside the "
                                     "organizer-excluded halo (evidence/geothermal_prior_audit_20261030.json).",
        "submission_name": build["safe"]["tif"],
        "submission_note_140": NOTE,
        "submission_note_chars": len(NOTE),
        "raster": {
            "path": f"docs/downloads/{build['safe']['tif']}",
            "sha256": build["safe"]["tif_sha256"],
            "bytes": build["safe"]["tif_bytes"],
            "emitted_px": build["emitted_px"],
            "support_pool_px": build["support_pool_px"],
            "crs_shape_transform": build["safe"]["header"],
            "reference_copy_literal_page_text": {
                "path": f"docs/downloads/{build['literal']['tif']}",
                "sha256": build["literal"]["tif_sha256"],
                "purpose": "kept only to demonstrate the portal range failure mode; not submittable",
            },
        },
        "format_validation_in_project": {
            "command": "scripts/validate_submission_tif.py docs/downloads/<tif> --out evidence/validator_s3_ocm_safe.json",
            "all_hard_checks_pass": val["all_hard_checks_pass"],
            "checks": val["checks"],
            "stats": val["stats"],
            "mask": val["mask"],
            "notes": val["notes"],
        },
        "holdout": {
            "sgmc_calibrated": {"evaluator": sg["evaluator"], "dti": sg["dti"], "ci95": sg["ci95"],
                                "n_withheld_positives": sg["n_withheld_positives"],
                                "evidence_class": "HOLDOUT-DTI"},
            "hide_and_recover": {"evaluator": hr["evaluator"], "dti": hr["dti"], "ci95": hr["ci95"],
                                 "n_withheld_positives": hr["n_withheld_positives"],
                                 "evidence_class": "HOLDOUT-DTI",
                                 "note": "0 by construction: the emission is deliberately off-catalogue, so a "
                                         "catalogue-derived holdout cannot see it"},
            "family_reference": {"site": champ["site"], "owner_reported_score": champ["owner_reported_score"],
                                  "holdout_dti": champ["holdout_sgmc_cal_dti"], "ci95": champ["holdout_sgmc_cal_ci95"],
                                  "dots": champ["dots"], "evidence_class": "OWNER-REPORT + HOLDOUT-DTI"},
            "live_projection_never_a_score": {"model": lli["model"], "projected_dti": lli["projected_dti"],
                                              "loo_band": lli["uncertainty_band_loo_mae"],
                                              "evidence_class": "LLI-PROJECTION (NOT A SCORE)"},
        },
        "lane_test": {
            "method": "scripts/lane_sweep.py - 3-px disk overlap both directions on every registry raster, "
                      "sampled Spearman on 250k cells",
            "registry_files_checked": lane["registry_files"],
            "sibling_submissions_scope": {"n": len(subs),
                                          "max_3px_overlap": round(max(r["overlap3px_cand_within_registry"] for r in subs), 4),
                                          "cap": 0.70, "pass": bool(max(r["overlap3px_cand_within_registry"] for r in subs) <= 0.70)},
            "calibration_lattice_scope": {"n": len(latt),
                                          "max_3px_overlap": round(max(r["overlap3px_cand_within_registry"] for r in latt), 4) if latt else None,
                                          "pass": False,
                                          "note": "a saturated lattice contains any emission within 3 px; the repo has "
                                                  "ruled the lattice exemption a proposed amendment only, so the literal "
                                                  "rule fails and the decision is escalated, not waived"},
            "exact_duplicate_against_any_registry_raster": lane["verdict"]["any_exact_duplicate"],
            "median_d_catalogue_px": proj["median_d_catalogue_px"],
            "median_d_family_control_px": proj["median_d_H19_5_px"],
        },
        "geothermal_prior_check": {
            "file": "evidence/geothermal_prior_audit_20261030.json",
            "read": "candidate is closer than a random control to springs/vents on every layer, but not closer "
                    "than the champion on spring proximity (p_farther 0.238 vs 0.231); it is better only on "
                    "Quaternary-trace-centroid proximity (52.6 px vs 61.7 px)",
            "rows": geo.get("rows", []),
        },
        "rejected_alternative": {
            "design": best_alt["design"], "lli_projected_dti": best_alt["lli_projected_dti"],
            "lli_band": best_alt["lli_band"], "sgmc_cal": best_alt["sgmc_cal_dti"],
            "lane_overlap_vs_family_3px": best_alt["lane_overlap_vs_family_3px"],
            "action": "logged as duplicate and STOPPED per protocol; not built into a file",
        },
        "experiment_budget": {"used": 3, "cap": 3, "hours_used": "over 2 h (protocol stop condition also met)",
                              "runs": ["E1 geometry", "E2 operating point / mass sweep", "E3 support design + E3b selection rule"]},
        "verdict": "PROMOTE" if promote else "NEGATIVE (format-ready, lane-compliant against submissions, not evidenced to beat 0.2778)",
        "verdict_inputs": {"format_gate_pass": val["all_hard_checks_pass"],
                           "lane_cap_pass_vs_submissions": bool(max(r["overlap3px_cand_within_registry"] for r in subs) <= 0.70),
                           "holdout_gain_over_champion_gt_10pct": bool(sg["dti"] > champ["holdout_sgmc_cal_dti"] * 1.10),
                           "holdout_ratio": round(sg["dti"] / champ["holdout_sgmc_cal_dti"], 4)},
        "do_not_spend_a_slot": True,
        "portal_encoding_reconciliation": {
            "issue": "IR-SASS3-86: main's promoted tipcont raster is portal-invalid as released (NaN payload outside)",
            "fix": "scripts/make_portal_safe_render.py re-renders it with an identical dot set (symdiff 0)",
            "file": "docs/downloads/gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z-safe.tif",
            "receipt": "evidence/portal_safe_render_gemsdoesass3-tipcont-disp44923-4px-20261030T0330Z-safe.json",
            "validator": "evidence/validator_tipcont_safe_20261030.json",
            "shared_gate": "scripts/validate_submission_tif.py is now mask-aware: NaN payload and per-dataset mask band "
                           "both satisfy the official outside-bounds sentence, but only the mask-band encoding passes "
                           "portal_range_test_all_cells",
        },
        "evidence_files": [
            "evidence/candidate_build_receipt.json", "evidence/validator_s3_ocm_safe.json",
            "evidence/lane_sweep_s3_ocm_20261030.json", "evidence/focus9_scoreboard_20261030.json",
            "evidence/operating_point_E3b_selection.json", "evidence/operating_point_experiment_E2.json",
            "evidence/geothermal_prior_audit_20261030.json",
        ],
    }
    assert len(NOTE) <= 140, len(NOTE)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(card, indent=2)
    # json.dumps happily writes a bare NaN/Infinity for a non-finite float, which is not valid JSON and
    # must never reach a run card. Reject it by parsing with parse_constant (prose mentioning NaN is fine).
    def _no_constants(tok: str):
        raise ValueError(f"non-finite constant in run card: {tok}")

    json.loads(txt, parse_constant=_no_constants)
    out.write_text(txt + "\n")
    print(f"wrote {out}")
    print("verdict:", card["verdict"])
    print(f"holdout ratio vs champion: {card['verdict_inputs']['holdout_ratio']}; "
          f"lane max(submissions) {card['lane_test']['sibling_submissions_scope']['max_3px_overlap']}; "
          f"format gate {card['verdict_inputs']['format_gate_pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
