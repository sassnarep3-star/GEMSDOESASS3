#!/usr/bin/env python3
"""Generate publication-grade scientific diagnostic figures for GEMSDOESASS3 GitHub Pages."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32 import holdout, lwst_geoconduit as lwst  # noqa: E402


def main() -> int:
    ddir = Path("/tmp/gems_data")
    wdir = Path("/tmp/gems_work")
    assets = ROOT / "docs" / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    run_card = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    canary = json.loads((ROOT / "evidence" / "leakage_canary_report.json").read_text())
    uniq = json.loads((ROOT / "evidence" / "uniqueness_audit_386.json").read_text())

    cand_tif = ROOT / "docs" / "downloads" / run_card["submission_name"]
    ctx = holdout.load_holdout_context(ddir)
    foot = ctx.foot
    labels = ctx.labels
    sgmc_off = ctx.sgmc_off

    with rasterio.open(cand_tif) as ds:
        cand_dots = (ds.read(1) > 0) & foot

    lwst_mm = np.load(wdir / "lwst_extra_stack.npy", mmap_mode="r")
    prob_oof = np.load(wdir / "lwst_full_oof.npy", mmap_mode="r")

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.edgecolor": "#cbd5e1",
        "axes.linewidth": 0.9,
        "figure.facecolor": "#ffffff",
    })

    # --- Figure 1: 3-Panel Spatial Diagnostic ---
    s = 4
    foot_s = foot[::s, ::s]
    lbl_s = ndi.maximum_filter(labels, size=4)[::s, ::s]
    sgmc_s = ndi.maximum_filter(sgmc_off, size=4)[::s, ::s]
    dots_s = ndi.maximum_filter(cand_dots, size=4)[::s, ::s]

    raw_conduit = lwst_mm[:, :, 14] * (
        0.42 * lwst_mm[:, :, 4] + 0.30 * lwst_mm[:, :, 11] + 0.28 * lwst_mm[:, :, 7]
    )
    conduit_max = ndi.maximum_filter(raw_conduit, size=4)[::s, ::s]
    conduit_field = np.where(foot_s, conduit_max, np.nan)
    vmax_c = float(np.nanpercentile(conduit_field, 98.5))
    oof_s = np.where(foot_s, ndi.maximum_filter(prob_oof, size=4)[::s, ::s], np.nan)

    fig, axes = plt.subplots(1, 3, figsize=(15.8, 5.9), dpi=160)
    # Panel A
    ax = axes[0]
    bg = np.full((*foot_s.shape, 3), 0.96, dtype=np.float32)
    bg[foot_s] = [0.90, 0.93, 0.96]
    bg[sgmc_s] = [0.92, 0.50, 0.10]
    bg[lbl_s] = [0.08, 0.26, 0.56]
    ax.imshow(bg, interpolation="nearest")
    ax.set_title("A. Mapped Catalogue vs. Off-Catalogue SGMC\nBlue: labels.tif (60,988 px) | Orange: SGMC >300 m (62,703 px)", fontsize=9.8, fontweight="bold", pad=8)
    ax.set_xticks([]); ax.set_yticks([])

    # Panel B
    ax = axes[1]
    bg2 = np.full((*foot_s.shape, 3), 0.96, dtype=np.float32)
    ax.imshow(bg2, interpolation="nearest")
    im = ax.imshow(conduit_field, cmap="inferno", vmin=0.0, vmax=max(vmax_c, 0.5), interpolation="bilinear")
    ax.set_title("B. LWST-GeoConduit Physical Ridges (Zero Labels)\n3-D SPI Wavenumber + Wijns Theta + Transtensional Slip", fontsize=9.8, fontweight="bold", pad=8)
    ax.set_xticks([]); ax.set_yticks([])
    cb = fig.colorbar(im, ax=ax, fraction=0.042, pad=0.02)
    cb.ax.tick_params(labelsize=8)
    cb.set_label("400 m Block-Max Conduit Z-Score", fontsize=8)

    # Panel C
    ax = axes[2]
    bg3 = np.full((*foot_s.shape, 3), 0.96, dtype=np.float32)
    bg3[foot_s] = [0.08, 0.11, 0.18]
    bg3[lbl_s] = [0.30, 0.40, 0.54]
    is_ha = dots_s & (np.nan_to_num(oof_s, nan=0.0) >= 0.30)
    is_hb = dots_s & (~is_ha)
    bg3[is_hb] = [0.99, 0.73, 0.18]
    bg3[is_ha] = [0.16, 0.89, 0.72]
    ax.imshow(bg3, interpolation="nearest")
    ax.set_title("C. Shipped EXP3 Dual-Horizon Allocation (37,654 Dots)\nTeal: Horizon-A OOF (19,584d) | Gold: Horizon-B LWST (18,070d)", fontsize=9.8, fontweight="bold", pad=8)
    ax.set_xticks([]); ax.set_yticks([])

    fig.suptitle(
        "GEMSDOESASS3 Spatial Architecture — Great Basin Study Area (EPSG:32611, 3,730 x 3,292 @ 100 m)",
        fontsize=12.2, fontweight="bold", y=0.99, color="#0f172a"
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(assets / "fig1_lwst_great_basin_map.png", dpi=160, bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)

    # --- Figure 2: Pareto Frontier & Live Calibration ---
    fig, axes = plt.subplots(1, 2, figsize=(14.8, 5.6), dpi=160)

    ax = axes[0]
    ax.axvline(0.099202, color="#64748b", linestyle="--", linewidth=1.1, label="0.2778 Champion HR Baseline (0.0992)")
    ax.axhline(0.064121, color="#0284c7", linestyle=":", linewidth=1.2, label="0.2778 Champion SGMC Baseline (0.0641)")
    ax.fill_between([0.099202, 0.160], 0.064121, 0.082, color="#dcfce7", alpha=0.55, label="Dual-Win Zone (Beats 0.2778 on BOTH)")

    pts = [
        ("0.2778 Champion (32)", 0.099202, 0.064121, "#1e293b", "s", 85, (-0.036, 0.0016)),
        ("D2.8 0.2600 (25/30)", 0.092800, 0.060592, "#64748b", "o", 60, (-0.031, -0.0028)),
        ("EXP1 Unsup LWST", 0.045596, 0.075215, "#d97706", "^", 95, (0.0025, -0.0005)),
        ("EXP2 Dual-HGB OOF", 0.116690, 0.050066, "#2563eb", "v", 95, (-0.016, -0.0032)),
        ("GEMSDOE28 S22 (promote)", 0.144900, 0.050532, "#ef4444", "D", 65, (-0.038, 0.0020)),
        ("GEMSDOE36 KPL36 (promote)", 0.140700, 0.044458, "#dc2626", "D", 65, (-0.043, -0.0025)),
        ("GEMSDOE32 H47-1 (held)", 0.119765, 0.065888, "#7c3aed", "P", 85, (0.0022, 0.0012)),
        ("GEMSDOE24 S3DEP1 (held >70% ov)", 0.146300, 0.073816, "#9333ea", "X", 80, (-0.052, 0.0014)),
        ("GEMSDOESASS3 EXP3 (SHIPPED)", 0.111062, 0.065702, "#059669", "*", 250, (-0.010, -0.0036)),
    ]
    for lbl, x, y, col, mk, sz, (dx, dy) in pts:
        ax.scatter([x], [y], c=col, marker=mk, s=sz, zorder=5, edgecolors="#0f172a", linewidths=0.7)
        ax.annotate(lbl, (x, y), xytext=(x + dx, y + dy), fontsize=8.1,
                    fontweight="bold" if "SHIPPED" in lbl else "normal",
                    color="#065f46" if "SHIPPED" in lbl else "#1e293b")

    ax.set_xlim(0.038, 0.158)
    ax.set_ylim(0.040, 0.080)
    ax.set_xlabel("HOLDOUT-DTI: HIDE-RECOVER-v3.0 (Withheld Quaternary Faults, n=22,232)", fontsize=9.2, fontweight="bold")
    ax.set_ylabel("Off-Catalogue HOLDOUT-DTI (SGMC-CAL-v3.0, n=62,703)", fontsize=9.2, fontweight="bold")
    ax.set_title("A. Dual-Domain Pareto Frontier Across Focus Sites\nEXP3 Is the Only Unique Promoted Raster in the Dual-Win Zone", fontsize=10.2, fontweight="bold")
    ax.grid(True, alpha=0.28)
    ax.legend(loc="lower left", fontsize=8.0)

    ax = axes[1]
    live_pts = [
        ("30: MSDB1 (0.1462)", 0.049232, 0.1462, "#dc2626", (0.0502, 0.150)),
        ("27: H29 (0.2190)", 0.055815, 0.2190, "#ea580c", (0.0510, 0.222)),
        ("24: H25-1 (0.2477)", 0.057932, 0.2477, "#475569", (0.0518, 0.249)),
        ("27: T-v2 (0.2449)", 0.058262, 0.2449, "#475569", (0.0588, 0.236)),
        ("25/30: D2.8 (0.2600)", 0.060592, 0.2600, "#334155", (0.0543, 0.264)),
        ("33: H33d (0.2632)", 0.062551, 0.2632, "#334155", (0.0616, 0.251)),
        ("28/31: H27-4 (0.2708)", 0.063010, 0.2708, "#1e293b", (0.0560, 0.276)),
        ("28: H36-1 (0.2710)", 0.062967, 0.2710, "#1e293b", (0.0635, 0.263)),
        ("32: Champ (0.2778)", 0.064121, 0.2778, "#0284c7", (0.0578, 0.287)),
        ("36: PINN (0.2750)", 0.064444, 0.2750, "#0f172a", (0.0648, 0.274)),
    ]
    xs_l = np.array([p[1] for p in live_pts])
    ys_l = np.array([p[2] for p in live_pts])
    coef = np.polyfit(xs_l, ys_l, 1)
    xx_fit = np.linspace(0.0475, 0.067, 50)
    ax.plot(xx_fit, np.polyval(coef, xx_fit), "--", color="#64748b", linewidth=1.2, label="Empirical Trend Across 10 Live Receipts (Spearman r = 0.96)")
    for lbl, x, y, col, (tx, ty) in live_pts:
        ax.scatter([x], [y], c=col, s=58, zorder=5, edgecolors="#0f172a", linewidths=0.6)
        ax.annotate(lbl, (x, y), xytext=(tx, ty), fontsize=7.8, color="#1e293b",
                    arrowprops=dict(arrowstyle="-", color="#94a3b8", lw=0.7))
    ax.axvline(0.065702, color="#059669", linewidth=2.1, linestyle="-.", label="GEMSDOESASS3 EXP3 SGMC-CAL = 0.0657 (Unscored Live)")
    ax.set_xlim(0.0475, 0.0695)
    ax.set_ylim(0.135, 0.298)
    ax.set_xlabel("Off-Catalogue HOLDOUT-DTI (GEMSDOE32-SGMC-CAL-v3.0)", fontsize=9.2, fontweight="bold")
    ax.set_ylabel("ORGANIZER-CONFIRMED Live DrivenData DTI", fontsize=9.2, fontweight="bold")
    ax.set_title("B. Empirical Alignment of Off-Catalogue SGMC-CAL-v3.0\nvs. ORGANIZER-CONFIRMED DrivenData Leaderboard Receipts", fontsize=10.2, fontweight="bold")
    ax.grid(True, alpha=0.28)
    ax.legend(loc="lower right", fontsize=8.0)

    fig.tight_layout()
    fig.savefig(assets / "fig2_pareto_holdout_sgmc.png", dpi=160, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)

    # --- Figure 3: Deduplicated Top-12 Uniqueness Overlaps & Top-14 Leakage Canary ---
    fig, axes = plt.subplots(1, 2, figsize=(15.0, 5.2), dpi=160)

    ax = axes[0]
    dedup_ov = []
    seen_stems = set()
    for r in uniq["final_dots"]["top_25_genuine_by_overlap"]:
        stem = re.sub(r"-(zeros|nan|allfinite)\.tif$", "", Path(r["path"]).name)
        key = f"{r['repo']}:{stem}"
        if key not in seen_stems:
            seen_stems.add(key)
            dedup_ov.append((r, stem))
        if len(dedup_ov) == 12:
            break
    dedup_ov = dedup_ov[::-1]
    labels_ov = [f"{r['repo']}: {stem[:32]}" for r, stem in dedup_ov]
    vals_ov = [r["within_3px_fraction"] for r, _ in dedup_ov]
    ax.barh(range(len(dedup_ov)), vals_ov, color="#0d9488", edgecolor="#0f172a", height=0.68)
    ax.axvline(0.70, color="#dc2626", linestyle="--", linewidth=1.8, label="Protocol Rule 1 Ceiling (0.70)")
    ax.set_yticks(range(len(dedup_ov)))
    ax.set_yticklabels(labels_ov, fontsize=7.9)
    ax.set_xlim(0.0, 0.80)
    ax.set_xlabel("Fraction of Candidate Dots Within <= 3 px (300 m) of Registry Raster", fontsize=9.0, fontweight="bold")
    ax.set_title("A. 385-Raster Uniqueness Gate (Top-12 Distinct Candidates)\nMax Overlap = 0.6327 <= 0.70 | Max |Spearman| = 0.1255 <= 0.90", fontsize=9.8, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.28)
    ax.legend(loc="lower right", fontsize=8.0)

    ax = axes[1]
    top_c = sorted(canary["channels"], key=lambda x: x["symmetric_auc_canary"], reverse=True)[:14][::-1]
    lwst_set = set(lwst.LWST_CHANNELS)
    c_names = [f"{c['channel']} ({'LWST' if c['channel'] in lwst_set else 'base'})" for c in top_c]
    c_aucs = [c["symmetric_auc_canary"] for c in top_c]
    colors_c = ["#2563eb" if c["channel"] in lwst_set else "#64748b" for c in top_c]
    ax.barh(range(len(top_c)), c_aucs, color=colors_c, edgecolor="#0f172a", height=0.68)
    ax.axvline(0.90, color="#dc2626", linestyle="--", linewidth=1.8, label="Protocol Rule 4 Canary Ceiling (0.90)")
    ax.axvline(0.50, color="#94a3b8", linestyle=":", linewidth=1.0)
    ax.set_yticks(range(len(top_c)))
    ax.set_yticklabels(c_names, fontsize=8.0)
    ax.set_xlim(0.45, 0.96)
    ax.set_xlabel("Single-Feature Symmetric Holdout AUC max(AUC, 1 - AUC)", fontsize=9.0, fontweight="bold")
    ax.set_title("B. 51-Channel Single-Feature Leakage Canary (n=22,232)\nAll 51/51 Passed (Max = curv_s2 @ 0.5883; Blue = LWST)", fontsize=9.8, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.28)
    ax.legend(loc="lower right", fontsize=8.0)

    fig.tight_layout()
    fig.savefig(assets / "fig3_uniqueness_canary_audit.png", dpi=160, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)
    print("Regenerated polished figures in docs/assets/ successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
