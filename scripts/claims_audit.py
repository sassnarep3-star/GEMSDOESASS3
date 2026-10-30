#!/usr/bin/env python3
"""Machine-checked reconciliation of every number this repository asserts in prose.

Reads the evidence receipts and, for each pinned claim, asserts that (a) the receipt carries exactly the value the
prose claims and (b) the prose documents (README.md, the lane report, the generated pages) render that value.
Any drift - a stale digit after a re-run, a rounded number that no longer rounds the same way, a receipt replaced
by a different run - fails this script. Exit 0 = every claim reconciles.

This is the anti-hallucination pass: the prose is not trusted, it is diffed against the bytes.
Writes evidence/claims_audit_<date>.json.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROSE = ("README.md", "docs/research/lane-H-SASS3-I-20261030.md", "docs/research/hypotheses-ranked-20261030.md",
         "index.html", "docs/index.html", "docs/executive-summary.html")


def load(rel: str):
    return json.loads((ROOT / rel).read_text())


def build_claims():
    card = load("evidence/current_run_card.json")
    name = card["submission_name"]
    audit = load(f"docs/downloads/{name}-audit.json")
    val = load("evidence/lli_candidate_validation_union.json")
    mat = load("evidence/lli_lambda_design_matrix_20261030.json")
    e5 = load("evidence/projection_e5_champ_plus_lamdots_20261030.json")
    lli = load("evidence/lli_score_model_verification.json")
    emi = load("evidence/lambda_emission_variants.json")
    pbc = load("evidence/pool_buffer_coverage_20261030.json")
    man = load("data/prepared_manifest.json")["counts"]
    summ, dup, pub, ref, ceil = val["projection_summary"], val["duplicate_tests"], \
        lli["published_theta_check_on_local_pool"], lli["local_refit"], emi["lane_feasibility_ceiling"]

    def vp(density, role):
        return val["projections"][density][role]["projected_dti"]

    def row(frag):
        return next(v for k, v in mat["candidates"].items() if frag in k)

    e5row = next(v for v in e5["candidates"].values() if v["role"] == "candidate")
    R = round
    return [
        # packaged artefact and its own receipt chain
        ("shipped_sha256_is_the_same_file_everywhere", audit["sha256_tif"], card["raster_sha256"],
         [audit["sha256_tif"]], "card, README and audit agree on the digest"),
        ("shipped_bytes", audit["bytes"], 49162447, [], "the .tif is uncompressed, like the accepted champion"),
        ("positive_cells", audit["positive_cells"], card["validator_output"]["positive_cells"], ["20,416"],
         "dot count quoted in prose"),
        ("emitted_value", audit["emitted_value"], 1.0, [], "binary surface is optimal under a max"),
        ("outside_mode_is_zeros", audit["outside_mode"].split(" ")[0], "zeros", ["zeros"],
         "portal-safe convention (IR-SASS3-75)"),
        ("nodata_tag", audit["grid"]["nodata"], None, [], "no nodata tag: nothing escapes the range check"),
        ("crs_and_shape", f"{audit['grid']['crs']} {audit['grid']['width']}x{audit['grid']['height']}",
         "EPSG:32611 3292x3730", ["3292 x 3730", "3292×3730", "EPSG:32611"], "grid facts"),
        ("transform", audit["grid"]["transform"], [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0], [],
         "grid facts"),
        # uniqueness
        ("duplicate_test_pool_size", dup["n_pool"], 122, ["122-raster", "122 rasters"],
         "the pool the uniqueness verdict rests on"),
        ("packager_pool_sweep", audit["pool_size_checked"], 126, ["126"],
         "the pool the packager XOR sweep covers"),
        ("buffer_measurement_pool", pbc["pool_rasters_read"], 130, ["130"],
         "the pool the infeasibility proof covers"),
        ("identical_sibling_files", audit["identical_sibling_files"], [], [], "0 duplicates"),
        ("worst_exact_cell_share", R(audit["worst_sibling_exact_cell_share"]["frac"], 4), 0.3138, ["31.4%", "31.38%"],
         "uniqueness margin quoted in prose"),
        ("min_xor_cells", R(dup["min_xor_cells"]["cells"]), 48204, ["48,204"], "falsifiable duplicate test"),
        ("worst_3px_overlap", R(dup["worst_3px_overlap"]["frac"], 4), 1.0, ["1.000", "100.0%"],
         "literal lane number, reported not hidden"),
        ("lattice_3px_overlap", R(audit["calibration_lattice_3px_overlap"], 6), 0.998775, ["99.88%", "99.8775"],
         "overlap against the 13GEMSDOE calibration lattice"),
        ("lane_gate_disclosed_as_infeasible", card["registry_correlation_and_overlap"]
         ["literal_uniqueness_gate"].split(" ")[0], "NOT", ["NOT SATISFIABLE-BY-CONSTRUCTION"], "IR-SASS3-76"),
        ("pool_buffer_coverage", R(pbc["buffer_coverage_of_scored_domain"], 5), 1.0,
         ["99.99996", "5,167,371"], "the 3-px rule leaves two usable cells"),
        ("cells_left_for_a_lane_compliant_raster", pbc["cells_a_lane_compliance_raster_may_use"]
         if "cells_a_lane_compliance_raster_may_use" in pbc else pbc["cells_a_lane_compliant_raster_may_use"],
         2, ["2 usable cells", "2 cells out of 5,106,385"], "IR-SASS3-76"),
        ("strict_compliance_ceiling", float(f"{ceil['max_projected_dti']:.3e}"), 7.408e-08, ["7.4e-08"],
         "upper bound over strictly compliant rasters"),
        ("pool_union_dots", pbc["pool_union_dots"], 2565397, ["2,565,397"], "pool size in the lane report"),
        # projections
        ("proj_S0_candidate", R(vp("published_S0", "candidate"), 4), R(audit["projections"]["candidate"]
                                                                        ["published_S0"], 4), ["0.4010", "0.401"],
         "lane report table + card bracket"),
        ("proj_S3_candidate", R(vp("published_S3", "candidate"), 4), 0.2346, ["0.2346"], "lane report table"),
        ("proj_local_candidate", R(vp("local_convex", "candidate"), 4), 0.1614, ["0.1614", "0.161"],
         "third density"),
        ("proj_S0_champion", R(vp("published_S0", "champion_control"), 4), 0.2860, ["0.2860"], "control"),
        ("proj_S3_champion", R(vp("published_S3", "champion_control"), 4), 0.2843, ["0.2843"], "control"),
        ("proj_local_champion", R(vp("local_convex", "champion_control"), 4), 0.2664, ["0.2664"], "control"),
        ("paired_delta_S0", R(vp("published_S0", "candidate") - vp("published_S0", "champion_control"), 4),
         0.1150, ["+0.1150"], "README bracket"),
        ("paired_delta_S3", R(vp("published_S3", "candidate") - vp("published_S3", "champion_control"), 4),
         -0.0496, ["−0.0496"], "README bracket"),
        ("paired_delta_local", R(vp("local_convex", "candidate") - vp("local_convex", "champion_control"), 4),
         -0.1051, ["−0.1051"], "README bracket"),
        ("delta_worst_unpaired", R(summ["delta_worst_case"], 4), -0.1246, ["−0.125", "-0.1246", "−0.1246"],
         "the promotion rule outcome"),
        ("delta_best", R(summ["delta_best_case"], 4), 0.1346, ["0.1346"], "bracket sentence"),
        ("densities_tested", summ["n_lambda_variants"], 3, ["three truth densities", "three densities",
                                                              "three-density"],
         "not a single-density comparison"),
        ("promotion_rule_passed", card["projection_bracket"]["promotion_rule_passed"], False,
         ["negative for promotion"], "the verdict"),
        ("ok_to_download", card["ok_to_download"], True, ["**true**"], "download flag in the README table"),
        ("ok_to_submit", card["ok_to_submit"], False, ["**false**"], "submission flag in the README table"),
        # design matrix
        ("E1_S0", R(row("17187")["projections"]["published_S0"]["projected_dti"], 4), 0.3983, ["0.3983"], "E1"),
        ("E1_worst", R(row("17187")["delta_worst_case"], 4), -0.1265, ["−0.1265", "-0.1265"], "E1"),
        ("E2_worst", R(row("12953")["delta_worst_case"], 4), -0.1204, ["−0.1204", "-0.1204"], "E2"),
        ("E4_dots", row("meadots")["projections"]["published_S0"]["dots"], 17489, ["17,489"], "E4"),
        ("E4_worst", R(row("meadots")["delta_worst_case"], 4), -0.1141, ["−0.1141", "-0.1141"], "E4"),
        ("E5_worst", R(e5row["delta_worst_case"], 4), -0.0195, ["−0.0195", "-0.0195"], "E5"),
        ("E5_dots", e5row["projections"]["published_S0"]["dots"], 56295, ["56,295"], "E5"),
        # grid facts
        ("footprint_px", man["footprint_valid_pixels"], 5167373, ["5,167,373"], "scored domain"),
        ("outside_px", man["outside_footprint_pixels"], 7111787, ["7,111,787"], "outside the bounds"),
        ("catalogue_px", man["positive_catalogue_label_pixels"], 60988, ["60,988"], "labels.tif positives"),
        ("active_px", man["negative_in_footprint_pixels"], 5106385, ["5,106,385"], "scored minus catalogue"),
        # LLI instrument
        ("lli_mae", R(pub["mae"], 4), 0.0192, ["0.0192", "0.01920"], "instrument accuracy"),
        ("lli_spearman", R(pub["spearman_pred_vs_live"], 5), 0.94408, ["0.94408"], "instrument rank agreement"),
        ("lli_refit_loo", R(ref["loo_mae"], 5), 0.02023, ["0.02023"], "cross-validation claim"),
        ("lli_refit_lso", R(ref["leave_site_out_mae"], 5), 0.02164, ["0.02164"], "cross-validation claim"),
        ("lli_upstream_loo", R(ref["upstream_loo_mae"], 6), 0.022069, ["0.022069"], "published fit comparison"),
        ("lli_g_px", R(pub["g_truth_pixels"], 4), 16948.2757, ["16,948.2757", "16,948.3", "16948.2757"],
         "spec reproduction"),
        ("local_refit_pool_n", val["local_convex_fit"]["n_rasters"], 33, [], "the third density's pool"),
        ("local_refit_loo_mae", R(val["local_convex_fit"]["loo_mae"], 4), 0.0212, ["0.0212"], "±0.02 error claim"),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    texts = {p: (ROOT / p).read_text() if (ROOT / p).is_file() else "" for p in PROSE}
    rows, mismatches = [], []
    for cid, receipt, expect, renderings, note in build_claims():
        ok_value = receipt == expect
        hits = [p for p, t in texts.items() if t and any(s in t for s in renderings)] if renderings else ["n/a"]
        row = {"id": cid, "receipt_value": receipt, "expected": expect, "note": note,
               "value_matches": bool(ok_value), "rendered_in": hits, "prose_ok": bool(hits)}
        rows.append(row)
        if not (ok_value and hits):
            mismatches.append(cid)
    out = {"schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "purpose": "reconcile prose numbers against evidence receipts (anti-hallucination pass)",
           "claims": len(rows), "reconciled": len(rows) - len(mismatches), "mismatches": mismatches,
           "rows": rows,
           "external_claims_not_locally_verifiable": [
               {"claim": "leaderboard #1 0.4544 (xiaofanhu), #2 0.3916, #5 0.3642, fetched 2026-10-30",
                "source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
                "class": "LEADERBOARD-PAGE (public split); fetched, not an organizer receipt"},
               {"claim": "live scores of the nine focus-site files (0.2449-0.2778)",
                "source": "reg32/docs/score-ledger.csv and site mirrors",
                "class": "OWNER-REPORT; not organizer receipts"}]}
    dest = Path(a.out) if a.out else ROOT / "evidence" / f"claims_audit_{time.strftime('%Y%m%d', time.gmtime())}.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("claims", "reconciled", "mismatches")}, indent=1))
    for r in rows:
        if not (r["value_matches"] and r["prose_ok"]):
            print("  FAIL", json.dumps(r))
    print("wrote", dest)
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
