#!/usr/bin/env python3
"""Re-derive every number in evidence/session_card_20261030.json from its receipt and fail on any mismatch.

This is the anti-hallucination gate for the site: if a number on the page cannot be reproduced from the
file named in `sources`, the build is wrong. Exit 0 = all numbers reproduce.

Usage: python scripts/verify_session_card.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"


def load(name: str) -> dict:
    return json.loads((EV / name).read_text())


def close(a, b, tol: float = 1e-9) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def main() -> int:
    card = load("session_card_20261030.json")
    sdr = load("sdr1_build_receipt.json")
    exp3 = load(sorted(EV.glob("exp3_sarpu_legal21k_*.json"))[-1])
    hr = load("hide_recover_legal_lane_20261030.json")
    sg = load("sgmc_cal_legal_lane_20261030.json")
    focus9_part = load("sgmc_cal_focus9_partial_20261030.json")
    focus9_rest = load("sgmc_cal_focus9_rest_20261030.json")
    uq = load("uniqueness_audit_legal_lane_20261030.json")
    uq3 = load("uniqueness_audit_exp3_20261030.json")
    union = load("registry_union_coverage_20261030.json")
    conc = load("focus9_concordance_20261030.json")
    champ_lat = load("champion_lattice_overlap_20261030.json")
    led = load("lwst_experiment_ledger.json")

    exp3_name = Path(exp3["output"]["tif"]).name
    sdr_name = Path(sdr["output"]["tif"]).name
    checks: list[tuple[str, bool, str]] = []

    def chk(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    # decision block (2026-10-31: the promoted file is the LB-inversion candidate in the portal-safe
    # encoding; the tipcontinuation raster stays as a superseded alternative)
    d = card["decision"]
    tip = load("hide_recover_tipcont_20261030.json")
    safe_build = json.loads((ROOT / "docs/downloads/gemsdoesass3-lbinv-84262-20261030T0900Z-safe-build.json").read_text())
    chk("decision.file==lbinv-safe", d["file_to_download"] == safe_build["submission_name"] + ".tif", d["file_to_download"])
    chk("decision.dots==lbinv-safe receipt", d["dots"] == safe_build["n_dots"])
    import hashlib
    tp = ROOT / "docs" / "downloads" / d["file_to_download"]
    chk("decision file exists", tp.exists(), str(tp))
    if tp.exists():
        h = hashlib.sha256()
        with tp.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        chk("decision sha matches bytes", h.hexdigest() == d["tif_sha256"], h.hexdigest())
    z = ROOT / "docs" / "downloads" / d["zip"]
    chk("decision zip exists", z.exists(), str(z))
    if z.exists():
        hz = hashlib.sha256(z.read_bytes()).hexdigest()
        chk("decision zip sha matches bytes", hz == d["zip_sha256"], hz)
    chk("sdr1 is a listed alternative", any(a["file"] == sdr_name for a in d["alternatives"]))
    chk("blocked file==exp3", d["blocked"]["file"] == exp3_name)

    # estimates
    e = card["estimates"]
    chk("exp3 HR", close(e["exp3"]["hide_and_recover"]["point"], exp3["hide_and_recover"]["pooled_dti"]))
    chk("exp3 HR CI", e["exp3"]["hide_and_recover"]["ci95"] == exp3["hide_and_recover"]["ci95"])
    chk("exp3 SGMC", close(e["exp3"]["sgmc_cal"]["point"], exp3["sgmc"]["calibrated"]))
    chk("sdr1 HR", close(e["sdr1"]["hide_and_recover"]["point"], hr["sdr1_spaced_dense"]["pooled_dti"]))
    chk("sdr1 SGMC", close(e["sdr1"]["sgmc_cal"]["point"], sg["results"]["sdr1_spaced_dense"]["calibrated"]))
    chk("incumbent HR", close(e["incumbent_disp21k"]["hide_and_recover"]["point"], hr["disp21k_incumbent"]["pooled_dti"]))
    chk("incumbent SGMC", close(e["incumbent_disp21k"]["sgmc_cal"]["point"], focus9_part["results"]["disp21k_current"]["calibrated"]))
    chk("champion HR ref", close(e["champion_reference"]["hide_and_recover"]["point"],
                                  led["baseline_champion_02778"]["holdout_dti"]["pooled_dti"]))
    chk("exp2 ref HR", close(e["supervised_reference_exp2_37654"]["hide_and_recover"]["point"],
                              led["experiments"]["EXP2_LWST_SARPU_DUAL_OOF"]["holdout_dti"]["pooled_dti"]))

    # uniqueness
    u = card["uniqueness"]
    chk("sdr1 max within3", u["sdr1"]["max_within3"]["frac"] == uq["summary"][sdr_name]["max_within3"]["frac"])
    chk("sdr1 surface rho", u["sdr1"]["surface_stage"]["max_abs_surface_spearman"]["rho"]
        == uq["summary"][sdr_name]["surface_stage"]["max_abs_surface_spearman"]["rho"])
    chk("exp3 max within3", u["exp3_binary_surface"]["max_within3"]["frac"] == uq3["summary"][exp3_name]["max_within3"]["frac"])
    chk("registry coverage full", uq["registry_coverage"]["ok"] == 386 and uq["registry_coverage"]["coverage_gap"] == 0
        and uq["registry_coverage"]["sha_mismatch"] == 0, str(uq["registry_coverage"]))
    chk("union coverage", card["union_coverage"]["footprint_covered_by_union_3px"] == union["footprint_covered_by_union_3px"])
    chk("champion lattice overlap", card["champion_lattice_overlap"]["champion_within3_of_lattice_frac"]
        == champ_lat["champion_within3_of_lattice_frac"])

    # canary
    chk("canary worst", close(card["canary"]["worst_symmetric_auc"], exp3["leakage_canary"]["worst_symmetric_auc"]))
    chk("canary pass", card["canary"]["result"] is True)

    # projections reproduce from the calibration receipt
    p = card["projections"]
    chk("factor", close(p["calibration"]["factor"], conc["transfer_factor"]))
    chk("spearman", close(p["calibration"]["spearman_rho"], conc["spearman"]))
    chk("sdr1 projection", close(p["files"]["sdr1"]["projected_lb"],
                                  round(sg["results"]["sdr1_spaced_dense"]["calibrated"] * conc["transfer_factor"], 3), 1e-3))
    chk("disp21k projection", close(p["files"]["disp21k"]["projected_lb"],
                                     round(focus9_part["results"]["disp21k_current"]["calibrated"] * conc["transfer_factor"], 3), 1e-3))
    chk("exp3 projection", close(p["files"]["exp3"]["projected_lb"],
                                  round(exp3["sgmc"]["calibrated"] * conc["transfer_factor"], 3), 1e-3))
    tip_sg = load("sgmc_cal_tipcont_20261030.json")["results"]["tipcont_44923"]
    chk("tipcont projection", close(p["files"]["tipcont"]["projected_lb"],
                                     round(tip_sg["calibrated"] * conc["transfer_factor"], 3), 1e-3))
    tip_uq = load("uniqueness_audit_tipcont_20261030.json")
    chk("tipcont Rule 1", tip_uq["summary"][tip["file"]]["passes_rule_1"] is True)
    chk("tipcont HR", close(card["estimates_tipcont"]["hide_and_recover"]["point"], tip["pooled_dti"]))

    # nine-site rows all carry a proxy measurement
    chk("nine focus rows", len(card["focus9"]) == 9 and all(r["sgmc_cal_holdout_dti"] for r in card["focus9"]))
    site_key = {"GEMSDOE24": ("p", "gems24_d1p5"), "GEMSDOE25": ("p", "gems25_d2p8"), "GEMSDOE27": ("p", "gems27_tgc_v2"),
                "GEMSDOE28": ("p", "gems28_h27_4_r1"), "GEMSDOE30": ("r", "gems30_d28"), "GEMSDOE31": ("r", "gems31_h27_4"),
                "GEMSDOE32": ("r", "gems32_champion"), "GEMSDOE33": ("r", "gems33_h33d"), "GEMSDOE36": ("r", "gems36_anderson")}
    for row in card["focus9"]:
        src, key = site_key[row["site"]]
        ref = (focus9_part if src == "p" else focus9_rest)["results"][key]
        chk(f"{row['site']} proxy", close(row["sgmc_cal_holdout_dti"]["point"], ref["calibrated"]))

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail and not ok else ''}")
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks reproduce")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
