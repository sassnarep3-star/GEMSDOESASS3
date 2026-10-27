#!/usr/bin/env python3
"""Generate publication-grade diagnostic figures in docs/assets/ from verified JSON/NPZ evidence."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"
ASSETS.mkdir(parents=True, exist_ok=True)


def fig1_nine_sites_and_collar_mechanism() -> None:
    audit = json.loads((ROOT / "evidence/nine_sites_executive_audit.json").read_text())
    card = json.loads((ROOT / "evidence/current_run_card.json").read_text())

    sites = audit["sites"]
    names = [s["site"].replace("GEMSDOE", "GEMS-") for s in sites]
    hist_scores = [s["hist_score_owner_report"] for s in sites]
    latest_holdout = [s["latest_unique_candidate"]["holdout_dti"]["dti"] for s in sites]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2), dpi=160)
    fig.patch.set_facecolor("#0f172a")
    for ax in (ax1, ax2):
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#e2e8f0", labelsize=9)
        for sp in ax.spines.values():
            sp.set_color("#334155")

    # Left panel: H19-5 Set-Algebra Collar Purification Curve (OWNER-REPORT)
    steps = [
        "19GEMSDOE\nH19-5 Raw\n(121,131 px)",
        "GEMS-24\nd=1.5 Thin\n(60,069 px)",
        "GEMS-25 ≡ 30\nd=2.8 B=0\n(44,090 px)",
        "GEMS-28 ≡ 31\nd=2.8 B=1\n(40,199 px)",
        "GEMS-32 ★\nd=2.8 B=2\n(37,654 px)",
        "GEMS-36\nB=2 + 1200\n(38,854 px)",
    ]
    step_scores = [0.2225, 0.2477, 0.2600, 0.2708, 0.2778, 0.2750]
    colors_l = ["#64748b", "#38bdf8", "#0ea5e9", "#6366f1", "#10b981", "#f59e0b"]
    bars1 = ax1.bar(range(len(steps)), step_scores, color=colors_l, width=0.62, edgecolor="#f8fafc", linewidth=0.8)
    ax1.plot(range(len(steps)), step_scores, color="#f8fafc", marker="o", linewidth=1.6, markersize=5)
    ax1.set_xticks(range(len(steps)))
    ax1.set_xticklabels(steps, fontsize=8, color="#e2e8f0")
    ax1.set_ylim(0.18, 0.305)
    ax1.set_ylabel("Live Score [OWNER-REPORT]", color="#f8fafc", fontsize=10, fontweight="bold")
    ax1.set_title("Exact H19-5 Set-Algebra & Collar Purification (0 px SymDiff)", color="#f8fafc", fontsize=10.5, fontweight="bold")
    ax1.grid(axis="y", color="#334155", linestyle="--", alpha=0.6)
    for b, v in zip(bars1, step_scores):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.003, f"{v:.4f}", ha="center", va="bottom", color="#f8fafc", fontsize=8.5, fontweight="bold")

    # Right panel: Latest Unique Off-H19-5 Candidates on Shared Holdout (gems57-pooled-hide-v2)
    labels_r = names + ["SASS1\n(cbceb1)", "SASS3 ★\n(GSD-HUA)"]
    vals_r = latest_holdout + [0.001715, card["holdout_dti"]["dti"]]
    cols_r = ["#475569" if i != len(labels_r) - 1 else "#10b981" for i in range(len(labels_r))]
    cols_r[3] = "#f59e0b"  # GEMS-28 s22 (>70% overlap flag)
    cols_r[2] = "#38bdf8"  # GEMS-27 h31 (best unique peer)
    y_pos = np.arange(len(labels_r))
    bars2 = ax2.barh(y_pos, vals_r, color=cols_r, height=0.66, edgecolor="#f8fafc", linewidth=0.7)
    ax2.axvline(0.064944, color="#f43f5e", linestyle="--", linewidth=1.5, label="CTRL-0 Fold-Honest H19-5 B=2 (0.0649)")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels_r, fontsize=8.5, color="#e2e8f0")
    ax2.set_xlim(0, 0.086)
    ax2.set_xlabel("Pooled HOLDOUT-DTI [gems57-pooled-hide-v2, n=22,893]", color="#f8fafc", fontsize=9.5, fontweight="bold")
    ax2.set_title("Cross-Site Unique Candidate Holdout Comparison", color="#f8fafc", fontsize=10.5, fontweight="bold")
    ax2.legend(loc="lower right", facecolor="#0f172a", edgecolor="#475569", labelcolor="#f8fafc", fontsize=8)
    ax2.grid(axis="x", color="#334155", linestyle="--", alpha=0.6)
    for b, v in zip(bars2, vals_r):
        ax2.text(v + 0.0012, b.get_y() + b.get_height() / 2, f"{v:.4f}", va="center", color="#f8fafc", fontsize=8, fontweight="bold")

    fig.tight_layout()
    fig.savefig(ASSETS / "fig1_nine_sites_algebra.png", dpi=160)
    plt.close(fig)


def fig2_gsd_hua_holdout_ladder() -> None:
    exp = json.loads((ROOT / "evidence/gsd_hua_experiments.json").read_text())
    scores = exp["holdout_scores"]
    arm_order = [
        ("CTRL-1_19BAND_HGB", "CTRL-1: Raw 19-Band HGB\n(37,654 dots)", "#64748b"),
        ("EXP-1_GSD_HUA_PURE_SUBSURF", "EXP-1: Pure Subsurface Tower\n(36 non-DEM cols, 80.8% ov)", "#38bdf8"),
        ("CTRL-0_H19_5_B2", "CTRL-0: Fold-Honest H19-5 B=2\n(GEMSDOE32 ref, 37,654 dots)", "#f43f5e"),
        ("EXP-2_GSD_HUA_FULL_MULTIPHYS", "EXP-2: Full 46-Feat GSD-HUA\n(Unwhitened, 87.2% ov DUP)", "#f59e0b"),
        ("EXP-3_GSD_HUA_SAR_DECONFOUNDED", "EXP-3: GSD-HUA SAR-Deconf ★\n(PROMOTED, 67.4% ov <= 70%)", "#10b981"),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 4.9), dpi=160)
    fig.patch.set_facecolor("#0f172a")
    for ax in (ax1, ax2):
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#e2e8f0", labelsize=9)
        for sp in ax.spines.values():
            sp.set_color("#334155")

    y = np.arange(len(arm_order))
    means = [scores[k]["dti"] for k, _, _ in arm_order]
    lo = [scores[k]["dti"] - scores[k]["ci95"][0] for k, _, _ in arm_order]
    hi = [scores[k]["ci95"][1] - scores[k]["dti"] for k, _, _ in arm_order]
    cols = [c for _, _, c in arm_order]
    lbls = [l for _, l, _ in arm_order]

    ax1.barh(y, means, xerr=[lo, hi], color=cols, height=0.58, capsize=4, ecolor="#f8fafc", edgecolor="#f8fafc", linewidth=0.8)
    ax1.set_yticks(y)
    ax1.set_yticklabels(lbls, fontsize=8.5, color="#e2e8f0")
    ax1.set_xlim(0, 0.098)
    ax1.set_xlabel("HOLDOUT-DTI +/- 95% Block-Bootstrap CI (n_withheld = 22,893)", color="#f8fafc", fontsize=9.5, fontweight="bold")
    ax1.set_title("H-GASS3-1 (GSD-HUA) 3-Experiment Holdout Ladder", color="#f8fafc", fontsize=10.5, fontweight="bold")
    ax1.grid(axis="x", color="#334155", linestyle="--", alpha=0.6)
    for yi, m, h in zip(y, means, hi):
        ax1.text(m + h + 0.0015, yi, f"{m:.5f}", va="center", color="#f8fafc", fontsize=8.5, fontweight="bold")

    # Right panel: Uniqueness 3-px Overlap vs HOLDOUT-DTI Frontier
    pts = [
        ("EXP-1 Subsurface", 0.8080, 0.05168, "#38bdf8"),
        ("EXP-2 Unwhitened", 0.8716, 0.07050, "#f59e0b"),
        ("GEMSDOE28 s22", 0.7508, 0.01627, "#fb7185"),
        ("GEMSDOE27 h31", 0.5808, 0.01368, "#94a3b8"),
        ("GEMSDOE32 h47", 0.5146, 0.00619, "#94a3b8"),
        ("GEMSDOESASS1", 0.2034, 0.00172, "#94a3b8"),
        ("EXP-3 GSD-HUA ★\n(PROMOTED)", 0.6745, 0.07202, "#10b981"),
    ]
    ax2.axvspan(0.70, 0.95, color="#ef4444", alpha=0.18, label="Duplicate Zone (>70% 3-px Overlap)")
    ax2.axvline(0.70, color="#ef4444", linestyle="--", linewidth=1.6)
    ax2.axhline(0.064944, color="#38bdf8", linestyle=":", linewidth=1.4, label="CTRL-0 H19-5 B=2 (0.06494)")
    for name, ov, dti, c in pts:
        sz = 150 if "EXP-3" in name else 80
        ax2.scatter([ov], [dti], s=sz, color=c, edgecolors="#f8fafc", linewidth=1.2, zorder=5)
        dx = -0.02 if ov > 0.78 else 0.012
        ha = "right" if ov > 0.78 else "left"
        if "EXP-3" in name:
            dx, ha = -0.020, "right"
            ax2.text(ov + dx, dti - 0.0115, name, color="#10b981", fontsize=8.5, ha=ha, fontweight="bold")
        else:
            ax2.text(ov + dx, dti + 0.001, name, color="#f8fafc", fontsize=8, ha=ha)
    ax2.set_xlim(0.15, 0.94)
    ax2.set_ylim(-0.003, 0.092)
    ax2.set_xlabel("Worst 3-px Forward Overlap Across All 42 Dot-Field Rasters", color="#f8fafc", fontsize=9.5, fontweight="bold")
    ax2.set_ylabel("Pooled HOLDOUT-DTI", color="#f8fafc", fontsize=9.5, fontweight="bold")
    ax2.set_title("Uniqueness Gate (<= 0.70) vs Holdout Recovery Frontier", color="#f8fafc", fontsize=10.5, fontweight="bold")
    ax2.legend(loc="upper left", facecolor="#0f172a", edgecolor="#475569", labelcolor="#f8fafc", fontsize=8)
    ax2.grid(color="#334155", linestyle="--", alpha=0.6)

    fig.tight_layout()
    fig.savefig(ASSETS / "fig2_gsd_hua_holdout_ladder.png", dpi=160)
    plt.close(fig)


def fig3_nevada_prediction_map() -> None:
    npz = np.load(ROOT / "evidence/gsd_hua_map_preview.npz")
    surf = npz["surface_ds"].astype(np.float32)
    fp = npz["footprint_ds"]
    cat = npz["catalogue_ds"]
    dots_yx = npz["dots_yx"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 6.2), dpi=160)
    fig.patch.set_facecolor("#0f172a")
    for ax in (ax1, ax2):
        ax.set_facecolor("#090d16")
        ax.tick_params(colors="#cbd5e1", labelsize=8)
        for sp in ax.spines.values():
            sp.set_color("#334155")

    disp = np.ma.masked_where(~fp, surf)
    im = ax1.imshow(disp, cmap="magma", vmin=0.0, vmax=0.85, interpolation="nearest")
    cb = fig.colorbar(im, ax=ax1, fraction=0.042, pad=0.03)
    cb.ax.yaxis.set_tick_params(color="#e2e8f0", labelcolor="#e2e8f0", labelsize=8)
    cb.set_label("SAR-Deconfounded GSD-HUA Surface [0, 1]", color="#e2e8f0", fontsize=8.5)
    ax1.set_title("Continuous GSD-HUA Fault Discovery Surface\n(Spearman <= 0.115 vs All 43 Registry Rasters)", color="#f8fafc", fontsize=10, fontweight="bold")
    ax1.set_xlabel("X (400 m ds px, EPSG:32611)", color="#cbd5e1", fontsize=8.5)
    ax1.set_ylabel("Y (400 m ds px, EPSG:32611)", color="#cbd5e1", fontsize=8.5)

    bg = np.zeros((*fp.shape, 3), dtype=np.float32)
    bg[fp] = [0.11, 0.16, 0.24]
    bg[cat] = [0.96, 0.25, 0.37]  # Mapped catalogue in crimson
    ax2.imshow(bg, interpolation="nearest")
    ax2.scatter(
        dots_yx[::2, 1] / 4.0,
        dots_yx[::2, 0] / 4.0,
        s=0.45,
        c="#10b981",
        alpha=0.78,
        linewidths=0,
        label="Emitted Off-Catalogue Dots (37,654 px, B=2)",
    )
    ax2.plot([], [], color="#f43f5e", linewidth=2, label="Mapped Catalogue (0 Overlap Pixels)")
    ax2.set_title("Emitted GeoTIFF: 37,654 Dots (73.1% Cover >=150 m, 42.8% Slope <4 deg)\nAll-Finite float32 in [0, 1] | 34.3% 3-px Overlap vs GEMSDOE32", color="#f8fafc", fontsize=9.6, fontweight="bold")
    ax2.set_xlabel("X (400 m ds px, EPSG:32611)", color="#cbd5e1", fontsize=8.5)
    ax2.legend(loc="lower left", facecolor="#0f172a", edgecolor="#475569", labelcolor="#f8fafc", fontsize=8, markerscale=8)

    fig.tight_layout()
    fig.savefig(ASSETS / "fig3_nevada_gsd_hua_map.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig1_nine_sites_and_collar_mechanism()
    fig2_gsd_hua_holdout_ladder()
    fig3_nevada_prediction_map()
    print("Generated all 3 diagnostic figures in docs/assets/")
