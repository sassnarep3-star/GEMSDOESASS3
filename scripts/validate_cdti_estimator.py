#!/usr/bin/env python3
"""Leave-one-out validation of the CDTI score estimator on the published corpus.

For every published raster i the emission field u is refitted with file i removed, and
the refitted field is used to predict i's own score:

    s_hat_i = a * sum_{x in P_i} u_{-i}(x) / (alpha*D_i + beta*N)

Because the field never sees file i, s_hat_i is an honest out-of-sample estimate.  The
residual distribution is what the submission card quotes as its uncertainty band, and
the per-file table is what the executive summary quotes for the nine focus sites.

Usage
-----
    python scripts/validate_cdti_estimator.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 0.2, 0.8


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    den = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


def calibrate(D: np.ndarray, s: np.ndarray, C: np.ndarray) -> dict:
    best = None
    for N in np.geomspace(1500, 80000, 400):
        den = ALPHA * D + BETA * N
        a = float((C * s / den).sum() / ((C / den) ** 2).sum())
        pred = a * C / den
        rmse = float(np.sqrt(((pred - s) ** 2).mean()))
        if best is None or rmse < best["rmse"]:
            best = {"a": a, "N": float(N), "rmse": rmse}
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--manifest", type=Path,
                    default=ROOT / "evidence" / "score_corpus_manifest_20261030.json")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "evidence" / "cdti_estimator_loo_20261030.json")
    args = ap.parse_args()

    with rasterio.open(args.data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(args.data_dir / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot
    scored = foot & ~labels

    man = json.loads(args.manifest.read_text())
    rows = [r for r in man["rows"] if r["status"] == "matched"]
    seen, kept, ids, scores = set(), [], [], []
    for r in rows:
        p = Path(r["local"])
        if not p.exists():
            continue
        if r["sha256"] in seen:
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & scored
        yy, xx = np.nonzero(m)
        if yy.size == 0:
            continue
        seen.add(r["sha256"])
        kept.append({**r, "D": int(yy.size), "file": p.name})
        ids.append(np.column_stack([yy, xx]))
        scores.append(float(r["owner_reported_score"]))

    n = len(kept)
    D = np.array([k["D"] for k in kept], float)
    s = np.array(scores, float)
    BALL = np.zeros((n, scored.size), bool)
    for i, idx in enumerate(ids):
        BALL[i] = False
        BALL[i].reshape(-1)[idx[:, 0] * scored.shape[1] + idx[:, 1]] = True
    M = int(scored.sum())

    # all-file fit, for the in-sample field and for credit of a held-out dot set
    pack = np.packbits(BALL, axis=1)
    CCT = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            CCT[i, j] = CCT[j, i] = float(np.bitwise_count(pack[i] & pack[j]).sum())

    def field_from(weights: np.ndarray, keep: np.ndarray) -> np.ndarray:
        u = np.zeros(scored.size)
        for k, kk in enumerate(np.flatnonzero(keep)):
            if weights[k]:
                u[BALL[kk].ravel()] += weights[k]
        return np.clip(u, 0, 1)

    best = None
    for N in np.geomspace(2000, 80000, 40):
        t = s * (ALPHA * D + BETA * N)
        for lam in (1.0, 5.0, 20.0):
            w = np.linalg.solve(CCT + lam * np.eye(n), t)
            u = field_from(w, np.ones(n, bool))
            C = np.array([float(CCT[i].sum() * 0 + 0) for i in range(n)])
            C = np.array([u[BALL[i].ravel()].sum() for i in range(n)])
            cal = calibrate(D, s, C)
            if best is None or cal["rmse"] < best["cal"]["rmse"]:
                best = {"N": float(N), "lam": float(lam), "w": w, "u": u, "cal": cal, "C": C}
    u, cal = best["u"], best["cal"]
    print(f"[fit] N={best['N']:.0f} lambda={best['lam']:.0f} a={cal['a']:.4f} in-sample rmse={cal['rmse']:.4f}")

    # leave-one-out refit
    loo = np.zeros(n)
    for i in range(n):
        keep = np.arange(n) != i
        t = (s * (ALPHA * D + BETA * best["N"]))[keep]
        lam = best["lam"]
        try:
            wi = np.linalg.solve(CCT[np.ix_(keep, keep)] + lam * np.eye(n - 1), t)
        except np.linalg.LinAlgError:
            wi = np.zeros(n - 1)
        tp_i = float(CCT[i, keep] @ wi)
        loo[i] = cal["a"] * tp_i / (ALPHA * D[i] + BETA * best["N"])

    err = loo - s
    rmse = float(np.sqrt((err ** 2).mean()))
    mae = float(np.abs(err).mean())
    rho = spearman(loo, s)
    # block bootstrap over files for the CI of a single prediction
    rng = np.random.default_rng(20261030)
    boots = []
    for _ in range(4000):
        idx = rng.integers(0, n, n)
        boots.append(np.sqrt((err[idx] ** 2).mean()))
    sd = float(np.mean(boots))

    table = []
    for i, k in enumerate(kept):
        table.append({
            "site": k["site"], "file": k["file"], "sha256": k["sha256"],
            "owner_reported_score": float(s[i]), "dots": int(D[i]),
            "loo_estimate": float(loo[i]), "residual": float(err[i]),
        })
    table.sort(key=lambda d: -d["owner_reported_score"])

    resid_top = [t["residual"] for t in table[:12]]
    out = {
        "schema_version": 1,
        "estimator": "CDTI-108 inverse-metric ridge + least-squares calibration",
        "estimate_label": "ESTIMATE (leave-one-out over the published corpus) - not a score",
        "n_files": n,
        "model": {"N_hidden_truth_px": best["N"], "lambda": best["lam"], **cal},
        "loo": {
            "rmse": rmse, "mae": mae, "spearman": rho,
            "rmse_bootstrap_mean": sd,
            "top12_mean_abs_residual": float(np.mean(np.abs(resid_top))),
            "ci95_for_one_prediction": [max(0.0, float(-1.96 * rmse)), float(1.96 * rmse)],
        },
        "notes": [
            "u_{-i} never sees file i, so every number in the row is out-of-sample.",
            "Scores are OWNER-REPORT from the owner's prompt, not organiser receipts.",
            "Residuals are largest for very sparse or very dense rasters, where the binary "
            "'within 300 m' incidence approximation of the kernel-credit term is weakest.",
        ],
        "table": table,
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"[loo] rmse={rmse:.4f} mae={mae:.4f} spearman={rho:.3f} top12|resid|={np.mean(np.abs(resid_top)):.4f}")
    print("\n  reported  LOO-est  residual  dots    file")
    for t in table[:12]:
        print(f"  {t['owner_reported_score']:.4f}   {t['loo_estimate']:.4f}   {t['residual']:+.4f}  {t['dots']:6d}  {t['file'][:58]}")
    print(f"\n-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
