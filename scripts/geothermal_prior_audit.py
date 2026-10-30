#!/usr/bin/env python3
"""Reusable geothermal-vent / hot-spring prior audit on the 100 m competition grid (deliverable #7).

Reads the pinned GDR derived-feature extracts (free official mirrors of gdr.openei.org/submissions/1391
and the USGS/INGENIOUS extensions), rasterises the point layers onto the competition grid, and measures
how close three emissions are to them:

  * the SASS3 candidate (docs/downloads/*-s3hash-safe.tif)
  * the family champion 0.2778 file (GEMSDOE32, SHA-verified sibling byte in the registry checkout)
  * a uniform random control inside the footprint (fixed seed)
  * the catalogue mask itself (labels.tif), as the reference that "on a known fault" looks like

Reported per layer: median distance in px, the fraction of dots within 3 px (= 300 m, the scoring
kernel radius), and the rank-biserial AUC of "closer to the layer" for candidate-vs-control. AUC 0.5
means the prior carries no information for that emission. This is the file to re-run when a new
candidate is built; it never overwrites a receipt of another experiment.

Usage:
  /home/user/.venv/bin/python scripts/geothermal_prior_audit.py \
      [--candidate docs/downloads/<file>.tif] [--registry /tmp/registry_git] [--out evidence/...]
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
HEIGHT, WIDTH = 3730, 3292


def dot_mask(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    return np.isfinite(arr) & (arr > 0) & foot


def read_dots(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return dot_mask(a, foot)


def load_layer_grid(name: str, row_key: str, col_key: str, filt=None) -> np.ndarray:
    """Boolean grid of unique rows/cols from a GDR extract CSV, clipped to the competition grid."""
    g = np.zeros((HEIGHT, WIDTH), dtype=bool)
    p = ROOT / ".cache" / "gems_data" / "external" / name
    if not p.exists():
        return g
    with p.open() as f:
        for r in csv.DictReader(f):
            if filt and not filt(r):
                continue
            try:
                row, col = int(float(r[row_key])), int(float(r[col_key]))
            except (KeyError, TypeError, ValueError):
                continue
            if 0 <= row < HEIGHT and 0 <= col < WIDTH:
                g[row, col] = True
    return g


def stats(mask: np.ndarray, d: np.ndarray, label: str) -> dict:
    n = int(mask.sum())
    if n == 0:
        return {"label": label, "n_dots": 0}
    dd = d[mask]
    return {
        "label": label,
        "n_dots": n,
        "median_d_layer_px": round(float(np.median(dd)), 3),
        "frac_within_3px": round(float((dd <= 3.0001).mean()), 4),
        "frac_beyond_10px": round(float((dd > 10.0).mean()), 4),
        "frac_on_layer": round(float((dd < 1.0).mean()), 4),
    }


def auc_closer(mask_a: np.ndarray, mask_b: np.ndarray, d: np.ndarray) -> float:
    """P(an A dot lies FARTHER from the layer than a B dot), Mann-Whitney.

    Read it as a proximity odds: 0.5 = the two emissions sit at the same distance from the layer;
    below 0.5 means A is systematically CLOSER than B (a geothermal association); above 0.5 means A is
    farther. Kept deliberately asymmetric so the printed key says what it counts.
    """
    da, db = d[mask_a], d[mask_b]
    if da.size == 0 or db.size == 0:
        return float("nan")
    rng = np.random.default_rng(20261030)
    da = rng.choice(da, size=min(da.size, 20000), replace=False)
    db = rng.choice(db, size=min(db.size, 20000), replace=False)
    # rank of a's values within the pooled sample
    order = np.argsort(np.concatenate([da, db]), kind="stable")
    ranks = np.empty(order.size, dtype=float)
    ranks[order] = np.arange(1, order.size + 1)
    ra = ranks[: da.size].sum()
    n1, n2 = da.size, db.size
    return round(float((2.0 * ra - n1 * (n1 + 1)) / (2.0 * n1 * n2)), 4)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", default="docs/downloads/gemsdoesass3-s3-ocm-wide44090-20261030T024750Z-s3hash-safe.tif")
    ap.add_argument("--champion", default="GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    ap.add_argument("--registry", default="/tmp/registry_git")
    ap.add_argument("--data-dir", default=str(ROOT / ".cache" / "gems_data"))
    ap.add_argument("--out", default=str(ROOT / "evidence/geothermal_prior_audit_20261030.json"))
    args = ap.parse_args()

    ddir = Path(args.data_dir)
    with rasterio.open(ddir / "training_features.tif") as ds:
        foot = np.isfinite(ds.read(1))  # band 1 carries the official nodata sentinel outside the footprint
    with rasterio.open(ddir / "labels.tif") as ds:
        labels = ds.read(1) > 0

    cand = read_dots(ROOT / args.candidate, foot)
    champ_path = Path(args.registry) / args.champion
    champ = read_dots(champ_path, foot) if champ_path.is_file() else np.zeros_like(cand)
    rng = np.random.default_rng(20261030)
    idx = np.flatnonzero(foot.ravel())
    control = np.zeros(foot.size, bool)
    control[rng.choice(idx, size=int(cand.sum()), replace=False)] = True
    control = control.reshape(foot.shape) & foot

    layers = {
        "hot_springs_any": load_layer_grid("gdr_wellspring_in_footprint.csv", "row", "col"),
        "hot_springs_class_Hot": load_layer_grid(
            "gdr_wellspring_in_footprint.csv", "row", "col", lambda r: r.get("thermalclass") == "Hot"),
        "volcanic_vents": load_layer_grid("gdr_volcanic_vents_in_footprint.csv", "row", "col"),
        "qfault_trace_centroids": load_layer_grid("gdr_qfaults_traces.csv", "centroid_row", "centroid_col"),
        "catalogue_labels": labels,
    }
    out = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "scripts/geothermal_prior_audit.py",
        "grid": {"height": HEIGHT, "width": WIDTH, "cell_m": 100.0, "kernel_radius_px": 3},
        "emissions": {
            "sass3_candidate": str(ROOT / args.candidate),
            "family_champion": str(champ_path) if champ_path.is_file() else "MISSING",
            "random_control": f"{int(control.sum())} uniform footprint cells, seed 20261030",
        },
        "layers": {k: int(v.sum()) for k, v in layers.items()},
        "rows": [],
        "caveat": ("Distances are 100 m-grid px on EPSG:32611; spring/vent points are derived extracts, not the "
                   "authoritative GDR layer. No number here is a score. AUC 0.5 = the prior adds no ranking "
                   "information for that emission. p_*_farther_than_control < 0.5 = closer than random."),
    }
    for name, g in layers.items():
        if not g.any():
            out["rows"].append({"layer": name, "status": "layer_empty_or_missing"})
            continue
        d = distance_transform_edt(~g)  # px; 1 px = 100 m on this grid
        row = {"layer": name}
        row["candidate"] = stats(cand, d, "candidate")
        row["champion"] = stats(champ, d, "champion")
        row["control"] = stats(control, d, "control")
        row["p_candidate_farther_than_control"] = auc_closer(cand, control, d)
        row["p_champion_farther_than_control"] = auc_closer(champ, control, d)
        out["rows"].append(row)
        print(f"{name:24s} cand_med={row['candidate'].get('median_d_layer_px')} "
              f"champ_med={row['champion'].get('median_d_layer_px')} "
              f"ctrl_med={row['control'].get('median_d_layer_px')} "
              f"p_farther(cand)={row['p_candidate_farther_than_control']} p_farther(champ)={row['p_champion_farther_than_control']}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
