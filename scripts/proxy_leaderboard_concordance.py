#!/usr/bin/env python3
"""Does the repo's holdout proxy rank known leaderboard scores the same way?

The repo reports HOLDOUT-DTI numbers (GEMSDOE32-HIDE-RECOVER-v3.0 and GEMSDOE32-SGMC-CAL-v3.0).
Those are proxies. Before using a proxy to choose a submission, we test whether it agrees with
the scores the organizer reports. This script:

1. reads `registry/owner_reported_scores_focus.json` (scores typed in the task prompt, label OWNER-REPORT),
2. loads each named raster from a checkout of the public sibling repositories,
3. scores each raster with the SHARED evaluator (`gems32.holdout`, no private fork),
4. reports Spearman rank correlation between each proxy and the owner-reported score,
5. writes everything to `evidence/proxy_leaderboard_concordance.json` with raster sha256 values.

Inputs
------
* the feature/label data placed by `scripts/download_competition_data.sh` (default `.cache/gems_data`)
* `--sibling-root DIR`: directory containing `GEMSDOE24-main/`, `GEMSDOE25-main/`, ... (a checkout of the
  public repositories `buffedlizard55-lab/GEMSDOE{24,25,27,28,30,31,32,33,36}`).

Caveats (recorded in the output)
--------------------------------
* Owner-reported scores are NOT organizer receipts. They are used only to test rank agreement.
* n is small (about 20). A Spearman estimate is reported with a bootstrap 95% CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems32 import holdout  # noqa: E402
from gems32.paths import data_dir  # noqa: E402

B_VISIBLE_PX = 2.0


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def spearman_ci(x: np.ndarray, y: np.ndarray, n_boot: int = 2000, seed: int = 20261028) -> tuple[float, list[float]]:
    rho = float(spearmanr(x, y).statistic)
    rng = np.random.default_rng(seed)
    n = len(x)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(set(x[idx])) < 2 or len(set(y[idx])) < 2:
            continue
        boots.append(float(spearmanr(x[idx], y[idx]).statistic))
    lo, hi = np.percentile(boots, [2.5, 97.5]) if boots else (float("nan"), float("nan"))
    return rho, [round(float(lo), 4), round(float(hi), 4)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sibling-root", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=ROOT / "registry" / "owner_reported_scores_focus.json")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "evidence" / "proxy_leaderboard_concordance.json")
    args = ap.parse_args(argv)

    man = json.loads(args.manifest.read_text())
    ctx = holdout.load_holdout_context(args.data_dir or data_dir())

    rows = []
    for e in man["entries"]:
        path = args.sibling_root / e["repo_dir"] / e["file"]
        row = {"site": e["site"], "file": e["file"], "owner_reported_score": e["owner_reported_score"]}
        if not path.exists():
            row["error"] = "missing"
            rows.append(row)
            continue
        with rasterio.open(path) as ds:
            arr = ds.read(1)
            if arr.shape != ctx.foot.shape:
                row["error"] = f"shape {arr.shape}"
                rows.append(row)
                continue
        mask = np.isfinite(arr) & (arr > 0) & ctx.foot
        hr = holdout.evaluate_hide_and_recover(mask, ctx, b_visible_px=B_VISIBLE_PX, name=e["file"])
        sg = holdout.evaluate_sgmc_with_ci(mask, ctx, name=e["file"])
        row.update({
            "sha256": sha256_file(path),
            "dots_in_footprint": int(mask.sum()),
            "hide_recover_dti": round(hr["pooled_dti"], 6),
            "hide_recover_ci95": [round(v, 6) for v in hr["ci95_cluster_bootstrap"]],
            "n_withheld_positives": hr["n_withheld_positives"],
            "sgmc_raw_dti": round(sg["sgmc_raw_pooled_dti"], 6),
            "sgmc_calibrated_dti": round(sg["sgmc_prevalence_calibrated_dti"], 6),
            "sgmc_calibrated_ci95": [round(v, 6) for v in sg["sgmc_calibrated_ci95"]],
        })
        rows.append(row)
        print(f"{e['site']:9s} {e['owner_reported_score']:.4f}  HR={row['hide_recover_dti']:.6f}  "
              f"SGMC_cal={row['sgmc_calibrated_dti']:.6f}  dots={row['dots_in_footprint']}  {e['file']}", flush=True)

    ok = [r for r in rows if "error" not in r]
    y = np.array([r["owner_reported_score"] for r in ok], dtype=float)
    conc = {}
    for key in ("hide_recover_dti", "sgmc_calibrated_dti", "sgmc_raw_dti"):
        x = np.array([r[key] for r in ok], dtype=float)
        rho, ci = spearman_ci(x, y)
        conc[key] = {"spearman_rho_vs_owner_score": round(rho, 4), "bootstrap_ci95": ci, "n": len(ok)}

    out = {
        "schema_version": 1,
        "label_scores": "OWNER-REPORT (task-prompt list; not organizer receipts)",
        "label_proxies": "HOLDOUT-DTI (shared evaluator gems32.holdout; GEMSDOE32-HIDE-RECOVER-v3.0 with B_visible=2 px; GEMSDOE32-SGMC-CAL-v3.0)",
        "b_visible_px": B_VISIBLE_PX,
        "concordance": conc,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(conc, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
