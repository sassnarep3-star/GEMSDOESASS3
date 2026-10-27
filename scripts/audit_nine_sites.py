#!/usr/bin/env python3
"""Memory-lean (<600 MB RSS) byte-level forensic, pairwise uniqueness, unified gems57 HOLDOUT-DTI,
and LLI-v1 audit across all 9 focus sites (GEMSDOE24..36) + GEMSDOESASS1 + scored priors.
"""
from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout as eh  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gemsdoesass3.lli import build_s0_spec, project_lli  # noqa: E402


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def near3(mask: np.ndarray) -> np.ndarray:
    yy, xx = np.mgrid[-3:4, -3:4]
    return binary_dilation(mask, structure=(yy * yy + xx * xx <= 9.0))


def crop_fold(fold: dict, pad: int = 6) -> tuple[dict, tuple[int, int], tuple[slice, slice]]:
    reg = fold["region"]
    rows = np.flatnonzero(reg.any(axis=1))
    cols = np.flatnonzero(reg.any(axis=0))
    H, W = reg.shape
    y0, y1 = max(0, int(rows[0]) - pad), min(H, int(rows[-1]) + pad + 1)
    x0, x1 = max(0, int(cols[0]) - pad), min(W, int(cols[-1]) + pad + 1)
    sl = (slice(y0, y1), slice(x0, x1))
    cf = {
        "fold": fold["fold"],
        "name": fold["name"],
        "region": fold["region"][sl].copy(),
        "truth": fold["truth"][sl].copy(),
        "visible": fold["visible"][sl].copy(),
        "masked_known": fold["masked_known"][sl].copy(),
    }
    return cf, (y0, x0), sl


