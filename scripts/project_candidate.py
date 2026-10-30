#!/usr/bin/env python3
"""Fast projection of one or more candidate rasters under every available truth density.

Companion to `scripts/lli_validate_candidate.py` (which also runs the pool-wide duplicate and 3-px lane
tests).  This one only builds the strata and projects, so it is cheap enough to run inside a build loop.

Densities used:
  published_S0 / published_S3 - GEMSDOE32's published fits (111 live rasters, LOO MAE 0.0219-0.0221)
  local_convex               - our own bounded-lambda refit on the locally mirrored live pool
  champion_control           - the 0.2778 file is projected in the same run so the comparison is a
                               difference of projections under identical conditions

Output: JSON on stdout and in evidence/projection_<name>.json.  Every number is a PROJECTION.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import ledger_inversion as li  # noqa: E402

spec_mod = importlib.util.spec_from_file_location("bl", ROOT / "scripts" / "build_lambda_candidate.py")
bl = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(bl)

CHAMP = Path("/tmp/g32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
LEDGER = ROOT / "evidence" / "score_ledger_index.json"


def mask_of(p, shape):
    with rasterio.open(p) as ds:
        a = ds.read(1)
    if a.shape != shape:
        raise SystemExit(f"{p}: grid mismatch {a.shape} != {shape}")
    return np.isfinite(a) & (a > 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates", nargs="+")
    ap.add_argument("--out", default="")
    ap.add_argument("--no-champion", action="store_true")
    a = ap.parse_args()

    ev = json.loads((ROOT / "evidence" / "lli_score_model_verification.json").read_text())
    th0 = np.array(ev["published_theta_check_on_local_pool"]["theta"], float)
    th3 = np.array(json.loads(Path("/home/user/reg32/live_ledger_inversion.json").read_text())
                   ["designs"]["S3"]["fit"]["theta"], float)
    sp0, lam0_grid, foot, lab, active, _ = bl.build_strata("S0", th0)
    sp3, lam3_grid, _, _, _, _ = bl.build_strata("S3", th3)
    lams = {"published_S0": (sp0, li.strata_lambda(th0, sp0)), "published_S3": (sp3, li.strata_lambda(th3, sp3))}

    shape = foot.shape
    led = json.loads(LEDGER.read_text())["index"]

    # local refit on the mirrored pool (bounded lambda + smoothness prior), independent of the published fits
    pool = sorted({p for g in ("/tmp/g32/docs/downloads/*.tif", "/home/user/focus/*.tif", "/home/user/ledger/*.tif")
                   for p in map(Path, __import__("glob").glob(g))})
    A, B, N, S, seen, rows = [], [], [], [], set(), []
    for p in pool:
        try:
            m = mask_of(p, shape)
        except SystemExit:
            continue
        dig = hashlib.sha256(np.round(np.where(m, 1.0, 0.0)[active], 5).tobytes()).hexdigest()[:16]
        if dig in seen or not m.any():
            continue
        seen.add(dig)
        live = None
        for stem, rec in led.items():
            if len(stem) > 8 and stem in p.name:
                live = rec["score"]
                break
        if live is None:
            continue
        row = li.design_row(np.where(m, 1.0, 0.0).astype(np.float32) * active, sp0)
        if row["N"] <= 0:
            continue
        A.append(row["A"]); B.append(row["B"]); N.append(row["N"]); S.append(live)
        rows.append({"file": p.name, "live": live})
    local_note = {"n_rasters_matched": len(S)}
    if len(S) >= 20:
        Aa, Ba, Na, sa = map(np.asarray, (A, B, N, S))
        fitc = li.fit_convex(Aa, Ba, Na, sa, sp0, mu=1.0)
        looc = li.loo_convex(Aa, Ba, Na, sa, sp0, mu=1.0)
        lams["local_convex"] = (sp0, fitc["lambda"])
        local_note.update({"loo_mae": looc["mae"], "loo_spearman": looc["spearman"],
                           "g_px": float(fitc["g"]), "lambda_max": float(fitc["lambda"].max()),
                           "lambda_min": float(fitc["lambda"].min()), "examples": rows[:6]})
    else:
        local_note["skipped"] = f"only {len(S)} pool rasters matched a live score"
    print(f"local refit: {json.dumps({k: v for k, v in local_note.items() if k != 'examples'})}", flush=True)

    out = {"schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "evidence_class": "PROJECTIONS (LLI-v1 model outputs); never scores. Champion row is the "
                             "control whose live score 0.2778 is OWNER-REPORT.",
           "densities": sorted(lams), "local_convex_fit": local_note, "candidates": {}}
    items = [(Path(c), "candidate") for c in a.candidates]
    if not a.no_champion and CHAMP.exists():
        items.append((CHAMP, "champion_control"))
    masks = {}
    for p, kind in items:
        masks[p.name] = (mask_of(p, shape), kind)
    for name, (m, kind) in masks.items():
        per = {}
        for tag, (sp, lam_vec) in lams.items():
            row = li.design_row(np.where(m, 1.0, 0.0).astype(np.float32) * active, sp)
            c = li.predict_components(row["A"][None, :], row["B"][None, :], np.array([row["N"]]),
                                      sp.sizes, lam_vec)
            per[tag] = {"projected_dti": float(c["dti"][0]), "tp": float(c["tp"][0]),
                        "fp": float(c["fp"][0]), "fn": float(c["fn"][0]), "dots": int(m.sum()),
                        "N_mass": float(row["N"])}
        out["candidates"][name] = {"role": kind, "sha256": bl.sha256_file(
            next(p for p, _ in items if p.name == name)), "projections": per}
    champ_rows = [v["projections"] for v in out["candidates"].values() if v["role"] == "champion_control"]
    for name, v in out["candidates"].items():
        if v["role"] != "candidate":
            continue
        deltas = {t: v["projections"][t]["projected_dti"] - c[t]["projected_dti"]
                  for t in v["projections"] for c in champ_rows if t in c}
        v["delta_vs_champion"] = {k: round(x, 4) for k, x in deltas.items()}
        v["delta_worst_case"] = round(min(deltas.values()), 4) if deltas else None
        v["maximin_beats_champion"] = bool(deltas) and min(deltas.values()) > 0
    print(json.dumps(out, indent=1))
    dest = Path(a.out) if a.out else ROOT / "evidence" / f"projection_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print("wrote", dest, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