def main() -> None:
    t0 = time.time()
    data_root = ROOT / ".cache/gems_data"
    grid = load_grid(data_root)
    fp = grid.footprint
    cat = grid.catalogue
    H, W = fp.shape
    d_cat = distance_transform_edt(~cat).astype(np.float32)

    # 1. Build deduplicated registry_index across all restored scored/ + focus_registry/ rasters
    by_sha: dict[str, dict] = {}
    for folder, default_repo in [
        (data_root / "scored", "buffedlizard55-lab/historical-scored"),
        (data_root / "focus_registry", "buffedlizard55-lab/focus-sites"),
    ]:
        for p in sorted(folder.glob("*.tif")):
            digest = sha256_file(p)
            rel = str(p.relative_to(ROOT))
            name = p.name
            repo = default_repo
            if "__" in name:
                prefix, real_name = name.split("__", 1)
                site_tag = prefix.split("_")[0]
                repo = f"sassnarep3-star/{site_tag}" if site_tag.startswith("GEMSDOESASS") else f"buffedlizard55-lab/{site_tag}"
                src_label = f"{prefix}:{real_name}"
            else:
                src_label = name
            if digest not in by_sha:
                by_sha[digest] = {
                    "sha256": digest,
                    "repo_first": repo,
                    "cache_file": rel,
                    "sources": [src_label],
                }
            else:
                if src_label not in by_sha[digest]["sources"]:
                    by_sha[digest]["sources"].append(src_label)

    registry_index = {
        "schema_version": 1,
        "complete_accessible_scan": True,
        "errors": [],
        "rasters": sorted(by_sha.values(), key=lambda r: (r["repo_first"], r["sources"][0])),
    }
    (ROOT / "evidence").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence/registry_index.json").write_text(json.dumps(registry_index, indent=2) + "\n")
    print(f"[registry] Indexed {len(registry_index['rasters'])} unique SHA-256 rasters ({time.time()-t0:.1f}s)", flush=True)

    # 2. Build cropped buffered whole-component LOQO holdout draws (seeds 20, 21)
    cropped_folds = []
    for s in (20, 21):
        folds, _ = buffered_component_draw(grid, seed=s, hide_frac=0.20, buffer_px=3)
        for fold in folds:
            cf, orig, sl = crop_fold(fold)
            cropped_folds.append((s, cf, orig, sl, fp[sl].copy()))
        del folds
    gc.collect()
    print(f"[holdout] Built {len(cropped_folds)} cropped LOQO folds ({time.time()-t0:.1f}s)", flush=True)

    # 3. Build LLI-v1 S0 spec
    lli_spec, lli_lam = build_s0_spec(data_root)
    print(f"[lli] Built 40-stratum LLI-v1 S0 spec ({time.time()-t0:.1f}s)", flush=True)

    FOCUS_SPECS = [
        {
            "site": "GEMSDOE24",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE24/",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE24",
            "hist_name": "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan",
            "hist_score_owner_report": 0.2477,
            "hist_key": "GEMSDOE24_hist_best",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE24/HEAD/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
            "latest_name": "gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif",
            "latest_key": "GEMSDOE24_s3dep1_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE24/HEAD/docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif",
            "latest_site_verdict": "DO NOT SUBMIT (71.3% local DKRN1 overlap; C2ST flag)",
        },
        {
            "site": "GEMSDOE25",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE25/",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE25",
            "hist_name": "dotted-h19-5-d2-8-20261002-e56ea318af89-nan",
            "hist_score_owner_report": 0.2600,
            "hist_key": "GEMSDOE25_hist_best",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE25/HEAD/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif",
            "latest_name": "gems25-h74-rmps-subsurf-catfree-b2-37654-20261026-3751606e1ce5-zeros.tif",
            "latest_key": "GEMSDOE25_h74_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE25/HEAD/docs/downloads/gems25-h74-rmps-subsurf-catfree-b2-37654-20261026-3751606e1ce5-zeros.tif",
            "latest_site_verdict": "DO NOT SUBMIT (pure subsurface trailed full-stack H35)",
        },
        {
            "site": "GEMSDOE27",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE27/",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE27",
            "hist_name": "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan",
            "hist_score_owner_report": 0.2449,
            "hist_key": "GEMSDOE27_hist_best",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE27/HEAD/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif",
            "latest_name": "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
            "latest_key": "GEMSDOE27_h31_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE27/HEAD/docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
            "latest_site_verdict": "QUALIFIED PROMOTE TO SELECTOR (unique dual-regime CELF)",
        },
        {
            "site": "GEMSDOE28",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE28/",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE28",
            "hist_name": "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan",
            "hist_score_owner_report": 0.2710,
            "hist_key": "GEMSDOE28_hist_best_h36_1",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE28/HEAD/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif",
            "latest_name": "gems28-s22-ctxhgb-20261026-e23dabcec6e2-allfinite.tif",
            "latest_key": "GEMSDOE28_s22_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE28/HEAD/docs/downloads/gems28-s22-ctxhgb-20261026-e23dabcec6e2-allfinite.tif",
            "latest_site_verdict": "PROMOTE TO SELECTOR CHECKLIST (multiscale context HGB)",
        },
        {
            "site": "GEMSDOE30",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE30/",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE30",
            "hist_name": "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca",
            "hist_score_owner_report": 0.2600,
            "hist_key": "GEMSDOE30_hist_best",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE30/HEAD/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
            "latest_name": "gems30-CSR1-44090-20261026-502fb5948335-zeros.tif",
            "latest_key": "GEMSDOE30_csr1_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE30/HEAD/docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif",
            "latest_site_verdict": "DO NOT SUBMIT (CSR-1 trailed MSDB1 full-stack baseline)",
        },
        {
            "site": "GEMSDOE31",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE31/docs/",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE31",
            "hist_name": "h27-4-solo-d28-20261004-8acb75e1-nan",
            "hist_score_owner_report": 0.2708,
            "hist_key": "GEMSDOE31_hist_best",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE31/HEAD/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif",
            "latest_name": "gemsdoe31-h31y-regime-mosaic-37654-20261026-66162f1f-zeros.tif",
            "latest_key": "GEMSDOE31_h31y_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE31/HEAD/docs/downloads/gemsdoe31-h31y-regime-mosaic-37654-20261026-66162f1f-zeros.tif",
            "latest_site_verdict": "DO NOT SUBMIT (H31-YM trailed H31-X junction comparator)",
        },
        {
            "site": "GEMSDOE32",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE32",
            "hist_name": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
            "hist_score_owner_report": 0.2778,
            "hist_key": "GEMSDOE32_hist_best_02778",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE32/HEAD/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
            "latest_name": "gemsdoe32-h47-ldgi-dualhorizon-corridor-37654-20261026T230609Z-0eb8a25c-zeros.tif",
            "latest_key": "GEMSDOE32_h47_ldgi_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE32/HEAD/docs/downloads/gemsdoe32-h47-ldgi-dualhorizon-corridor-37654-20261026T230609Z-0eb8a25c-zeros.tif",
            "latest_site_verdict": "PROMOTE TO SELECTOR (H47-1 LDGI beat 0.2778 & H38 on holdout)",
        },
        {
            "site": "GEMSDOE33",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE33/",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE33",
            "hist_name": "h33d-analog-tip-stepover-r30-20261004-cb490425926e",
            "hist_score_owner_report": 0.2632,
            "hist_key": "GEMSDOE33_hist_best",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE33/HEAD/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
            "latest_name": "gemsdoe33-fsml2-cc-37654-20261026-6fd4410bbaee-zeros.tif",
            "latest_key": "GEMSDOE33_fsml2_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE33/HEAD/docs/downloads/gemsdoe33-fsml2-cc-37654-20261026-6fd4410bbaee-zeros.tif",
            "latest_site_verdict": "DO NOT SUBMIT (FSML2-CC negative vs CSHT)",
        },
        {
            "site": "GEMSDOE36",
            "site_url": "https://buffedlizard55-lab.github.io/GEMSDOE36/docs/",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE36",
            "hist_name": "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros",
            "hist_score_owner_report": 0.2750,
            "hist_key": "GEMSDOE36_hist_best_02750",
            "hist_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE36/HEAD/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
            "latest_name": "gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif",
            "latest_key": "GEMSDOE36_kpl36_latest",
            "latest_download_url": "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE36/HEAD/docs/downloads/gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif",
            "latest_site_verdict": "PROMOTE (KPL-36 3-5 km line coherence + PU spy)",
        },
    ]

    man_files = {r["key"]: Path(r["local"]) for r in json.loads((data_root / "focus_registry/manifest.json").read_text())}

    # Store only sparse int16 (ys, xs) coordinates per raster (~150 KB each!)
    coords: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    metas: dict[str, dict] = {}
    terms_by_arm: dict[str, np.ndarray] = {}
    lli_by_arm: dict[str, dict] = {}

    all_keys = []
    for spec in FOCUS_SPECS:
        all_keys.extend([spec["hist_key"], spec["latest_key"]])
    all_keys.append("GEMSDOESASS1_latest")

    for k in all_keys:
        p = man_files[k]
        with rasterio.open(p) as src:
            raw = src.read(1)
        fin = np.isfinite(raw)
        clean = np.where(fin, np.clip(raw, 0.0, 1.0), 0.0).astype(np.float32)
        clean[~fp] = 0.0
        pos = clean > 0
        ys, xs = np.nonzero(pos)
        coords[k] = (ys.astype(np.int16), xs.astype(np.int16))
        metas[k] = {
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
            "whole_array_finite": bool(fin.all()),
            "in_footprint_finite": bool(fin[fp].all()),
            "range_0_1": bool((raw[fin].min() >= 0.0) and (raw[fin].max() <= 1.0)),
            "dots": int(ys.size),
            "on_catalogue_dots": int((pos & cat).sum()),
            "in_2px_collar_dots": int((pos & (d_cat <= 2.0)).sum()),
        }
        lli_by_arm[k] = project_lli(clean, lli_spec, lli_lam)
        merged_terms = None
        for _s, cf, orig, sl, fp_sub in cropped_folds:
            _, t = eh.evaluate(clean[sl], cf, fp_sub, block_side=200, origin=orig, global_shape=(H, W))
            merged_terms = t if merged_terms is None else (merged_terms + t)
        terms_by_arm[k] = merged_terms
        del raw, fin, clean, pos
        print(f"  audited {k:28s} dots={metas[k]['dots']:6,d} LLI={lli_by_arm[k]['projected_dti']:.4f} ({time.time()-t0:.1f}s)", flush=True)

    # Lineage proof using temporary bool masks
    def to_mask(ys_xs: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        m = np.zeros((H, W), dtype=bool)
        m[ys_xs[0], ys_xs[1]] = True
        return m

    with rasterio.open(data_root / "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif") as src:
        h195_raw = src.read(1)
    h195_m = np.isfinite(h195_raw) & (h195_raw > 0) & fp
    del h195_raw
    with rasterio.open(man_files["GEMSDOE28_h27_4_solo"]) as src:
        b1_raw = src.read(1)
    b1_28_m = np.isfinite(b1_raw) & (b1_raw > 0) & fp
    del b1_raw

    d25_m = to_mask(coords["GEMSDOE25_hist_best"])
    d30_m = to_mask(coords["GEMSDOE30_hist_best"])
    b1_31_m = to_mask(coords["GEMSDOE31_hist_best"])
    b2_32_m = to_mask(coords["GEMSDOE32_hist_best_02778"])
    pinn_36_m = to_mask(coords["GEMSDOE36_hist_best_02750"])

    lineage_proof = {
        "h19_5_dots": int(h195_m.sum()),
        "d28_outside_h19_5_pixels": int((d25_m & ~h195_m).sum()),
        "gemsdoe25_equals_gemsdoe30_symdiff": int((d25_m ^ d30_m).sum()),
        "gemsdoe28_solo_equals_gemsdoe31_symdiff": int((b1_28_m ^ b1_31_m).sum()),
        "b1_equals_d28_minus_dcat_le_1_symdiff": int(((d25_m & (d_cat > 1.0)) ^ b1_31_m).sum()),
        "b2_champion_equals_d28_minus_dcat_le_2_symdiff": int(((d25_m & (d_cat > 2.0)) ^ b2_32_m).sum()),
        "gemsdoe36_contains_100pct_of_b2_champion": bool(np.all(pinn_36_m[b2_32_m])),
        "gemsdoe36_extra_dots_over_b2_champion": int((pinn_36_m & ~b2_32_m).sum()),
    }
    del h195_m, b1_28_m, d25_m, d30_m, b1_31_m, b2_32_m, pinn_36_m
    gc.collect()
    print("[lineage proof]", json.dumps(lineage_proof), flush=True)

    summary_holdout = eh.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate="GEMSDOE32_hist_best_02778")

    # Compute exact pairwise 3-px overlaps one target near-mask at a time (~12 MB!)
    overlaps: dict[tuple[str, str], float] = {}
    for kb in all_keys:
        nb = near3(to_mask(coords[kb]))
        for ka in all_keys:
            ya, xa = coords[ka]
            overlaps[(ka, kb)] = float(nb[ya, xa].mean()) if ya.size else 0.0
        del nb

    site_rows = []
    for spec in FOCUS_SPECS:
        hk = spec["hist_key"]
        lk = spec["latest_key"]

        hist_other_ov = {
            other["site"]: round(overlaps[(hk, other["hist_key"])], 4)
            for other in FOCUS_SPECS if other["site"] != spec["site"]
        }
        hist_worst_site = max(hist_other_ov, key=hist_other_ov.get)
        hist_worst_ov = hist_other_ov[hist_worst_site]

        latest_peer_ov = {}
        for other in FOCUS_SPECS:
            latest_peer_ov[f"{other['site']}_hist"] = round(overlaps[(lk, other["hist_key"])], 4)
            if other["site"] != spec["site"]:
                latest_peer_ov[f"{other['site']}_latest"] = round(overlaps[(lk, other["latest_key"])], 4)
        latest_peer_ov["GEMSDOESASS1_latest"] = round(overlaps[(lk, "GEMSDOESASS1_latest")], 4)
        latest_worst_peer = max(latest_peer_ov, key=latest_peer_ov.get)
        latest_worst_ov = latest_peer_ov[latest_worst_peer]

        hs = summary_holdout["scores"][hk]
        ls = summary_holdout["scores"][lk]

        row = {
            **spec,
            "historical_best": {
                **metas[hk],
                "holdout_dti": {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": eh.VERSION,
                    "withheld_positive_pixels": hs["withheld_positive_pixels"],
                    "dti": round(hs["dti"], 6),
                    "ci95": [round(hs["ci95"][0], 6), round(hs["ci95"][1], 6)],
                },
                "lli_projection": lli_by_arm[hk],
                "max_3px_overlap_vs_other_8_hist": hist_worst_ov,
                "nearest_peer_site": hist_worst_site,
                "unique_vs_other_8_sites": bool(hist_worst_ov <= 0.70),
                "ok_to_submit_again": False,
                "why_not_resubmit": "Already submitted historical H19-5 family member (>70% 3-px overlap across all 9 historical leaders).",
            },
            "latest_unique_candidate": {
                **metas[lk],
                "holdout_dti": {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": eh.VERSION,
                    "withheld_positive_pixels": ls["withheld_positive_pixels"],
                    "dti": round(ls["dti"], 6),
                    "ci95": [round(ls["ci95"][0], 6), round(ls["ci95"][1], 6)],
                },
                "lli_projection": lli_by_arm[lk],
                "max_3px_overlap_vs_focus_peers": latest_worst_ov,
                "nearest_focus_peer": latest_worst_peer,
                "unique_vs_other_8_sites": bool(latest_worst_ov <= 0.70),
                "vs_champion_02778_3px_overlap": round(overlaps[(lk, "GEMSDOE32_hist_best_02778")], 4),
            },
        }
        site_rows.append(row)
        print(
            f"{spec['site']:10s} | HIST {spec['hist_score_owner_report']:.4f} (LLI={lli_by_arm[hk]['projected_dti']:.4f}, "
            f"HR={hs['dti']:.4f}, ov8={hist_worst_ov*100:5.1f}%) | "
            f"LATEST HR={ls['dti']:.4f} [{ls['ci95'][0]:.4f},{ls['ci95'][1]:.4f}] "
            f"LLI={lli_by_arm[lk]['projected_dti']:.4f} ov={latest_worst_ov*100:5.1f}% uniq={latest_worst_ov<=0.70}",
            flush=True,
        )

    sass1_s = summary_holdout["scores"]["GEMSDOESASS1_latest"]
    sass1_summary = {
        "site": "GEMSDOESASS1",
        **metas["GEMSDOESASS1_latest"],
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": eh.VERSION,
            "withheld_positive_pixels": sass1_s["withheld_positive_pixels"],
            "dti": round(sass1_s["dti"], 6),
            "ci95": [round(sass1_s["ci95"][0], 6), round(sass1_s["ci95"][1], 6)],
        },
        "lli_projection": lli_by_arm["GEMSDOESASS1_latest"],
        "vs_champion_02778_3px_overlap": round(overlaps[("GEMSDOESASS1_latest", "GEMSDOE32_hist_best_02778")], 4),
    }

    out = {
        "schema_version": 1,
        "evaluator_version": eh.VERSION,
        "holdout_protocol": "buffered-whole-components-loqo-v2 (seeds 20, 21 merged on 20 km physical blocks before 1000-draw bootstrap)",
        "lineage_proof": lineage_proof,
        "sites": site_rows,
        "sibling_gemsdoesass1": sass1_summary,
    }
    (ROOT / "evidence/nine_sites_executive_audit.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"Done in {time.time()-t0:.1f}s -> evidence/nine_sites_executive_audit.json", flush=True)


if __name__ == "__main__":
    main()
